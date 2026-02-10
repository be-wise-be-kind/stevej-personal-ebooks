# Chapter 2: Model Serving Frameworks

![Chapter 2 Opener](../assets/ch02-opener.html)

\newpage

## Overview

Every serving team eventually faces a question that has no universal answer: which framework should run the models? The choice determines how models are loaded, how requests are batched, how GPU memory is allocated, how versions are managed, and how the system scales. Choose poorly, and the team spends months working around limitations that a different framework would have solved out of the box. Choose well, and the framework fades into the background, doing its job while the team focuses on the problems that are actually unique to their product.

But first, what does it mean to "run a model" at all? A trained model is a file: a set of numerical weights (often billions of them for LLMs) plus a description of the neural network architecture that connects them. On its own, the file does nothing. Running the model means loading those weights into GPU memory, accepting input data over the network, feeding it through the network's layers (matrix multiplications, attention computations, activation functions), and returning the output. For a speech recognition model, that means audio bytes go in and a text transcript comes out. For a large language model, a text prompt goes in and tokens come out one at a time. This process, turning input into output through a loaded model, is called *inference*.

A serving framework is the software that manages this entire lifecycle. It loads models onto GPUs, listens for incoming requests, routes those requests to the right model, batches multiple requests together for efficient GPU utilization, manages GPU memory across concurrent users, handles model versioning so you can update without downtime, and scales capacity up or down as traffic changes. Without a serving framework, every team would need to build all of this from scratch. The framework is the layer between "we trained a model that works in a notebook" and "users can hit an API endpoint and get predictions back in milliseconds."

The challenge is that the landscape moves fast. A framework that was the obvious choice in 2023 may be in maintenance mode by 2025. A benchmark that crowned one engine the fastest may tell a completely different story at a different concurrency level. The serving team needs a mental model for evaluating frameworks that survives the next wave of releases, not just a snapshot of today's leaderboard.

This chapter provides that mental model. We trace three generations of serving frameworks, each solving the previous generation's primary limitation. We then present a decision framework grounded in model type, latency requirements, scaling model, and operational complexity. From there, we cover the operational mechanics that matter regardless of which framework you choose: model loading, version management, hot-swapping, multi-model serving, and GPU memory partitioning. We close with the hybrid approach that most production systems actually use, and the pitfalls that trip teams up along the way.

## The Three Generations of Serving Frameworks

The evolution of ML inference serving frameworks follows a clear arc: from framework-locked servers to framework-agnostic platforms to attention-aware engines. Each generation emerged because the previous one could not handle a new class of workload.

![Framework Generations Timeline](../assets/ch02-framework-generations.html)

\newpage

### Generation 1: Framework-Specific Servers (2016-2020)

The first generation solved a genuine problem: how to move a trained model out of a notebook and behind an API without writing a bespoke server from scratch.

**TensorFlow Serving** was the pioneer. Google open-sourced it in February 2016 and released v1.0 in August 2017 [Source: Google, 2016]. Written in C++ with a gRPC interface, it introduced concepts that remain relevant today: model versioning through a directory-based repository, a batching scheduler that groups requests for efficient GPU utilization, and a model lifecycle manager that handles loading and unloading. TensorFlow Serving was the first tool that made "model in production" a repeatable process rather than an ad hoc engineering effort. Its limitation was absolute framework coupling: it served TensorFlow models and nothing else.

**TorchServe**, launched by AWS and Facebook (now Meta) in 2020, brought the same idea to PyTorch. It offered a more flexible handler system where custom Python code could preprocess and postprocess requests, making it easier to wrap complex model pipelines. TorchServe found adoption among teams that had standardized on PyTorch for training and wanted a straightforward path to production.

Both tools shared fundamental constraints. They supported only their parent framework. Their batching was static: collect N requests, process them, return results. GPU scheduling was rudimentary. Multi-model management was limited. And crucially, neither was designed for the transformer-based LLM workloads that would come to dominate inference demand.

