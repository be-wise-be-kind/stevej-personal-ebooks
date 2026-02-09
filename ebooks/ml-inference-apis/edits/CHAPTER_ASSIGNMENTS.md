# Chapter Assignments

Per-chapter specifications for authoring "Productionizing ML Inference APIs." Each entry contains key concepts, diagrams, cross-references, research topics, and priority notes to guide the authoring agent.

---

## Preface

**Key Concepts**:
- Why this book exists -- the gap between training a model and serving it in production
- Target audience: backend engineers, platform engineers, SREs, tech leads, API engineers
- What the reader will learn (serving, not training)
- How to read the book (five parts, sequential or selective)
- Relationship to "Before the 3 AM Alert" (companion, not replacement)
- What this book does NOT cover (training, data pipelines, model architecture, frontend SDKs)
- Conventions: pseudocode, citations, cross-references, provider examples, the 300ms rule

**Suggested Diagrams**: None (preface does not include diagrams)

**Cross-References to Book 1**: "Before the 3 AM Alert" referenced as companion book; explain what Book 1 covers (observability, caching, protocols, scaling, auth) and how Book 2 builds on it

**Cross-References to Other Chapters**: Overview of all five parts and 13 chapters

**Research Topics**: None -- preface is written last, after all chapters are complete, based on the final content

**Estimated Word Count**: 1000-1500

**Priority Notes**: Write LAST (PR15). The preface must accurately reflect the final content of all chapters. It should be direct and informative, not promotional.

---

## Chapter 1: The Serving Problem

**Key Concepts**:
- The serving engineer's role: bridging research and production
- Why ML inference serving is a distinct engineering discipline
- The problem landscape: GPU costs, latency budgets, cold starts, model lifecycle, talent gap
- How speech/audio differs from other inference (continuous streams, 300ms rule, codec-dependent, bidirectional)
- Industry context: LLM revolution, speech/audio AI renaissance (2024-2026)
- Batch vs real-time vs streaming inference -- when to use which
- The difficulties: GPU utilization, latency anatomy of an inference request, cold start problem, model lifecycle
- The innovations: continuous batching, PagedAttention, quantization (FP8/FP4), speculative decoding
- The serving framework landscape (three generations)
- The business case: user experience, cost, competitive advantage
- This book's approach: measurement-driven, serving not training, audio as running example

**Suggested Diagrams**:
- ch01-opener.html (chapter opener)
- ch01-latency-breakdown.html (inference request latency anatomy with ms annotations)
- ch01-serving-landscape.html (framework ecosystem map, three generations)
- ch01-innovation-timeline.html (key innovations timeline)

**Cross-References to Book 1**: Ch 1 (The Empirical Discipline -- measurement-driven philosophy), Ch 3 (Observability), Ch 5 (Network & Connection -- protocol fundamentals)

**Cross-References to Other Chapters**: Forward references to all Parts (I-V) and chapters as a roadmap for the book

**Research Topics**: Topics 1 (ML Inference Serving Frameworks), 2 (GPU Optimization Advances), 3 (Real-Time Speech/Audio API Landscape), 8 (SLOs for Streaming ML)

**Estimated Word Count**: 5000-7000

**Priority Notes**: This is the most important chapter. It sets the tone and philosophy for the entire book. Must be the most detailed outline of any chapter. Direct, informative exposition -- no fictional scenario or narrative hook. Include specific numbers from research (benchmarks, pricing, latency figures). Reference competitor APIs by name.

---

## Chapter 2: Model Serving Frameworks

**Key Concepts**:
- Three generations of frameworks: Gen 1 (TF Serving, TorchServe), Gen 2 (Triton, KServe, BentoML, Ray Serve), Gen 3 (vLLM, SGLang, TensorRT-LLM)
- Framework selection criteria: model type, latency requirements, scaling model, operational complexity
- Detailed comparison: vLLM (PagedAttention, fastest TTFT, safe default) vs SGLang (RadixAttention, prefix caching, best for chat/RAG) vs TensorRT-LLM (NVIDIA-optimized, FP8/FP4, highest setup complexity)
- Model loading strategies: eager, lazy, pre-warming
- Version management: model repository pattern, label-based routing, gradual rollout
- Hot-swapping without downtime: dual-GPU, rolling update, connection draining
- Multi-model serving: GPU memory management (MPS vs MIG), ensemble pipelines
- When to build your own: the hybrid approach (framework for inference + custom layers)
- Build vs adopt decision framework

