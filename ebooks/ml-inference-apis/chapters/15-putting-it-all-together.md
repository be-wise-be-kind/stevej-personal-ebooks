# Chapter 15: Putting It All Together

![Chapter 15 Opener](../assets/ch15-opener.html)

\newpage

## Overview

- Synthesizing every decision from the book into a single coherent system -- from blank canvas to production streaming speech API
- Walking through common failure modes, operational runbooks, and the recovery patterns that keep inference systems running
- Looking ahead at the evolving landscape and the serving engineer's ongoing discipline

## Case Study: Building a Production Streaming Speech API

### The Scenario

- A team is tasked with building a real-time speech-to-text API that supports streaming audio input and streaming transcript output
- Requirements: sub-300ms perceived latency, multi-tenant with per-customer billing, available in three regions (US, EU, Asia-Pacific), SOC 2 compliant
- The team has a trained ASR model (Whisper-derived, ~1.5B parameters) and must take it from artifact to production
- Budget: moderate -- the company is past startup phase but cost-conscious, targeting positive unit economics within six months

### Starting with the Model Artifact

- The trained model is a PyTorch checkpoint -- the serving team receives weights, tokenizer, and a reference inference script
- First decision: what framework to serve it with -- evaluating against the criteria from Chapter 2
- For a Whisper-derived model with streaming requirements, the choice narrows to vLLM (if using attention-based decoding) or a custom pipeline on Triton (if the model has non-standard components)
- Profiling the model: memory footprint, inference latency per audio chunk, maximum batch size on target GPU class

> **From Book 1:** For foundational performance profiling methodology, see "Before the 3 AM Alert" Chapter 1: The Empirical Discipline.

### Framework Selection Decision

- Evaluating vLLM, TensorRT-LLM, and Triton against: model compatibility, streaming support, operational complexity, team expertise (Chapter 2)
- TensorRT-LLM chosen for the core inference engine: best throughput on NVIDIA hardware, FP8 quantization support for the target H100 GPUs
- Triton as the orchestration layer: manages the multi-model pipeline (VAD + ASR + punctuation), handles request scheduling
- The tradeoff acknowledged: higher setup complexity in exchange for maximum performance on the target hardware

### GPU Optimization Choices

- FP8 quantization reduces model size from 3GB to 1.5GB, enabling larger batch sizes on a single H100 (Chapter 3)
- CUDA graph compilation for the fixed-shape portions of the inference pipeline, avoiding kernel launch overhead
- Pre-allocated KV cache and audio buffer pools to eliminate runtime memory allocation
- Cold start mitigation: model weights baked into the container image, warm-up inference runs during readiness probe period

## Architecture Walkthrough: End-to-End

### Audio Input Path

- Client connects via WebSocket (primary) or gRPC (high-performance clients) -- protocol selection from Chapter 5
- Audio arrives as Opus-encoded chunks at 20ms intervals (50 chunks per second)
- Edge proxy terminates TLS, authenticates the API key, and routes to the correct region based on customer configuration (Chapter 10)
- The WebSocket connection is pinned to a specific inference instance for the duration of the stream -- sticky session routing

### The Inference Pipeline

- **Stage 1: Audio Decoding** -- Opus chunks decoded to PCM samples, resampled to 16kHz mono if needed
- **Stage 2: Voice Activity Detection (VAD)** -- Silero VAD or equivalent identifies speech segments, suppresses silence to reduce unnecessary inference
- **Stage 3: Audio Buffering** -- Speech chunks accumulated into inference-ready windows (e.g., 1-second segments with overlap)
- **Stage 4: ASR Inference** -- Buffered audio processed by the quantized Whisper model on GPU, producing token sequences
- **Stage 5: Token Decoding and Punctuation** -- Tokens decoded to text, punctuation model adds periods, commas, question marks
- **Stage 6: Partial Result Assembly** -- Partial transcripts assembled, compared against previous partials, stability markers applied
- Pipeline from Chapter 6 realized end-to-end with Triton's ensemble scheduler managing the DAG