The Gen 1 era has now closed. TorchServe's repository was archived on August 7, 2025, making it read-only with no planned updates, bug fixes, or security patches [Source: GitHub, 2025]. TensorFlow Serving remains functional but sees minimal new development. Teams still running Gen 1 frameworks face a migration, not a question of if, but when.

### Generation 2: Multi-Framework Orchestration (2020-2023)

The second generation broke the framework coupling. As organizations adopted multiple ML frameworks (PyTorch for research, ONNX for optimization, TensorRT for deployment), the one-framework-per-server model became untenable.

**Triton Inference Server** (NVIDIA) was the first major multi-framework serving platform. It can load models from TensorFlow, PyTorch, ONNX, TensorRT, and custom backends within a single server instance, with GPU scheduling and an ensemble pipeline system for chaining models into directed acyclic graphs. Triton's ensemble scheduler is "mainly an event-driven scheduler with very minimal overhead" that is "almost never the bottleneck," and running the full pipeline on GPU provides up to 6x improvement versus CPU-based pre- and postprocessing [Source: NVIDIA, 2025]. Triton has since evolved into the orchestration layer of the NVIDIA Dynamo Platform (announced March 2025), positioning it as the routing and management layer that sits above individual inference engines.

**KServe** brought Kubernetes-native model serving with Knative autoscaling, including the ability to scale to zero replicas when no traffic arrives (by setting `minReplicas=0` explicitly). Scale-to-zero is compelling for cost savings but introduces cold start latency: the full pod scheduling, container startup, and model loading sequence must complete before the first request can be served. For large LLMs, model caching can reduce this cold start from 15-20 minutes to under one minute [Source: KServe, 2025]. KServe's standardized inference protocol (the V2 inference protocol, also adopted by Triton) means that the same client code works regardless of which backend engine serves the model.

**BentoML** took a developer-experience-first approach: define a model server as a Python class, package it as a container, and deploy it anywhere. BentoML works without Kubernetes, making it accessible to startups and small teams. Its documentation reflects a pragmatic progression philosophy: use Ollama for prototyping, graduate to vLLM or SGLang for production, and adopt distributed platforms only when multi-region or multi-cluster requirements emerge [Source: BentoML, 2025].

**Ray Serve** extends the Ray distributed computing framework to model serving. Its distinguishing capability is flexible composition: multiple models and business logic can be wired together in Python with built-in support for autoscaling, fault tolerance, and resource management. Ray Serve's prefix-aware routing, which directs requests to replicas most likely to have the relevant KV cache prefix already loaded, achieves a 60% reduction in time to first token (TTFT) for LLM workloads [Source: Anyscale, 2025]. It also supports wide expert parallelism for mixture-of-experts models, prefill-decode disaggregation, and fractional GPU allocation. The trade-off is operational complexity: running a Ray cluster adds infrastructure overhead that smaller teams may not be prepared for.

**Text Generation Inference (TGI)**, Hugging Face's serving engine, bridged Gen 2 and Gen 3 by adding continuous batching and PagedAttention to a Hugging Face-native serving experience. However, TGI entered maintenance mode on December 11, 2025, with Hugging Face recommending vLLM or SGLang as alternatives [Source: Hugging Face, 2025]. TGI's trajectory illustrates a broader pattern: frameworks that do not keep pace with the LLM-specific optimization frontier lose relevance quickly.

### Generation 3: LLM-Optimized Engines (2023-Present)

The third generation exists because LLM inference has fundamentally different characteristics from traditional ML inference. Transformer models are autoregressive: each output token depends on the previous one, making the KV cache the central bottleneck. Gen 3 engines treat the KV cache as a first-class data structure with sophisticated allocation, sharing, and eviction strategies. They implement continuous batching at the iteration level, inserting new requests and evicting completed ones after every decode step. These are not features bolted onto a general-purpose server; they are the architectural foundation.

