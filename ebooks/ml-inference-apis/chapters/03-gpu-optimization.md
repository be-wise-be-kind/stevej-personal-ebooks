# Chapter 3: GPU Optimization & Cold Starts

![Chapter 3 Opener](../assets/ch03-opener.html)

\newpage

## Overview

A GPU is, at its core, a massively parallel arithmetic engine. Where a CPU has a handful of powerful cores optimized for sequential logic, a GPU has thousands of smaller cores designed to execute the same operation across many data elements simultaneously. Neural network inference is fundamentally matrix multiplication: input activations multiplied by weight matrices, layer after layer. GPUs can perform these matrix multiplications across an entire batch of inputs in the time a CPU would spend on a single one. This is why inference infrastructure is built around GPUs, and why their cost dominates the serving budget.

Yet most organizations dramatically underutilize the GPUs they are paying for. The hardware is capable of processing thousands of requests per second, but the serving stack often keeps it idle for most of its time: waiting for requests to arrive, waiting for memory transfers, waiting for the slowest sequence in a batch to finish. At $1.50-$7 per hour for an inference-grade GPU [Source: AWS, 2025; RunPod, 2025], even 50% idle time doubles the effective per-request cost. The difference between a serving stack that burns money and one that delivers low-latency inference at sustainable cost comes down to the techniques in this chapter.

We cover the full GPU optimization stack: batching strategies that keep the GPU fed, KV cache management that prevents the memory bottleneck from throttling throughput, cold start mitigation that eliminates the minutes-long penalty of bringing new instances online, quantization techniques that trade precision for capacity, attention kernels that squeeze more FLOPS from the hardware, and speculative decoding that accelerates autoregressive generation. Each technique addresses a different bottleneck, and the most effective serving stacks apply them in combination.

## Why GPUs Sit Idle

### The Utilization Problem

The simplest possible inference setup dedicates one GPU to one request at a time. The request arrives, the GPU performs a forward pass in microseconds to milliseconds, the result is returned, and the GPU waits for the next request. During that wait, thousands of CUDA cores sit idle. Even under moderate traffic, this approach wastes 90% or more of available compute [Source: BentoML, 2025].

The waste has two primary sources. First, most inference workloads are *memory-bandwidth limited*, not compute limited. The GPU's arithmetic units can multiply matrices far faster than the memory bus can deliver the weight data to those units. The result is that the compute cores frequently stall, waiting for the next chunk of weights to arrive from High Bandwidth Memory (HBM). Second, request arrival patterns are bursty. Real-world traffic comes in spikes followed by lulls, and a GPU sized for peak load sits largely idle during off-peak periods.

The economic consequence is direct. If a team provisions ten H100 GPUs at $3.50 per hour each and utilizes them at 30%, the effective cost per useful compute-hour is $11.67, not $3.50. Every optimization technique in this chapter works toward the same goal: pushing that utilization number higher.

### Measuring GPU Utilization

Before optimizing, we need to measure. Several metrics capture different aspects of GPU utilization:

**SM (Streaming Multiprocessor) occupancy** measures the percentage of GPU cores actively executing work. This is the primary compute utilization metric. Low SM occupancy with high traffic indicates that the serving stack is not batching effectively or that the workload is memory-bound.

**Memory bandwidth utilization** measures how much of the GPU's memory bus capacity is being used to transfer weights and activations. High bandwidth utilization with low SM occupancy confirms a memory-bound workload, where the bottleneck is data transfer rather than computation.

**GPU memory utilization** measures how much of the GPU's HBM is allocated. High memory utilization does not imply high compute efficiency; a fully loaded KV cache can fill memory while the GPU's compute units remain mostly idle.

The key monitoring tools are NVIDIA DCGM (Data Center GPU Manager) for detailed telemetry, `nvidia-smi` for quick spot-checks, and Prometheus exporters for GPU metrics that feed into standard observability stacks. A common gap: these exporters (DCGM-exporter, node-exporter, cAdvisor) must be explicitly deployed alongside inference workloads. Dashboard queries for GPU utilization, temperature, and memory pressure return "no data" silently if the exporters are missing. Teams mistake empty panels for "no problems" rather than "no data." Verify that your exporters are running and that your dashboard queries match the metric names they emit before trusting the output. The goal of measurement is not just a utilization number; it is a diagnosis of *which* bottleneck limits throughput: compute, memory bandwidth, or simply idle time between requests.

## Dynamic and Continuous Batching

### Static Batching: The Baseline

The simplest batching strategy collects N requests, processes them together as a single batch, and returns all results once the entire batch completes. This is static batching, and it was the default approach in first-generation serving frameworks.

