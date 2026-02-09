# Research Summary: Productionizing ML Inference APIs

Research conducted 2026-02-09 via web searches across 8 topic areas. Full raw search results in `raw-web-search-results.md`.

---

## Topic 1: ML Inference Serving Frameworks

### Key Findings
- **vLLM**: Most widely adopted LLM serving engine. PagedAttention + continuous batching. Fastest TTFT across concurrency levels. 4,741 tok/s at 100 concurrent requests (GPT-OSS-120B benchmark). Safe default for production.
- **SGLang**: RadixAttention for prefix caching, ~16,200 tok/s (29% faster than vLLM on H100 with Llama 3.1 8B). Most stable per-token latency (4-21ms). Best for chat/RAG scenarios with KV reuse.
- **TensorRT-LLM**: NVIDIA's optimized runtime. FP8/FP4/INT4 quantization, inflight batching. Outperforms SGLang and vLLM on B200 GPUs. Higher setup complexity.
- **Triton Inference Server**: Multi-framework orchestration layer. Often paired with TensorRT-LLM for model execution. GPU scheduling, ensemble pipelines.
- **KServe**: Kubernetes-native. Serverless model inference with Knative autoscaling (scale-to-zero). Best for K8s-heavy orgs.
- **BentoML**: Developer-friendly, Python-class based. Good for startups/small teams. Works without Kubernetes.
- **Ray Serve**: Distributed AI apps on Ray. Flexible but heavier operational footprint.
- **LitServe**: Lightweight serving from Lightning AI. Limited 2025 comparison data.
- **Ollama**: Local-first LLM serving. Simplified deployment, growing ecosystem.
- **Consolidation trend**: vLLM/SGLang/TensorRT-LLM dominating LLM serving. KServe/BentoML for general ML. Triton as orchestration layer.

### Notable Sources
- MarkTechPost: "Comparing Top 6 Inference Runtimes for LLM Serving in 2025"
- Clarifai: "Comparing SGLang, vLLM, and TensorRT-LLM with GPT-OSS-120B"
- BentoML: "LLM Inference Handbook — Choosing the Right Framework"
- Northflank: "vLLM vs TensorRT-LLM: Key differences, performance"

### Implications for Outline
- Chapter 2 must cover all three generations of frameworks with clear decision tree
- vLLM vs SGLang vs TensorRT-LLM needs detailed comparison with specific benchmarks
- KServe/BentoML positioning as "general ML" vs "LLM-optimized" is an important distinction
- The "hybrid approach" (framework for inference + custom layers) needs emphasis

---

## Topic 2: GPU Optimization Advances

### Key Findings
- **Continuous batching**: Evicts completed sequences, inserts new ones. Eliminates head-of-line blocking. 2-4x throughput improvement vs older stacks at same latency.
- **PagedAttention**: Treats KV cache like virtual memory. Fixed-size blocks reduce fragmentation. Now table stakes for LLM serving.
- **KV cache is the bottleneck**: Industry consensus — winners are runtimes that treat KV as first-class data structure (paged, quantized, reused, offloaded).
- **FP8**: Stable for training and inference with proper calibration. Significant speed/throughput/memory gains vs FP16/BF16.
- **NVFP4 KV cache**: Reduces memory 50% vs FP8. Enables doubling context length and batch size on Blackwell GPUs.
- **Speculative decoding**: Draft tokens from lightweight model, validated by main model. Accelerates decoding without quality loss. Listed as "upcoming" in many platforms.
- **FlashAttention-3**: 1.5-2x faster than FA-2 with FP16 (740 TFLOPS), up to 1.2 PFLOPS with FP8. Optimized for Hopper (H100).
- **FlashAttention-4**: New kernel for Blackwell architecture, ~20% speedup over NVIDIA cuDNN attention.
- **Hardware trajectory**: Hopper (H100) -> Blackwell (B200). FP8 -> FP4. Flash Attention 3 -> 4. Each generation brings lower precision at higher throughput.

### Notable Sources
- NVIDIA Blog: "Optimizing Inference for Long Context with NVFP4 KV Cache"
- Stixor: "The New LLM Inference Stack 2025: FA-3, FP8 & FP4"
- Nebius: "Serving LLMs with vLLM: A Practical Inference Guide"
- FlashAttention-3 paper (Dao et al.)

### Implications for Outline
- Chapter 3 should organize around the KV cache insight — it's the central bottleneck
- Quantization progression (FP16 -> FP8 -> FP4 -> INT4) needs its own section
- FlashAttention versions should be covered as implementation detail, not chapter focus
- Cold start section should connect to model loading time + GPU memory management

---

## Topic 3: Real-Time Speech/Audio API Landscape

