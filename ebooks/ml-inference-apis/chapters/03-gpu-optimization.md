# Chapter 3: GPU Optimization & Cold Starts

<!-- DIAGRAM: ch03-opener.html - Chapter 3 Opener -->

\newpage

## Overview

- GPUs are the most expensive component of inference infrastructure, and most organizations underutilize them dramatically
- This chapter covers the full optimization stack: batching, KV cache management, quantization, attention kernels, speculative decoding, and cold start mitigation
- Mastering these techniques is the difference between a serving stack that burns money and one that delivers low-latency inference at sustainable cost

## Why GPUs Sit Idle

### The Utilization Problem

- Naive one-request-per-GPU serving wastes 90%+ of available compute; the GPU finishes its work in microseconds and waits for the next request
- Memory-bound vs compute-bound: most inference workloads are memory-bandwidth limited, meaning the GPU's arithmetic units are starved while waiting for data transfer
- Request arrival patterns are bursty; traffic spikes followed by idle periods leave GPUs doing nothing between bursts
- The economic consequence: at $2-8/hr per inference-grade GPU, even 50% idle time doubles your effective per-request cost

### Measuring GPU Utilization

- SM (Streaming Multiprocessor) occupancy: percentage of GPU cores actively executing; the primary metric
- Memory bandwidth utilization: how much of the GPU's memory bus is being used for weight/activation reads
- GPU memory utilization vs GPU compute utilization; high memory usage does not mean high compute efficiency
- Monitoring tools: NVIDIA DCGM, nvidia-smi, Prometheus exporters for GPU metrics
- The goal: understand whether you are compute-bound, memory-bound, or simply idle

## Dynamic and Continuous Batching

### Static Batching: The Baseline

- Collect N requests, wait until all N complete, return all results; simple but wasteful
- Shorter sequences wait for longer ones to finish, padding the batch with wasted compute
- Throughput limited by the longest sequence in the batch; a single long request slows down the entire group
- Acceptable for batch/offline workloads where latency is not a constraint

### Dynamic Batching

- Collect incoming requests within a configurable time window (e.g., 10-50ms), form a batch, execute together
- Requests that arrive during execution wait for the next batch cycle
- Significant improvement over static batching: better utilization without requiring all requests to arrive simultaneously
- Triton Inference Server's dynamic batcher is the canonical implementation for general ML models

### Continuous Batching

- The key innovation: evict completed sequences immediately and insert new ones without waiting for the entire batch to finish
- Each token generation step can have a different set of active sequences; maximizing GPU utilization at every step
- 2-4x throughput improvement over static batching at equivalent latency [Source: BentoML, 2025]
- Now table stakes for LLM serving; vLLM, SGLang, TensorRT-LLM all implement continuous batching as their default
- Iteration-level scheduling: the scheduler makes decisions at every decode step, not at the request level

<!-- DIAGRAM: ch03-batching-comparison.html - Static vs Dynamic vs Continuous Batching -->

\newpage

### Tuning Batching Parameters

- Max batch size: larger batches increase throughput but add latency; find the sweet spot for your latency SLO
- Max wait time: how long to accumulate requests before dispatching; too short wastes GPU, too long adds queue delay
- Prefill vs decode scheduling: prefill (processing the full prompt) is compute-heavy while decode (generating tokens) is memory-heavy; some runtimes schedule these separately
- Monitoring: track batch sizes over time to understand whether your batching config matches actual traffic patterns

## KV Cache: The Central Bottleneck

### Why KV Cache Matters

- Transformer models recompute attention over all previous tokens at each step; KV cache stores these intermediate results to avoid redundant computation
- KV cache size grows linearly with sequence length and batch size, often consuming more GPU memory than the model weights themselves
- For long-context models (128K+ tokens), KV cache can require 10-100+ GB per request; dwarfing model size
- Industry consensus: the winners in inference serving are runtimes that treat KV cache as a first-class data structure [Source: Stixor, 2025]

### PagedAttention

- Insight: treat KV cache like virtual memory; allocate fixed-size blocks (pages) rather than contiguous memory per sequence
- Traditional approach allocates maximum possible sequence length upfront, wasting memory for shorter actual sequences
- PagedAttention eliminates internal fragmentation by allocating pages on demand and reclaiming them when sequences finish
- Enables near-zero memory waste; reported <4% fragmentation vs 60-80% with pre-allocated contiguous buffers [Source: vLLM paper, 2023]
- Pioneered by vLLM, now adopted or adapted by SGLang, TensorRT-LLM, and others