The problem is structural. In a batch of sequences with varying lengths, every sequence must wait for the longest one to finish. Short sequences that complete early are padded with wasted compute while the batch waits for the straggler. A batch containing one 2,048-token sequence and seven 50-token sequences processes at the speed of the 2,048-token sequence. The seven short sequences could have been returned orders of magnitude sooner.

Static batching remains acceptable for offline and batch workloads where latency is not a constraint. For real-time serving, it is inadequate.

### Dynamic Batching

Dynamic batching improves on static batching by collecting incoming requests within a configurable time window (typically 10-50 milliseconds), forming a batch from whatever has arrived, and executing that batch together. Requests that arrive during execution wait for the next batch cycle.

This is a meaningful improvement: the GPU processes multiple requests per batch cycle without requiring all requests to arrive simultaneously. Triton Inference Server's dynamic batcher is the canonical implementation for general ML models. The trade-off is tuning the time window: too short and batches are small, underutilizing the GPU; too long and requests queue unnecessarily, adding latency.

### Continuous Batching

Continuous batching is the key innovation that unlocked high-throughput LLM serving. The insight is simple: do not wait for the entire batch to finish before accepting new work. Instead, evict completed sequences immediately and insert new ones at every decode step.

In autoregressive generation, the model produces one token per forward pass. With continuous batching, each forward pass can operate on a different set of active sequences. A sequence that finishes its generation is removed, and a new request from the queue takes its slot in the very next iteration. The GPU is never waiting for a straggler because there is no batch-level completion; there is only a continuous stream of token-level work.

The throughput improvement is substantial. Continuous batching delivers 2-4x throughput improvement over static batching at equivalent latency [Source: vLLM, 2023; Stixor, 2025]. This is now table stakes for LLM serving: vLLM, SGLang, and TensorRT-LLM all implement continuous batching as their default scheduling strategy.

The scheduler operates at the *iteration level*, making decisions about which sequences to include in each forward pass. This iteration-level scheduling is what distinguishes continuous batching from dynamic batching: the granularity of scheduling shifts from the request level to the individual token generation step.

![Batching Comparison](../assets/ch03-batching-comparison.html)

\newpage

### Tuning Batching Parameters

Even with continuous batching, configuration matters. The key parameters are:

**Maximum batch size** determines how many sequences can be active simultaneously. Larger batches increase throughput but add latency to individual requests because each forward pass does more work. The right value depends on your latency SLO: if p99 latency must stay under 200ms, the batch size must be small enough that a single forward pass completes within that budget.

**Prefill vs decode scheduling** addresses a fundamental asymmetry. Prefill (processing the full input prompt) is compute-heavy: it processes all input tokens in a single forward pass. Decode (generating output tokens one at a time) is memory-bandwidth-heavy: each step reads the full KV cache but produces only one token. Some runtimes schedule prefill and decode on separate GPU resources, or use chunked prefill to interleave prefill work into decode batches without causing latency spikes.

**Monitoring batch sizes over time** reveals whether the batching configuration matches actual traffic patterns. If batches consistently hit the maximum, the GPU is saturated and throughput can be increased with more replicas. If batches are consistently small, the GPU is underutilized and resources are being wasted.

## KV Cache: The Central Bottleneck

### Why KV Cache Matters

Transformer models compute attention over all previous tokens at each generation step. Without caching, the model would recompute the key and value projections for every prior token at every step, an O(N²) cost that makes long-sequence generation prohibitively slow. The KV cache stores these intermediate results: the key (K) and value (V) tensors for each layer and each token that has been processed. With the cache, each new token only needs to compute attention against the stored keys and values, reducing the per-step cost to O(N).

The problem is that KV cache size grows linearly with sequence length and batch size, and for modern long-context models, it can dwarf the model weights themselves. A 70 billion parameter model at FP16 requires approximately 140 GB for its weights (70B parameters × 2 bytes per parameter). The KV cache for a 128K-token context window can add tens of gigabytes *per sequence* on top of that. When serving multiple concurrent users, KV cache memory can easily exceed model weight memory.

The industry consensus is clear: the winners in inference serving are the runtimes that treat KV cache as a first-class data structure, with sophisticated allocation, sharing, quantization, and eviction strategies [Source: Stixor, 2025]. Every technique in this section addresses a different dimension of the KV cache bottleneck.

### PagedAttention

The foundational innovation in KV cache management is PagedAttention, introduced by vLLM in 2023 [Source: Kwon et al., 2023]. The insight comes directly from operating systems: treat KV cache like virtual memory.

