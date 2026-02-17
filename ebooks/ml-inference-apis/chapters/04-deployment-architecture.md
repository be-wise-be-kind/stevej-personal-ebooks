# Chapter 4: Deployment Architecture Strategies

![Chapter 4 Opener](../assets/ch04-opener.html)

\newpage

## Overview

Chapters 2 and 3 addressed which serving framework to choose and how to squeeze maximum performance from a GPU. Chapter 15 will address how to scale inference globally. But between "which framework" and "how to scale" lies a decision that shapes everything else: how do you organize the deployment itself? Do all models share one cluster? Does each model get its own isolated deployment? Does a central platform team provide templates that product teams instantiate?

This is the deployment architecture decision, and it is distinct from the framework selection or scaling strategy. It determines blast radius when something fails, how fast teams can ship model updates independently, how much GPU spend you waste on fragmentation, and whether your third engineering team spends weeks building infrastructure or hours configuring a template. The knowledge to make this decision well lives scattered across engineering blogs from Uber, Spotify, DoorDash, Pinterest, and others, but no single resource synthesizes it for ML inference workloads. This chapter fills that gap.

ML inference deployment differs from traditional microservices deployment in three fundamental ways. First, GPU scarcity: GPUs cost 10-100x more per hour than CPUs, and provisioning new ones takes minutes, not seconds [Source: AWS, 2025]. Second, model artifacts are enormous: a single model checkpoint can be 1-140 GB, compared to the 50-500 MB container images typical of microservices [Source: BentoML, 2025]. Third, noisy-neighbor effects on GPUs are severe: one model's batch can evict another model's weights from GPU memory, spiking the second model's latency from 45ms to 200ms or beyond [Source: vCluster, 2025]. These constraints mean that deployment architecture patterns designed for CPU microservices frequently fail when applied to inference workloads without adaptation.

We present three patterns as an evolution, not static choices. Most organizations move through them as they grow, and understanding all three helps you choose the right starting point and recognize when to transition.

## Bridging the Gap

This chapter draws on concepts from both ML infrastructure and API engineering. If you have not encountered these before, this section provides the context you will need.

**From the ML side**, this chapter relies on Kubernetes and infrastructure-as-code concepts that are standard in platform engineering. A Kubernetes cluster is a group of machines (nodes) managed as a unit; pods are the smallest deployable units (typically one container); namespaces are logical partitions within a cluster for isolating teams or workloads. Node pools are groups of nodes with the same hardware configuration (e.g., a pool of GPU nodes and a separate pool of CPU nodes). Infrastructure-as-code (IaC) tools like Terraform or OpenTofu define infrastructure declaratively in files rather than manually clicking through cloud consoles; changes are version-controlled and reviewed like application code. GitOps extends this by making a Git repository the single source of truth: a change merged to Git automatically triggers infrastructure updates. A "golden path" is an opinionated, pre-built template that encodes best practices; teams follow it by default but can deviate when they have a justified reason.

**From the API side**, ML deployments introduce constraints that do not exist in CPU-based services. Model artifacts range from 1 GB to 140 GB, meaning that pulling a new container image or loading a model at startup takes minutes, not the seconds you expect from a typical API server. GPU memory is a hard constraint: if a model's weights plus its runtime allocations (KV cache, batch buffers) exceed available VRAM, the process crashes with an out-of-memory error. There is no swap space, no graceful degradation, no automatic retry. Noisy-neighbor problems on GPUs are qualitatively worse than on CPUs. On a CPU, a noisy neighbor causes slowdowns; on a GPU, a noisy neighbor can evict another model's weights from memory entirely, causing not just latency spikes but potential OOM crashes. This is why GPU isolation patterns like NVIDIA MIG (Multi-Instance GPU, which provides hardware-level GPU partitioning) and MPS (Multi-Process Service, which provides software-level GPU sharing) matter far more than their CPU equivalents (cgroups, CPU pinning).

## The Three Deployment Patterns

