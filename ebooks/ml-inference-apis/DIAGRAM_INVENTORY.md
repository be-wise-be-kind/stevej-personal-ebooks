# Diagram Inventory

**Total Planned Diagrams**: 60
**Status**: All diagrams pending -- to be created during chapter authoring PRs
**Template**: `.ai/templates/html-diagram.html`
**Quality Guide**: `.ai/howto/evaluating-diagram-quality.md`
**Location**: `ebooks/ml-inference-apis/assets/`

---

## Chapter 1: The Serving Problem (4 diagrams)

| Filename | Description | Status |
|----------|-------------|--------|
| ch01-opener.html | Chapter opener illustration -- the serving engineer's role bridging trained models and production APIs | Pending |
| ch01-latency-breakdown.html | Inference request latency anatomy: network transit, request parsing, queue wait, model loading, GPU compute, post-processing, response serialization, network transit -- with ms annotations at each stage | Pending |
| ch01-serving-landscape.html | ML inference framework ecosystem map showing three generations (TF Serving/TorchServe, Triton/KServe/BentoML, vLLM/SGLang/TensorRT-LLM) and their relationships | Pending |
| ch01-innovation-timeline.html | Timeline of key ML inference innovations: PagedAttention, continuous batching, FlashAttention versions, FP8/FP4 quantization, speculative decoding | Pending |

---

## Chapter 2: Model Serving Frameworks (4 diagrams)

| Filename | Description | Status |
|----------|-------------|--------|
| ch02-opener.html | Chapter opener illustration -- the framework selection decision | Pending |
| ch02-framework-decision-tree.html | Decision tree for framework selection based on model type, latency requirements, scaling model, and operational complexity -- leads to specific framework recommendations | Pending |
| ch02-multi-model-architecture.html | Multi-model serving architecture showing GPU memory management (MPS/MIG), ensemble pipelines (VAD, ASR, punctuation, NER), and model routing | Pending |
| ch02-framework-generations.html | Three-generation timeline of serving frameworks: Gen 1 (framework-specific), Gen 2 (multi-framework orchestration), Gen 3 (LLM-optimized engines) with key features at each generation | Pending |

---

## Chapter 3: GPU Optimization & Cold Starts (5 diagrams)

| Filename | Description | Status |
|----------|-------------|--------|
| ch03-opener.html | Chapter opener illustration -- GPU utilization and optimization | Pending |
| ch03-batching-comparison.html | Side-by-side comparison of static batching, dynamic batching, and continuous batching -- showing how requests flow through each approach with throughput/latency tradeoffs | Pending |
| ch03-kv-cache-paging.html | PagedAttention visualization: traditional contiguous allocation vs paged allocation with fixed-size blocks, showing memory fragmentation reduction | Pending |
| ch03-cold-start-anatomy.html | Cold start timeline breakdown: container spin-up, runtime initialization, CUDA context creation, model weight loading, warm-up inference -- with time annotations for each phase | Pending |
| ch03-quantization-tradeoffs.html | Quantization precision spectrum (FP32, FP16, BF16, FP8, FP4, INT8, INT4) showing memory reduction, throughput improvement, and quality impact at each level | Pending |

---

## Chapter 4: Streaming Audio Architecture (4 diagrams)

| Filename | Description | Status |
|----------|-------------|--------|
| ch04-opener.html | Chapter opener illustration -- end-to-end streaming audio pipeline | Pending |
| ch04-e2e-architecture.html | End-to-end streaming architecture: client audio capture, codec encoding, transport (WebSocket/gRPC), server receive, VAD, inference engine, post-processing, response stream back to client | Pending |
| ch04-chunk-size-tradeoff.html | Chunk size selection tradeoff diagram: smaller chunks (100ms) provide lower latency but less context vs larger chunks (250ms) provide better accuracy but higher latency -- with provider examples | Pending |
| ch04-provider-comparison.html | Provider comparison table/diagram: Deepgram (WebSocket, binary, 100ms chunks), AssemblyAI (WebSocket, sub-300ms), Google (gRPC, 25KB limit), Amazon (WebSocket+HTTP/2, 15s blocks), OpenAI (WebRTC+WebSocket+SIP) | Pending |

---

## Chapter 5: Protocol Selection for Audio (4 diagrams)

| Filename | Description | Status |
|----------|-------------|--------|
| ch05-opener.html | Chapter opener illustration -- protocol selection for audio streaming | Pending |
| ch05-protocol-decision-tree.html | Decision tree for protocol selection: client constraints (browser vs server), latency targets, bidirectionality needs, NAT traversal requirements -- leading to WebSocket, gRPC, WebRTC, or WebTransport recommendations | Pending |
| ch05-binary-vs-base64.html | Binary vs base64 encoding comparison: bandwidth overhead (33% increase for base64), CPU cost of encoding/decoding, when each is appropriate (binary WebSocket frames vs JSON-wrapped base64) | Pending |
| ch05-protocol-comparison-table.html | Protocol comparison matrix: WebSocket, gRPC, WebRTC, WebTransport, MoQ -- comparing latency, browser support, NAT traversal, reliability, production readiness, and which providers use each | Pending |