Traditional KV cache allocation reserves a contiguous block of GPU memory for each sequence, sized to the *maximum possible* sequence length. If a model supports 128K tokens but the average request uses only 2K tokens, the remaining 126K tokens worth of memory is allocated but unused. Across a batch of concurrent sequences, this over-allocation wastes 60-80% of available KV cache memory [Source: Kwon et al., 2023].

PagedAttention eliminates this waste by allocating fixed-size blocks (pages) on demand, rather than reserving contiguous memory upfront. As a sequence grows, new pages are allocated. When a sequence completes, its pages are immediately reclaimed and made available to other sequences. Pages for a single sequence need not be physically contiguous in memory; a page table maps logical token positions to physical memory locations.

The result is dramatic: PagedAttention reduces KV cache memory waste to less than 4%, compared to 60-80% with traditional allocation [Source: Kwon et al., 2023]. This directly translates to higher concurrency: the same GPU memory can serve more simultaneous sequences, which means more throughput at the same hardware cost.

Pioneered by vLLM, PagedAttention has been adopted or adapted by SGLang, TensorRT-LLM, and most other Gen 3 serving engines. It is no longer a competitive advantage; it is a prerequisite.

![KV Cache Paging](../assets/ch03-kv-cache-paging.html)

\newpage

### KV Cache Quantization

If PagedAttention reduces waste in how memory is allocated, KV cache quantization reduces the amount of memory each token requires in the first place. Rather than storing keys and values at FP16 (2 bytes per element), quantized KV caches use lower precision formats.

NVIDIA's NVFP4 KV cache quantization reduces memory consumption by 50% compared to FP8, with less than 1% accuracy degradation on standard benchmarks [Source: NVIDIA, 2025]. The memory savings compound with batch size: halving the per-token KV cache footprint allows doubling the number of concurrent sequences on the same GPU, directly increasing throughput.

The trade-off is quality. While NVFP4 shows minimal degradation on general benchmarks, the impact on specific tasks varies. Calibration and evaluation on your production workload are required before deploying quantized KV caches.

### KV Cache Reuse (Prefix Caching)

Many inference workloads share common prefixes across requests. In a chat application, every message includes the same system prompt. In RAG (Retrieval Augmented Generation), the retrieved context documents change but the instructions are identical. In few-shot prompting, the examples are the same across requests.

Prefix caching exploits this redundancy. If multiple requests share an identical prefix, the KV cache for that prefix is computed once and reused across all subsequent requests. SGLang's RadixAttention organizes cached prefixes in a radix tree data structure, enabling efficient lookup, insertion, and sharing across concurrent requests [Source: LMSYS, 2024].

The savings are substantial. For prefix-heavy workloads, prefix caching can reduce prefill computation by 50-90%, depending on the ratio of shared prefix length to total sequence length [Source: LMSYS, 2024; BentoML, 2025]. This translates directly to lower time-to-first-token (TTFT) and higher throughput, because the GPU skips the most expensive phase of processing for the majority of requests.

### KV Cache Offloading

When GPU memory is exhausted, KV cache offloading provides an escape valve. The idea is hierarchical storage: hot sequences (actively generating tokens) keep their KV cache on GPU memory, warm sequences (recently active but paused) are offloaded to CPU memory, and cold sequences (idle for longer periods) can be offloaded to NVMe storage.

The trade-off is latency. When an offloaded sequence becomes active again, its KV cache must be transferred back to GPU memory, adding hundreds of milliseconds to seconds of delay depending on the cache size and the storage tier. Offloading is best suited for long-running sessions with variable activity, such as conversational agents where users pause between messages.

## Cold Start Anatomy

### What Happens During a Cold Start

A cold start occurs whenever a new inference instance must be brought online from scratch: a fresh deployment, an auto-scaling event, a recovery from failure. The sequence of operations explains why cold starts are so painful for ML workloads.

**Container pull** starts the process. The container image must be downloaded from a registry and started. For ML inference containers, which often include large framework dependencies, this alone can take seconds to tens of seconds depending on image size and network bandwidth.

**Runtime initialization** follows. The Python interpreter starts, CUDA drivers are loaded, CUDA context is created for each GPU, and libraries like cuBLAS and cuDNN are initialized. This phase typically takes 4-30 seconds depending on the framework and hardware [Source: Tensorfuse, 2025].

**Model loading** is the dominant cost. Model weights must be transferred from storage (object storage like S3, a network filesystem, or local NVMe) to GPU memory. For a 15 GB model (Llama 3 8B), this takes 23-35 seconds; for a 130 GB model (Llama 2 70B), approximately 127 seconds [Source: NVIDIA, 2025]. The bottleneck is storage throughput: even with high-bandwidth storage, transferring hundreds of gigabytes takes time.