![Complete System Architecture](../assets/ch15-complete-architecture.html)

\newpage

### Transcript Output Path

- Partial results streamed back to the client over the same WebSocket connection as JSON messages
- Each message includes: transcript text, confidence score, word-level timestamps, is_final flag, sequence number
- Final results emitted when the VAD detects end-of-utterance or the client sends an end-of-stream signal
- API response format follows the design patterns from Chapter 7 -- consistent envelope, cursor-based sequencing, error codes

### Supporting Infrastructure

- **API Gateway**: rate limiting, authentication, request routing, protocol translation (Chapter 7, Chapter 10)
- **Usage Metering**: every audio second processed is metered and attributed to the customer's account (Chapter 13)
- **Observability Stack**: distributed traces from client connection through every pipeline stage, GPU metrics, per-stream latency histograms (Chapter 12)
- **Model Registry**: tracks which model version is deployed in each region, supports rollback (Chapter 2)
- **Configuration Service**: feature flags, per-customer settings, rate limits synchronized across regions

## Decision Points Mapped to Chapters

### Infrastructure Decisions

- **Which serving framework?** Chapter 2 -- Framework selection criteria: model type, latency requirements, scaling model, operational complexity
- **How to optimize GPU usage?** Chapter 3 -- Quantization (FP8), CUDA graphs, memory pooling, cold start mitigation
- **How to scale globally?** Chapter 14 -- GPU-aware load balancing, auto-scaling signals, multi-region deployment, cost optimization

### Streaming and Protocol Decisions

- **How to handle streaming audio?** Chapter 4 -- Chunk-based streaming, jitter buffers, backpressure, codec selection
- **Which protocol for audio transport?** Chapter 5 -- WebSocket for broad compatibility, gRPC for high-performance clients, WebRTC for browser-native real-time
- **How to build the inference pipeline?** Chapter 6 -- Multi-stage pipeline with VAD gating, overlap buffering, partial result streaming

### API and Business Decisions

- **How to design the API?** Chapter 7 -- Streaming endpoint design, error handling, versioning, SDK patterns
- **How to design streaming response contracts?** Chapter 8 -- Streaming response formats, partial result semantics, client contract guarantees
- **How to version APIs and optimize developer experience?** Chapter 9 -- API versioning strategies, deprecation policies, SDK design, developer portal patterns
- **How to meter and bill?** Chapter 13 -- Per-second metering, idempotent usage events, billing pipeline, revenue reconciliation

### Enterprise Decisions

- **How to secure audio data?** Chapter 10 -- TLS, API key management, audio encryption at rest, tenant isolation
- **How to meet compliance requirements?** Chapter 11 -- GDPR for voice biometrics, SOC 2 controls, data retention, audit logging
- **How to define and monitor SLOs?** Chapter 12 -- Availability, latency, stream success rate, error budgets for streaming systems

![Decision Flowchart: Major Architecture Choices](../assets/ch15-decision-flowchart.html)

\newpage

## What Goes Wrong and How to Recover

### GPU Out-of-Memory (OOM)

- **Cause**: batch size too large, KV cache exhaustion, memory leak in inference pipeline, unexpected input length
- **Symptoms**: CUDA OOM error, inference process crash, all active streams on the instance fail simultaneously
- **Immediate response**: the instance is marked unhealthy, load balancer stops routing new requests, active streams are redistributed to healthy instances
- **Recovery**: the process restarts, reloads the model, and re-enters the serving pool -- total recovery time: 1-3 minutes depending on model size
- **Prevention**: memory limits on batch size, KV cache caps, input length validation, canary deployments that test with production-like loads

### Cold Start Storms

- **Cause**: a scaling event brings up many new instances simultaneously, all competing for GPU resources and model downloads
- **Symptoms**: mass cold start latency, storage bandwidth saturation (many instances pulling model weights concurrently), cascading timeouts
- **Immediate response**: rate-limit instance creation to avoid overwhelming shared resources (model storage, container registry)
- **Recovery**: stagger instance starts, use local model caching, pre-position model artifacts in regional storage
- **Prevention**: warm pool of pre-provisioned instances, predictive scaling, model weights baked into container images

