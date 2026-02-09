# Chapter 2: Model Serving Frameworks

<!-- DIAGRAM: ch02-opener.html - Chapter 2 Opener -->

\newpage

## Overview

- The framework landscape has evolved through three generations, each solving progressively harder problems
- Choosing the right framework is one of the most consequential infrastructure decisions a serving team makes
- This chapter provides a decision framework grounded in real benchmarks and operational requirements

## The Three Generations of Serving Frameworks

### Generation 1: Framework-Specific Servers

- TensorFlow Serving: the original production serving solution, tightly coupled to TF ecosystem
- TorchServe: PyTorch's answer, flexible but historically less mature for production workloads
- Limitations: single-framework lock-in, basic batching, limited GPU scheduling
- Still relevant for teams deeply invested in a single framework with simple serving needs

### Generation 2: Multi-Framework Orchestration

- **Triton Inference Server**: NVIDIA's multi-framework orchestration layer; supports TensorRT, PyTorch, TensorFlow, ONNX
  - GPU scheduling, ensemble pipelines, model repository management
  - Often paired with TensorRT-LLM for model execution
- **KServe**: Kubernetes-native serverless inference
  - Knative autoscaling with scale-to-zero capability
  - Best fit for organizations heavily invested in Kubernetes
  - Standardized inference protocol across frameworks
- **BentoML**: Developer-friendly, Python-class based model serving
  - Works without Kubernetes; good for startups and small teams
  - Rapid prototyping to production path
  - Growing LLM support via OpenLLM
- **Ray Serve**: Distributed AI applications on Ray
  - Flexible composition of models and business logic
  - Heavier operational footprint; best when already using Ray ecosystem

### Generation 3: LLM-Optimized Engines

- **vLLM**: Most widely adopted LLM serving engine
  - PagedAttention + continuous batching as core innovations
  - Fastest TTFT across concurrency levels
  - 4,741 tok/s at 100 concurrent requests (GPT-OSS-120B benchmark) [Source: Clarifai, 2025]
  - Safe default for production LLM serving
- **SGLang**: RadixAttention for prefix caching
  - ~16,200 tok/s, 29% faster than vLLM on H100 with Llama 3.1 8B [Source: Clarifai, 2025]
  - Most stable per-token latency (4-21ms range)
  - Best for chat/RAG scenarios with significant KV cache reuse
- **TensorRT-LLM**: NVIDIA's optimized runtime
  - FP8/FP4/INT4 quantization, inflight batching
  - Outperforms SGLang and vLLM on Blackwell (B200) GPUs
  - Higher setup complexity; requires NVIDIA-specific toolchain
  - Best when squeezing maximum performance from NVIDIA hardware

## Framework Selection Criteria

### Model Type

- LLM/transformer models → Gen 3 engines (vLLM, SGLang, TensorRT-LLM)
- Traditional ML (XGBoost, sklearn, custom PyTorch) → Gen 2 frameworks (KServe, BentoML, Triton)
- Multi-model ensembles → Triton (native pipeline support) or Ray Serve (composition)

### Latency Requirements

- Sub-100ms (real-time interactive) → TensorRT-LLM with quantization, or vLLM with optimized config
- Sub-300ms (voice AI threshold) → vLLM or SGLang with continuous batching
- Seconds-tolerant (batch/async) → any framework, optimize for throughput over latency

### Scaling Model

- Kubernetes-native auto-scaling → KServe
- Serverless / scale-to-zero → KServe with Knative
- GPU cluster management → Triton + Kubernetes, or Ray Serve
- Single-server / small team → BentoML or vLLM standalone

### Operational Complexity

- Lowest: BentoML, vLLM standalone
- Moderate: KServe, Triton
- Highest: TensorRT-LLM (build pipeline), Ray Serve (cluster management)

<!-- DIAGRAM: ch02-framework-decision-tree.html - Framework Selection Decision Tree -->

\newpage

## Model Loading, Versioning, and Hot-Swapping

### Model Loading Strategies