**Warm-up inference** is the final step. The first inference pass is slower than steady-state because CUDA kernels must be compiled or JIT-optimized, and CUDA graphs may need to be captured. Running a dummy inference pass during startup absorbs this penalty before real traffic arrives.

Total cold start ranges from 30 seconds for smaller models with optimized pipelines to several minutes for large models loaded from remote storage [Source: NVIDIA, 2025; Tensorfuse, 2025].

![Cold Start Anatomy](../assets/ch03-cold-start-anatomy.html)

\newpage

### Why Cold Starts Are Worse for ML

To appreciate the severity, compare ML inference cold starts to traditional application cold starts. A web server written in Go or Rust starts in tens of milliseconds. A Java application server starts in a few seconds. An ML inference server serving a 70B parameter model starts in minutes.

The disparity comes from model size. A 70B parameter model at FP16 is approximately 140 GB (70 billion parameters × 2 bytes per parameter). This is orders of magnitude larger than any typical application binary. Every byte must be transferred to GPU memory, and GPU memory allocation is not as simple as a `malloc`: the runtime must find or create contiguous memory blocks, which may require defragmentation.

Multi-GPU models multiply the cost. A model distributed across 4 GPUs via tensor parallelism requires 4 separate CUDA context initializations and 4 separate weight transfers. The transfers cannot always proceed fully in parallel due to NVLink bandwidth constraints and coordination overhead.

The implication for auto-scaling is severe. When a traffic spike triggers a scale-up event, every new instance pays the full cold start penalty. During those minutes, the existing instances absorb the entire load spike, potentially degrading latency for all users. Cold start mitigation is not a nice-to-have; it is a prerequisite for reliable auto-scaling.

## Cold Start Mitigation

Four strategies address cold starts, each with different trade-offs between cost, complexity, and latency reduction.

### Pre-Warming

Pre-warming loads models and runs dummy inference passes during a startup grace period, before the instance accepts traffic. Kubernetes readiness probes are the standard mechanism: the pod is marked as ready only after the model is loaded, the CUDA context is initialized, and a warm-up inference completes successfully. Until then, the load balancer routes no traffic to the pod.

This does not reduce the cold start duration itself. It hides the cold start from users by ensuring that no request is routed to an instance that is not fully prepared. The trade-off is longer startup time: the instance consumes GPU resources during the warming period without serving any production traffic.

### Model Caching

Model caching eliminates the storage transfer bottleneck by keeping model weights on fast local storage rather than downloading from object storage on every start. Three approaches exist:

**Local NVMe caching** stores model weights on the instance's local SSD. After the first download, subsequent starts load from local disk at NVMe speeds (3-7 GB/s) rather than network speeds.

**Container image baking** includes model weights directly in the container image. This creates very large images (140+ GB for a 70B model) but guarantees that weights are available immediately on container start, with no separate download step.

**Shared filesystem caching** uses network-attached storage (EFS, Lustre, FSx) to cache models across instances. Multiple instances on the same node or in the same availability zone share a single cached copy.

### Persistent GPU Pools

The most direct mitigation is to never scale to zero. Maintaining a pool of GPU instances with models pre-loaded, even during low-traffic periods, ensures that cold starts only occur when scaling *up*, not when serving the first request of the day.

The cost trade-off is explicit: you pay for idle GPUs during off-peak hours to avoid the latency penalty of cold starts. For latency-sensitive endpoints, this is usually the right decision. A hybrid approach combines a persistent pool for baseline traffic with auto-scaled instances for burst capacity, accepting that burst capacity has higher initial latency.

### Snapshot and Restore

Snapshot and restore captures the state of a fully initialized inference process (CUDA context, loaded model weights, compiled kernels) and restores it on new instances without repeating the initialization sequence.

CRIU (Checkpoint/Restore In Userspace) checkpoints the entire process state, including GPU memory, and restores it on a new container. NVIDIA's CUDA checkpoint APIs provide GPU-aware checkpointing that captures GPU memory state directly. The result can reduce cold starts from minutes to seconds: the new instance resumes from a pre-initialized state rather than reinitializing from scratch.

This technique is still maturing in production. Reliability across different GPU instances and portability of snapshots between hardware configurations are active challenges. But for teams with the infrastructure to support it, snapshot and restore offers the most dramatic cold start reduction.

## Quantization for Inference

### The Precision Spectrum

