# Chapter 14: Scaling Inference Globally

<!-- DIAGRAM: ch14-opener.html - Chapter 14 Opener -->

\newpage

## Overview

- **Ground the reader**: explain why scaling ML inference is different from scaling traditional web services. When a web application needs more capacity, you add more CPU-based servers behind a load balancer; they start in seconds and cost pennies per hour. When an ML inference system needs more capacity, you add GPU instances that cost $2-8/hour each, take 30-120 seconds to load a multi-gigabyte model into GPU memory before they can serve any traffic, and require careful memory management because each GPU has a fixed amount of fast memory shared across all concurrent requests. Scaling decisions that are trivial for CPU services (like "just add more instances") become engineering problems when GPUs are involved.
- Taking a single-region inference deployment to a globally distributed, auto-scaling system that handles variable demand while controlling costs
- GPU-aware scaling is fundamentally different from traditional web service scaling; signals, policies, and cold start tradeoffs all change
- Multi-region deployment introduces model replication, request routing, and data sovereignty constraints that do not exist in single-region setups

## Horizontal Scaling for Inference

### Adding GPU Instances

- Horizontal scaling means running more GPU instances behind a load balancer rather than upgrading to larger individual GPUs
- The basic unit of scale is a GPU instance with a loaded model; scaling up means bringing new instances online and loading the model onto GPU memory
- Instance warm-up time matters: unlike CPU services that start in seconds, a GPU instance may take 30-120 seconds to load a multi-gigabyte model before it can serve traffic
- Readiness probes must verify that the model is loaded and a warm-up inference has completed; not just that the container is running

### GPU-Aware Load Balancing

- Round-robin and least-connections are insufficient for inference workloads; they ignore GPU state entirely
- GPU-aware load balancing must consider: GPU memory utilization, number of active inference streams, whether the target model version is loaded, current batch queue depth
- Weighted routing based on GPU headroom: an instance at 40% GPU memory utilization should receive more traffic than one at 85%
- Sticky sessions for streaming workloads: once an audio stream is routed to an instance, subsequent chunks must go to the same instance to maintain decoder state
- Health signals from the GPU (temperature, ECC errors, memory fragmentation) should influence routing decisions

### Scaling Granularity

- Whole-instance scaling: add or remove entire GPU VMs; coarsest granularity, simplest to implement
- Pod-level scaling: in Kubernetes, scale inference pods independently of GPU nodes using fractional GPU allocation (MIG, MPS)
- Model-level scaling: within a multi-model serving setup, scale individual model replicas based on per-model demand
- The right granularity depends on workload mix; single-model deployments scale at the instance level; multi-model deployments benefit from finer granularity

## Auto-Scaling for Inference

### Scaling Signals

- **GPU utilization**: the most direct signal; sustained >80% utilization indicates the need for more capacity
- **Request queue depth**: requests waiting for an available inference slot; if the queue grows, throughput is insufficient
- **Latency P95/P99**: when tail latency exceeds the SLO threshold, scale up even if average latency looks healthy
- **Active stream count**: for streaming workloads, the number of concurrent open streams is a better signal than request rate. **Measurement caveat**: a point-in-time gauge sampled at coarse intervals (e.g., 60 seconds) misses short-lived streams entirely, reporting zero even under heavy load. Use a high-water-mark counter that tracks peak concurrent streams within each export interval, or sample at sub-second granularity. If the scaling signal reads zero, the auto-scaler never triggers (see Chapter 12)
- **KV cache utilization**: for LLM workloads, KV cache memory pressure limits batch sizes before GPU compute saturates
- Composite signals: combine multiple metrics with weighted scoring rather than relying on any single signal

<!-- DIAGRAM: ch14-autoscaling-signals.html - Auto-Scaling Signals for GPU Inference -->

\newpage

### Scaling Policies

- Step scaling: add N instances when a threshold is breached; simple but can overshoot or undershoot
- Target tracking: maintain a target value for a chosen metric (e.g., keep GPU utilization at 70%); the controller adjusts instance count continuously
- Predictive scaling: use historical patterns (business hours, weekly cycles) to pre-provision capacity before demand arrives
- Cooldown periods must be longer for GPU instances than for CPU services; removing an instance means losing a loaded model that took minutes to prepare
- Asymmetric scaling: scale up aggressively (fast response to demand spikes) but scale down conservatively (avoid cold start storms from premature removal)

### Scale-Up Speed vs Cold Start Tradeoff