The three patterns we cover — shared cluster, container-per-model, and platform template — represent an organizational maturity progression. Each solves problems the previous one creates, and each introduces new costs. The right pattern for your organization depends on team count, model count, and where you are in that progression.

![Deployment Architecture Patterns](../assets/ch04-three-patterns.html)

\newpage

### Pattern 1: Single Shared Cluster

The simplest deployment architecture puts all models into one Kubernetes cluster with shared GPU node pools. Models may share individual GPUs through NVIDIA MIG or MPS partitioning, or they may each claim a full GPU within the shared pool. One team manages the cluster, deploys all models, and operates the infrastructure.

**When it works.** This pattern is right for a single team running 1-3 models in a cost-sensitive environment. A startup deploying Whisper ASR and a VAD model together on a single A100 using MIG partitioning can achieve excellent GPU utilization at minimal operational overhead. One cluster, one CI/CD pipeline, one set of alerts. The total infrastructure cost is the lowest of any pattern because there is zero fragmentation: every GPU slot that is paid for can be used by any model.

DoorDash's early ML platform followed this pattern: a centralized team managed a Kubernetes cluster serving multiple models, growing to 38 models and 6.8 million peak predictions per second before the architecture needed to evolve [Source: DoorDash Engineering, 2021]. The single-cluster approach kept operational complexity low during the period when the ML team was small and deployment frequency was manageable.

**How it fails.** The failure mode is coupling. Every model shares a blast radius: a misconfigured deployment for Model A can take down Model B's GPU node. Deployment schedules are coupled: if team A wants to deploy on Tuesday but team B's model is running a critical customer demo, someone waits. Resource contention is implicit: one model's traffic spike consumes GPU capacity that another model needs.

The noisy-neighbor problem is the most insidious failure. Without hardware-level isolation (MIG), models sharing a GPU interfere with each other's performance unpredictably. Model A's large batch can evict Model B's weights from GPU memory, forcing Model B to reload weights from system RAM or storage. This weight eviction manifests as latency spikes: inference that normally takes 45ms suddenly takes 200ms or more while weights are re-fetched [Source: vCluster, 2025].

**Speech API example.** A startup deploys Whisper ASR (automatic speech recognition) and Silero VAD on a single A100 GPU with MIG, allocating a 3g.20gb partition to Whisper and a 1g.5gb partition to VAD. Total cost: one GPU instance. The VAD model handles speech detection, feeding only speech segments to the larger ASR model. With MIG, the two models have hardware-isolated memory and compute, preventing interference. This works well until the team adds a third model (TTS) that needs its own MIG partition, at which point the A100's seven MIG slices become a constraint.

### Pattern 2: Container-per-Model (Dedicated Resources)

The second pattern gives each model its own deployment: its own container image, its own GPU allocation, its own Kubernetes deployment or node pool, and its own CI/CD pipeline. Models are isolated from each other at the infrastructure level.

**Isolation boundaries.** The key benefit is blast-radius containment. When the ASR model's deployment fails, the TTS model continues serving. When the diarization model needs a GPU upgrade, the ASR model's infrastructure is untouched. Each model has its own deployment lifecycle: the ASR team can deploy three times a day while the TTS team deploys weekly, with no coordination required.

Meta's FBLearner Flow exemplified this pattern at scale: each model ran as its own container with independent auto-scaling, allowing teams to operate independently even across hundreds of models [Source: Meta Engineering, 2016]. Lyft's LyftLearn adopted a similar approach with per-team model serving microservices, enabling teams to own their model's full lifecycle from training through serving [Source: Lyft Engineering, 2023].

**The cost of isolation.** Dedicated resources mean fragmentation. If Model A's GPU is allocated but 60% idle during off-peak, that capacity cannot be borrowed by Model B's deployment. In practice, organizations running container-per-model report 30-50% higher GPU spend compared to shared clusters, driven primarily by the inability to bin-pack across model boundaries [Source: AWS, 2023]. The operational overhead also multiplies: each model needs its own monitoring dashboards, alerting rules, scaling policies, and on-call runbooks.