Quantization reduces the numerical precision of model weights and activations, trading a controlled amount of accuracy for reduced memory usage and increased throughput. The spectrum ranges from full precision to aggressively compressed formats:

**FP32** (32-bit floating point, 4 bytes per parameter) is training precision. Rarely used for inference due to memory cost.

**FP16 / BF16** (16-bit, 2 bytes per parameter) is the baseline for inference. BF16 (brain float) preserves the dynamic range of FP32 with reduced mantissa precision, making it more numerically stable for some workloads.

**FP8** (8-bit, 1 byte per parameter) halves memory versus FP16 and doubles throughput on hardware with native FP8 support. Two formats exist: E4M3 (higher precision) and E5M2 (higher dynamic range).

**FP4 / INT4** (4-bit, 0.5 bytes per parameter) quarters memory versus FP16 (a 75% reduction). The most aggressive compression that maintains usable model quality.

Each step down the precision ladder roughly halves memory usage and can increase throughput, but the quality impact varies by model, task, and the specific quantization technique applied.

### FP8: The Production Standard

FP8 has emerged as the standard precision for production LLM inference. It is stable for production deployment with proper calibration, offering significant speed, throughput, and memory improvements over FP16 [Source: Stixor, 2025].

The hardware story is compelling. NVIDIA H100 (Hopper) GPUs include native FP8 tensor cores that execute FP8 operations at twice the throughput of FP16 operations. NVIDIA B200 (Blackwell) GPUs continue this support and add native FP4. The software ecosystem has followed: vLLM, SGLang, and TensorRT-LLM all support FP8 inference out of the box.

Calibration is the critical step. FP8 quantization requires running a representative set of inputs through the model to determine optimal per-tensor or per-channel scaling factors. These scaling factors map the FP16 value range to the smaller FP8 range with minimal information loss. Poor calibration (using non-representative data) leads to subtle quality degradation that may not appear in general benchmarks but surfaces in production on specific input distributions.

Most production LLM deployments in 2025-2026 have standardized on FP8 as the default inference precision [Source: Stixor, 2025].

### FP4 and INT4: The Frontier

FP4 reduces model memory by 75% compared to FP16 (0.5 bytes versus 2 bytes per parameter), making 70B+ models feasible on a single GPU with 80 GB of memory. NVIDIA's NVFP4 format targets Blackwell architecture with native hardware support [Source: NVIDIA, 2025].

INT4 quantization (via techniques like GPTQ and AWQ) provides similar compression using integer arithmetic. INT4 has a longer track record and broader tooling support, but FP4's floating-point representation handles outlier weights more gracefully.

The quality degradation at 4-bit precision is measurable. On general LLM benchmarks, NVFP4 shows less than 1% accuracy degradation [Source: NVIDIA, 2025]. But benchmark results do not guarantee production quality. A medical transcription model quantized to INT4 may produce errors that are unacceptable in clinical settings, even if its perplexity score is nearly unchanged. The precision-to-risk mapping must match the deployment context.

FP4 and INT4 are best suited for cost-sensitive deployments where the memory savings justify the quality trade-off, edge inference where GPU memory is limited, or as draft models in speculative decoding (discussed below) where occasional errors are corrected by the full-precision verifier.

![Quantization Tradeoffs](../assets/ch03-quantization-tradeoffs.html)

\newpage

### Quantization Best Practices

Quantization is not a fire-and-forget optimization. Five practices distinguish successful production deployments from problematic ones.

**Benchmark on your actual evaluation set.** Generic benchmarks (MMLU, HellaSwag) measure general capability. Your production workload has specific input distributions, output requirements, and error tolerances. A model that scores well on MMLU at INT4 may perform poorly on domain-specific medical terminology or code generation.

**Use task-specific metrics.** For ASR, measure Word Error Rate (WER). For LLMs, measure perplexity and downstream task accuracy. For code generation, measure pass@k. The metric must capture what matters for your use case.

**Calibrate on representative data.** The calibration dataset should match your production traffic distribution. If your production workload is 80% customer service conversations and 20% technical documentation, the calibration dataset should reflect that ratio.

**Consider mixed-precision approaches.** Not all layers are equally sensitive to quantization. Attention layers often tolerate lower precision better than feed-forward layers. Mixed-precision quantization applies different precision levels to different layers based on sensitivity analysis, achieving better quality at the same average bit width.

**Monitor quality in production.** A/B test quantized models against full-precision baselines with real traffic. Quality degradation can be subtle and input-dependent; only production monitoring catches issues that offline evaluation misses.

## Attention Optimization

### FlashAttention-3