- Eager loading: load all models at startup; predictable but slow cold starts
- Lazy loading: load on first request; fast startup but unpredictable first-request latency
- Pre-warming: load models during health check period before accepting traffic

### Version Management

- Model repository pattern: directory-based versioning (Triton, TorchServe)
- Label-based routing: "production", "canary", "shadow" labels mapping to model versions
- Gradual rollout: shift traffic percentage from old to new version

### Hot-Swapping Without Downtime

- The challenge: replacing a multi-gigabyte model on GPU while serving live traffic
- Dual-GPU strategy: load new version on secondary GPU, switch routing, unload old
- Rolling update: in a multi-replica setup, update one replica at a time
- Connection draining: finish in-flight requests before swapping

## Multi-Model Serving

### GPU Memory Management

- A single GPU can host multiple small models; but memory is the constraint
- MPS (Multi-Process Service): share a GPU across multiple inference processes
- MIG (Multi-Instance GPU): hardware-level GPU partitioning on A100/H100
- When to use which: MPS for lightweight models, MIG for isolation guarantees

### Ensemble Pipelines

- Chaining models: audio → VAD → ASR → punctuation → NER (named entity recognition)
- Triton's ensemble scheduler: define DAGs of model dependencies
- Latency implications: each model in the chain adds to total response time
- Optimization: pipeline parallelism where models process different chunks concurrently

<!-- DIAGRAM: ch02-multi-model-architecture.html - Multi-Model Serving Architecture -->

\newpage

## When to Build Your Own

### The Hybrid Approach

- Use a framework for model inference (the hard part) + custom layers for everything else
- Common pattern: vLLM/TensorRT-LLM for inference + custom API gateway for routing, auth, metering
- Why pure framework solutions often fall short: business logic, billing integration, custom protocols

### Build vs Adopt Decision Framework

- Build when: unique requirements (custom protocols, proprietary hardware, extreme optimization)
- Adopt when: standard models, standard protocols, team lacks GPU-level expertise
- The 80/20 rule: frameworks handle 80% of serving needs; the remaining 20% is your competitive advantage

<!-- DIAGRAM: ch02-framework-generations.html - Framework Generations Timeline -->

\newpage

## Common Pitfalls

- **Choosing based on benchmarks alone**: benchmarks test specific models on specific hardware; your workload will differ
- **Over-engineering for scale too early**: start with vLLM or BentoML, migrate to more complex setups when bottlenecks emerge
- **Ignoring operational cost**: TensorRT-LLM may be 15% faster but requires significantly more operational expertise
- **Framework lock-in**: design your API layer independently of the serving framework; swap the engine without changing the contract
- **Neglecting model loading time**: a framework that serves fast but takes 5 minutes to load a model creates terrible auto-scaling behavior

## Summary

- Three generations of frameworks: framework-specific → multi-framework orchestration → LLM-optimized engines
- vLLM is the safe default for LLM serving; SGLang excels at KV-reuse scenarios; TensorRT-LLM for maximum NVIDIA performance
- KServe for Kubernetes-native deployments; BentoML for developer-friendly small teams; Triton for multi-model orchestration
- Framework selection depends on: model type, latency requirements, scaling model, operational complexity
- The hybrid approach (framework for inference + custom layers) is the most common production pattern
- Model loading, versioning, and hot-swapping are operational concerns that matter as much as raw performance
- Design your API layer independently of the framework; you will likely swap engines over time

## References

*To be populated during chapter authoring. Initial sources:*

1. Clarifai (2025). "Comparing SGLang, vLLM, and TensorRT-LLM with GPT-OSS-120B."
2. MarkTechPost (2025). "Comparing Top 6 Inference Runtimes for LLM Serving in 2025."
3. BentoML (2025). "LLM Inference Handbook; Choosing the Right Framework."
4. Northflank (2025). "vLLM vs TensorRT-LLM: Key differences, performance."

---

**Next: [Chapter 3: GPU Optimization & Cold Starts](./03-gpu-optimization.md)**