<!-- DIAGRAM: ch03-kv-cache-paging.html - PagedAttention and KV Cache Paging -->

\newpage

### KV Cache Quantization

- Quantize cached keys and values to lower precision (FP8, FP4) to reduce memory footprint
- NVFP4 KV cache: reduces memory consumption by 50% compared to FP8 with minimal quality degradation [Source: NVIDIA, 2025]
- Allows serving more concurrent sequences on the same GPU, directly increasing throughput
- Quality impact depends on the model; calibration and evaluation required before production deployment

### KV Cache Reuse (Prefix Caching)

- If multiple requests share a common prefix (e.g., system prompt, few-shot examples), cache the KV for that prefix and reuse it
- SGLang's RadixAttention organizes cached prefixes in a radix tree for efficient lookup and sharing
- Particularly valuable for chat and RAG workloads where system instructions are identical across requests
- Can reduce prefill computation by 50-90% for prefix-heavy workloads

### KV Cache Offloading

- When GPU memory is exhausted, offload KV cache to CPU memory or NVMe storage
- Hierarchical approach: hot sequences on GPU, warm on CPU, cold on disk
- Adds latency when offloaded sequences are needed; best for long-running sessions with variable activity
- Trade-off: more concurrent sessions vs higher tail latency for reloaded sequences

## Cold Start Anatomy

### What Happens During a Cold Start

- Container spin-up: pulling and starting the container image (seconds to minutes depending on image size and registry)
- Runtime initialization: Python interpreter, CUDA context creation, cuBLAS/cuDNN library loading (5-30 seconds)
- Model loading: transferring multi-gigabyte weights from storage to GPU memory (10-120 seconds depending on model size and storage speed)
- Warm-up inference: first inference pass is often slower due to kernel compilation, JIT optimization, and CUDA graph capture
- Total cold start: 30 seconds to several minutes for large models; completely unacceptable for real-time serving

<!-- DIAGRAM: ch03-cold-start-anatomy.html - Cold Start Anatomy -->

\newpage

### Why Cold Starts Are Worse for ML

- Model size: a 70B parameter model at FP16 is ~140GB; orders of magnitude larger than typical application binaries
- GPU memory allocation: must reserve contiguous GPU memory blocks, which may require defragmentation
- CUDA context: each GPU requires its own CUDA context initialization, and multi-GPU models multiply this cost
- Framework overhead: ML frameworks like PyTorch carry significant initialization time before any model is loaded
- Contrast with traditional services: a web server cold starts in milliseconds; an ML inference server cold starts in minutes

## Cold Start Mitigation

### Pre-Warming

- Load models and run dummy inference passes during a health check grace period before the instance accepts traffic
- Kubernetes readiness probes: only mark the pod as ready after model loading and warm-up complete
- Pre-warm CUDA graphs and JIT-compiled kernels to avoid first-request latency spikes
- Trade-off: longer startup time in exchange for consistent first-request latency

### Model Caching

- Cache model weights on local NVMe or shared filesystem (EFS, Lustre) to avoid downloading from object storage on every start
- Container image layering: bake model weights into the container image or use init containers to pre-fetch
- Model registry with local caching: download once, reuse across container restarts on the same node
- For multi-model serving, keep frequently-used models in a warm cache and evict cold models via LRU

### Persistent GPU Pools

- Maintain a pool of GPU instances with models pre-loaded, even during low-traffic periods
- Minimum replica count: never scale to zero for latency-sensitive endpoints
- The cost trade-off: paying for idle GPUs during off-peak hours vs the latency penalty of cold starts
- Hybrid approach: persistent pool for baseline traffic + auto-scaled instances for burst capacity

### Snapshot and Restore

- Capture a snapshot of the fully initialized CUDA context and loaded model, restore it on new instances
- CRIU (Checkpoint/Restore In Userspace): checkpoint the entire process state, restore on a new container
- NVIDIA's CUDA checkpoint APIs: GPU-aware checkpointing that captures GPU memory state
- Significantly reduces cold start from minutes to seconds; the new instance resumes from a pre-initialized state
- Still maturing in production: reliability and portability across GPU instances are active challenges

## Quantization for Inference

### The Precision Spectrum