**vLLM** is the most widely adopted LLM serving engine and the safe default for most production deployments. Its core innovation, PagedAttention, reduces KV cache memory waste from 60-80% under traditional allocation to less than 4% [Source: Red Hat, 2025; Kwon et al., 2023]. On the Clarifai GPT-OSS-120B benchmark (2xH100, August 2025), vLLM achieved 4,741 tokens per second at 100 concurrent requests with a TTFT of 1.87 seconds, the fastest first-token latency at high concurrency [Source: Clarifai, 2025]. The production adoption list is extensive: Amazon Rufus (serving 250 million+ customers), LinkedIn (50+ GenAI use cases with a 7% TPOT improvement), Roblox (50% latency reduction processing 4 billion tokens per week), and Stripe (73% inference cost reduction) [Source: AWS, 2025; LinkedIn, 2025; Red Hat, 2025]. Inferact Inc. launched in January 2026 with $150 million in seed funding at an $800 million valuation to commercialize vLLM, signaling the industry's confidence in its trajectory.

**SGLang** takes a different optimization path. Where vLLM focuses on memory efficiency through PagedAttention, SGLang's RadixAttention organizes the KV cache as a radix tree, enabling automatic prefix caching across requests. When many requests share a common prefix (the system prompt in a chat application, the context documents in RAG), SGLang reuses the cached KV entries rather than recomputing them, achieving up to 5x throughput on prefix-heavy workloads [Source: LMSYS, 2024]. Its cache-aware load balancer further improves performance: 1.9x throughput and 3.8x cache hit rate by routing requests to the replica most likely to have the relevant prefix cached [Source: LMSYS, 2024]. On the AIMultiple benchmark (H100 80GB, Llama 3.1 8B, January 2026), SGLang achieved 16,215 tokens per second, roughly 29% faster than vLLM on the same hardware and model [Source: AIMultiple, 2026]. These two benchmark results (vLLM's 4,741 tok/s on GPT-OSS-120B and SGLang's 16,215 tok/s on Llama 3.1 8B) come from different benchmarks with different models and hardware; they illustrate each engine's strengths under different conditions, not a head-to-head comparison.

**TensorRT-LLM** is NVIDIA's compiler-optimized runtime. It achieves its performance through ahead-of-time compilation: model weights are compiled into GPU-specific execution plans that exploit hardware-level optimizations like FP8 and FP4 quantization kernels. On the Clarifai benchmark, TensorRT-LLM delivered 243 tokens per second at concurrency 1, the best single-request throughput of any engine tested. But this advantage inverts at scale: at concurrency 100, its throughput dropped to 1,943 tokens per second, the lowest of the three engines [Source: Clarifai, 2025]. On Blackwell hardware, the picture changes again: a single B200 GPU achieved 0.023-second TTFT and sustained 7,236 tokens per second at maximum load, with NVIDIA's InferenceMAX benchmarks showing up to 60,000 tokens per second per GPU [Source: Clarifai, 2025; NVIDIA, 2025].

The operational cost of TensorRT-LLM is substantial. Its GPU-specific compilation means that a model compiled on an A40 cannot run on an A100, because the same GPU must be used for both compilation and inference [Source: Towards Data Science, 2024]. Engine build times run 7+ minutes for large models, and Llama 3.1 405B requires at least 8 additional H100 GPUs just for the build process [Source: Baseten, 2025]. BentoML's assessment is direct: TensorRT-LLM is "the most challenging to set up," requiring reading across Triton and TRT-LLM documentation, converting checkpoints, building TensorRT engines, and writing extensive configuration files [Source: BentoML, 2024]. Teams that choose TensorRT-LLM should budget for this operational overhead and ensure they have the GPU engineering expertise to maintain it.

## Framework Selection Criteria

There is no universally best serving framework. The right choice depends on four dimensions: what kind of model you are serving, what latency your users require, how your infrastructure scales, and how much operational complexity your team can absorb.

### Model Type

The first filter is the simplest. If you are serving a transformer-based LLM (GPT, Llama, Mistral, and similar architectures), a Gen 3 engine is the right starting point. These engines implement continuous batching, KV cache management, and attention-aware scheduling as core features, and no amount of configuration on a Gen 2 platform will replicate those capabilities.

For traditional ML models (computer vision, recommendation, tabular models like XGBoost and scikit-learn, or custom PyTorch architectures that are not autoregressive transformers), Gen 2 frameworks remain the pragmatic choice. KServe and BentoML handle these workloads well, with straightforward deployment and scaling.