Standard attention computation has O(N²) memory complexity: it materializes the full N × N attention matrix, which becomes prohibitive for long sequences. FlashAttention reimagines this computation by tiling the attention calculation into blocks that fit in GPU SRAM (on-chip memory), avoiding the need to ever materialize the full matrix in HBM.

FlashAttention-3, optimized for NVIDIA Hopper (H100) architecture, achieves 1.5-2x speedup over FlashAttention-2, reaching up to 740 TFLOPS on FP16, approximately 75% utilization of the H100's theoretical maximum [Source: Dao et al., 2024]. The key technique is warp specialization: overlapping computation with memory access using asynchronous CUDA operations, so the GPU is computing one tile while loading the next.

FlashAttention-3 is now integrated into vLLM, SGLang, and TensorRT-LLM as the default attention kernel on Hopper GPUs. For serving teams, this is not a tunable; it is a foundation that the serving engine handles automatically.

### FlashAttention-4

FlashAttention-4 targets NVIDIA Blackwell (B200) architecture, achieving up to 22% improvement over NVIDIA's cuDNN attention baseline and reaching 1,605 TFLOPS, approximately 71% of Blackwell's theoretical maximum [Source: ASCII News, 2026; Modal, 2026]. It leverages Blackwell-specific hardware features including larger shared memory and new tensor core instructions.

For teams currently on Hopper hardware, FlashAttention-3 remains the right choice. FlashAttention-4 is relevant for hardware planning and for teams deploying on Blackwell GPUs.

### Multi-Head vs Grouped-Query vs Multi-Query Attention

The attention mechanism itself has evolved to reduce KV cache pressure:

**Multi-Head Attention (MHA)** gives each attention head its own set of key and value projections. This provides the highest representational capacity but the largest KV cache footprint, since every head stores its own K and V tensors.

**Grouped-Query Attention (GQA)** shares key-value projections across groups of attention heads. If a model has 32 attention heads grouped into 8 KV groups, the KV cache is 4x smaller than MHA while retaining most of MHA's quality. GQA has become the default architecture for new model families including Llama 3 and Mistral.

**Multi-Query Attention (MQA)** takes this to the extreme: all attention heads share a single set of key-value projections. This minimizes the KV cache but can degrade quality on complex reasoning tasks.

For serving engineers, the attention architecture is determined by the model, not by the serving stack. But understanding the implications matters for capacity planning: a GQA model requires significantly less KV cache memory per sequence than an equivalent MHA model, which directly affects how many concurrent requests a GPU can handle.

## Speculative Decoding

### How It Works

Autoregressive generation is inherently sequential: each token depends on the previous one, and the model produces one token per forward pass. For large models, each forward pass is expensive. Speculative decoding breaks this bottleneck by using a fast, lightweight "draft" model to speculate multiple tokens ahead.

The process works in three steps. First, a small draft model (typically 5-10x smaller than the target model, such as Llama 3 1B drafting for Llama 3 70B) generates N candidate tokens quickly. Second, the full target model validates all N tokens in a single forward pass, which is nearly as fast as validating one token because the computation parallelizes across the sequence. Third, the target model accepts tokens that match its own distribution and rejects tokens that diverge.

The key property is *no quality loss*. The target model has final say on every token. The output distribution is mathematically identical to what the target model would produce on its own. Speculative decoding does not approximate; it accelerates.

### When to Use Speculative Decoding

Speculative decoding is most effective when the draft model has a high acceptance rate, meaning it correctly predicts what the target model would generate. This works best for predictable text: code generation, structured output (JSON, XML), form-filling, and template-based content. For these workloads, acceptance rates of 70-90% are achievable, yielding significant latency reduction.

The technique is less effective for highly creative or unpredictable generation (open-ended conversation, creative writing) where the draft model frequently guesses wrong. When acceptance rates drop below 50%, the overhead of running the draft model can exceed the benefit.

### Practical Considerations

Speculative decoding requires hosting two models simultaneously: the target model and the draft model. The draft model's memory overhead is modest (a 1B draft model adds only a few GB at FP8), but it consumes some GPU compute that would otherwise be available for the target model.

Several variations reduce this overhead:

**Tree-based speculative decoding** generates multiple candidate continuations as a tree rather than a single sequence, then validates the entire tree in one pass. This increases the probability that at least one branch matches the target model's preference.

**Medusa heads** add lightweight prediction heads directly to the target model, eliminating the need for a separate draft model entirely. The prediction heads are small enough that their overhead is negligible.

**Self-speculative decoding** uses early-exit layers of the target model itself as the draft predictor. If the model's intermediate layers can predict the final output with reasonable accuracy, no separate model is needed.

