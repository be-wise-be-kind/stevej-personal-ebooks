# Productionizing ML Inference APIs - AI Context

**Scope**: Book architecture, scope, design decisions, and reference materials

---

## Overview

"Productionizing ML Inference APIs: A Serving Engineer's Guide to Real-Time Speech and Audio" is a technical ebook about the engineering discipline of taking trained ML models and serving them in production behind well-designed APIs. It uses real-time speech and audio as the running example throughout — one of the most demanding inference serving workloads.

## Book Vision

### Core Thesis
The serving engineer's perspective is underserved in technical literature. Most ML resources focus on training. Most API resources don't address ML-specific concerns (GPU optimization, model lifecycle, streaming inference). This book bridges the gap.

### Positioning
- **Companion to Book 1**: "Before the 3 AM Alert" covers foundational API performance. This book builds on it for ML inference.
- **Serving, not training**: The reader is NOT building ML models. They are taking trained models and making them production-ready.
- **Audio as running example**: Speech/audio combines the hardest constraints (streaming, real-time, codec-dependent). Patterns generalize to easier workloads.
- **Measurement-driven**: Following Book 1's empirical approach — measure first, optimize with purpose.

### What Success Looks Like
A serving engineer reads this book and can confidently:
- Choose and deploy a model serving framework
- Optimize GPU utilization and cold starts
- Build a streaming audio inference pipeline
- Design APIs for ML services
- Implement metering and billing
- Meet enterprise security and compliance requirements
- Set and monitor meaningful SLOs
- Scale inference globally

## Target Audience

1. **Backend Engineers** moving into ML infrastructure
2. **Platform Engineers** building inference platforms
3. **Site Reliability Engineers** responsible for ML system SLOs
4. **Technical Leaders** evaluating inference infrastructure decisions
5. **API Engineers** working on speech/audio/real-time ML products

**Prerequisites**: Backend API experience, HTTP/WebSocket familiarity, containerization basics. No ML training experience needed.

## Scope Boundaries

### In Scope
- Model serving frameworks and selection
- GPU optimization, batching, quantization, cold starts
- Real-time audio streaming architecture and protocols
- API design patterns for ML services
- Usage metering and billing systems
- Security for streaming audio and ML APIs
- Compliance (SOC 2, GDPR, EU AI Act, HIPAA)
- SLOs for streaming ML systems
- Global scaling of inference infrastructure

### Out of Scope
- Model training, hyperparameter tuning, experiment tracking
- Data pipelines, feature stores, data labeling
- ML model architecture design
- Frontend/client SDK implementation (beyond API contract)
- Database administration
- Comprehensive security (beyond ML/audio-specific)

## Relationship to Book 1

### Cross-Reference Guide

| Book 2 Topic | Book 1 Chapter | Relationship |
|---------------|----------------|--------------|
| Protocol selection (Ch 5) | Ch 5: Network & Connection | Book 1 covers fundamentals; Book 2 covers audio-specific application |
| Observability (Ch 6, 11) | Ch 3: Observability | Book 1 covers OpenTelemetry etc.; Book 2 covers ML-specific metrics |
| Monitoring/SLOs (Ch 11) | Ch 4: Monitoring | Book 1 covers general; Book 2 covers streaming ML SLOs |
| Rate limiting (Ch 8, 9) | Ch 10: Traffic Management | Book 1 covers algorithms; Book 2 covers billing-tier integration |
| Auth (Ch 9) | Ch 11: Auth Performance | Book 1 covers auth perf; Book 2 covers streaming auth design |
| Scaling (Ch 12) | Ch 9, 12: Compute, Geographic | Book 1 covers general; Book 2 covers GPU-specific scaling |

**Convention**: Where Book 2 needs Book 1 content, provide a brief recap (1-2 paragraphs) + explicit cross-reference: "For a deep dive on [topic], see 'Before the 3 AM Alert' Chapter N."

## Key Design Decisions

### Chapter Structure
- **5 Parts, 13 Chapters + Preface**: Follows Book 1 pattern but with thematic Parts
- Part I: Foundations (Ch 1-3) — Problem, frameworks, GPU
- Part II: Audio Streaming (Ch 4-6) — Architecture, protocols, pipelines
- Part III: API Design (Ch 7-8) — ML APIs, metering
- Part IV: Enterprise (Ch 9-11) — Security, compliance, SLOs
- Part V: Scale (Ch 12-13) — Global scaling, synthesis

### Chapter Overview Philosophy: Ground the Reader
Each chapter's Overview section should be generous about assumed knowledge. The target audience is backend engineers moving into ML infrastructure, not ML researchers. Before diving into the chapter's specifics, the Overview should briefly explain the foundational concepts the chapter builds on. Ask: "Would a backend engineer with no ML experience understand what this chapter is about from the Overview alone?"