### Key Findings
- **OpenAI Realtime API**: GA August 2025. gpt-realtime speech-to-speech. Supports WebRTC (browser/mobile), WebSocket (server-to-server), and SIP. Audio formats: PCM (24kHz), Opus preferred. Base64-encoded audio over WebSocket.
- **Deepgram**: WebSocket streaming. Nova-3 model. Sub-200ms latency. Per-second billing ($0.0043-0.0077/min). 100ms chunk size recommended. Binary WebSocket frames. Interim + final results pattern.
- **AssemblyAI**: WebSocket streaming. Universal-2/Slam-1 models. Sub-300ms latency. $0.15/hr base. Multilingual streaming (6 languages). PII redaction built-in.
- **Google Cloud Speech**: gRPC bidirectional streaming only (not REST). Chirp 3 model GA 2025. 25KB per-message limit. 16kHz sample rate recommended. US region only for V2 API.
- **Amazon Transcribe**: WebSocket + HTTP/2 streaming. 15-second block billing (more expensive for short utterances).
- **ElevenLabs**: TTS focus. Flash v2.5 at ~75ms latency. Character-based pricing.
- **Pricing landscape**: Per-second billing (Deepgram, AssemblyAI) beats 15-sec blocks (AWS) by up to 36% on short utterances. This is a key architectural decision for metering.

### Notable Sources
- AssemblyAI: "Top APIs and Models for Real-Time Speech Recognition 2026"
- Deepgram: "Best Speech-to-Text APIs 2026"
- OpenAI: Realtime API documentation
- Google Cloud Speech-to-Text documentation

### Implications for Outline
- Chapter 4 needs detailed comparison of how each provider architects streaming
- The WebRTC vs WebSocket vs gRPC choice is provider-determined, not just technical
- Chapter 8 (metering) should cover per-second vs block billing as a design decision
- OpenAI Realtime supporting 3 protocols (WebRTC/WebSocket/SIP) is notable for Chapter 5

---

## Topic 4: Streaming Protocols for Audio

### Key Findings
- **WebSocket**: Dominant in production speech AI. Binary frames reduce bandwidth ~33% vs base64 JSON. Persistent connections eliminate handshake overhead. 100-200ms chunks over WebSocket = sub-300ms E2E latency.
- **gRPC bidirectional**: Used by Google Cloud Speech exclusively. Protobuf efficiency. 25KB per-message limit for audio. Better for server-to-server.
- **WebRTC**: Built-in jitter buffers, NAT traversal, codec negotiation. Used by OpenAI Realtime for browser/mobile. Best for ultra-low latency browser streaming. Overkill for server-to-server.
- **WebTransport**: Chrome/Edge support. Exposes QUIC datagrams (unreliable delivery). Eliminates head-of-line blocking. Safari doesn't support yet.
- **Media over QUIC (MoQ)**: Ultra-low latency (300ms RTT + encode/decode). NOT production-ready as of Dec 2024. Red5 planned support by end 2025. MoQ and WebRTC will coexist.
- **Production reality**: WebSocket dominates. gRPC for Google ecosystem. WebRTC for browser audio. WebTransport/MoQ are future, not present.
- **The 300ms rule**: AssemblyAI specifically calls out 300ms as the threshold for voice AI applications.

### Notable Sources
- GetStream: "WebRTC vs WebSocket: Which Keeps Audio in Sync for AI?"
- VideoSDK: "What is Replacing WebSockets? Deep Dive into WebTransport, HTTP/3"
- Red5: "MOQ vs WebRTC: Why Both Can and Should Exist"
- WINK: "Media over QUIC Implementation — Technical Analysis 2025"

### Implications for Outline
- Chapter 5 should be realistic: WebSocket is dominant, gRPC for Google, WebRTC for browser
- WebTransport/MoQ deserve a "looking ahead" section, not a recommendation
- The decision framework should be practical, not theoretical
- Cross-reference Book 1 Ch 5 for protocol fundamentals, focus on audio-specific application

---

## Topic 5: API Design for ML Services

### Key Findings
- **Google AIPs (API Improvement Proposals)**: Resource-oriented design (AIP-121), Long-running operations (AIP-151) for >10s jobs, Standard methods (List/Get/Create/Update/Delete), Custom methods (AIP-136).
- **Long-running operations**: Return `google.longrunning.Operation` with name + done status. Client polls for completion. Analogous to Python Future / Node.js Promise.
- **OpenAI API as de facto standard**: SSE (Server-Sent Events) for streaming responses. Chat Completions streaming with `data:` prefix + `[DONE]` signal. New Responses API with structured event types (response.created, response.output_text.delta, response.completed).
- **Multimodality**: First-class citizen in 2025 APIs (docs, audio, images, video).
- **Agent patterns**: OpenAI Responses API, Agents SDK, AgentKit for multi-step workflows. AGENTS.md spec, MCP (Model Context Protocol).
- **Azure OpenAI**: v1 API (Aug 2025) with rolling api-version, faster release cycle.

### Notable Sources
- Google AIP: aip.dev (AIPs 121, 133, 136, 151)
- OpenAI: API Reference, Streaming Events documentation
- OpenAI: "OpenAI for Developers in 2025"