**Speech API example.** A team running ASR, TTS (text-to-speech), speaker diarization, and PII (personally identifiable information) redaction deploys each as an independent Kubernetes deployment. The ASR model gets two H100 GPUs, TTS gets one A10G, diarization gets one L4, and PII redaction runs on CPU. Each model scales independently: ASR scales based on audio stream count, TTS scales on character throughput. When the ASR model is updated to a new Whisper checkpoint, only the ASR deployment is touched. The tradeoff: four separate CI/CD pipelines, four sets of scaling policies, four monitoring configurations.

### Pattern 3: Platform Template Architecture

The third pattern introduces a platform team that provides reusable infrastructure templates. Instead of each product team building its own deployment pipeline from scratch, the platform team maintains Terraform modules and Helm charts that encode best practices. Product teams instantiate these templates with parameters specific to their model: model name, GPU class, replica count, scaling thresholds.

This is the pattern that Uber's Michelangelo, Spotify's Hendrix, Pinterest's MLEnv, and Shopify's Merlin all converged on, though each with different implementation details [Source: Uber Engineering, 2022; Anyscale, 2024; Pinterest Engineering, 2023; Shopify Engineering, 2022].

**The golden path.** A golden path is an opinionated but extensible default [Source: Red Hat, 2024]. The platform team's Terraform module might default to an A10G GPU, 2 replicas, 70% GPU utilization scale-up threshold, and a standard Grafana dashboard. A product team deploying a new ASR model fills in a configuration file specifying their model name, artifact location, and any parameter overrides, then runs a single pipeline to get a production-ready deployment with monitoring, alerting, auto-scaling, and cost attribution already configured.

Pinterest's MLEnv platform demonstrates the power of this approach: adoption grew from under 5% to over 95% in three years, precisely because the golden path removed weeks of infrastructure setup from the model deployment process [Source: Pinterest Engineering, 2023]. Airbnb's Bighead platform showed a similar trajectory, reducing model deployment time from 8-12 weeks to days by providing standardized infrastructure templates [Source: Databricks Summit, 2018].

![Platform Template Architecture](../assets/ch04-platform-template.html)

\newpage

**Shared services vs team-owned.** The platform template pattern works because it draws a clear line between what the platform centralizes and what teams own:

*Centralize:*
- Observability infrastructure (Prometheus, Grafana, tracing)
- Model registry and artifact storage
- API gateway and ingress routing
- Certificate management and TLS termination
- Cost attribution and chargeback reporting

*Team-owned:*
- Scaling policies and thresholds
- Framework configuration (batch sizes, quantization settings)
- Model artifacts and training pipeline
- Deployment cadence and release schedule
- Quality gates and acceptance criteria

**Team autonomy within guardrails.** The risk of any centralized platform is becoming a bottleneck. Policy engines like Open Policy Agent (OPA), Gatekeeper, or Kyverno enforce organizational guardrails (GPU quotas, security policies, naming conventions) without requiring the platform team to review every deployment [Source: CNCF, 2024]. Teams deploy freely within the guardrails; the guardrails prevent the deployment patterns that would cause problems for others.

**Speech API example.** A company with 8+ speech models (ASR in 5 languages, TTS in 3 voices, diarization, PII redaction) uses the platform template pattern. Each model team uses the same Terraform module to deploy their model, specifying GPU class, replica count, and model-specific configuration. All models share a centralized Grafana instance with per-model dashboards auto-generated from the deployment template. Per-team deployment pipelines run independently, but all feed into the same model registry and pass the same quality gates enforced by the platform. A new language-specific ASR model goes from "trained" to "deployed with full observability" in hours, not weeks.

## Infrastructure-as-Code for ML Deployments

### Terraform Module Design

Infrastructure-as-code is the foundation that makes Patterns 2 and 3 reproducible. For ML deployments, the key Terraform design decision is separating persistent and ephemeral resources into different state files.