**Suggested Diagrams**:
- ch02-opener.html (chapter opener)
- ch02-framework-decision-tree.html (selection decision tree)
- ch02-multi-model-architecture.html (multi-model serving with GPU memory management)
- ch02-framework-generations.html (three-generation timeline)

**Cross-References to Book 1**: None directly -- this is ML-specific content

**Cross-References to Other Chapters**: Forward to Ch 3 (GPU optimization details), Ch 6 (inference pipelines using these frameworks), Ch 12 (scaling with these frameworks)

**Research Topics**: Topic 1 (ML Inference Serving Frameworks)

**Estimated Word Count**: 4000-6000

**Priority Notes**: Include specific benchmark numbers from Clarifai comparison (4,741 tok/s vLLM, 16,200 tok/s SGLang). The hybrid approach (framework + custom layers) is the most common production pattern -- emphasize this. Design your API layer independently of the framework.

---

## Chapter 3: GPU Optimization & Cold Starts

**Key Concepts**:
- Why GPUs sit idle: the utilization problem, memory-bound vs compute-bound, bursty request patterns
- Measuring GPU utilization: SM occupancy, memory bandwidth, DCGM/nvidia-smi
- Static vs dynamic vs continuous batching (with throughput/latency tradeoffs)
- Tuning batching parameters: max batch size, max wait time, prefill vs decode scheduling
- KV cache as the central bottleneck (industry consensus)
- PagedAttention: virtual memory for KV cache, near-zero fragmentation
- KV cache quantization: NVFP4 (50% memory reduction vs FP8)
- KV cache reuse: RadixAttention, prefix caching for chat/RAG
- KV cache offloading: GPU -> CPU -> NVMe hierarchy
- Cold start anatomy: container spin-up, runtime init, CUDA context, model loading, warm-up inference
- Cold start mitigation: pre-warming, model caching, persistent GPU pools, snapshot/restore (CRIU)
- Quantization spectrum: FP32 -> FP16 -> BF16 -> FP8 -> FP4 -> INT8 -> INT4
- FP8 as production standard, FP4/INT4 as frontier
- FlashAttention-3 (1.5-2x speedup, Hopper) and FlashAttention-4 (Blackwell)
- Multi-Head vs Grouped-Query vs Multi-Query Attention
- Speculative decoding: draft + verifier, no quality loss, tree-based variants
- Right-sizing GPU instances: cost vs latency, spot/preemptible, hardware trajectory

**Suggested Diagrams**:
- ch03-opener.html (chapter opener)
- ch03-batching-comparison.html (static vs dynamic vs continuous batching)
- ch03-kv-cache-paging.html (PagedAttention visualization)
- ch03-cold-start-anatomy.html (cold start timeline breakdown)
- ch03-quantization-tradeoffs.html (precision spectrum with tradeoffs)

**Cross-References to Book 1**: Ch 9 (Compute and Scaling -- general scaling patterns)

**Cross-References to Other Chapters**: Back to Ch 2 (frameworks implement these optimizations), forward to Ch 12 (scaling at the infrastructure level)

**Research Topics**: Topic 2 (GPU Optimization Advances)

**Estimated Word Count**: 5000-7000

**Priority Notes**: This is the most technically dense chapter. Organize around the KV cache insight -- it is the central bottleneck. Include specific numbers: 2-4x throughput for continuous batching, <4% fragmentation for PagedAttention, 50% memory reduction for NVFP4, 740 TFLOPS for FlashAttention-3. Always frame optimizations within latency SLO constraints.

---

## Chapter 4: Streaming Audio Architecture