- The fundamental tension: scaling up fast requires pre-provisioned or pre-warmed instances, which cost money when idle
- Warm pool strategy: maintain N idle instances with models pre-loaded, ready to receive traffic instantly
- Container image optimization: smaller images pull faster; use multi-stage builds, strip debug symbols, pre-download model weights into the image vs fetching at runtime
- Model caching on local NVMe: if an instance was recently active, the model weights may still be on local storage, reducing reload time from minutes to seconds
- KServe Knative integration: scale-to-zero saves cost but adds the longest cold start; suitable only for batch or low-priority workloads

> **From Book 1:** For a deep dive on general horizontal and vertical scaling patterns, see "Before the 3 AM Alert" Chapter 9.

### Serverless Inference

- Serverless GPU offerings (AWS Lambda with GPU, various GPU serverless providers) abstract away instance management
- Cold start penalty is most severe in serverless: no persistent model in memory, full load on every invocation
- Best suited for: bursty, low-frequency workloads where paying for idle GPUs is worse than paying for cold starts
- Not suitable for: real-time streaming inference where connection persistence and sub-second latency are required

## Multi-Region Deployment

### Model Replication Across Regions

- Model artifacts (weights, configs, tokenizers) must be replicated to storage in each serving region
- Replication strategies: push-based (CI/CD deploys to all regions simultaneously) vs pull-based (each region pulls from a central artifact store on demand)
- Version consistency: all regions should serve the same model version during steady state; staggered rollouts are acceptable during deployment windows
- Model registries (MLflow, Weights & Biases, custom) as the source of truth for which version each region should serve

### Request Routing

- **Latency-based routing**: DNS or load balancer routes each request to the region with the lowest measured latency; AWS Route 53, Google Cloud DNS, Cloudflare Load Balancing
- **Geography-based routing**: route based on the client's geographic location to the nearest region; simpler but less adaptive than latency-based
- **Capacity-aware routing**: if the nearest region is at capacity, overflow to the next-closest region rather than queueing
- **Failover routing**: if a region is unhealthy, automatically redirect traffic to backup regions with health-check-driven DNS failover
- Anycast for UDP-based protocols: when using WebRTC or RTP for audio, anycast routing naturally selects the nearest edge

<!-- DIAGRAM: ch14-multi-region-architecture.html - Multi-Region Inference Architecture -->

\newpage

### Data Sovereignty Constraints

- Audio data is personally identifiable in many jurisdictions; the voice itself is biometric data under GDPR and similar laws
- Some customers require that their audio never leaves a specific geographic region (EU, specific country)
- Per-tenant region pinning: route a customer's requests to their designated region regardless of latency
- Processing and storage separation: inference can happen in-region while aggregated, anonymized metrics flow to a central location
- Logging and debugging implications: request logs containing audio snippets must stay in the same region as the audio itself

> **From Book 1:** For a deep dive on geographic optimization including CDN, edge, and multi-region patterns, see "Before the 3 AM Alert" Chapter 12.

### Multi-Region Consistency Challenges

- Model version drift: if one region updates and another lags, clients may get inconsistent results depending on routing
- Configuration drift: feature flags, rate limits, and billing rules must be synchronized across regions
- Monitoring aggregation: SLO dashboards must show per-region and global views; a healthy global P95 can mask a struggling region

## Edge Inference vs Centralized

### When to Push Models to the Edge

- Small models (VAD, keyword spotting, noise suppression) are excellent edge candidates; they run on CPUs or lightweight GPUs
- Large models (ASR, LLM, TTS) remain centralized; they require GPU memory and compute that edge nodes cannot economically provide
- The hybrid pattern: run VAD and audio preprocessing at the edge, stream only speech segments to centralized inference, reducing bandwidth and latency for non-speech audio
- Edge inference eliminates one network hop; critical when every millisecond counts against the 300ms voice AI threshold

### The Latency vs Cost Tradeoff

- Edge GPUs (NVIDIA Jetson, T4 at edge locations) are less powerful but closer to users; lower latency, lower throughput
- Centralized GPUs (A100, H100, B200 in cloud regions) are more powerful but farther from users; higher throughput, higher latency
- Break-even analysis: compare the cost of edge GPU fleet vs the latency improvement it provides; often the math only works for very latency-sensitive, high-volume workloads
- CDN-style inference caching: for deterministic models with repeated inputs, cache results at edge; limited applicability for audio but useful for TTS with common phrases