**Base workspace (persistent):** Object storage for model artifacts, the model registry database, observability data stores, DNS records, and network configuration. These resources outlive any individual GPU deployment and must not be destroyed when compute is recycled.

**Runtime workspace (ephemeral):** GPU instances, Kubernetes node pools, inference server deployments, load balancers. These resources can be destroyed and recreated without data loss. When a runtime workspace is recreated, inference servers pull cached model artifacts from the base workspace's storage rather than re-downloading from the training pipeline.

This separation enables cost optimization: tear down expensive GPU instances during off-hours while maintaining 24/7 access to dashboards and model artifacts. In Terraform or OpenTofu, implement this as separate state files or workspaces with explicit data dependencies between them [Source: Stripe Engineering, 2023].

### Helm Chart Patterns for GPU Workloads

Standard Kubernetes Helm charts need GPU-specific extensions for inference deployments:

**GPU resource requests.** Kubernetes `nvidia.com/gpu` resource requests are non-compressible: a pod requesting 1 GPU gets exactly 1 GPU, or it does not schedule. Unlike CPU requests where a pod can be throttled, a GPU request is all-or-nothing. Charts must specify both the GPU count and the GPU type (via node selectors or affinity rules targeting specific GPU node pools).

**Model-loading readiness probes.** Standard HTTP readiness probes check if a server is listening. For inference, the readiness probe must verify that the model is loaded into GPU memory and a warm-up inference has completed successfully. A probe that returns healthy before model loading completes will receive traffic that it cannot serve, causing request failures.

**NVMe caching for model weights.** Instances with local NVMe storage can cache model weights across container restarts. The Helm chart configures an init container that checks local NVMe for a cached copy of the model weights before falling back to downloading from object storage. This reduces cold start time from minutes (full download) to seconds (local copy).

### GitOps and the Two-Source-of-Truth Problem

GitOps works well for infrastructure configuration: changes to Helm values or Terraform variables are committed to Git, and a reconciliation loop (ArgoCD, Flux) applies them to the cluster. But ML deployments have two sources of truth: Git for infrastructure configuration, and the model registry for model weights and versions.

The model weights cannot live in Git. A 15 GB model checkpoint does not belong in a Git repository. The practical solution is a two-pointer system: Git stores the infrastructure configuration and a reference to the model version (e.g., `model_version: whisper-v3.2`), while the model registry stores the actual artifacts. The deployment pipeline resolves the pointer at deploy time, pulling the correct weights from the registry.

Netflix's approach to this problem uses OCI Image Volumes, separating model weights from runtime containers entirely. The model weights are packaged as OCI artifacts and mounted as volumes at runtime, allowing the runtime container and the model artifact to have independent lifecycle and versioning [Source: Netflix/Medium, 2025].

## CI/CD for Model Deployments

### Four Key Differences from Code CI/CD

Model deployment pipelines share the structure of code deployment pipelines but differ in four critical ways:

**Artifact size.** A code deployment artifact is typically 50-500 MB. A model artifact is 1-15 GB for medium models, 15-140 GB for large models. This means build steps that take seconds for code take minutes for models. Container pulls that are sub-second for code images take 1-5 minutes for model images. Every stage of the pipeline must account for these transfer times.

**Build time.** Compiling a model for optimized inference (e.g., building a TensorRT-LLM engine) takes 7+ minutes, compared to seconds for most code builds. This makes iterative "fix and re-deploy" cycles much slower and increases the cost of build pipeline failures.

**Quality validation.** Code deployments validate correctness through deterministic tests: unit tests pass or fail. Model deployments validate quality through statistical evaluation: word error rate on a reference dataset, latency percentiles under load, accuracy across demographic subgroups. A model can be "correct" (no crashes) but "bad" (5% higher WER than the previous version). The quality gate is a statistical comparison, not a binary pass/fail.

**Rollback criteria.** Code rollback is triggered by crashes, error rate spikes, or test failures. Model rollback is triggered by quality degradation that may take hours to detect through production traffic analysis. The rollback itself is also slower: rolling back a model means loading the previous version's weights onto GPUs, which takes minutes per instance.