**Key Concepts**:
- End-to-end architecture: client audio capture -> codec encoding -> transport -> server receive -> VAD -> inference -> post-processing -> response stream
- Audio fundamentals for serving engineers: sample rates (8kHz, 16kHz, 24kHz, 48kHz), bit depth (16-bit, 32-bit float), channels (mono, stereo), codecs (PCM, Opus, FLAC)
- Chunk size selection: the latency vs accuracy tradeoff (100ms vs 200ms vs 250ms chunks)
- Voice Activity Detection (VAD): intelligent segmentation to reduce unnecessary inference
- Buffering strategies: when to buffer, when to drop, when to interpolate
- Reference architectures from production providers:
  - Deepgram: WebSocket, binary frames, 100ms chunks, Nova-3, per-second billing
  - AssemblyAI: WebSocket, sub-300ms, Universal-2/Slam-1, PII redaction
  - Google Cloud Speech: gRPC bidirectional, Chirp 3, 25KB message limit, 16kHz recommended
  - Amazon Transcribe: WebSocket + HTTP/2, 15-second block billing
  - OpenAI Realtime: WebRTC + WebSocket + SIP, PCM 24kHz, Opus preferred

**Suggested Diagrams**:
- ch04-opener.html (chapter opener)
- ch04-e2e-architecture.html (end-to-end streaming architecture)
- ch04-chunk-size-tradeoff.html (chunk size selection tradeoffs)
- ch04-provider-comparison.html (provider architecture comparison)

**Cross-References to Book 1**: Ch 5 (Network & Connection Optimization -- protocol fundamentals, WebSocket basics)

**Cross-References to Other Chapters**: Forward to Ch 5 (protocol selection details), Ch 6 (connecting transport to inference)

**Research Topics**: Topic 3 (Real-Time Speech/Audio API Landscape), Topic 4 (Streaming Protocols for Audio)

**Estimated Word Count**: 4000-6000

**Priority Notes**: Ground abstract concepts in real provider implementations. The provider comparison table is critical -- it shows how different companies solve the same problem differently. The 300ms rule should appear here as the defining constraint for streaming audio architecture.

---

## Chapter 5: Protocol Selection for Audio

**Key Concepts**:
- WebSocket for audio: binary framing (33% bandwidth savings over base64), persistent connections, backpressure (dropping stale audio > buffering)
- gRPC bidirectional streaming: protobuf for audio chunks, deadline propagation, Google's approach
- WebRTC: jitter buffers, NAT traversal, codec negotiation, OpenAI's browser/mobile approach
- WebTransport: QUIC datagrams (unreliable delivery), head-of-line blocking elimination, browser support status (Chrome/Edge yes, Safari no)
- Media over QUIC (MoQ): ultra-low latency, NOT production-ready, timeline
- Decision framework: client constraints (browser vs server), latency targets, bidirectionality needs, browser requirements
- Production reality: WebSocket dominates, gRPC for Google ecosystem, WebRTC for browser audio, WebTransport/MoQ are future

**Suggested Diagrams**:
- ch05-opener.html (chapter opener)
- ch05-protocol-decision-tree.html (protocol selection decision tree)
- ch05-binary-vs-base64.html (binary vs base64 encoding comparison)
- ch05-protocol-comparison-table.html (protocol comparison matrix)

**Cross-References to Book 1**: Ch 5 (Network & Connection Optimization -- WebSocket lifecycle, SSE, gRPC, WebTransport fundamentals covered in depth). Provide brief recap and cross-reference, do not re-teach fundamentals.

**Cross-References to Other Chapters**: Back to Ch 4 (streaming architecture), forward to Ch 6 (connecting protocol to inference pipeline)

**Research Topics**: Topic 4 (Streaming Protocols for Audio)

**Estimated Word Count**: 4000-5000

**Priority Notes**: Be realistic about production readiness. WebSocket is the dominant choice and the chapter should reflect this. WebTransport and MoQ deserve a "looking ahead" section, not a primary recommendation. The decision framework should be practical, helping the reader make a concrete choice for their situation.

---

## Chapter 6: Streaming Inference Pipelines

**Key Concepts**:
- Connecting the transport layer to the inference layer (bridging Ch 4-5 with Ch 2-3)
- Request queuing and scheduling for streaming workloads
- Partial results and incremental decoding: streaming transcription word-by-word, interim vs final results
- Handling multiple concurrent streams per server instance: per-stream state, GPU resource allocation
- Graceful degradation under load: quality reduction (lower sample rate, simpler model) vs request rejection with backpressure
- End-to-end latency tracing through the streaming pipeline (span design for streaming)
- Buffering and flow control between pipeline stages