---

## Chapter 6: Streaming Inference Pipelines (4 diagrams)

| Filename | Description | Status |
|----------|-------------|--------|
| ch06-opener.html | Chapter opener illustration -- streaming inference pipeline | Pending |
| ch06-streaming-pipeline.html | Streaming inference pipeline: transport layer receive, request queue, scheduler, inference engine (with partial/incremental decoding), post-processing, response stream -- showing data flow and buffering points | Pending |
| ch06-concurrent-streams.html | Concurrent stream handling on a single server instance: multiple client connections multiplexed to shared inference engine with per-stream state management and GPU resource allocation | Pending |
| ch06-degradation-strategies.html | Graceful degradation strategies under load: quality reduction (lower sample rate, simpler model), request queuing with backpressure, request rejection with retry guidance -- decision flow based on load level | Pending |

---

## Chapter 7: Designing ML-Facing APIs (3 diagrams)

| Filename | Description | Status |
|----------|-------------|--------|
| ch07-opener.html | Chapter opener illustration -- ML API design patterns | Pending |
| ch07-sync-vs-async-decision.html | Sync vs async API pattern decision: short inference (<1s) uses synchronous request/response, medium inference (1-30s) uses streaming/SSE, long inference (>30s) uses long-running operations (AIP-151 pattern) with polling | Pending |
| ch07-error-handling-taxonomy.html | Error handling taxonomy for ML APIs: model-specific failures (not loaded, GPU OOM, inference timeout), request-level errors (invalid input, queue full), and appropriate HTTP/gRPC status codes for each | Pending |

---

## Chapter 8: Streaming Response Contracts (4 diagrams)

| Filename | Description | Status |
|----------|-------------|--------|
| ch08-opener.html | Chapter opener illustration -- streaming response contract design | Pending |
| ch08-streaming-response-patterns.html | Streaming response design patterns: SSE with `data:` prefix and `[DONE]` signal (OpenAI pattern), WebSocket message schemas with interim/final results, gRPC server streaming with typed responses | Pending |
| ch08-connection-lifecycle.html | Connection lifecycle for streaming inference: connection establishment, authentication, streaming session, keep-alive/heartbeat, graceful shutdown, error termination -- with state transitions | Pending |
| ch08-interim-final-results.html | Interim vs final results flow: partial transcription updates arriving progressively, stability indicators, finalization signals, and client-side rendering strategies | Pending |

---

## Chapter 9: API Versioning & Developer Experience (4 diagrams)

| Filename | Description | Status |
|----------|-------------|--------|
| ch09-opener.html | Chapter opener illustration -- API versioning and developer experience | Pending |
| ch09-versioning-strategies.html | API versioning strategies: URL path versioning (/v1/), header versioning, content negotiation -- and how model versions map to API versions (model v2 behind API v1, canary routing) | Pending |
| ch09-two-axis-versioning.html | Two-axis versioning: API version (contract stability) vs model version (capability evolution) -- showing independent lifecycle management and the mapping between them | Pending |
| ch09-developer-journey.html | Developer journey through an ML API: discovery, authentication, first API call, streaming integration, SDK adoption, version migration -- with friction points and DX optimizations at each stage | Pending |

---

## Chapter 10: Security for Audio ML APIs (4 diagrams)

| Filename | Description | Status |
|----------|-------------|--------|
| ch10-opener.html | Chapter opener illustration -- security for audio ML APIs | Pending |
| ch10-streaming-auth-flow.html | Streaming authentication flow: initial token validation on WebSocket upgrade/gRPC connection, per-message authorization, token refresh during long-running streams, connection termination on auth failure | Pending |
| ch10-api-key-lifecycle.html | API key lifecycle: generation (with scoping to endpoints/features), distribution, rotation schedule, usage monitoring, revocation -- showing the complete key management flow | Pending |
| ch10-pii-redaction-pipeline.html | PII redaction pipeline for audio transcripts: raw transcript, entity detection (names, SSN, credit cards, addresses), redaction (masking, replacement, removal), audit logging of redaction events | Pending |

---

## Chapter 11: Compliance & Data Governance (4 diagrams)

| Filename | Description | Status |
|----------|-------------|--------|
| ch11-opener.html | Chapter opener illustration -- compliance and data governance | Pending |
| ch11-eu-ai-act-timeline.html | EU AI Act implementation timeline: Prohibited practices (Feb 2025), GPAI obligations (Aug 2025), High-risk + transparency rules (Aug 2026), Regulated products (Aug 2027) -- with penalty ranges (up to EUR 35M / 7% turnover) | Pending |
| ch11-compliance-matrix.html | Compliance requirements matrix: SOC 2, HIPAA, GDPR, CCPA, EU AI Act -- cross-referenced with audio ML API requirements (encryption, audit logging, data retention, PII handling, consent, BAAs) | Pending |
| ch11-data-lifecycle.html | Audio data lifecycle: ingestion (with consent), processing (inference), storage (encrypted, regional), retention (configurable TTL), deletion (verified erasure), audit trail at each stage | Pending |