## Right-Sizing GPU Instances

### Cost vs Latency Trade-offs

GPU selection involves a fundamental tension between per-hour cost and per-request cost. Larger GPUs (H100, B200) cost more per hour but can serve more concurrent requests, which means the per-request cost decreases as utilization increases. Smaller GPUs (A10G, L4) are cheaper per hour but may require more instances for the same aggregate throughput.

The right analysis is total cost at your expected traffic patterns. A single H100 at $3.50/hour serving 100 requests per second costs $0.035 per 1,000 requests. Four L4s at $0.50/hour each, collectively serving the same 100 requests per second, cost $0.020 per 1,000 requests, cheaper but with four times the operational overhead of managing separate instances.

Spot and preemptible instances offer 60-90% savings over on-demand pricing [Source: AWS, 2025]. For batch inference workloads, spot instances are compelling: the workload is fault-tolerant and can be retried if the instance is reclaimed. For real-time serving, spot instances add risk: an instance reclamation during an active audio transcription session drops the connection. Hybrid approaches use on-demand instances for the persistent baseline pool and spot instances for burst capacity, accepting occasional failures on the burst tier.

### GPU Selection Framework

Three factors determine the minimum GPU requirement:

**Model memory** is the floor. The model weights, KV cache for the target concurrency, and activation memory must all fit in GPU memory simultaneously. A 70B model at FP8 requires approximately 70 GB for weights alone. Add KV cache for 32 concurrent sequences with 4K context, and the total easily exceeds 80 GB, requiring either a B200 (192 GB HBM3e) or multi-GPU tensor parallelism across H100s (80 GB HBM3 each) [Source: NVIDIA, 2025].

**Throughput requirements** determine whether a single GPU suffices or whether multiple GPUs or instances are needed. If your SLO requires 500 tokens per second and a single H100 delivers 300, you need at least two.

**Latency requirements** constrain how large batches can be and therefore how efficiently each GPU is utilized. Tighter latency budgets mean smaller batches, lower utilization per GPU, and more GPUs needed for the same throughput.

### The Hardware Trajectory

The progression from Hopper to Blackwell follows a clear pattern. Each GPU generation increases memory capacity, memory bandwidth, and compute throughput, while adding native support for lower-precision formats. The H100 introduced native FP8 tensor cores; the B200 adds native FP4 and doubles memory to 192 GB HBM3e with 8 TB/s bandwidth [Source: NVIDIA, 2025].

For serving teams, the practical implication is to optimize for current hardware while designing for the next generation. Code that assumes FP16 everywhere will not benefit from FP8 hardware. Architectures that hard-code memory limits will not scale when memory doubles. The serving stack should parameterize precision and memory allocation so that upgrading to new hardware is a configuration change, not an architecture change.

> **From Book 1:** For a deep dive on compute resource scaling patterns and cost optimization strategies, see "Before the 3 AM Alert" Chapter 9: Compute and Scaling.

## Common Pitfalls

- **Optimizing GPU utilization without a latency budget.** Maximizing throughput is meaningless if it violates latency SLOs. A batch size of 256 might push utilization to 95%, but if p99 latency jumps from 150ms to 2 seconds, users leave. Always optimize *within* latency constraints, not instead of them.

- **Skipping quantization calibration.** Deploying a quantized model without calibration on representative data leads to subtle quality degradation that does not surface in generic benchmarks but appears in production on specific input distributions. An FP8 model calibrated on English text may perform poorly on multilingual inputs.

- **Treating cold starts as a deployment-only problem.** Cold starts occur during auto-scaling events, the worst possible time: traffic is already elevated, existing instances are already loaded, and the cold-starting instance adds no capacity for 30 seconds to several minutes. Plan for cold starts as a traffic management problem, not just a deployment problem.

- **Ignoring KV cache memory in capacity planning.** Teams size their GPU instances for model weights and forget that KV cache for concurrent requests can exceed model weight memory. A 14 GB model serving 64 concurrent sequences with 8K context at FP16 may need 40+ GB of KV cache memory on top of the model weights.

- **Applying speculative decoding universally.** Speculative decoding hurts throughput when the draft model has low acceptance rates. The draft model still consumes compute and memory; if its predictions are rejected more than 50% of the time, the overhead exceeds the benefit. Measure acceptance rate on your specific workload before committing.

- **Over-quantizing safety-critical models.** INT4 quantization on a medical transcription model may produce word substitutions that are clinically dangerous, even if the model's aggregate WER is only marginally higher. Match precision to risk tolerance: FP8 for general workloads, FP16 for safety-critical ones. Chapter 12 covers SLO-driven quality thresholds in depth.