### Stream Disconnection Cascades

- **Cause**: a network partition, instance failure, or deployment event disconnects many streams simultaneously
- **Symptoms**: spike in WebSocket close events, surge in reconnection attempts, potential thundering herd on remaining instances
- **Immediate response**: client-side exponential backoff with jitter prevents reconnection storms; server-side connection admission control limits concurrent new connections
- **Recovery**: clients reconnect, resume from last confirmed sequence number, the pipeline re-establishes stream state
- **Prevention**: graceful drain before deployments, connection migration for planned events, multi-instance stream redundancy for critical customers

### Model Version Rollback

- **Cause**: a newly deployed model version degrades transcription quality -- higher word error rate, missing punctuation, language detection failures
- **Symptoms**: quality metric degradation detected by automated evaluation or customer complaints
- **Immediate response**: traffic shifted back to the previous model version using model registry labels -- "production" label moved from v2 to v1
- **Recovery**: full rollback completes within minutes as instances reload the previous version; canary instances with the bad version are drained
- **Prevention**: canary deployment with automated quality evaluation (word error rate on a reference dataset), shadow mode testing before live traffic exposure

### Billing Discrepancies

- **Cause**: metering events lost due to queue failures, double-counted due to retry logic, or attributed to the wrong customer due to routing bugs
- **Symptoms**: customer complaints about unexpected charges, revenue reconciliation mismatches, audit failures
- **Immediate response**: isolate the affected metering pipeline, switch to conservative (under-count) mode while investigating
- **Recovery**: replay metering events from the event log, reconcile against inference logs, issue credits for overcharges
- **Prevention**: idempotent metering with deduplication keys, end-to-end metering pipeline testing, daily reconciliation between metering and inference logs

### Latency Degradation Without Obvious Cause

- **Cause**: GPU thermal throttling, noisy neighbor on shared infrastructure, memory fragmentation after long uptime, driver bug
- **Symptoms**: gradual P95/P99 latency increase with no corresponding traffic increase
- **Immediate response**: compare affected instances against healthy baselines -- check GPU clock speeds, memory utilization, process uptime
- **Recovery**: rolling restart of affected instances clears memory fragmentation; instance replacement addresses hardware issues
- **Prevention**: periodic instance recycling (restart instances on a schedule), GPU health monitoring with proactive drain

## Operational Runbook Patterns

### Deployment Checklist

- **Pre-deployment**: model quality validation on reference dataset, load test on staging with production-like traffic patterns, GPU memory profiling
- **Canary phase**: deploy to 1-2% of traffic in a single region, monitor word error rate, latency, GPU utilization, error rate for minimum 30 minutes
- **Regional rollout**: deploy region-by-region with 15-minute soak periods between regions, monitoring per-region SLOs
- **Full deployment**: all regions serving the new version, canary instances decommissioned, rollback artifacts retained for 72 hours
- **Post-deployment**: 24-hour watch period with lowered alerting thresholds, automated quality comparison against pre-deployment baseline

### Incident Response for Inference Systems

- **Detection**: SLO burn rate alerts (Chapter 12), GPU health alerts, customer-reported quality degradation
- **Triage**: is this a capacity issue (need more instances), a quality issue (bad model version), an infrastructure issue (GPU failure, network), or a dependency issue (model storage, config service)?
- **Containment**: for capacity -- emergency scale-up; for quality -- rollback model version; for infrastructure -- drain affected instances; for dependency -- activate fallback/cached configuration
- **Resolution**: root cause analysis after containment, fix applied and verified, postmortem written with action items
- **Communication**: status page updates during incident, customer-facing RCA for significant events

![Operational Runbook Decision Tree](../assets/ch15-runbook-patterns.html)

\newpage

### Capacity Planning