### Implications for Outline
- Chapter 7 should cover Google AIP patterns AND OpenAI patterns as two design philosophies
- Long-running operations pattern deserves its own subsection (batch inference use case)
- SSE streaming pattern is critical for Chapter 7 (OpenAI has standardized it)
- Model-version-to-API-version mapping needs practical examples

---

## Topic 6: Usage Metering & Billing

### Key Findings
- **Stripe Meters API**: New standard (legacy usage records removed in API v2025-03-31). Meters specify aggregation over billing periods. LLM proxy feature: call models + record usage in one request.
- **Stripe token billing**: Purpose-built for LLM token metering.
- **OpenMeter**: Open-source real-time metering. Acquired by Kong (2025). Native Stripe integration. Used by Lever, Apollo GraphQL, Google.
- **Billing models for speech**: Per-second (Deepgram, AssemblyAI), per-15-second-block (AWS), per-character (ElevenLabs for TTS), per-hour (AssemblyAI base).
- **Feature stacking**: AssemblyAI's $0.0025/min base can 3-4x with features (PII redaction, diarization, etc.).
- **2026 = year of AI unit economics**: Organizations realizing AI without financial governance is a margin-bleeding cost center.

### Notable Sources
- Stripe: Meters API Reference, Token Billing Documentation
- OpenMeter: openmeter.io, Kong acquisition announcement
- BrasTranscripts: Deepgram/AssemblyAI pricing breakdowns

### Implications for Outline
- Chapter 8 should cover Stripe Meters as the primary billing integration path
- OpenMeter as the open-source alternative
- Per-second vs per-block billing as an architectural decision (not just pricing)
- Feature-based pricing stacking needs coverage (common pattern in speech APIs)

---

## Topic 7: Enterprise Compliance for AI/ML

### Key Findings
- **EU AI Act timeline**: Prohibited practices (Feb 2025), GPAI obligations (Aug 2025), **High-risk + transparency rules (Aug 2026)**, Regulated products (Aug 2027). Fines: up to EUR 35M or 7% global turnover.
- **SOC 2**: De facto requirement for B2B AI. Enterprise customers won't sign without it. Not a law but effectively mandatory.
- **HIPAA for audio**: Requires encryption, granular access logs, BAAs with every processor. Telehealth sessions specifically covered.
- **GDPR for voice**: Voice = personal data requiring explicit consent. Honor erasure/access/portability for recordings.
- **Audio-specific privacy risks**: Biometric voiceprints, background conversations, emotional states alongside explicit identifiers.
- **PII redaction**: Deepgram (zero-retention defaults, configurable redaction, sub-300ms), AssemblyAI (HIPAA + BAA, auto PHI redaction), Voicegain (95%+ accuracy, audio + text redaction).
- **Key compliance features**: Zero-retention defaults, configurable redaction, regional processing, BAAs, audit logging, data residency.

### Notable Sources
- EU AI Act Service Desk: Implementation Timeline
- Deepgram: "Standard Compliance Speech-to-Text: HIPAA, SOC 2, GDPR"
- Wiz: "AI Compliance in 2026: Definition, Standards, and Frameworks"
- DLA Piper: "Latest Wave of Obligations Under the EU AI Act"

### Implications for Outline
- Chapter 10 must cover EU AI Act timeline prominently (Aug 2026 is the big date)
- Audio-specific privacy risks deserve their own section (distinct from text data)
- PII redaction should be both Chapter 9 (security) and Chapter 10 (compliance) topic
- SOC 2 positioning as "not law but effectively mandatory" is important framing

---

## Topic 8: SLOs for Streaming ML Systems

### Key Findings
- **Speech-to-text SLOs**: P95 TTFB <= 300ms, P95 Final <= 800ms for 3-sec utterances, RTF (real-time factor) < 1.0.
- **LLM serving SLOs**: TTFT < 500ms, TPOT (time per output token) < 15ms, E2E latency < 2s.
- **Interactive agent target**: TTFT <= 100ms P95 (aligns with RAIL/MDN UX heuristic for "feels instantaneous").
- **Goodput**: Percentage of requests meeting SLOs. Measures quality of throughput, not just volume.
- **Voice agent metrics (2026)**: Speed (TTFT), accuracy (WER), processing efficiency (RTF).
- **Jitter buffers**: WebRTC/gRPC/WebSocket pipelines use them. Smooth variable packet arrival but add delay.
- **Academic work**: "Revisiting SLO and Goodput Metrics in LLM Serving" (2024), "JITServe: SLO-aware LLM Serving" (2025).

### Notable Sources
- Gladia: "How to Measure Latency in STT (TTFB, Partials, Finals, RTF)"
- Anyscale: "Understand LLM Latency and Throughput Metrics"
- AssemblyAI: "The 300ms Rule: Why Latency Makes or Breaks Voice AI"
- BentoML: "Key Metrics for LLM Inference"

### Implications for Outline
- Chapter 11 should define specific SLI/SLO targets (the numbers above are excellent starting points)
- Goodput is an important concept to introduce (not just throughput)
- RTF (real-time factor) is a speech-specific metric that deserves explanation
- The 300ms and 100ms thresholds should be prominently featured