## Summary

- GPU utilization is the single biggest lever for inference cost reduction; most organizations waste 50-90% of available compute through naive serving approaches
- Continuous batching evicts completed sequences and inserts new ones at every decode step, delivering 2-4x throughput improvement over static batching and is now table stakes for LLM serving
- KV cache is the central memory bottleneck for transformer inference; PagedAttention reduces memory waste from 60-80% to under 4% by treating cache memory like virtual memory with on-demand page allocation
- KV cache quantization (NVFP4 reduces memory 50% vs FP8), prefix caching (50-90% prefill reduction for shared prefixes), and offloading provide additional memory management strategies
- Cold starts for ML models take 30 seconds to several minutes; mitigation requires pre-warming, model caching, persistent GPU pools, or snapshot and restore
- FP8 is the production standard for quantization with native hardware support on H100 and B200; FP4/INT4 are emerging for cost-sensitive workloads but require careful quality evaluation
- FlashAttention-3 delivers 1.5-2x speedup over FA-2 on Hopper GPUs (740 TFLOPS FP16); FlashAttention-4 targets Blackwell with 22% improvement over cuDNN
- Speculative decoding accelerates autoregressive generation without quality loss by using a lightweight draft model; most effective for predictable output patterns with high acceptance rates
- The hardware trajectory from Hopper (80 GB HBM3, native FP8) to Blackwell (192 GB HBM3e, native FP4) rewards serving architectures that parameterize precision and memory allocation

## References

1. **Kwon, W., et al.** (2023). "Efficient Memory Management for Large Language Model Serving with PagedAttention." *Proceedings of the ACM Symposium on Operating Systems Principles (SOSP '23)*. arXiv:2309.06180. https://arxiv.org/abs/2309.06180
2. **Dao, T., et al.** (2024). "FlashAttention-3: Fast and Exact Attention with Asynchrony and Low-Precision." arXiv:2407.08608. https://tridao.me/blog/2024/flash3/
3. **NVIDIA** (2025). "Optimizing Inference for Long Context and Large Batch Sizes with NVFP4 KV Cache." https://developer.nvidia.com/blog/optimizing-inference-for-long-context-and-large-batch-sizes-with-nvfp4-kv-cache/
4. **Stixor** (2025). "The New LLM Inference Stack 2025: FA-3, FP8 & FP4." https://www.stixor.com/blogs/new-inference-stack-2025
5. **BentoML** (2025). "LLM Inference Handbook: Static, Dynamic, and Continuous Batching." https://bentoml.com/llm/inference-optimization/static-dynamic-continuous-batching
6. **vLLM** (2023). "Easy, Fast, and Cheap LLM Serving with PagedAttention." https://blog.vllm.ai/2023/06/20/vllm.html
7. **LMSYS** (2024). "SGLang: Efficient Execution of Structured Language Model Programs." https://lmsys.org/blog/2024-01-17-sglang/
8. **NVIDIA** (2025). "Reducing Cold Start Latency for LLM Inference with NVIDIA Run:ai Model Streamer." https://developer.nvidia.com/blog/reducing-cold-start-latency-for-llm-inference-with-nvidia-runai-model-streamer/
9. **Tensorfuse** (2025). "Reducing GPU Cold Start Time with vLLM." https://tensorfuse.io/docs/blogs/reducing_gpu_cold_start
10. **AWS** (2025). "EC2 On-Demand Instance Pricing." https://aws.amazon.com/ec2/pricing/on-demand/
11. **AWS** (2025). "EC2 Spot Instances." https://aws.amazon.com/ec2/spot/
12. **NVIDIA** (2025). "NVIDIA H100 Tensor Core GPU." https://www.nvidia.com/en-us/data-center/h100/
13. **NVIDIA** (2025). "NVIDIA B200 Tensor Core GPU." https://www.nvidia.com/en-us/data-center/dgx-b200/
14. **ASCII News** (2026). "FlashAttention-4 Achieves 2.4x Speedup on Blackwell GPUs." https://ascii.co.uk/news/article/news-20260123-e5a5676f/flashattention-4-achieves-24x-speedup-on-blackwell-gpus
15. **Modal** (2026). "We Reverse-Engineered Flash Attention 4." https://modal.com/blog/reverse-engineer-flash-attention-4
16. **BentoML** (2025). "LLM Inference Handbook: Prefix Caching." https://bentoml.com/llm/inference-optimization/prefix-caching

---

**Next: [Chapter 4: Streaming Audio Architecture](./04-streaming-audio-architecture.md)**