### WebRTC and Edge

- WebRTC's TURN/STUN infrastructure naturally creates edge presence for audio routing
- OpenAI Realtime API's WebRTC mode demonstrates the pattern: audio enters via WebRTC edge, inference happens centralized
- The edge handles codec negotiation, jitter buffering, and packet loss concealment; inference stays centralized

## Cost Optimization

### Spot and Preemptible GPU Instances

- Spot instances offer 60-90% discounts but can be reclaimed with 30-120 seconds of warning
- Suitable for: batch inference, shadow testing, non-critical workloads where interruption is tolerable
- Risky for: real-time streaming; a reclaimed instance means dropped audio streams and broken connections
- Mitigation: use spot for a portion of capacity with graceful drain on preemption signal; migrate active streams to on-demand instances
- Spot fleet diversity: spread across multiple GPU types and availability zones to reduce simultaneous reclamation risk

### Right-Sizing GPU Instances

- Matching GPU class to model size: a 1B parameter model does not need an H100; an A10G or L4 is sufficient and far cheaper
- Memory headroom: the model must fit in GPU memory with room for KV cache and batch buffers; 20-30% headroom is a reasonable target
- Throughput matching: select GPU compute power based on required requests per second, not just model fit
- Common mistake: using the largest available GPU "just in case" instead of profiling actual requirements

### Scheduled Scaling

- Most inference workloads follow predictable patterns: business hours peak, overnight trough, weekend dip
- Scheduled scaling policies: pre-provision capacity before the morning ramp, scale down after business hours
- Timezone-aware scheduling: for global deployments, each region has its own demand curve
- Combining scheduled + reactive scaling: scheduled handles the predictable baseline, reactive handles unexpected spikes

### Reserved Instances and Savings Plans

- Reserved instances (1-year or 3-year commitments) offer 30-60% discounts over on-demand pricing
- Use reserved instances for the baseline capacity that is always needed; the minimum GPU count even during off-peak
- Layer on-demand for predictable peaks and spot for burst capacity above that
- The three-tier cost model: reserved (baseline) + on-demand (predictable peak) + spot (burst)

<!-- DIAGRAM: ch14-cost-optimization-strategies.html - Cost Optimization Strategies -->

\newpage

### Cost Monitoring and Allocation

- Per-model cost tracking: attribute GPU-hours to specific models to understand unit economics
- Per-customer cost tracking: when models serve multiple tenants, allocate inference cost by usage
- GPU idle time monitoring: track the percentage of provisioned GPU-seconds that are actually used for inference
- Cost anomaly detection: alert when GPU spend deviates significantly from forecasts; often indicates a scaling policy misconfiguration

### Cost-First Observability Design

- Observability infrastructure itself has cost that scales with inference traffic: every request generates metrics, traces, and logs. At inference scale (thousands of requests per second), telemetry storage and processing become a significant line item
- **Feature flags for instrumentation**: implement a runtime kill switch (e.g., `OTEL_ENABLED=false`) that disables all telemetry collection. This serves two purposes: zero-overhead operation when debugging is not needed, and an immediate escape valve if telemetry volume causes cost overruns. Use a separate flag for profiling (higher CPU overhead) vs. metrics/traces/logs
- **Storage consolidation**: use a single object storage bucket with path prefixes (e.g., `s3://observability/metrics/`, `s3://observability/traces/`, `s3://observability/logs/`) rather than separate buckets per telemetry pillar. Reduces management overhead and enables unified lifecycle policies (e.g., 7-day retention for dev, 30-day for production)
- **Single-binary components**: for small-to-medium deployments, use single-binary mode for observability backends (Loki, Tempo, Mimir all support this). Scale to distributed mode only when data volume requires it. A single t3.medium can run the full Grafana stack for a dev/staging inference environment
- Design for the progression: start cheap and simple, add complexity only when measurement proves the simpler approach is insufficient

### Workspace Separation (Persistent vs Ephemeral Infrastructure)

- Separate infrastructure into "base" (persistent) and "runtime" (ephemeral) workspaces to protect long-lived data from compute lifecycle events
- **Base workspace** (persistent): object storage for metrics/logs/traces, model weight caches, model registries, configuration databases, billing records. This is data that must survive infrastructure teardown
- **Runtime workspace** (ephemeral): GPU instances, inference servers, API gateways, load balancers. This is compute that can be destroyed and recreated without data loss
- **Benefit**: tearing down all compute during cost-cutting or maintenance (`destroy runtime`) does not destroy historical observability data, model artifacts, or billing records. When runtime is recreated, instances pull cached model artifacts from base storage rather than re-downloading
- This separation also enables cost optimization: keep expensive GPU instances only during business hours while maintaining 24/7 access to historical dashboards and alerting on base infrastructure
- In Terraform/OpenTofu: implement as separate state files or workspaces with explicit data dependencies between them