Concrete guidance:
- **Explain what the thing is** before explaining why it's hard. If a chapter covers GPU optimization, briefly explain what a GPU does for ML and why inference uses them. If a chapter covers streaming audio, explain what it means for audio to be streamed vs processed in batch.
- **One or two paragraphs is enough.** This is not a textbook introduction; it's a bridge so the reader isn't lost before the chapter starts.
- **Don't assume Book 1 knowledge.** Many readers will pick up this book without reading "Before the 3 AM Alert." Brief recaps are always welcome; "see Book 1 Chapter N" cross-references are good but should not be the only explanation.
- **Chapters 1-2 set the pattern.** Their Overviews explain what model serving is and what a serving framework does before diving in. Later chapters should follow suit for their respective domains.

### Bridging the Gap Section (Mandatory)
Every chapter MUST include a `## Bridging the Gap` section immediately after the Overview. This section grounds both primary reader archetypes before the chapter dives into content:
- **From the ML side**: Explain API/infrastructure concepts the chapter uses (2-3 sentences each)
- **From the API side**: Explain ML/GPU concepts the chapter uses (2-3 sentences each)
- Keep it to 3-5 paragraphs total
- See the Per-Chapter Bridge Content section below for guidance on what to cover

### Chapter 1 Philosophy
Chapter 1 is a comprehensive introduction (like Book 1's Ch 1 "The Empirical Discipline"):
- Direct, informative exposition — no fictional scenario or narrative hook
- Covers problem landscape, industry context, difficulties, innovations, business case, approach
- Most detailed outline of any chapter
- Sets tone and philosophy for entire book

### Pseudocode Philosophy
Same as Book 1: pseudocode over production code because:
- AI has commoditized code generation
- Real code ages poorly
- Pseudocode is language-agnostic
- The concepts matter more than implementation details

### Citation Approach
- Inline: `[Source: Author, Year]`
- Full details in WORKS_CITED.md organized by chapter
- Frequently Cited Works table at top of WORKS_CITED.md
- Prefer primary sources (papers, official docs) over blog posts where available

## Competitor APIs to Reference Throughout

These real-world APIs should be referenced as production examples:

| Provider | Focus | Protocol | Key Detail |
|----------|-------|----------|------------|
| **Deepgram** | Streaming ASR | WebSocket (binary) | Nova-3, 100ms chunks, per-second billing |
| **AssemblyAI** | Streaming ASR | WebSocket | Slam-1/Universal-2, sub-300ms, PII redaction |
| **Google Cloud Speech** | Streaming ASR | gRPC bidirectional | Chirp 3, 25KB message limit, 16kHz recommended |
| **Amazon Transcribe** | Streaming ASR | WebSocket + HTTP/2 | 15-second block billing |
| **OpenAI Realtime** | Speech-to-speech | WebRTC + WebSocket + SIP | PCM 24kHz, Opus preferred, base64 over WS |
| **ElevenLabs** | TTS | WebSocket | Flash v2.5, ~75ms latency, character billing |
| **Azure Speech** | ASR/TTS | SDK (WebSocket under hood) | Integrated with Azure OpenAI |

## Research Sources Master List

Research is stored in `.roadmap/in-progress/ml-inference-apis/research/`:
- `RESEARCH_SUMMARY.md` — Synthesized findings across 8 topics with key numbers and sources
- `raw-web-search-results.md` — Full raw search results for deep reference

### Topic Coverage
1. ML Inference Serving Frameworks (vLLM, SGLang, TensorRT-LLM, Triton, KServe, BentoML)
2. GPU Optimization (continuous batching, PagedAttention, FP8/FP4, FlashAttention 3/4)
3. Real-Time Speech/Audio API Landscape (provider comparison, pricing, protocols)
4. Streaming Protocols for Audio (WebSocket, gRPC, WebRTC, WebTransport, MoQ)
5. API Design for ML Services (Google AIPs, OpenAI patterns, LRO, SSE streaming)
6. Usage Metering & Billing (Stripe Meters, OpenMeter, per-second vs block billing)
7. Enterprise Compliance (EU AI Act Aug 2026, SOC 2, HIPAA, GDPR for audio)
8. SLOs for Streaming ML (TTFT, TPOT, RTF, goodput, the 300ms rule)

## AI Agent Guidance

### When Writing Chapters
- Consult RESEARCH_SUMMARY.md for the relevant topic(s) before writing
- Include specific numbers from research (benchmarks, pricing, latency targets)
- Reference competitor APIs by name with technical details
- Include `[Source: Author, Year]` citations for all factual claims
- Cross-reference Book 1 where applicable (brief recap + link)
- Follow chapter conventions exactly (see AGENTS.md)

### When Creating Diagrams
- Use `.ai/templates/html-diagram.html` as starting template
- Follow `.ai/howto/evaluating-diagram-quality.md` for quality standards
- Name as `chNN-name.html` in `ebooks/ml-inference-apis/assets/`
- Reference as `![Caption](../assets/chNN-name.html)` + `\newpage`

### Common Patterns
- **Provider comparison tables**: Use throughout to ground abstract concepts in real-world implementations
- **Decision trees/frameworks**: Each chapter should help the reader make concrete decisions
- **Cross-reference boxes**: `> **From Book 1:** For a deep dive on [topic], see "Before the 3 AM Alert" Chapter N.`
- **The 300ms rule**: Reference this latency threshold frequently — it's the book's equivalent of Book 1's "measure first"
- **Bridging the Gap sections**: `## Bridging the Gap` after Overview in every chapter. Two subsections: "From the ML side" (explains API/infra concepts for ML engineers) and "From the API side" (explains ML concepts for API engineers). See Per-Chapter Bridge Content below.

## Per-Chapter Bridge Content

Guidance for what each chapter's Bridging the Gap section should cover. Chapters 1-3 have full prose already written; chapters 4-15 have outlines written and should be expanded to full prose when those chapters are authored.

### Chapter 1: The Serving Problem
- **ML side**: APIs, request/response model, API contracts, SLOs
- **API side**: Trained models, forward passes, GPUs for matrix multiplication

### Chapter 2: Model Serving Frameworks
- **ML side**: Serving frameworks as analogous to web servers/app frameworks, container orchestration (Kubernetes)
- **API side**: Model loading (why it's slow — gigabytes of weights into GPU memory), batching (grouping requests for GPU efficiency)

### Chapter 3: GPU Optimization & Cold Starts
- **ML side**: GPU utilization metrics, cost-per-request analysis, auto-scaling and cold start delays
- **API side**: GPU architecture (SIMD cores), GPU memory (VRAM/HBM), precision formats (FP32/FP16/INT8/FP4)

### Chapter 4: Streaming Audio Architecture
- **ML side**: Persistent connections (WebSocket, gRPC), codecs (Opus, FLAC, PCM), bandwidth planning
- **API side**: Sample rate, bit depth, data rate calculation, Voice Activity Detection (VAD)

### Chapter 5: Protocol Selection
- **ML side**: Protocol impact on load balancers, proxies, idle timeouts, flow control
- **API side**: Why HTTP request-response is insufficient for audio, bidirectional communication, binary framing vs base64 overhead

### Chapter 6: Streaming Inference Pipelines
- **ML side**: Distributed tracing (OpenTelemetry, spans), queue theory (queue depth, Little's Law), backpressure
- **API side**: GPU layer-by-layer computation, KV cache reads/writes, batching across streams, pipeline parallelism (CPU/GPU overlap)

### Chapter 7: Designing ML APIs
- **ML side**: REST conventions (resources, methods, status codes), idempotency, JSON schemas
- **API side**: Variable cost per request (60x range for audio), "model not loaded" (503) failure mode, streaming response delivery

### Chapter 8: Streaming Response Contracts
- **ML side**: SSE, WebSocket, gRPC as transport mechanisms, Protocol Buffers, message framing
- **API side**: Autoregressive token-by-token generation, interim vs final speech results, incremental delivery

### Chapter 9: API Versioning & Developer Experience
- **ML side**: URL path versioning, deprecation policies, SDKs, developer onboarding metrics
- **API side**: Two-axis versioning (API schema + model version), model pinning for reproducibility

### Chapter 10: Security for Audio ML APIs
- **ML side**: JWT, OAuth 2.0 Client Credentials, token bucket rate limiting, TLS/mTLS
- **API side**: Voice as biometric data, background conversation capture, GPU-aware rate limiting (compute-seconds), audio PII redaction

### Chapter 11: Compliance & Data Governance
- **ML side**: SOC 2 auditing, GDPR data rights, HIPAA BAAs, audit logging requirements
- **API side**: Voice as biometric data under GDPR/BIPA, EU AI Act obligations (Aug 2026), model lifecycle auditability

### Chapter 12: SLOs for Streaming ML Systems
- **ML side**: SLI/SLO/SLA definitions, error budgets (allowed failure rate), burn rate
- **API side**: TTFT, TPOT, RTF (must be <1.0), goodput (quality-adjusted throughput), KV cache pressure as capacity signal

### Chapter 13: Usage Metering & Billing
- **ML side**: Metering event pipelines (collection → aggregation → invoicing), idempotency keys, billing-tier rate limiting
- **API side**: 60x cost variance per request, feature-based pricing complexity, per-block billing overcharge on short utterances

### Chapter 14: Scaling Inference Globally
- **ML side**: Horizontal scaling, auto-scaling signals, multi-region deployment, spot vs reserved instances
- **API side**: Model loading delay (30-120s), GPU memory as binding constraint, KV cache determines max concurrency, GPU right-sizing

### Chapter 15: Putting It All Together
- **ML side**: Deployment checklists, incident response process, capacity planning, runbooks
- **API side**: GPU OOM (crashes all active requests), cold start storms, model rollback (accuracy degradation vs crash)
