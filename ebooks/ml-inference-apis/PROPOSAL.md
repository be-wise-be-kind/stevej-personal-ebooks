# Proposed Ebook: Productionizing ML Inference APIs

## Context: How This Proposal Came About

Steve Jackson recently joined Aldea as a Senior API & Platform Engineer. His role centers on building and evolving Aldea's real-time speech/audio APIs — wrapping trained ML models in production-grade inference layers, exposing them through well-designed APIs, and ensuring they meet enterprise requirements for security, compliance, observability, and scale.

Steve previously authored an ebook called **"Before the 3 AM Alert: What Every Developer Should Know About API Performance"** (located at `/home/stevejackson/Projects/stevej-personal-ebooks/ebooks/api-optimization/`). That book is a comprehensive 14-chapter guide covering API performance fundamentals, observability (OpenTelemetry, Grafana stack), monitoring, network/connection optimization, caching, database patterns, async processing, compute scaling, traffic management, auth performance, edge infrastructure, and performance testing. It includes appendices on auth fundamentals (JWT, OAuth2, API keys, WebSocket auth) and GraphQL optimization.

When building a reading plan for the Aldea role, we did a gap analysis between the existing ebook and the job description. The ebook already covers:
- Observability & distributed tracing (Ch 3)
- Monitoring, dashboards, alerting (Ch 4)
- Protocol fundamentals — WebSocket (connection lifecycle, backpressure, observability, scaling), SSE, WebTransport, and gRPC are all covered **in depth** in Ch 5, including comparison tables and when to use which
- Caching, database, async patterns (Ch 6-8)
- Compute & scaling (Ch 9)
- Traffic management & rate limiting (Ch 10)
- Auth performance including OAuth2, API keys, JWT (Ch 11 + Appendix A)
- Edge/geographic optimization (Ch 12)
- Performance testing (Ch 13)

**The gaps** — topics central to the Aldea role that the ebook does NOT cover — are:

1. **ML inference serving** — model serving frameworks (Triton, TorchServe, vLLM, KServe), dynamic batching, GPU scheduling, model loading/unloading
2. **Speech/audio streaming pipelines** — real-time ASR/TTS, audio chunking strategies, VAD (voice activity detection), codec selection (PCM vs Opus), binary framing
3. **GPU optimization & cold starts** — GPU utilization, cold start mitigation, model caching, quantization, container pre-warming
4. **API design & versioning** — resource-oriented design, versioning strategies, long-running operations, developer experience (distinct from the performance focus of book 1)
5. **Usage metering & billing** — tracking API consumption, aggregation pipelines, billing integration
6. **SOC2 compliance & data security for audio** — audit logging, data retention/deletion, PII in transcripts, encryption for sensitive audio
7. **SLOs for streaming systems** — defining SLIs/SLOs specifically for real-time streaming (jitter, connection drop rates, end-to-end latency)
8. **Real-time audio streaming patterns** — applying protocol knowledge (already in book 1) to audio-specific use cases