- FP32 (full precision) -> FP16 (half precision) -> BF16 (brain float) -> FP8 -> FP4 -> INT8 -> INT4
- Each step roughly halves memory usage and can increase throughput, with varying quality impact
- Not all quantization is equal: weight-only quantization vs weight-and-activation quantization have different tradeoff profiles
- The trend: production inference is moving toward FP8 as the default, with FP4 emerging for cost-sensitive workloads

### FP8: The Production Standard

- FP8 (E4M3 and E5M2 formats) is now stable for production inference with proper calibration [Source: Stixor, 2025]
- Halves memory vs FP16, enabling larger batch sizes or larger models on the same GPU
- Hardware support: native FP8 tensor cores on H100 (Hopper) and B200 (Blackwell)
- Calibration: run representative inputs through the model to determine optimal scaling factors
- Most production LLM deployments in 2025-2026 use FP8 as the default precision

### FP4 and INT4: The Frontier

- NVFP4: NVIDIA's 4-bit floating point format, targeting Blackwell architecture
- INT4: integer 4-bit quantization (GPTQ, AWQ); more aggressive compression with higher quality risk
- FP4 reduces memory by 75% vs FP16, making 70B+ models feasible on a single GPU
- Quality degradation is measurable: careful evaluation on your specific task is essential before production use
- Best suited for: cost-sensitive deployments, edge inference, or as a draft model in speculative decoding

<!-- DIAGRAM: ch03-quantization-tradeoffs.html - Quantization Precision Tradeoffs -->

\newpage

### Quantization Best Practices

- Always benchmark quantized vs full-precision on your actual evaluation set; generic benchmarks are insufficient
- Use task-specific metrics: for ASR, measure Word Error Rate (WER); for LLMs, measure perplexity and downstream task accuracy
- Calibrate on representative data: the calibration dataset should match your production traffic distribution
- Layer-by-layer sensitivity: some layers tolerate aggressive quantization, others do not; mixed-precision approaches quantize selectively
- Monitor quality in production: A/B test quantized models against full-precision baselines with real traffic

## Attention Optimization

### FlashAttention-3

- 1.5-2x faster than FlashAttention-2, achieving up to 740 TFLOPS on FP16 [Source: Dao et al., 2024]
- Key technique: overlaps computation with memory access using asynchronous CUDA operations (warp specialization)
- Reduces GPU memory usage from O(N^2) to O(N) for attention computation
- Now integrated into vLLM, SGLang, and TensorRT-LLM as the default attention kernel on Hopper GPUs
- Enables longer context windows without running out of GPU memory

### FlashAttention-4

- Targeting Blackwell (B200) architecture with ~20% improvement over cuDNN baseline
- Leverages Blackwell-specific hardware features: larger shared memory, new tensor core instructions
- Expected to further push the boundary on achievable context lengths and batch sizes
- Not yet widely available; teams on Hopper hardware should use FlashAttention-3

### Multi-Head vs Grouped-Query vs Multi-Query Attention

- Multi-Head Attention (MHA): each head has its own KV; highest quality, highest memory cost
- Grouped-Query Attention (GQA): groups of heads share KV; reduces KV cache size with minimal quality loss
- Multi-Query Attention (MQA): all heads share one KV; smallest cache but may degrade quality
- GQA has emerged as the default for new model architectures (Llama 3, Mistral); practical sweet spot

## Speculative Decoding

### How It Works

- Use a lightweight "draft" model to generate N candidate tokens quickly (e.g., a 1B model drafting for a 70B model)
- The full "verifier" model validates all N tokens in a single forward pass; accepting correct tokens, rejecting incorrect ones
- If the draft model is accurate enough, you get N tokens for roughly the cost of 1 forward pass on the large model
- No quality loss: the full model has final say on every token; the output distribution is mathematically identical

### When to Use Speculative Decoding

- Most effective when the draft model has high acceptance rate; works best for predictable text (code, structured output)
- Less effective for highly creative or unpredictable generation where the draft model frequently guesses wrong
- Requires hosting two models simultaneously; adds memory overhead for the draft model
- Net benefit depends on: draft model accuracy, size ratio between draft and verifier, latency sensitivity of the workload

### Practical Considerations

- Draft model selection: same architecture family, 5-10x smaller (e.g., Llama-3 1B drafting for Llama-3 70B)
- Tree-based speculative decoding: generate multiple candidate continuations as a tree, verify the full tree in one pass
- Medusa heads: add lightweight prediction heads to the main model itself, avoiding a separate draft model entirely
- Self-speculative decoding: use early exit layers of the same model as the draft; no separate model needed