For multi-model ensembles where several models feed into each other (a speech pipeline of VAD, ASR, punctuation, and NER, for example), Triton's ensemble scheduler or Ray Serve's composition API provides native pipeline support. These tools manage data flow between models, schedule GPU resources across the pipeline stages, and handle failures at individual stages without bringing down the entire chain.

### Latency Requirements

The Clarifai benchmark data reveals a counterintuitive truth: the "fastest" framework depends entirely on your concurrency level. TensorRT-LLM delivered the best throughput at concurrency 1 (243 tok/s) but the worst at concurrency 100 (1,943 tok/s). SGLang led at mid-range concurrency (3,109 tok/s at concurrency 50) but fell behind vLLM at high concurrency. vLLM scaled most consistently, achieving the highest throughput (4,741 tok/s) and fastest TTFT (1.87 seconds) at concurrency 100 [Source: Clarifai, 2025].

For sub-100ms latency targets (real-time interactive applications), TensorRT-LLM with quantization is the strongest option, provided you operate at low concurrency per GPU and can absorb the operational complexity. For the 100-300ms range that defines the voice AI threshold (Chapter 1), vLLM or SGLang with continuous batching provides the best balance of performance and operational simplicity. For seconds-tolerant workloads (batch processing, async jobs), any framework works; optimize for throughput over latency.

### Scaling Model

KServe is the natural choice for teams with existing Kubernetes infrastructure who need autoscaling, scale-to-zero, and standardized deployment patterns. Its Knative integration handles pod scheduling, traffic splitting, and canary deployments through familiar Kubernetes primitives.

For teams that need distributed compute beyond a single node (tensor parallelism across multiple GPUs, pipeline parallelism across machines, or flexible model composition), Ray Serve provides the most capable distributed runtime.

For single-server deployments or teams without Kubernetes, vLLM's standalone mode or BentoML's container-based approach provides the lowest barrier to entry. vLLM can run as a single process with an OpenAI-compatible API endpoint, which is sufficient for many production workloads.

### Operational Complexity

This dimension is often underweighted and frequently decisive. We can group the frameworks into three operational tiers:

**Lowest complexity**: vLLM standalone and BentoML. Both can be deployed with a single command, require minimal configuration, and provide sensible defaults. vLLM's OpenAI-compatible API means existing client code often works without modification.