**Suggested Diagrams**:
- ch06-opener.html (chapter opener)
- ch06-streaming-pipeline.html (transport -> queue -> scheduler -> inference -> post-processing -> response)
- ch06-concurrent-streams.html (multiple clients multiplexed to shared inference engine)
- ch06-degradation-strategies.html (degradation decision flow based on load level)

**Cross-References to Book 1**: Ch 3 (Observability & Distributed Tracing -- trace/span concepts for streaming)

**Cross-References to Other Chapters**: Back to Ch 2 (frameworks), Ch 4 (audio architecture), Ch 5 (protocols). Forward to Ch 11 (SLOs for pipeline metrics).

**Research Topics**: Topic 1 (ML Inference Serving Frameworks), Topic 3 (Real-Time Speech/Audio API Landscape), Topic 4 (Streaming Protocols for Audio)

**Estimated Word Count**: 4000-6000

**Priority Notes**: This is the synthesis chapter for Part II. It must connect the dots between audio architecture (Ch 4), protocol selection (Ch 5), and the serving frameworks and GPU optimization from Part I (Ch 2-3). The graceful degradation section is critical for production readiness.

---

## Chapter 7: Designing ML-Facing APIs

**Key Concepts**:
- Resource-oriented API design for inference endpoints (Google AIP patterns: AIP-121, AIP-133, AIP-136)
- Synchronous vs asynchronous API patterns: short inference (<1s, sync), medium (1-30s, streaming), long (>30s, long-running operations via AIP-151)
- Streaming response design:
  - SSE with `data:` prefix and `[DONE]` signal (OpenAI Chat Completions pattern)
  - OpenAI Responses API structured events (response.created, response.output_text.delta, response.completed)
  - WebSocket message schemas with interim/final results
  - gRPC server streaming
- Error handling for ML-specific failures: model not loaded, GPU OOM, inference timeout, queue full
- API versioning strategies: URL path vs header vs content negotiation, model version to API version mapping
- SDK and developer experience: making inference APIs easy to integrate

**Suggested Diagrams**:
- ch07-opener.html (chapter opener)
- ch07-sync-vs-async-decision.html (sync/async/LRO decision framework)
- ch07-streaming-response-patterns.html (SSE, WebSocket, gRPC streaming patterns)
- ch07-versioning-strategies.html (versioning approaches + model version mapping)

**Cross-References to Book 1**: Ch 10 (Traffic Management -- rate limiting algorithms referenced in API design)

**Cross-References to Other Chapters**: Back to Ch 4-6 (streaming patterns this API exposes). Forward to Ch 8 (metering these API calls), Ch 9 (securing these APIs).

**Research Topics**: Topic 5 (API Design for ML Services)

**Estimated Word Count**: 4000-6000

**Priority Notes**: Cover both Google AIP patterns and OpenAI patterns as two design philosophies. The long-running operations pattern (AIP-151) deserves its own subsection for batch inference. SSE streaming is critical -- OpenAI has standardized it and many developers expect it. Model-version-to-API-version mapping needs practical examples.

---

## Chapter 8: Usage Metering & Billing

**Key Concepts**:
- What to meter: audio seconds, API calls, compute time, tokens, characters
- Billing models comparison: per-second (Deepgram, AssemblyAI), per-15-second-block (AWS), per-character (ElevenLabs), per-token (OpenAI), per-hour base (AssemblyAI)
- Feature-based pricing stacking: base rate + PII redaction + diarization + summarization (AssemblyAI pattern: $0.0025/min base can 3-4x)
- Metering architecture: idempotent event collection, event queue, aggregation pipeline, billing period roll-up
- Real-time vs batch metering tradeoffs
- Stripe Meters API integration: meter definition, event ingestion, aggregation, invoice generation (new standard, legacy usage records removed)
- Stripe token billing: purpose-built for LLM token metering
- OpenMeter as open-source alternative (acquired by Kong 2025, native Stripe integration)
- Rate limiting tied to billing tiers
- Audit trail for usage disputes
- 2026 reality: AI without financial governance is a margin-bleeding cost center

**Suggested Diagrams**:
- ch08-opener.html (chapter opener)
- ch08-metering-architecture.html (event collection -> aggregation -> billing)
- ch08-billing-model-comparison.html (per-second vs per-block vs per-character vs per-token)
- ch08-stripe-integration.html (Stripe Meters API end-to-end flow)