## Right-Sizing GPU Instances

### Cost vs Latency Trade-offs

- Larger GPUs (H100, B200) have higher per-hour cost but can serve more concurrent requests; lower per-request cost at high utilization
- Smaller GPUs (A10G, L4) are cheaper per hour but may require more instances for the same throughput
- The break-even analysis: model the total cost at your expected traffic patterns, not just the per-hour rate
- Spot/preemptible instances: 60-90% cost savings but require graceful handling of preemption; suitable for batch, risky for real-time

### GPU Selection Framework

- Model size determines the minimum GPU memory: model weights + KV cache + activation memory must all fit
- Single GPU vs multi-GPU: tensor parallelism splits the model across GPUs but adds communication overhead
- Inference-optimized GPUs (L4, L40S) vs training GPUs (A100, H100): inference GPUs are often more cost-effective for serving
- Cloud provider specifics: availability varies by region, and different providers offer different GPU-instance combinations

### The Hardware Trajectory

- Hopper (H100): the current production workhorse for large model inference, native FP8 support
- Blackwell (B200): next generation with native FP4, larger memory (192GB HBM3e), 2-4x inference improvement over H100
- The trend: each generation adds lower-precision tensor core support, enabling more aggressive quantization
- Planning horizon: optimize for current hardware (Hopper/FP8) while designing for future hardware (Blackwell/FP4)

> **From Book 1:** For a deep dive on compute resource scaling patterns and cost optimization strategies, see "Before the 3 AM Alert" Chapter 9: Compute and Scaling.

## Common Pitfalls

- **Optimizing GPU utilization without a latency budget**: maximizing throughput at the expense of P99 latency violates your SLOs; always optimize within latency constraints
- **Skipping quantization calibration**: deploying a quantized model without calibration on representative data leads to subtle quality degradation that may not surface until production
- **Treating cold starts as a deployment-only problem**: auto-scaling events trigger cold starts under load; the worst time to pay the cold start penalty
- **Ignoring KV cache memory in capacity planning**: teams size GPUs for model weights and forget that KV cache for concurrent requests can exceed model size
- **Applying speculative decoding universally**: speculative decoding hurts throughput when the draft model has low acceptance rates; measure acceptance rate before committing
- **Over-quantizing safety-critical models**: INT4 quantization on a medical transcription model may produce dangerous errors; match precision to risk tolerance

## Summary

- GPU utilization is the single biggest lever for inference cost reduction; most organizations waste 50-90% of available compute
- Continuous batching (evicting completed sequences, inserting new ones at every decode step) delivers 2-4x throughput improvement and is now table stakes
- KV cache is the central memory bottleneck; PagedAttention, quantization (NVFP4), prefix caching, and offloading are the key management techniques
- Cold starts for ML models take 30 seconds to minutes; mitigation requires pre-warming, model caching, persistent GPU pools, or snapshot/restore
- FP8 is the production standard for quantization; FP4/INT4 are emerging for cost-sensitive workloads; always evaluate quality impact on your specific task
- FlashAttention-3 delivers 1.5-2x speedup over FA-2 and is the default kernel on Hopper; FlashAttention-4 targets Blackwell
- Speculative decoding accelerates autoregressive generation without quality loss; most effective for predictable output
- Right-sizing GPUs requires modeling total cost at your traffic patterns: model size, concurrency, latency constraints, and spot instance tolerance
- The hardware trajectory (Hopper -> Blackwell, FP8 -> FP4) rewards architectures that can adapt to new precision formats

## References

*To be populated during chapter authoring. Initial sources:*

1. NVIDIA (2025). "NVFP4 KV Cache: Reducing Memory Consumption for LLM Inference."
2. Stixor (2025). "The New LLM Inference Stack 2025: FA-3, FP8 & FP4."
3. Nebius (2025). "Serving LLMs with vLLM: A Step-by-Step Guide."
4. Dao, T. et al. (2024). "FlashAttention-3: Fast and Exact Attention with Asynchrony and Low-Precision."
5. Kwon, W. et al. (2023). "Efficient Memory Management for Large Language Model Serving with PagedAttention."
6. BentoML (2025). "LLM Inference Handbook; Continuous Batching and Beyond."
7. Clarifai (2025). "Comparing SGLang, vLLM, and TensorRT-LLM with GPT-OSS-120B."

---

**Next: [Chapter 4: Streaming Audio Architecture](./04-streaming-audio-architecture.md)**