**Moderate complexity**: KServe and Triton. Both require infrastructure investment (Kubernetes for KServe, NVIDIA's container runtime for Triton) but provide substantial operational capabilities in return: model management, traffic routing, health checking, and metrics collection.

**Highest complexity**: TensorRT-LLM and Ray Serve. TensorRT-LLM demands GPU-specific compilation pipelines, engine build infrastructure, and deep NVIDIA toolchain expertise. Ray Serve requires managing a distributed Ray cluster with its own scheduling, fault tolerance, and resource allocation concerns. Both are powerful but demand proportionally more engineering investment.

![Framework Selection Decision Tree](../assets/ch02-framework-decision-tree.html)

\newpage

## Model Loading, Versioning, and Hot-Swapping

Once a framework is chosen, three operational concerns dominate day-to-day work: how models are loaded, how versions are managed, and how models are swapped without dropping traffic.

### Model Loading

Model loading is the dominant contributor to cold start latency, and the numbers are larger than most teams expect. The NVIDIA Run:ai Model Streamer benchmarks (September 2025) measured loading a 15 GB model (Llama 3 8B) to vLLM engine readiness at 23-35 seconds depending on storage backend. A 130 GB model (Llama 2 70B) took approximately 127 seconds using vLLM's baseline download mechanism [Source: NVIDIA, 2025].

Three loading strategies exist, each with different trade-offs:

**Eager loading** loads all models at startup. The server is not ready to serve traffic until every model is in GPU memory. This is predictable (the server is always fully loaded) but creates long startup times and wastes GPU memory on models that may receive infrequent traffic.

**Lazy loading** defers model loading until the first request arrives. Startup is fast, but the first request for each model pays the full loading penalty (23-35 seconds for a 15 GB model). This is acceptable for development environments but creates unacceptable latency spikes in production.

**Pre-warming** loads models during a health check period before the server starts accepting traffic. The infrastructure (Kubernetes readiness probes, load balancer health checks) gates traffic until the model is verified as loaded and a warm-up inference has completed. This combines the predictability of eager loading with the ability to prioritize which models load first.

### Version Management

Triton's model repository pattern has become the de facto standard for version management. Models are stored in a directory structure where each version occupies a numbered subdirectory (1/, 2/, 3/). A version policy controls which versions are available at runtime: latest-only, specific versions, or all versions simultaneously. The EXPLICIT control mode is particularly important for production: when a new model version fails to load (due to a corrupt file, incompatible format, or GPU memory exhaustion), the failed reload preserves the existing model without availability loss [Source: NVIDIA, 2025]. The system degrades gracefully rather than catastrophically.

Label-based routing adds a logical layer on top of version numbers. A "production" label might point to version 7, a "canary" label to version 8, and a "shadow" label to version 9. Traffic routing rules reference labels rather than version numbers, which means promoting a canary to production is a label update rather than a redeployment. This separation between physical versions and logical routing enables sophisticated rollout patterns: shift 5% of traffic to canary, monitor error rates and latency for an hour, then promote if metrics hold.

### Hot-Swapping Without Downtime

Hot-swapping, the act of replacing one model version with another while serving live traffic, is one of the most operationally challenging tasks in inference serving. For streaming workloads, the stakes are higher: an active audio transcription session cannot be interrupted because the server decided to load a new model.

The standard approach is a rolling update across replicas. In a multi-replica deployment, one replica at a time loads the new model version while the others continue serving traffic. Each replica drains its active connections (completing in-flight requests and closing streaming sessions gracefully) before switching to the new version. This is slow (a deployment across 10 replicas may take 20 minutes) but safe.

NVIDIA's GPU memory swap technique (September 2025) offers a faster alternative for environments that support it. Rather than cold-starting a new model from storage, GPU memory swap keeps the replacement model's weights in CPU memory and transfers them to GPU memory when needed. The result is dramatic: TTFT drops from 140-208 seconds (cold start from zero) to 2-3 seconds (hot swap from CPU memory), a 50-66x improvement [Source: NVIDIA, 2025]. This technique is particularly valuable for multi-model serving scenarios where models are swapped frequently based on incoming request patterns.

## Multi-Model Serving

Production systems rarely serve a single model. A speech pipeline might chain VAD, ASR, punctuation restoration, and named entity recognition. A recommendation system might combine an embedding model, a ranking model, and a business rules engine. Multi-model serving introduces two challenges: how to partition GPU resources across models, and how to orchestrate model pipelines.

### GPU Memory Partitioning: MPS vs MIG

Two NVIDIA technologies enable multiple models to share a single GPU, each with fundamentally different isolation guarantees.

**MPS (Multi-Process Service)** provides software-based GPU sharing. Multiple inference processes submit work to the same GPU through a shared CUDA context, with the GPU interleaving execution. Pebble's benchmarks on an A100-80GB with Qwen3-4B-FP8 showed 50% cost reduction with only a 7.5% performance impact per model [Source: Pebble, 2025]. MPS supports up to 48 clients per GPU and requires no special hardware. The critical limitation is isolation: MPS provides no fault isolation. A crash or memory corruption in one process can affect all processes sharing the GPU. Use MPS when all processes are under the same trust boundary and the cost savings justify the shared-fate risk.

**MIG (Multi-Instance GPU)** provides hardware-level spatial partitioning, available on Ampere and later GPUs (A100, H100, B200). MIG divides the physical GPU into isolated instances, each with its own compute units, memory, and cache. An A100 80GB can be partitioned into up to 7 instances of 1g.10gb (1 compute slice, 10 GB memory), 3 instances of 2g.20gb, 2 instances of 3g.40gb, or 1 instance of 7g.80gb [Source: NVIDIA, 2025]. Each instance operates as if it were a separate, smaller GPU: a failure in one instance does not affect others, memory is fully isolated, and each instance can run a different model with different precision settings. MIG is the right choice for multi-tenant environments, workloads with strict SLA guarantees, or any situation where fault isolation is required.

The two technologies can be combined. Multiple MPS clients can run within a single MIG instance, up to 48 total clients per physical GPU [Source: TensorFusion, 2025]. This enables fine-grained resource allocation: use MIG for hardware isolation between tenants or workload classes, then use MPS within each MIG instance for further multiplexing of lightweight models.

### Ensemble Pipelines

Multi-model pipelines, where the output of one model feeds the input of the next, require careful orchestration. Consider a real-time speech processing pipeline: audio arrives, passes through voice activity detection to identify speech segments, flows into an ASR model for transcription, through a punctuation restoration model, and finally into a named entity recognition model. Four models, each with different resource requirements and latency characteristics.

Triton's ensemble scheduler manages these pipelines as directed acyclic graphs. Each model in the pipeline declares its inputs and outputs, and Triton routes data between them with minimal overhead. The event-driven scheduler adds almost no latency to the pipeline; the dominant cost is the inference time of each model [Source: NVIDIA, 2025]. When all pipeline stages run on GPU, the data stays in GPU memory between stages, avoiding the costly GPU-to-CPU-to-GPU transfers that naive pipeline implementations incur.

![Multi-Model Serving Architecture](../assets/ch02-multi-model-architecture.html)

\newpage

## When to Build Your Own

The most common production pattern is not pure framework adoption; it is a hybrid approach where a framework handles model inference (the hard, GPU-specific part) and custom code handles everything else.

### The Hybrid Approach

Every major vLLM production deployment we can examine follows this pattern. Amazon uses vLLM for Rufus inference but wraps it with custom routing, load balancing, and Trainium chip integration [Source: AWS, 2025]. LinkedIn uses vLLM across 50+ GenAI use cases but adds custom token-level optimizations and workload-specific scheduling [Source: LinkedIn, 2025]. Stripe uses vLLM for inference but builds custom cost optimization and metering layers [Source: Red Hat, 2025]. None of these organizations use vLLM's built-in API gateway as their production entry point. They all build custom API layers.

This is not a limitation of vLLM; it is a reflection of where framework boundaries naturally fall. The inference engine handles batching, KV cache management, GPU scheduling, and model execution. The custom layer handles authentication, rate limiting, usage metering, request routing across model versions, API contracts, billing integration, and business-specific logic. vLLM's architecture explicitly supports this pattern, with multi-tenant and multi-model setups typically built with an external router or API gateway [Source: Nebius, 2025].

The practical implication is design your API layer independently of the serving framework. The API contract your clients depend on (the endpoints, the request and response schemas, the streaming behavior, the error codes) should not change when you swap from vLLM to SGLang, or from SGLang to the next engine that emerges. This independence is not just good practice; it is survival insurance. TorchServe was archived. TGI entered maintenance mode. Frameworks get abandoned. Your API contract should outlive them. Chapter 7 covers API design in detail; Chapter 9 covers versioning strategies that maintain this independence.

### Build vs Adopt

Build custom serving infrastructure when you have requirements that no existing framework handles: proprietary hardware (custom ASICs, FPGAs), proprietary protocols (telephony SIP integration, legacy binary formats), or optimization targets that require kernel-level changes. These situations exist, but they are rarer than teams believe.

Adopt a framework when you serve standard model architectures on standard GPU hardware with standard protocols. This is the vast majority of cases. The 80/20 rule applies: frameworks handle 80% of the serving problem. The remaining 20% (the authentication, the metering, the business logic, the custom routing) is where your competitive advantage lives. Spend your engineering effort there, not on reimplementing PagedAttention.

## Common Pitfalls

- **Choosing based on benchmarks alone.** The Clarifai data makes this concrete: TensorRT-LLM wins at concurrency 1 (243 tok/s) but loses at concurrency 100 (1,943 tok/s vs vLLM's 4,741 tok/s) [Source: Clarifai, 2025]. A benchmark result is a data point at a specific model size, hardware configuration, and concurrency level. Your workload will differ. Run your own benchmarks with your models, your hardware, and your traffic patterns before committing.

- **Ignoring operational cost.** TensorRT-LLM may deliver superior throughput for your workload, but it requires GPU-specific compilation (a model compiled on A40 cannot run on A100), engine build times of 7+ minutes, and extensive configuration [Source: BentoML, 2024; Towards Data Science, 2024]. If your team spends two days debugging a build pipeline for every model update, the performance gain may not survive the operational math.

- **Framework lock-in.** TorchServe was archived in August 2025. TGI entered maintenance mode in December 2025. Frameworks get abandoned or superseded. If your API contract is tightly coupled to a specific framework's interface, every framework migration becomes an API migration, which means every client must update. Design the API layer independently (Chapter 7) and swap engines without changing the contract.

- **Neglecting model loading time.** A framework that serves fast but takes 35 seconds to load a 15 GB model creates terrible auto-scaling behavior [Source: NVIDIA, 2025]. When a traffic spike triggers a scale-up event, every new instance sits idle for 35 seconds while loading the model. During that window, existing instances absorb the full load. Plan for cold starts from the beginning: model caching, pre-warming, GPU memory swap, and readiness probes that gate traffic until models are verified as loaded. Chapter 3 covers cold start mitigation in depth.

- **Over-engineering for scale too early.** Start with vLLM standalone or BentoML. They work. Migrate to KServe, Triton, or Ray Serve when you have concrete evidence of a bottleneck that a simpler tool cannot solve. The team that spends three months building a Ray Serve cluster before serving their first production request has optimized for the wrong problem.

## Summary

- Three generations of serving frameworks have emerged: framework-specific servers (Gen 1, now largely archived), multi-framework orchestration platforms (Gen 2), and LLM-optimized engines (Gen 3)
- vLLM is the safe default for LLM serving: widest adoption, PagedAttention for memory efficiency, strongest high-concurrency throughput (4,741 tok/s at concurrency 100)
- SGLang excels at prefix-heavy workloads (chat, RAG) through RadixAttention: 29% faster than vLLM on Llama 3.1 8B, with automatic KV cache reuse across requests
- TensorRT-LLM delivers the best single-request performance at low concurrency but inverts at high concurrency, and carries the highest operational complexity
- KServe for Kubernetes-native deployments with scale-to-zero; BentoML for developer-friendly teams without Kubernetes; Triton for multi-model orchestration and ensemble pipelines
- Framework selection depends on four dimensions: model type, latency requirements, scaling model, and operational complexity, and no single benchmark captures all four
- The hybrid approach (framework for inference, custom layers for everything else) is the most common production pattern, used by Amazon, LinkedIn, Stripe, and others
- GPU memory partitioning via MPS (software sharing, 50% cost reduction, no fault isolation) and MIG (hardware isolation, up to 7 instances per A100) enables efficient multi-model serving
- Design your API layer independently of the framework; frameworks get archived, but your API contract must outlive them

## References

1. Google (2016). "Running Your Models in Production with TensorFlow Serving." https://opensource.googleblog.com/2016/02/running-your-models-in-production-with.html
2. GitHub (2025). "TorchServe Repository Archived." https://github.com/pytorch/serve/issues/3396
3. Hugging Face (2025). "Text Generation Inference Documentation." https://huggingface.co/docs/inference-endpoints/en/engines/tgi
4. NVIDIA (2025). "Triton Inference Server Ensemble Models." https://docs.nvidia.com/deeplearning/triton-inference-server/user-guide/docs/user_guide/ensemble_models.html
5. KServe (2025). "KServe Documentation." https://kserve.github.io/website/
6. BentoML (2025). "Choosing the Right Inference Framework." https://bentoml.com/llm/getting-started/choosing-the-right-inference-framework
7. Anyscale (2025). "Ray Serve: Faster First Token with Custom Routing." https://www.anyscale.com/blog/ray-serve-faster-first-token-custom-routing
8. Clarifai (2025). "Comparing SGLang, vLLM, and TensorRT-LLM with GPT-OSS-120B." https://www.clarifai.com/blog/comparing-sglang-vllm-and-tensorrt-llm-with-gpt-oss-120b
9. AIMultiple (2026). "LLM Inference Engines: vLLM vs LMDeploy vs SGLang." https://research.aimultiple.com/inference-engines/
10. Clarifai (2025). "Benchmarking GPT-OSS Across H100s and B200s." https://www.clarifai.com/blog/benchmarking-gpt-oss-across-h100s-and-b200s
11. NVIDIA (2025). "NVIDIA Blackwell Leads on New SemiAnalysis InferenceMAX Benchmarks." https://developer.nvidia.com/blog/nvidia-blackwell-leads-on-new-semianalysis-inferencemax-benchmarks/
12. Red Hat (2025). "How PagedAttention Resolves Memory Waste in LLM Systems." https://developers.redhat.com/articles/2025/07/24/how-pagedattention-resolves-memory-waste-llm-systems
13. Kwon, W. et al. (2023). "Efficient Memory Management for Large Language Model Serving with PagedAttention." Proceedings of the ACM SOSP '23. arXiv:2309.06180
14. LMSYS (2024). "SGLang: Efficient Execution of Structured Language Model Programs." https://lmsys.org/blog/2024-01-17-sglang/
15. AWS (2025). "How Amazon Scaled Rufus by Building Multi-Node Inference Using AWS Trainium Chips and vLLM." https://aws.amazon.com/blogs/machine-learning/how-amazon-scaled-rufus-by-building-multi-node-inference-using-aws-trainium-chips-and-vllm/
16. LinkedIn (2025). "LinkedIn Touts vLLM Brilliance for 50+ AI Use Cases." https://www.thestack.technology/linkedin-touts-vllm-brilliance-for-50-ai-use-cases/
17. Red Hat (2025). "How vLLM Accelerates AI Inference: 3 Enterprise Use Cases." https://www.redhat.com/en/topics/ai/how-vllm-accelerates-ai-inference-3-enterprise-use-cases
18. Towards Data Science (2024). "Deploying LLMs into Production Using TensorRT-LLM." https://towardsdatascience.com/deploying-llms-into-production-using-tensorrt-llm-ed36e620dac4/
19. Baseten (2025). "Automatic LLM Optimization with TensorRT-LLM Engine Builder." https://www.baseten.co/blog/automatic-llm-optimization-with-tensorrt-llm-engine-builder/
20. BentoML (2024). "Benchmarking LLM Inference Backends." https://bentoml.com/blog/benchmarking-llm-inference-backends
21. NVIDIA (2025). "Reducing Cold Start Latency for LLM Inference with NVIDIA Run:ai Model Streamer." https://developer.nvidia.com/blog/reducing-cold-start-latency-for-llm-inference-with-nvidia-runai-model-streamer/
22. NVIDIA (2025). "Cut Model Deployment Costs While Keeping Performance with GPU Memory Swap." https://developer.nvidia.com/blog/cut-model-deployment-costs-while-keeping-performance-with-gpu-memory-swap/
23. NVIDIA (2025). "Triton Model Management." https://docs.nvidia.com/deeplearning/triton-inference-server/user-guide/docs/user_guide/model_management.html
24. NVIDIA (2025). "Multi-Instance GPU User Guide." https://docs.nvidia.com/datacenter/tesla/mig-user-guide/
25. Pebble (2025). "NVIDIA MPS vs Dedicated GPU Allocation for LLM Inference." https://www.gopebble.com/case-studies/nvidia-mps-vs-dedicated-gpu-allocation-for-llm-inference
26. TensorFusion (2025). "MIG vs MPS Comparison." https://tensor-fusion.ai/guide/comparison/compare-with-mig-mps
27. Nebius (2025). "Serving LLMs with vLLM: A Practical Inference Guide." https://nebius.com/blog/serving-llms-with-vllm
28. Anyscale (2023). "Continuous Batching in LLM Inference." https://www.anyscale.com/blog/continuous-batching-llm-inference

---

**Next: [Chapter 3: GPU Optimization & Cold Starts](./03-gpu-optimization.md)**