**Cross-References to Book 1**: Ch 10 (Traffic Management -- rate limiting tied to billing)

**Cross-References to Other Chapters**: Back to Ch 7 (APIs being metered). Forward to Ch 9 (security for metering data).

**Research Topics**: Topic 6 (Usage Metering & Billing)

**Estimated Word Count**: 4000-5000

**Priority Notes**: Per-second vs per-block billing is an architectural decision, not just a pricing choice -- it affects how metering events are emitted and aggregated. Stripe Meters API is the primary billing integration path in 2025-2026. Feature stacking is a common but under-discussed pricing pattern in speech APIs.

---

## Chapter 9: Security for Audio ML APIs

**Key Concepts**:
- Authentication for streaming connections: token-based auth on WebSocket upgrade, per-stream auth for gRPC, token refresh during long-running streams
- API key management: generation (with scoping to endpoints/features), rotation schedule, usage monitoring, revocation
- OAuth2 flows for ML API access
- Rate limiting and abuse prevention for inference endpoints
- Securing audio data: encryption at rest (AES-256) and in transit (TLS 1.3)
- PII in transcripts: detection, redaction patterns (masking, replacement, removal), provider approaches (Deepgram zero-retention, AssemblyAI auto PHI redaction)
- Audio-specific privacy risks: biometric voiceprints, background conversations, emotional states

**Suggested Diagrams**:
- ch09-opener.html (chapter opener)
- ch09-streaming-auth-flow.html (auth flow for streaming connections)
- ch09-api-key-lifecycle.html (key generation through revocation)
- ch09-pii-redaction-pipeline.html (PII detection and redaction pipeline)

**Cross-References to Book 1**: Ch 11 (Auth Performance -- auth caching, token validation optimization), Appendix A (Auth Fundamentals -- JWT, OAuth2, API keys, WebSocket auth patterns)

**Cross-References to Other Chapters**: Back to Ch 7 (API design includes security). Forward to Ch 10 (compliance builds on security).

**Research Topics**: Topic 7 (Enterprise Compliance for AI/ML -- security subsections)

**Estimated Word Count**: 4000-5000

**Priority Notes**: This chapter focuses on security design decisions SPECIFIC to audio ML APIs -- not general API security (covered in Book 1). PII redaction deserves significant attention because voice data contains unique privacy risks. Zero-retention defaults as a pattern is worth highlighting.

---

## Chapter 10: Compliance & Data Governance

**Key Concepts**:
- SOC 2 for ML APIs: Trust Service Criteria applied to inference systems (not a law, but effectively mandatory for B2B)
- Audit logging: what to log (inference requests, data access, admin actions), how to log it (immutable append-only), retention requirements
- Data retention and deletion policies for audio data
- GDPR for voice data: voice = personal data requiring explicit consent, erasure/access/portability for recordings
- CCPA implications for stored audio and transcripts
- EU AI Act: implementation timeline (Prohibited Feb 2025, GPAI Aug 2025, High-risk Aug 2026, Regulated Aug 2027), requirements, penalties (up to EUR 35M / 7% global turnover)
- HIPAA for healthcare speech AI: encryption requirements, BAAs, PHI redaction in telehealth
- Data residency: keeping audio data in the right geography
- Building compliance into the architecture vs bolting it on

**Suggested Diagrams**:
- ch10-opener.html (chapter opener)
- ch10-eu-ai-act-timeline.html (implementation timeline with penalties)
- ch10-compliance-matrix.html (SOC 2 / HIPAA / GDPR / CCPA / EU AI Act requirements matrix)
- ch10-data-lifecycle.html (audio data lifecycle: ingestion through deletion)

**Cross-References to Book 1**: None directly -- compliance is new territory specific to ML/audio

**Cross-References to Other Chapters**: Back to Ch 9 (security foundation). Forward to Ch 11 (SLOs include compliance monitoring).

**Research Topics**: Topic 7 (Enterprise Compliance for AI/ML)

**Estimated Word Count**: 4000-6000

**Priority Notes**: EU AI Act timeline must be prominent -- August 2026 high-risk rules are the big deadline. Audio-specific privacy risks deserve their own section (distinct from text data). SOC 2 framing as "not law but effectively mandatory" is important. Cover building compliance into architecture from the start vs retrofitting.