![Model Deployment Pipeline](../assets/ch04-cicd-pipeline.html)

\newpage

### The Model Deployment Pipeline

A production model deployment pipeline follows this sequence:

1. **Validate.** Automated checks: model artifact integrity (checksum), compatibility with target GPU class, memory footprint estimation, schema compatibility with the serving framework.
2. **Build.** Container image construction, optional TensorRT engine compilation, model optimization (quantization, graph compilation).
3. **Quality gate.** Run the model against a reference evaluation dataset. Compare WER, latency, and accuracy against the currently deployed version. Fail the pipeline if quality degrades beyond defined thresholds.
4. **Staging.** Deploy to a staging environment with production-like traffic patterns (replayed from production logs). Verify end-to-end functionality including streaming, client compatibility, and monitoring integration.
5. **Canary (1-5%).** Deploy to a small percentage of production traffic. Monitor quality metrics, latency, error rates, and GPU utilization for a soak period.
6. **Soak (30-60 minutes).** Hold the canary deployment stable while monitoring for slow-onset issues: memory leaks, latency drift, quality degradation on edge cases.
7. **Promote.** Roll out to the full fleet, region by region, with per-region health checks between each rollout step.
8. **Post-deploy validation.** Automated quality checks on production traffic for 24 hours. Lowered alerting thresholds during the watch period.

### Shadow Deployments for Speech APIs

Shadow deployment is particularly powerful for speech inference. The shadow model receives the same audio stream as the production model but its results are discarded rather than returned to users. This allows direct comparison: run both models on identical audio, compare transcripts automatically, and quantify quality differences before any user is affected.

The implementation is straightforward for streaming audio: a router duplicates the audio stream to both the production and shadow inference pipelines. The shadow pipeline's transcripts are logged to a comparison dataset. An offline analysis job computes WER differences, identifies regression categories (specific accents, background noise levels, vocabulary domains), and generates a quality report.

The cost is the GPU resources for the shadow deployment. For a company that can afford it, shadow deployment is the safest way to validate model updates for speech workloads where quality regressions are hard to detect through synthetic benchmarks alone.

## Namespace and Tenant Isolation

### Multi-Tenant GPU Clusters

In Patterns 1 and 3, multiple teams share GPU infrastructure. Isolation must be enforced at four layers, each addressing a different failure mode:

**RBAC (Role-Based Access Control).** Each team gets a Kubernetes namespace with RBAC rules restricting who can create, modify, or delete resources in that namespace. CI/CD service accounts get minimal permissions: deploy to their own namespace, read (but not modify) shared resources. A misconfigured CI/CD pipeline in team A's namespace cannot accidentally delete team B's deployments.

**Network policies.** Default-deny network policies prevent pods in one namespace from communicating with pods in another namespace. Explicit allowlists grant access to shared services (model registry, monitoring endpoints, API gateway). This prevents a compromised or buggy service in one team's namespace from accessing another team's inference endpoints or data.

**Resource quotas.** Per-namespace GPU quotas prevent any single team from consuming all available GPU capacity. Set quotas with headroom: if a team typically uses 4 GPUs, set the quota to 6, allowing burst capacity without permitting unlimited consumption. Alert when a team approaches their quota limit, allowing capacity planning before the quota blocks deployments.

**GPU partitioning.** Namespace isolation without GPU-level isolation is a false sense of security. Two pods from different namespaces scheduled on the same GPU node can still interfere with each other's performance through GPU memory pressure and compute contention. NVIDIA MIG provides hardware-level isolation: each MIG partition has its own memory controller and compute resources. MPS provides software-level sharing with lower overhead but weaker isolation [Source: Pebble, 2025].

## The Noisy Neighbor Problem

### GPU Interference Patterns

The noisy-neighbor problem on GPUs is qualitatively different from CPU-based systems and deserves dedicated attention. Three interference patterns dominate:

**Memory pressure (weight eviction).** When two models share a GPU's memory through MPS or time-slicing, one model's large batch can pressure the unified memory space. If Model A allocates a large KV cache that pushes total memory usage near the GPU's limit, Model B's weights may be evicted to system RAM. The next time Model B runs inference, it must reload weights from system RAM (bandwidth-limited, adding hundreds of milliseconds) or from storage (adding seconds). This manifests as seemingly random latency spikes on Model B that correlate with Model A's traffic patterns.

**Compute contention (MPS).** NVIDIA MPS allows multiple processes to share GPU compute resources through software scheduling. Under light load, MPS works well: both models get the compute they need. Under heavy load, MPS cannot provide strong isolation guarantees. Model A's compute-heavy batch can delay Model B's time-sensitive inference request. NVIDIA reports MPS can achieve 50% cost reduction with approximately 7.5% performance impact under typical workloads, but the impact is higher under contention [Source: Pebble, 2025].

**Memory bandwidth saturation.** GPU performance is often memory-bandwidth limited, not compute limited (as discussed in Chapter 3). Two memory-bandwidth-limited models sharing a GPU compound the bottleneck: both compete for the same HBM bandwidth, and neither can achieve the throughput it would get in isolation. This is the subtlest interference pattern because it manifests as lower throughput rather than latency spikes.

![GPU Noisy Neighbor Effects](../assets/ch04-noisy-neighbor.html)

\newpage

### Detection

Noisy-neighbor interference is difficult to diagnose because the affected model's own metrics look normal in isolation. Detection requires cross-model correlation:

**Correlated latency spikes.** When Model B's P99 latency spikes correlate in time with Model A's traffic increases, the two models are likely interfering. Standard per-model dashboards miss this; you need a cross-model latency correlation view.

**GPU memory thrashing metrics.** NVIDIA DCGM exposes metrics for GPU memory page faults and PCIe data transfer volume. High page fault rates indicate weight eviction and reload cycles. A sudden increase in PCIe transfer volume when no new model is loading suggests weights are being evicted and re-fetched.

**Isolated baseline comparison.** Run the same model on a dedicated GPU and record baseline latency percentiles. Then compare production latency on the shared GPU against this baseline. A persistent gap indicates interference. If the gap grows during peak hours, it confirms the noisy-neighbor hypothesis.

### Mitigation

**MIG for hardware isolation.** Multi-Instance GPU provides the strongest isolation: each partition has dedicated memory and compute resources. The cost is reduced flexibility: MIG partitions are fixed sizes, and reconfiguring them requires stopping all workloads on the GPU. On A100 and H100, MIG supports up to seven partitions of varying sizes [Source: NVIDIA, 2025].

**Workload scheduling constraints.** Kubernetes scheduling rules can prevent incompatible workloads from landing on the same GPU node. Label latency-sensitive models and use anti-affinity rules to separate them from throughput-oriented batch workloads.

**Dedicated GPU pools.** The most reliable mitigation is the simplest: give latency-sensitive models their own GPU pool with no other workloads. This is Pattern 2 applied selectively: share GPUs for fault-tolerant workloads, isolate GPUs for latency-sensitive ones.

**Time-based partitioning.** NVIDIA time-slicing allows multiple workloads to share a GPU by alternating access. This can increase GPU utilization by up to 3x for light workloads [Source: NVIDIA, 2025], but each workload experiences the overhead of context switching. Time-slicing is appropriate for models with bursty, non-overlapping traffic patterns.

## The Evolution: Choosing Your Pattern

### Maturity Model

Most organizations evolve through these patterns rather than choosing one from the start:

**Ad hoc** → **Shared cluster (Pattern 1)** → **Container-per-model (Pattern 2)** → **Platform template (Pattern 3)**

The starting point depends on your organization's size and model count. A startup with one model should not build a platform team. An enterprise with 50 models should not have every team building their own infrastructure.

![Deployment Architecture Maturity](../assets/ch04-maturity-evolution.html)

\newpage