- **Demand forecasting**: project inference demand based on customer pipeline, seasonal patterns, and product roadmap
- **GPU procurement lead time**: GPU supply is constrained -- plan 3-6 months ahead for reserved capacity, longer for specialized hardware
- **Cost modeling**: maintain a model that maps projected request volume to GPU-hours to dollars, updated monthly
- **Headroom targets**: maintain 30-40% headroom above peak demand for safety margin -- more headroom costs money, less headroom risks SLO violations
- **Quarterly review**: compare actual demand against forecast, adjust reserved instance commitments and spot fleet policies

### Model Update Procedures

- **Model acceptance testing**: automated evaluation suite runs against the new model before any production deployment -- word error rate, latency per audio second, GPU memory usage
- **Shadow deployment**: new model serves production traffic in parallel with the active model, results compared but not returned to users
- **A/B testing**: when quality differences are subtle, route a percentage of traffic to each version and measure user-facing metrics
- **Rollback criteria**: define explicit thresholds -- if word error rate increases by >2% or P95 latency increases by >50ms, automatic rollback triggers
- **Model deprecation**: old versions are retained for 30 days after replacement, then archived -- GPU memory is too expensive for indefinite retention

## The Evolving Landscape

### Hardware Evolution

- **NVIDIA Blackwell (B200)**: 2-4x inference performance over H100, native FP4 support, larger GPU memory -- changes the cost equation for large model serving
- **AMD MI300X and Intel Gaudi 3**: competitive GPU alternatives emerging -- multi-vendor GPU fleets become practical, reducing NVIDIA dependency
- **Inference-specific accelerators**: AWS Inferentia, Google TPU v5e, custom ASICs designed for inference rather than training -- lower cost per inference for standard architectures
- **The trend**: inference cost per token/second is dropping rapidly, enabling new use cases but also requiring continuous infrastructure optimization to stay competitive

### Protocol Evolution

- **Media over QUIC (MoQ)**: IETF standard for low-latency media transport -- may replace WebSocket for audio streaming with better congestion control and multiplexing
- **WebTransport maturity**: browser-native, QUIC-based transport gaining adoption -- bidirectional streams without TCP head-of-line blocking
- **The protocol convergence**: WebRTC for browser real-time, gRPC for service-to-service, WebSocket declining as MoQ and WebTransport mature

### Quantization Frontiers

- **FP4 inference**: halving memory again from FP8, enabling 2x larger batches or models on the same hardware
- **Mixed-precision serving**: different layers of the model at different precisions based on sensitivity analysis
- **Quantization-aware fine-tuning**: models trained with quantization in mind, closing the quality gap between FP16 and FP4/INT4

### Multimodal and Agent Inference

- **Multimodal models**: single models processing audio + text + image simultaneously -- serving infrastructure must handle heterogeneous input streams
- **Agent workloads**: LLM agents making tool calls that trigger additional inference -- cascading inference chains with variable latency
- **Speech-to-speech models**: direct audio-in to audio-out without intermediate text -- changes the pipeline architecture entirely (no separate ASR + TTS stages)
- **The implication for serving engineers**: pipeline complexity increases, but the fundamental patterns (streaming, batching, scaling, monitoring) remain

### Edge and On-Device Inference

- **Smaller, distilled models**: purpose-built for on-device inference -- VAD, wake word detection, basic ASR running on phones and IoT devices
- **Hybrid edge-cloud architectures**: device runs a small model for initial processing, cloud handles the heavy inference -- reduces bandwidth and latency
- **Privacy-first inference**: sensitive audio processed entirely on-device, only anonymized metadata sent to the cloud
- **WebGPU and WASM**: browser-based inference for lightweight models, eliminating the network hop entirely

### Staying Current

- The inference serving landscape changes quarterly -- new frameworks, new hardware, new quantization techniques
- Build abstractions that isolate your system from specific technology choices -- swap the inference engine without changing the API
- Invest in benchmarking infrastructure: the ability to quickly evaluate a new framework or GPU against your workload is a competitive advantage
- Community engagement: vLLM, SGLang, Triton communities are where operational knowledge is shared before it reaches documentation

## The Serving Engineer's Discipline

### What This Book Has Covered