---

## Chapter 11: SLOs for Streaming ML Systems

**Key Concepts**:
- Streaming-specific SLIs taxonomy:
  - Latency: TTFT (time to first token/byte), TPOT (time per output token), inter-token latency, end-to-end latency
  - Quality: WER (word error rate), goodput (% of requests meeting SLOs), RTF (real-time factor < 1.0)
  - Reliability: connection drops, reconnection success rates, availability
- Target numbers: TTFT <= 100ms (interactive agent), TTFT <= 300ms (voice AI), P95 Final <= 800ms (3-sec utterance)
- The 300ms rule for voice AI -- the book's recurring threshold
- Goodput: measuring quality of throughput, not just volume
- Setting SLO targets: balancing user experience with infrastructure cost
- Error budgets for ML systems: how model accuracy interacts with infrastructure reliability
- Monitoring and alerting on SLO burn rate: fast-burn (2% in 1 hour) and slow-burn (5% in 6 hours) alerts
- Jitter buffers in streaming pipelines

**Suggested Diagrams**:
- ch11-opener.html (chapter opener)
- ch11-streaming-sli-taxonomy.html (SLI categories organized by type)
- ch11-slo-target-framework.html (target numbers by use case tier)
- ch11-burn-rate-alerting.html (burn rate alerting with budget projection)

**Cross-References to Book 1**: Ch 2 (Performance Fundamentals -- SLI/SLO/SLA definitions, percentile latencies), Ch 3 (Observability -- OpenTelemetry, distributed tracing), Ch 4 (Monitoring -- dashboards, alerting patterns)

**Cross-References to Other Chapters**: Back to Ch 6 (pipeline metrics to measure), Ch 9-10 (compliance monitoring). Forward to Ch 12 (scaling decisions driven by SLOs).

**Research Topics**: Topic 8 (SLOs for Streaming ML Systems)

**Estimated Word Count**: 4000-6000

**Priority Notes**: Define specific, actionable SLI/SLO targets with real numbers -- this is what makes the chapter immediately useful. Goodput is an important concept to introduce (distinct from raw throughput). RTF (real-time factor) is a speech-specific metric that needs clear explanation. The 300ms and 100ms thresholds should be prominently featured.

---

## Chapter 12: Scaling Inference Globally

**Key Concepts**:
- Horizontal scaling: adding GPU instances, load balancing inference requests (GPU-aware routing)
- Auto-scaling for inference: scaling signals (GPU utilization, request queue depth, latency P95, memory pressure), hysteresis to prevent flapping
- Cold starts during auto-scaling: the worst time to pay the cold start penalty (addressed in Ch 3, applied here)
- Multi-region deployment: model replication strategy, latency-based request routing, data sovereignty boundaries
- Edge inference vs centralized inference: when to push models closer to users (smaller models at edge, large models centralized)
- Cost optimization: spot/preemptible GPU instances (60-90% savings), right-sizing, scheduled scaling for predictable traffic, quantization as cost lever
- Capacity planning for inference workloads

**Suggested Diagrams**:
- ch12-opener.html (chapter opener)
- ch12-autoscaling-signals.html (scaling signal hierarchy with hysteresis)
- ch12-multi-region-architecture.html (multi-region deployment with routing and sovereignty)
- ch12-cost-optimization-strategies.html (cost optimization decision framework)

**Cross-References to Book 1**: Ch 9 (Compute and Scaling -- general horizontal/vertical scaling, auto-scaling patterns), Ch 12 (Geographic Optimization -- edge computing, CDN patterns, multi-region)

**Cross-References to Other Chapters**: Back to Ch 3 (GPU optimization and cold starts), Ch 11 (SLOs driving scaling decisions). Forward to Ch 13 (putting scaling into the complete system).

**Research Topics**: Topic 1 (ML Inference Serving Frameworks -- scaling characteristics), Topic 2 (GPU Optimization -- right-sizing)

**Estimated Word Count**: 4000-6000

**Priority Notes**: GPU-aware load balancing is unique to ML infrastructure -- traditional load balancing does not account for GPU memory utilization or model loading state. The cold-start-during-auto-scaling problem is critical and often underappreciated. Cost optimization should include specific GPU pricing examples to make the analysis concrete.