We searched for existing books that cover this intersection. **No single book exists.** The closest are:
- *Designing Machine Learning Systems* (Chip Huyen) — covers ML deployment broadly but isn't speech-specific or serving-focused
- *Machine Learning Production Systems* (O'Reilly, 2024) — model serving patterns, general
- *API Design Patterns* (JJ Geewax, Manning) — API design only, no ML context
- *Implementing Service Level Objectives* (Alex Hidalgo) — SLOs but not ML/audio-specific

The knowledge lives in scattered vendor docs (NVIDIA Triton, vLLM), conference talks, competitor API documentation (Deepgram, AssemblyAI, Google Cloud Speech), and tribal knowledge. No one has synthesized the **serving engineer's perspective** — the person who receives a trained model and must make it production-ready behind APIs.

## Critical Scope Decision

**This book is about SERVING, not TRAINING.** The reader is not building ML models. They are taking trained models and:
- Wrapping them in high-throughput inference layers
- Exposing them through well-designed, versioned APIs
- Streaming audio in real-time with low latency
- Handling auth, metering, and compliance
- Keeping everything observable and within SLOs
- Scaling globally

Out of scope: training pipelines, data labeling, feature stores, experiment tracking, model architecture design, hyperparameter tuning, dataset management.

## Relationship to Book 1

This is a **companion book**, not a replacement. Book 1 ("Before the 3 AM Alert") covers the foundational API performance layer. This book builds on top of it for the ML inference serving use case. Where book 1 covers WebSocket fundamentals, this book covers "how to stream audio over WebSocket to an inference endpoint." Where book 1 covers observability with OpenTelemetry, this book covers "what specific metrics and traces matter for ML inference pipelines."

The reader benefits from having read book 1 but this book should be self-contained enough to stand alone.

## Proposed Table of Contents

### Part I: Foundations of ML Inference Serving

**Chapter 1: The Serving Problem**
- What happens after the model is trained
- The serving engineer's role: the gap between research and production
- Latency budgets for real-time inference (where do the milliseconds go?)
- Batch vs real-time vs streaming inference — when to use which
- How speech/audio differs from text/image inference (continuous streams, time-sensitive, codec-dependent)

**Chapter 2: Model Serving Frameworks**
- Landscape: NVIDIA Triton, TorchServe, TensorFlow Serving, BentoML, vLLM, KServe, Seldon Core, LitServe
- Framework selection criteria: model type, latency requirements, scaling model, GPU support
- Model loading, versioning, and hot-swapping in production
- Multi-model serving on shared GPU infrastructure
- When to build your own vs adopt a framework

**Chapter 3: GPU Optimization & Cold Starts**
- GPU utilization: why GPUs sit idle and how to fix it
- Dynamic batching: collecting requests to maximize throughput without blowing latency budgets
- Cold start anatomy: model loading, runtime initialization, container spin-up
- Mitigation strategies: pre-warming, model caching, persistent GPU pools, snapshot/restore
- Quantization and model compression for inference (FP16, INT8, distillation)
- Right-sizing GPU instances: cost vs latency tradeoffs

### Part II: Real-Time Audio Streaming

**Chapter 4: Streaming Audio Architecture**
- End-to-end architecture: client → audio capture → transport → inference → response → client
- Audio fundamentals for serving engineers: sample rates, bit depth, channels, codecs (PCM, Opus, FLAC)
- Chunk size selection: the latency vs accuracy tradeoff
- Voice Activity Detection (VAD): intelligent segmentation to reduce unnecessary inference
- Buffering strategies: when to buffer, when to drop, when to interpolate
- Reference: how Deepgram (WebSocket), AssemblyAI (WebSocket), Google Cloud Speech (gRPC), and Amazon Transcribe (WebSocket + HTTP/2) architect their streaming APIs

**Chapter 5: Protocol Selection for Audio**
- Note: protocol fundamentals (WebSocket, SSE, gRPC, WebTransport) are covered in "Before the 3 AM Alert" Ch 5 — this chapter focuses on audio-specific application
- WebSocket for audio: binary framing, efficient payload encoding, backpressure when dropping stale audio is better than buffering
- gRPC bidirectional streaming for audio: protobuf message design for audio chunks, deadline propagation
- WebRTC: when you need jitter buffers, NAT traversal, and codec negotiation (and when it's overkill)
- WebTransport datagrams: unreliable delivery for lossy real-time audio — when dropping frames is a feature
- Making the choice: decision framework based on client constraints, latency targets, browser requirements

**Chapter 6: Streaming Inference Pipelines**
- Connecting the transport layer to the inference layer
- Request queuing and scheduling for streaming workloads
- Partial results and incremental decoding (streaming transcription word-by-word)
- Handling multiple concurrent streams per server instance
- Graceful degradation under load: quality reduction vs request rejection
- End-to-end latency tracing through the streaming pipeline

### Part III: API Design for ML Services

**Chapter 7: Designing ML-Facing APIs**
- Resource-oriented API design for inference endpoints
- Synchronous vs asynchronous API patterns for ML (short inference vs long-running jobs)
- Streaming response design: chunked responses, SSE events, WebSocket message schemas
- Error handling for ML-specific failures: model not loaded, GPU OOM, timeout during inference
- API versioning strategies: URL path vs header vs content negotiation, and how model versions map to API versions
- SDK and developer experience: making your inference API easy to integrate

**Chapter 8: Usage Metering & Billing**
- What to meter: audio seconds, API calls, compute time, tokens, characters
- Metering architecture: idempotent event collection, aggregation pipelines
- Real-time vs batch metering tradeoffs
- Billing integration patterns (Stripe usage-based billing, custom solutions)
- Rate limiting tied to billing tiers
- Audit trail for usage disputes

### Part IV: Enterprise Readiness

**Chapter 9: Security for Audio ML APIs**
- Authentication for streaming connections: token-based auth for WebSocket, per-stream auth for gRPC
- API key management: generation, rotation, scoping, revocation
- OAuth2 flows for ML API access
- Rate limiting and abuse prevention for inference endpoints
- Securing audio data: encryption at rest and in transit
- PII in transcripts: detection, redaction, handling
- Note: auth performance patterns are covered in "Before the 3 AM Alert" Ch 11 — this chapter focuses on the security design decisions specific to audio ML

**Chapter 10: Compliance & Data Governance**
- SOC2 for ML APIs: Trust Service Criteria applied to inference systems
- Audit logging: what to log, how to log it, retention requirements
- Data retention and deletion policies for audio data
- GDPR/CCPA implications for stored audio and transcripts
- Data residency: keeping audio data in the right geography
- Building compliance into the architecture vs bolting it on

**Chapter 11: SLOs for Streaming ML Systems**
- Defining SLIs for real-time inference: latency percentiles, throughput, availability
- Streaming-specific SLIs: jitter, connection drop rates, reconnection success rates, time-to-first-byte for transcription
- Setting SLO targets: balancing user experience with infrastructure cost
- Error budgets for ML systems: how model accuracy interacts with infrastructure reliability
- Monitoring and alerting on SLO burn rate
- Note: observability fundamentals are covered in "Before the 3 AM Alert" Ch 3-4 — this chapter focuses on what to measure and what targets to set for ML inference

### Part V: Operating at Scale

**Chapter 12: Scaling Inference Globally**
- Horizontal scaling: adding GPU instances, load balancing inference requests
- Auto-scaling for inference: scaling on GPU utilization, request queue depth, latency
- Multi-region deployment for inference: model replication, request routing, data sovereignty
- Edge inference vs centralized inference: when to push models closer to users
- Cost optimization: spot/preemptible GPU instances, right-sizing, scheduled scaling
- Note: general geographic optimization patterns are in "Before the 3 AM Alert" Ch 12 — this chapter covers ML-specific scaling concerns

**Chapter 13: Putting It All Together**
- Case study: building a production streaming speech API from scratch
- Architecture walkthrough: from audio input to transcription output
- The decisions along the way: framework, protocol, API design, security, metering, compliance
- What goes wrong and how to recover
- Operational runbook patterns for ML inference systems

## Competitor/Reference APIs to Study

These real-world APIs should be referenced throughout the book as examples of production choices:
- **Deepgram** — WebSocket-based streaming ASR, usage-based pricing
- **AssemblyAI** — WebSocket streaming, real-time transcription
- **Google Cloud Speech-to-Text** — gRPC bidirectional streaming
- **Amazon Transcribe** — WebSocket + HTTP/2 streaming
- **OpenAI Realtime API** — WebSocket-based, speech-to-speech
- **Azure Speech Services** — SDK-based, WebSocket under the hood

## Reference Materials Identified

### Books
- *Designing Machine Learning Systems* — Chip Huyen (O'Reilly) — Ch 7-9 on deployment/serving
- *Efficient Deep Learning* — Menghani (MIT Press) — inference optimization, quantization
- *API Design Patterns* — JJ Geewax (Manning) — versioning, resource design
- *The Design of Web APIs* — Arnaud Lauret (Manning) — API-first, developer experience
- *Implementing Service Level Objectives* — Alex Hidalgo (O'Reilly) — SLI/SLO framework
- *Site Reliability Engineering* (Google SRE Book) — Ch 4 on SLOs
- *Machine Learning Production Systems* (O'Reilly, 2024) — serving patterns
- *Machine Learning Infrastructure and Best Practices* (O'Reilly, 2024) — production ML for SWEs

### Docs & Frameworks
- NVIDIA Triton Inference Server documentation
- vLLM (PagedAttention, continuous batching)
- KServe / Seldon Core (Kubernetes-native model serving)
- BentoML / LitServe (lightweight serving)
- OpenTelemetry docs (instrumentation for inference pipelines)
- OWASP API Security Top 10
- SOC2 engineering guides (Vanta, Drata)
- Stripe usage-based billing documentation
- Google API Design Guide (cloud.google.com/apis/design)

### Speech/Audio Specific
- OpenAI Whisper paper and repo
- Streaming ASR papers (CTC, RNN-T architectures)
- NVIDIA Parakeet models documentation