### Migration Signals

Recognizing when to move is as important as knowing where to move:

**From Pattern 1 to Pattern 2:** The signal is deployment coupling. When the second team is blocked by the first team's deployment schedule, or when a deployment failure in one model affects another model's availability, the shared cluster has become a bottleneck. The business impact is measurable: deployment frequency decreases, time-to-production for new models increases, and incident blast radius grows.

**From Pattern 2 to Pattern 3:** The signal is infrastructure duplication. When three or more teams each spend weeks setting up their own CI/CD pipelines, monitoring dashboards, and scaling policies — doing essentially the same work with slight variations — the duplicated effort justifies investing in a platform. The business impact: engineering time spent on infrastructure is time not spent on model quality or product features. LinkedIn's Pro-ML platform was born from exactly this pattern: the platform team provided self-service onboarding that eliminated weeks of per-team infrastructure setup [Source: LinkedIn Engineering, 2022].

**Staying at Pattern 2:** Not every organization needs Pattern 3. If you have 2-4 models maintained by experienced infrastructure engineers, the overhead of building and maintaining a platform may exceed the savings. The platform template pattern pays off when infrastructure setup is a repeated cost across many teams, not when it is a one-time cost for a small number of teams.

**GPU cost as a forcing function.** When GPU costs exceed budget by 30% or more due to fragmentation across isolated deployments, it is time to evaluate shared infrastructure patterns. Stripe's Railyard platform achieved 73% inference cost reduction partly through better GPU utilization enabled by their centralized platform [Source: Stripe Engineering, 2023]. AWS SageMaker multi-model endpoints demonstrate up to 90% cost reduction versus dedicated endpoints for workloads with variable traffic [Source: AWS, 2023].

## Common Pitfalls

- **Over-isolating too early**: a startup spending three months building a platform engineering team before they have served a single model in production. Start with Pattern 1 or Pattern 2; build the platform when you have at least three teams whose deployment patterns are similar enough to templatize
- **Under-isolating at scale**: keeping all models on a shared cluster "because it worked when we started." The architecture that served 2 models and 1 team does not serve 15 models and 5 teams. Watch for the signals: deployment coupling, blast-radius incidents, and inter-team coordination costs
- **Treating the golden path as mandatory**: a platform that does not allow deviation loses teams with legitimate special requirements. The platform should be the easiest path, not the only path. A model that needs a custom GPU configuration or a non-standard framework should be deployable outside the template, with the understanding that the team accepts the operational overhead
- **Ignoring GPU-specific isolation**: namespace isolation in Kubernetes provides security boundaries but no performance isolation. Two models in different namespaces on the same GPU node will still interfere with each other. Use MIG, MPS, or dedicated node pools for models that need performance isolation
- **Building CI/CD for code, not models**: a deployment pipeline designed for 100 MB code artifacts will fail when asked to handle 15 GB model artifacts. Build times, transfer times, and validation steps are all fundamentally different. Design the pipeline for the model lifecycle from the start
- **Centralizing too much**: a platform team that must review and approve every deployment becomes a bottleneck instead of an enabler. Use policy engines (OPA, Kyverno) to enforce guardrails automatically, and reserve human review for changes that affect shared infrastructure

## Summary