- From a trained model artifact to a globally distributed, auto-scaling, metered, secure, compliant, observable inference API
- The technical depth: GPU optimization, streaming protocols, pipeline design, API patterns, billing systems, security controls, SLO frameworks, scaling strategies
- The overarching theme: measurement-driven decisions, not cargo-cult optimization -- every choice grounded in observable metrics and business requirements

### The Mindset

- The serving engineer's job is never done -- models change, traffic patterns shift, hardware evolves, customer requirements expand
- Operational excellence is the moat: anyone can deploy a model; keeping it fast, cheap, reliable, and compliant at scale is the hard part
- The discipline bridges software engineering, systems engineering, and ML infrastructure -- breadth matters as much as depth
- Invest in automation: manual operational work does not scale -- if you do it twice, automate it

### Building the Practice

- Start with observability: you cannot improve what you cannot measure -- instrument everything before optimizing anything
- Define SLOs early: they are the framework for every trade-off decision -- latency vs cost, availability vs complexity, features vs stability
- Build for change: the inference engine, the model, the protocol, the GPU -- all will change within 18 months -- design for replaceability
- Document decisions: future you (or your successor) needs to understand why the system is built this way, not just how

> **From Book 1:** For the foundational philosophy of measurement-driven engineering and building observable systems, see "Before the 3 AM Alert" Chapter 14: Putting It All Together.

## Common Pitfalls

- **Building without SLOs**: deploying an inference system without defined SLOs means every performance question becomes a debate rather than a measurement
- **Optimizing before measuring**: premature GPU optimization wastes engineering time -- profile first, then optimize the actual bottleneck
- **Ignoring the business layer**: a technically excellent inference system that cannot accurately bill customers or meet compliance requirements is not production-ready
- **Treating the architecture as static**: the system designed today will need significant changes within a year -- build for evolution, not perfection
- **Skipping the runbook**: incident response without documented runbooks means every outage is improvised -- the runbook turns a crisis into a procedure
- **Neglecting the edge cases**: the happy path works; production is about the 5% of requests that encounter codec mismatches, network partitions, GPU failures, or billing edge cases

## Summary

- A production streaming speech API integrates decisions from every chapter: framework selection, GPU optimization, streaming architecture, protocol choice, pipeline design, API design, streaming response contracts, API versioning, metering, security, compliance, SLOs, and scaling
- The end-to-end architecture spans: client connection (WebSocket/gRPC) through edge proxy, audio decoding, VAD, buffered ASR inference, token decoding, and partial result streaming
- Common failure modes -- GPU OOM, cold start storms, stream disconnection cascades, model rollback, billing discrepancies -- each have distinct detection, response, and prevention patterns
- Operational runbooks for deployment, incident response, capacity planning, and model updates are as important as the code itself
- The inference serving landscape is evolving rapidly: new GPUs (B200), new protocols (MoQ, WebTransport), new quantization (FP4), multimodal and agent workloads
- The serving engineer's discipline: measure first, define SLOs, build for change, automate operations, document decisions
- This book has been a guide from trained model to production system -- the rest is practice, measurement, and continuous improvement

## References

*To be populated during chapter authoring. Synthesis chapter -- references back to all earlier chapters:*

1. Chapters 1-14 of this book, referenced throughout for specific technical depth.
2. "Before the 3 AM Alert: What Every Developer Should Know About API Performance" -- Chapter 1 (empirical discipline), Chapter 9 (scaling), Chapter 12 (geographic optimization), Chapter 14 (synthesis).
3. OpenAI (2025). "Realtime API: WebRTC and WebSocket Integration Guide."
4. NVIDIA (2025). "Blackwell Architecture: Inference Performance Benchmarks."
5. IETF (2025). "Media over QUIC Transport (MoQ) -- Draft Specification."

---

*This concludes "Productionizing ML Inference APIs: A Serving Engineer's Guide to Real-Time Speech and Audio." The patterns, decisions, and trade-offs covered here will evolve as hardware, frameworks, and protocols advance -- but the discipline of measurement-driven serving engineering endures. Build observable systems, define your SLOs, and let the data guide your optimizations.*