---

## Chapter 12: SLOs for Streaming ML Systems (4 diagrams)

| Filename | Description | Status |
|----------|-------------|--------|
| ch12-opener.html | Chapter opener illustration -- SLOs for streaming ML systems | Pending |
| ch12-streaming-sli-taxonomy.html | Streaming SLI taxonomy: latency metrics (TTFT, TPOT, inter-token, E2E), quality metrics (WER, goodput, RTF), reliability metrics (connection drops, reconnection success, availability) -- organized by category | Pending |
| ch12-slo-target-framework.html | SLO target framework: interactive agent (TTFT <= 100ms P95), voice AI (TTFT <= 300ms P95), batch (P95 Final <= 800ms) -- with user experience impact at each threshold level | Pending |
| ch12-burn-rate-alerting.html | SLO burn rate alerting: error budget consumption over time, fast-burn alert (2% budget in 1 hour), slow-burn alert (5% budget in 6 hours), budget exhaustion projection -- with alert configuration | Pending |

---

## Chapter 13: Usage Metering & Billing (4 diagrams)

| Filename | Description | Status |
|----------|-------------|--------|
| ch13-opener.html | Chapter opener illustration -- usage metering and billing architecture | Pending |
| ch13-metering-architecture.html | Metering architecture: API request, idempotent event emission, event queue, aggregation pipeline, billing period roll-up -- showing the path from API call to invoice line item | Pending |
| ch13-billing-model-comparison.html | Billing model comparison: per-second (Deepgram, AssemblyAI), per-15-second-block (AWS), per-character (ElevenLabs), per-token (OpenAI) -- with cost impact analysis for different usage patterns | Pending |
| ch13-stripe-integration.html | Stripe Meters API integration: meter definition, event ingestion via API, aggregation, subscription billing period, invoice generation -- showing the end-to-end Stripe flow | Pending |

---

## Chapter 14: Scaling Inference Globally (4 diagrams)

| Filename | Description | Status |
|----------|-------------|--------|
| ch14-opener.html | Chapter opener illustration -- scaling inference globally | Pending |
| ch14-autoscaling-signals.html | Auto-scaling signal hierarchy: GPU utilization, request queue depth, latency P95, memory pressure -- showing which signals to use for scale-up vs scale-down decisions with hysteresis | Pending |
| ch14-multi-region-architecture.html | Multi-region inference deployment: model replicas across regions, request routing (latency-based, geography-based), data sovereignty boundaries, model synchronization strategy | Pending |
| ch14-cost-optimization-strategies.html | Cost optimization strategies: persistent pool for baseline traffic + spot/preemptible for burst, scheduled scaling for predictable patterns, right-sizing GPU instances, quantization for cost reduction | Pending |

---

## Chapter 15: Putting It All Together (4 diagrams)

| Filename | Description | Status |
|----------|-------------|--------|
| ch15-opener.html | Chapter opener illustration -- complete production system | Pending |
| ch15-complete-architecture.html | Complete production architecture: client, API gateway (auth, metering, rate limiting), load balancer, inference cluster (framework, GPU optimization, model serving), streaming pipeline, monitoring/SLOs, compliance layer -- the full system from Chapters 1-14 | Pending |
| ch15-decision-flowchart.html | Decision flowchart for building a production inference API: framework selection, protocol choice, API design pattern, billing model, security posture, compliance requirements, scaling strategy -- key decision points from each chapter | Pending |
| ch15-runbook-patterns.html | Operational runbook patterns: cold start remediation, GPU OOM response, model rollback, connection storm handling, SLO burn rate response, compliance incident response -- with decision trees for each scenario | Pending |

---

## Summary

| Chapter | Diagrams | Status |
|---------|----------|--------|
| Ch 1: The Serving Problem | 4 | All Pending |
| Ch 2: Model Serving Frameworks | 4 | All Pending |
| Ch 3: GPU Optimization & Cold Starts | 5 | All Pending |
| Ch 4: Streaming Audio Architecture | 4 | All Pending |
| Ch 5: Protocol Selection for Audio | 4 | All Pending |
| Ch 6: Streaming Inference Pipelines | 4 | All Pending |
| Ch 7: Designing ML-Facing APIs | 3 | All Pending |
| Ch 8: Streaming Response Contracts | 4 | All Pending |
| Ch 9: API Versioning & Developer Experience | 4 | All Pending |
| Ch 10: Security for Audio ML APIs | 4 | All Pending |
| Ch 11: Compliance & Data Governance | 4 | All Pending |
| Ch 12: SLOs for Streaming ML Systems | 4 | All Pending |
| Ch 13: Usage Metering & Billing | 4 | All Pending |
| Ch 14: Scaling Inference Globally | 4 | All Pending |
| Ch 15: Putting It All Together | 4 | All Pending |
| **Total** | **60** | **All Pending** |

---

*Last updated: February 2026*
*All diagrams use HTML with embedded SVG, created from `.ai/templates/html-diagram.html`*