## GPU Cluster Management

### Heterogeneous GPU Fleets

- Production fleets often mix GPU generations: A100s, H100s, B200s, L4s, T4s; each with different performance and cost profiles
- Workload-to-GPU matching: route latency-sensitive real-time inference to the fastest GPUs, batch jobs to older or cheaper GPUs
- Model compatibility matrix: not all models run equally well on all GPU types; quantized FP8 models require Hopper or newer
- Fleet planning: as new GPU generations arrive, phase in gradually while maintaining enough capacity on older hardware for fallback

### Workload Placement and Bin-Packing

- Bin-packing: fit as many models as possible onto each GPU to maximize utilization; analogous to container bin-packing on CPU nodes
- Constraints: models sharing a GPU must not exceed total memory, and interference between workloads must be acceptable
- MIG partitioning for isolation: on A100/H100, use Multi-Instance GPU to give each model a hardware-isolated GPU slice
- Affinity rules: some models perform better when co-located (shared preprocessing) or separated (memory-intensive workloads)

### GPU Health and Lifecycle

- GPU failure modes: ECC memory errors (correctable and uncorrectable), thermal throttling, driver crashes, CUDA context corruption
- Proactive monitoring: track GPU health metrics (temperature, power draw, ECC error count) and drain instances before hard failures
- Replacement workflows: when a GPU fails, the instance must be drained, replaced, and the model reloaded; automation is essential
- Driver and CUDA version management: upgrades require instance restarts; coordinate with scaling policies to avoid capacity gaps

## Common Pitfalls

- **Scaling on CPU metrics instead of GPU metrics**: CPU utilization tells you almost nothing about inference capacity; always scale on GPU utilization, queue depth, or latency
- **Ignoring cold start time in auto-scaling policies**: if it takes 2 minutes to load a model, scaling up on a latency spike is already too late; use predictive scaling or warm pools
- **Treating all regions identically**: traffic patterns, instance availability, and GPU pricing vary by region; tune scaling policies per region
- **Over-provisioning "just in case"**: fear of cold starts leads to massive GPU fleets running at 20% utilization; measure and right-size continuously
- **Neglecting spot instance drain handling**: using spot for real-time workloads without graceful drain logic causes silent stream failures
- **Single-signal auto-scaling**: relying on one metric (e.g., only GPU utilization) misses scenarios where latency degrades while utilization looks normal (memory pressure, queue depth buildup)

## Summary

- GPU-aware load balancing must consider GPU memory, active streams, model loaded status, and queue depth; not just round-robin
- Auto-scaling signals for inference include GPU utilization, request queue depth, P95 latency, active stream count, and KV cache pressure
- Scale up fast (warm pools, pre-provisioned instances) and scale down conservatively (long cooldowns, avoid cold start storms)
- Multi-region deployment requires model replication, latency-based routing, and data sovereignty compliance for audio data
- Edge inference suits small models (VAD, preprocessing); large models stay centralized where GPU resources are concentrated
- Cost optimization layers: reserved instances for baseline + on-demand for peaks + spot for burst; with right-sized GPU classes per model
- Heterogeneous GPU fleets require workload-to-GPU matching, bin-packing, MIG partitioning, and proactive health monitoring
- The 300ms voice AI threshold means every scaling decision; cold start time, routing latency, region selection; directly impacts user experience

## References

*To be populated during chapter authoring. Initial sources:*

1. KServe (2025). "Knative Autoscaling Configuration for Inference Services."
2. NVIDIA (2025). "Triton Inference Server: Cluster Management and Model Repository."
3. AWS (2025). "Auto Scaling GPU Instances for ML Inference."
4. Google Cloud (2025). "Best Practices for Serving ML Models at Scale."
5. Kubernetes (2025). "Horizontal Pod Autoscaler with Custom GPU Metrics."
6. NVIDIA (2025). "Multi-Instance GPU (MIG) User Guide."

---

**Next: [Chapter 15: Putting It All Together](./15-putting-it-all-together.md)**