---

## Chapter 13: Putting It All Together

**Key Concepts**:
- Case study: building a production streaming speech API from scratch (end-to-end walkthrough)
- Architecture walkthrough: from audio input to transcription output, showing every component
- The decisions along the way: framework selection (Ch 2), GPU optimization (Ch 3), audio architecture (Ch 4), protocol (Ch 5), pipeline (Ch 6), API design (Ch 7), metering (Ch 8), security (Ch 9), compliance (Ch 10), SLOs (Ch 11), scaling (Ch 12)
- What goes wrong and how to recover: common failure modes and remediation
- Operational runbook patterns for ML inference systems: cold start, GPU OOM, model rollback, connection storms, SLO burn, compliance incidents
- Lessons learned and key principles

**Suggested Diagrams**:
- ch13-opener.html (chapter opener)
- ch13-complete-architecture.html (full production system architecture)
- ch13-decision-flowchart.html (key decision points from all chapters)
- ch13-runbook-patterns.html (operational runbook decision trees)

**Cross-References to Book 1**: Ch 14 (Putting It All Together -- Book 1's synthesis chapter, similar structure)

**Cross-References to Other Chapters**: References ALL previous chapters (1-12). This is the synthesis chapter.

**Research Topics**: All topics in RESEARCH_SUMMARY.md (synthesis chapter draws from everything)

**Estimated Word Count**: 5000-8000

**Priority Notes**: This is a narrative case study chapter, not a reference chapter. Walk the reader through building a real system, making real decisions, encountering real problems. The tone should be practical and experience-driven. The runbook patterns section should be immediately actionable. May exceed normal word count limits given the synthesis scope (per style guide: "narrative case study chapters like 'Putting It All Together' may exceed this limit").

---

## Cross-Reference Summary

### Book 1 ("Before the 3 AM Alert") Cross-References

| Book 2 Chapter | Book 1 Chapter | Topic |
|----------------|----------------|-------|
| Ch 1 | Ch 1 | Measurement-driven philosophy |
| Ch 1 | Ch 3 | Observability fundamentals |
| Ch 1 | Ch 5 | Network/protocol fundamentals |
| Ch 3 | Ch 9 | Compute and scaling patterns |
| Ch 4 | Ch 5 | Protocol fundamentals (WebSocket, etc.) |
| Ch 5 | Ch 5 | Protocol deep dive (recap + audio-specific) |
| Ch 6 | Ch 3 | Distributed tracing for streaming |
| Ch 7 | Ch 10 | Rate limiting in API design |
| Ch 8 | Ch 10 | Rate limiting tied to billing |
| Ch 9 | Ch 11, App A | Auth performance, auth fundamentals |
| Ch 11 | Ch 2, 3, 4 | SLI/SLO definitions, observability, monitoring |
| Ch 12 | Ch 9, 12 | Compute scaling, geographic optimization |
| Ch 13 | Ch 14 | Synthesis chapter pattern |

### Internal Cross-References (Chapter-to-Chapter)

| From | To | Topic |
|------|----|-------|
| Ch 1 | All | Roadmap for the book |
| Ch 2 | Ch 3, 6, 12 | Framework -> GPU optimization, pipelines, scaling |
| Ch 3 | Ch 2, 12 | GPU optimization context, scaling implications |
| Ch 4 | Ch 5, 6 | Architecture -> protocols, pipelines |
| Ch 5 | Ch 4, 6 | Protocol -> architecture, pipelines |
| Ch 6 | Ch 2-5, 11 | Pipeline synthesis, SLO metrics |
| Ch 7 | Ch 4-6, 8, 9 | API design -> streaming, metering, security |
| Ch 8 | Ch 7, 9 | Metering -> API design, security |
| Ch 9 | Ch 7, 10 | Security -> API design, compliance |
| Ch 10 | Ch 9, 11 | Compliance -> security, monitoring |
| Ch 11 | Ch 6, 9-10, 12 | SLOs -> pipeline metrics, compliance, scaling |
| Ch 12 | Ch 3, 11 | Scaling -> GPU optimization, SLO-driven |
| Ch 13 | Ch 1-12 | Synthesis of all chapters |

---

*Last updated: February 2026*
*Use this document when beginning work on each chapter PR.*