- ML inference deployment architecture is the layer between framework selection (Chapter 2) and scaling strategy (Chapter 15) that determines blast radius, deployment independence, GPU efficiency, and team velocity
- Three patterns form a maturity progression: single shared cluster (lowest cost, highest coupling), container-per-model (strongest isolation, highest GPU fragmentation), platform template (best balance at scale, highest upfront investment)
- GPU-specific constraints — scarcity, multi-gigabyte artifacts, and severe noisy-neighbor effects — make deployment architecture for ML inference fundamentally different from traditional microservices deployment
- The noisy-neighbor problem on GPUs manifests as weight eviction, compute contention, and memory bandwidth saturation; detection requires cross-model correlation, not just per-model monitoring
- Infrastructure-as-code for ML deployments should separate persistent resources (model registry, observability storage) from ephemeral compute (GPU instances, inference servers) into distinct workspaces
- CI/CD for models differs from CI/CD for code in artifact size (GB not MB), build time (minutes not seconds), validation approach (statistical quality gates not deterministic tests), and rollback criteria (quality degradation not crashes)
- Shadow deployments are particularly powerful for speech APIs, allowing direct quality comparison by running two models on identical audio streams before affecting users
- Multi-tenant GPU clusters require isolation at four layers: RBAC, network policy, resource quota, and GPU partitioning (MIG/MPS); skipping GPU partitioning creates a false sense of security
- Migration signals are concrete: deployment coupling triggers the move from Pattern 1 to 2; infrastructure duplication across 3+ teams triggers the move from Pattern 2 to 3; GPU cost overruns by 30%+ trigger re-evaluation of isolation boundaries

## What's Next

With deployment architecture established, the next chapter shifts from infrastructure organization to the data that flows through it: real-time audio streams. Chapter 5 covers the end-to-end streaming audio architecture from microphone capture to inference response, including the audio fundamentals every serving engineer must understand.

## References

1. **Uber Engineering** (2022). "Michelangelo: Uber's Machine Learning Platform." Federation layer across multiple K8s clusters with intelligent scheduling.
2. **Anyscale** (2024). "Spotify Hendrix: Ray Clusters on GKE with Kubeflow Orchestration." Spotify's ML platform architecture.
3. **Pinterest Engineering** (2023). "MLEnv: Pinterest's ML Platform." Kubernetes-backed compute platform achieving 95% adoption from under 5%.
4. **Shopify Engineering** (2022). "Merlin: Shopify's ML Platform." Ray clusters as short-lived K8s workspaces; models as standard K8s services.
5. **DoorDash Engineering** (2021). "ML Platform: From Models to Production at DoorDash." 38 models, 6.8M peak predictions/sec, microservice-based K8s pods.
6. **Databricks Summit** (2018). "Bighead: Airbnb's Machine Learning Platform." Evolution from 8-12 week deployment to days.
7. **Netflix/Medium** (2025). "OCI Image Volumes: Separating Model Weights from Runtime Containers."
8. **Stripe Engineering** (2023). "Railyard: Stripe's ML Platform." K8s-based training and 73% inference cost reduction.
9. **LinkedIn Engineering** (2022). "Pro-ML: Model Cloud." Self-service model onboarding with GPU support.
10. **Meta Engineering** (2016). "FBLearner Flow: Managing Facebook's ML Experiments." Per-model containers with auto-scaling.
11. **Lyft Engineering** (2023). "LyftLearn: Hybrid SageMaker-K8s Architecture." Per-team model serving microservices.
12. **AWS** (2023). "SageMaker Multi-Model Endpoints: Cost Optimization." Up to 90% cost reduction vs dedicated endpoints.
13. **Pebble** (2025). "NVIDIA MPS vs Dedicated GPU Allocation for LLM Inference." 50% cost reduction with 7.5% performance impact.
14. **NVIDIA** (2025). "Multi-Instance GPU User Guide." Hardware-level GPU partitioning.
15. **NVIDIA** (2025). "GPU Time-Slicing for Kubernetes." Up to 3x utilization increase for light workloads.
16. **vCluster** (2025). "Noisy Neighbor Effects in GPU Clusters." 45ms inference spiking to 200ms under contention.
17. **Red Hat** (2024). "Golden Paths: Platform Engineering Best Practices."
18. **CNCF** (2024). "Platforms Working Group White Paper." Cloud-native platform engineering patterns.
19. **Skelton, M. & Pais, M.** (2019). *Team Topologies: Organizing Business and Technology Teams for Fast Flow.* IT Revolution Press.
20. **BentoML** (2025). "LLM Inference Handbook." Model artifact sizes and deployment patterns.

---

**Next: [Chapter 5: Streaming Audio Architecture](./05-streaming-audio-architecture.md)**
