# Chapter 1: The Serving Problem

![Chapter 1 Opener](../assets/ch01-opener.html)

\newpage

## Overview

Every machine learning model begins its life in a training environment: a notebook, a cluster of GPUs running for hours or days, a carefully orchestrated pipeline that transforms data into weights. When training completes, the team celebrates. The model achieves state-of-the-art accuracy on the benchmark. The research paper gets submitted. The demo works beautifully on a single machine.

Then someone asks: "How do we serve this to ten thousand users at once?"

That question opens a chasm that most organizations are not prepared for. The gap between a trained model and a production inference API is where months disappear, budgets inflate, and teams discover that the hard part was never training the model. The hard part is serving it: reliably, at low latency, at scale, at a cost the business can sustain. This chapter introduces the serving problem, explains why it constitutes a distinct engineering discipline, and establishes the measurement-driven philosophy that guides the rest of this book.

## Bridging the Gap

This chapter draws on concepts from both ML infrastructure and API engineering. If you have not encountered these before, this section provides the context you will need.

**From the ML side**, this chapter assumes familiarity with APIs and why their design matters for inference. An API (Application Programming Interface) is a contract between a client and a server: the client sends an HTTP request containing input data, the server processes it and returns a response. API contracts define what inputs are accepted, what outputs are guaranteed, and how errors are communicated. SLOs (Service Level Objectives) are targets a team sets for measurable metrics like response latency and availability. They are how you define "good enough" and decide when to stop optimizing.

**From the API side**, this chapter assumes familiarity with what a trained model is and what "serving" it means. A model is a large file of numerical weights learned during training, often billions of parameters for modern language models. A forward pass feeds input data through these weights to produce a prediction: audio bytes become a transcript, a text prompt becomes generated tokens. This computation happens on a GPU because it involves massive parallel matrix multiplications that CPUs handle orders of magnitude more slowly. "Serving" means making this forward pass available as an API that handles real traffic.

## The Serving Engineer's Role

The serving engineer occupies a space that few job descriptions fully capture. They are not ML researchers; they do not design model architectures or tune hyperparameters. They are not traditional backend engineers; the workloads they manage involve GPU memory hierarchies, KV cache pressure, and model version lifecycle rather than database connection pools and HTTP routing. They sit at the intersection of ML infrastructure and API engineering, taking a trained model artifact and making it fast, reliable, cost-effective, and compliant at scale.

The skillset is broad. A serving engineer must understand API design well enough to build contracts that external developers trust. They must understand distributed systems well enough to run inference across GPU clusters with load balancing and failover. They must understand GPU hardware well enough to diagnose why utilization is stuck at 40% and what batching strategy will push it higher. They must understand observability well enough to instrument a streaming pipeline end-to-end. They must understand security and compliance well enough to handle biometric audio data under GDPR. And they must understand billing well enough to meter usage accurately, because an inference API that cannot account for what it serves cannot sustain a business.

This role is underserved in technical literature. Most ML books focus on training. Most API books focus on general web services. Most infrastructure books assume CPU workloads. The intersection of all three, where inference serving lives, is where organizations need the most help and find the fewest resources. That is the gap this book addresses.

## The Problem Landscape

### Why ML Inference Serving Is Hard

Five characteristics make ML inference serving fundamentally different from traditional API development.

**GPU costs are high and unforgiving.** Inference-grade GPU instances cost 10-100x more per hour than the CPU instances that serve traditional web traffic. Unlike CPU-based web servers that cost cents per hour, leaving a GPU idle for even a few hours represents meaningful waste. Naive serving, where each request gets exclusive access to a GPU, wastes the vast majority of available compute because the GPU sits idle between requests. The economic pressure to maximize GPU utilization is constant and shapes every architectural decision. Chapter 3 covers the specific cost landscape and the optimization techniques that address this waste.

**Latency budgets are tight.** Real-time applications demand sub-second responses, but model inference is inherently compute-heavy. A single forward pass through a large language model can take 50-200 milliseconds of GPU time, and that is before accounting for network transit, queue wait, preprocessing, and postprocessing. For voice AI applications, the total end-to-end latency budget is 300 milliseconds [Source: AssemblyAI, 2025]. Every stage in the pipeline must be optimized to fit within this budget, and a single slow component can blow it entirely.

**Cold starts are painful.** When a new instance comes online, whether from auto-scaling, deployment, or recovery, it must load multi-gigabyte model weights from storage into GPU memory. This takes 10-60 seconds depending on model size and storage throughput. For context, a typical web application container starts in 1-3 seconds. The user impact is severe: the first request after a scale-up event can time out entirely. This is not a minor inconvenience; it is a fundamental constraint that drives warm pool strategies, model caching, and pre-warming pipelines.

**The model lifecycle never stops.** Models are not static artifacts. They are retrained on new data, fine-tuned for new domains, evaluated against quality benchmarks, A/B tested against previous versions, and sometimes rolled back when a new version degrades quality in production. Serving infrastructure must handle all of this: loading new versions, routing traffic between versions, draining connections from old versions, and maintaining service continuity throughout. A deployment that drops active audio streams because it restarted a server is not production-ready.

**The talent gap is real.** Few engineers have deep experience in both API engineering and ML infrastructure. Teams with strong ML backgrounds often lack production API design skills. Teams with strong backend experience often lack GPU optimization knowledge. The result is that organizations reinvent solutions to problems that have well-known answers, burning months on challenges that a cross-functional serving team could resolve in weeks.

### How Speech/Audio Differs from Other Inference

This book uses speech and audio as its primary running example, and for good reason: audio inference is among the most demanding workloads in the serving landscape. If you can serve audio well, you can serve anything.

**Continuous streams, not discrete requests.** A text-based API receives a complete input and returns a complete output. An audio API receives an unbounded stream of audio chunks, each arriving in real time, and must produce results continuously as the stream progresses. There is no clear "request" and "response"; there is an ongoing flow. This fundamentally changes the connection model, the protocol requirements, and the failure modes.

**The 300ms rule.** Voice AI applications must respond within 300 milliseconds to feel conversational [Source: AssemblyAI, 2025]. Beyond this threshold, users perceive delay, and the interaction feels broken. This is not a soft target; it is a discontinuous boundary where user experience changes abruptly. The 100ms threshold, where responses feel instantaneous per the RAIL model [Source: Google, 2024], is even more demanding. These numbers anchor every latency optimization in this book.

**Codec-dependent processing.** Audio arrives encoded in PCM, Opus, FLAC, or other formats, each with different bandwidth, quality, and latency characteristics. Opus is bandwidth-efficient but requires decoding. PCM is uncompressed and easy to process but consumes more network bandwidth. The choice of codec affects the entire pipeline: what the client sends, what the server decodes, and how much latency the encoding step adds.

**Bidirectional communication.** Real-time voice agents require simultaneous send and receive. The user speaks, the system transcribes, generates a response, synthesizes speech, and plays it back, all while the user's audio stream remains open. This bidirectional flow requires protocols that support full-duplex communication: WebSocket, gRPC bidirectional streaming, or WebRTC.

**Higher stakes for dropped data.** When a text API drops a request, the client retries. When an audio pipeline drops a chunk, the system misses words. There is no retrying a live audio stream; the moment has passed. This makes connection reliability and graceful degradation more critical for audio workloads than for most other inference types.

## The Industry Context

### The LLM Revolution and Its Infrastructure Demands

The period from 2024 through 2026 represents the most rapid expansion of ML inference infrastructure in the history of computing. Large language models that were research curiosities in 2022 are now embedded in production applications serving millions of users daily. Every chatbot, coding assistant, document summarizer, and voice agent runs on inference infrastructure, and the scale of demand has shifted the industry's focus from training to serving.

The economic logic is straightforward: training happens once (or periodically), but serving happens millions of times per day. Inference accounts for the vast majority of total compute spending over a model's production lifecycle, with leading AI companies spending billions of dollars annually on inference infrastructure alone [Source: Ankur's Newsletter, 2025; CloudZero, 2025]. Over a model's lifetime, serving costs dwarf training costs, and the efficiency of the serving infrastructure becomes the dominant factor in the business's unit economics. GPU supply constraints have accelerated this focus. When GPU availability is limited, using each GPU efficiently is not optional; it is existential.

### The Speech and Audio AI Renaissance

Speech and audio AI has entered a period of rapid capability expansion. The landscape in early 2026 spans three domains:

**Speech-to-text** has reached human-level accuracy for many use cases. Deepgram, AssemblyAI, and Google Cloud Speech offer streaming recognition with sub-second latency, while OpenAI's Whisper remains a strong open-source baseline. The leading providers have pushed latency below the 300ms threshold that makes voice AI feel conversational.

**Text-to-speech** is approaching human-indistinguishable quality. ElevenLabs and Azure Neural TTS deliver low-latency synthesis that makes real-time voice agents practical.

**Speech-to-speech** is the frontier. OpenAI's Realtime API represents a new class of unified model that processes audio input and produces audio output directly, bypassing the traditional pipeline of separate recognition, generation, and synthesis stages.

The competitive landscape is intense. Providers compete on four dimensions: latency (how fast), accuracy (how correct), pricing (how cheap), and protocol support (how easy to integrate). Each of these dimensions is shaped by infrastructure decisions that this book covers in detail. We examine specific providers' architectures, protocols, and pricing throughout Parts II-IV.

### Batch vs Real-Time vs Streaming Inference

Not all inference is created equal. Three modes exist, each with different characteristics and use cases.

**Batch inference** processes accumulated data offline. A company transcribes yesterday's customer service calls overnight. Latency is measured in minutes or hours, and the priority is throughput: process as many requests as possible per GPU-hour. Batch workloads can tolerate queue wait, can fill batches to maximum capacity, and can run on cheaper spot or preemptible GPU instances.

**Real-time inference** handles single request-response interactions. A user submits a prompt to a chatbot and receives a response. Latency must be low (typically 100ms to 2 seconds), and throughput matters but is secondary to responsiveness. Real-time workloads benefit from continuous batching, which collects requests arriving within a short window and processes them together without making any single request wait too long.

**Streaming inference** maintains persistent connections with continuous input and output. A user speaks into a microphone, and the transcription appears word by word in real time. Latency budgets are the tightest (the 300ms threshold), and the system must process audio faster than real-time to avoid falling behind. Streaming workloads require persistent connections, stateful session management, and protocols designed for bidirectional data flow.

This book focuses primarily on real-time and streaming inference, with batch as a contrast point. The streaming case, particularly for audio, combines the hardest constraints: tight latency budgets, persistent connections, stateful sessions, and continuous data flow. Patterns learned for streaming generalize readily to the simpler real-time and batch cases.

## The Difficulties

### GPU Utilization and Cost

GPU inference is expensive, and naive serving wastes the vast majority of that expense. If a GPU serves one request at a time and each request takes 100 milliseconds, the GPU is idle for most of its time even at moderate traffic levels. The gap between what organizations pay for GPU compute and what they actually use is often enormous.

A series of innovations, from batching strategies to memory management to precision reduction, have dramatically closed this gap. But even with these techniques, right-sizing GPU instances, using spot instances for interruptible workloads, scheduling capacity to follow demand curves, and monitoring utilization to detect waste are all part of a comprehensive cost strategy. Chapter 3 covers GPU optimization in detail, and Chapter 14 addresses cost optimization at scale.

### Latency Anatomy of an Inference Request

Understanding where milliseconds go in an inference request is essential for optimization. Without this breakdown, teams waste effort optimizing the wrong stage. A typical real-time speech-to-text request passes through six stages:

**Network transit** (20-50ms each way): the audio data travels from the client to the server and the response travels back. This is largely determined by geographic distance and network quality, which is why multi-region deployment (Chapter 14) matters.

**Queue wait** (0-100ms): the request waits for an available inference slot. With continuous batching, this is typically 5-20ms as the request joins the next batch iteration. With static batching, the wait can reach 50-100ms while the batch fills. Under heavy load, the queue grows and this stage dominates.

**Preprocessing** (5-20ms): audio decoding (if encoded), voice activity detection to identify speech segments, feature extraction, and input normalization. These run on CPU and are typically fast.

**GPU inference** (50-200ms): the model forward pass through all transformer layers, where each layer performs self-attention (reading from and writing to the KV cache) followed by feed-forward computation. For speech-to-text, the encoder forward pass typically dominates. For autoregressive text generation, each output token requires a full forward pass at roughly 5-8ms per token on current hardware [Source: NVIDIA, 2025]. Scheduling overhead between decode iterations adds approximately 4ms per step [Source: vLLM, 2025]. This is the largest single stage and the focus of GPU optimization efforts in Chapter 3.

**Postprocessing** (5-15ms): decoding model output into text, applying punctuation, formatting, and any feature processing (diarization, PII redaction). These run on CPU.

**Network return** (20-50ms): the response travels back to the client.

The total adds up: 100-435ms for a typical request, with 150-300ms being the common range. The critical insight is that every stage contributes, and the compounding effect means that small improvements across multiple stages add up. Ten stages each contributing 30ms yield 300ms total, which exactly hits the voice AI threshold with no margin.

One subtlety that trips up many teams: *measuring* these stages correctly for streaming workloads is harder than it appears. Standard HTTP middleware in most web frameworks measures request duration only until the response headers are sent. For a streaming inference API, headers are flushed immediately while the actual inference (the audio or transcript bytes) streams back over seconds or minutes in the response body. A middleware timer that stops at headers-sent will report sub-millisecond latency for a request that actually consumed 30 seconds of GPU time. Accurate latency measurement for streaming ML APIs requires instrumentation that captures the full response lifecycle, a topic we return to in Chapters 6 and 12.

![Inference Request Latency Breakdown](../assets/ch01-latency-breakdown.html)

\newpage

### The Cold Start Problem

Cold start is the delay between launching a new inference instance and that instance being ready to serve traffic. For ML workloads, this delay is dominated by model loading: transferring multi-gigabyte weight files from storage into GPU memory and initializing the model for inference. A large model can take 30 seconds to several minutes to load, orders of magnitude longer than a typical web application startup. For context, a standard web server starts in tens of milliseconds to a few seconds.

This matters in three scenarios. First, **auto-scaling events**: when traffic spikes and new instances spin up, those instances cannot serve traffic during the loading window. Existing instances must absorb the overflow, or requests queue and latency degrades. Second, **deployments**: rolling out a new model version requires loading the new model on fresh instances. If the rollout is too aggressive, the service loses capacity during the loading window. Third, **recovery**: when an instance fails and is replaced, the replacement instance has the same cold start delay.

Mitigation strategies exist: warm pools, model caching on fast local storage, optimized container images, and readiness probes that gate traffic until models are verified as loaded. Chapter 3 covers the cold start anatomy and these mitigation strategies in detail.

### Model Lifecycle in Production

A production model is not a static artifact. It evolves, and the serving infrastructure must evolve with it.

**Versioning** is the starting point. Models are identified by version, and the serving system must know which version to load on which instance. A model registry (MLflow, Weights & Biases, or a custom solution) serves as the source of truth for the current production version.

**A/B testing** requires serving multiple model versions simultaneously and routing a percentage of traffic to each. This means multiple versions loaded in GPU memory, potentially on the same instance (if multi-model serving is supported) or on separate instance groups. The serving infrastructure must support weighted routing and collect per-version metrics to evaluate the test.

**Hot-swapping** is the act of replacing one model version with another without dropping active connections. For streaming workloads, this is particularly important: an active audio transcription session cannot be interrupted because the server decided to load a new model. The approach is typically a rolling update: new instances load the new version, traffic is gradually shifted, and old instances are drained and terminated.

**Rollback** is the escape hatch. When a new model version degrades quality in production (higher word error rate, slower latency, unexpected outputs), the team must be able to revert to the previous version quickly. This requires keeping the previous version's artifacts available and the deployment system able to trigger a reverse rollout within minutes, not hours.

## The Innovations

The inference serving landscape has transformed between 2022 and 2026. A series of innovations, each building on the previous, has dramatically improved throughput, reduced memory requirements, and driven down the cost per token. Understanding what these innovations do and why they matter is essential background for the rest of this book. Chapter 3 covers each technique in depth with benchmarks, mechanics, and tuning guidance.

**Continuous batching** keeps GPUs fed by dynamically inserting new requests as completed ones finish, rather than waiting for an entire batch to complete before accepting new work. The result is substantially higher throughput at equivalent latency, and it has become table stakes for production LLM serving.

**PagedAttention** applies virtual memory concepts to the KV cache, the data structure that stores intermediate attention results during generation. Traditional allocation wastes the majority of KV cache memory through fragmentation; PagedAttention nearly eliminates that waste, enabling far more concurrent requests on the same hardware.

**Quantization** reduces model precision from 32-bit to 16-bit, 8-bit, or even 4-bit, roughly halving memory requirements at each step. Lower precision means smaller models, faster computation, and lower cost, with carefully managed quality trade-offs. The progression from FP32 to FP4 has made models that once required multi-GPU clusters feasible on a single GPU.

**Speculative decoding** uses a small, fast draft model to predict multiple tokens ahead, then validates them in a single pass through the full model. When the draft model predicts correctly (which it often does for predictable output), multiple tokens are confirmed in one step, accelerating generation without any quality loss.

## The Serving Framework Landscape

Three generations of serving frameworks have emerged since 2016, each solving the previous generation's core limitation. Framework-locked servers (TensorFlow Serving, TorchServe) gave way to multi-framework orchestration platforms (Triton, KServe, BentoML, Ray Serve), which gave way to LLM-optimized engines (vLLM, SGLang, TensorRT-LLM) purpose-built for transformer inference with innovations like continuous batching and PagedAttention as core features.

The consolidation trend is clear. For LLM workloads, Gen 3 engines dominate. For general ML workloads, Gen 2 platforms remain the pragmatic choice. The selection depends on model type, latency requirements, scaling model, operational complexity, and team expertise. Chapter 2 covers this landscape in detail with benchmark data and a decision framework for choosing the right tool.

## The Business Case

### User Experience

Latency directly impacts whether users perceive an inference-powered application as usable. The 300ms threshold for voice AI is not arbitrary; it is the point at which users perceive delay in a conversation and the interaction feels unnatural [Source: AssemblyAI, 2025]. For interactive chat applications, the 100ms threshold defines the boundary of "feels instantaneous" [Source: Google, 2024].

Streaming results provide an important perceptual advantage. When a speech-to-text system shows partial transcription appearing word by word as the user speaks, the perceived latency is the time to the first word, not the time to the final transcript. This is why time to first token (TTFT) is the primary latency metric for streaming systems: it determines the user's perception of responsiveness even when total processing time is longer. Chapter 12 formalizes this and other streaming-specific SLIs.

Cold starts create a different kind of experience degradation. A user whose first request takes 30 seconds because a new instance is loading a model has a fundamentally different experience from one whose request completes in 200 milliseconds. The variance is the problem; unpredictable latency erodes trust faster than consistently moderate latency.

### Cost

GPU inference is frequently the largest infrastructure line item for AI-powered companies. Even a modest GPU fleet running continuously can cost tens to hundreds of thousands of dollars per month in cloud compute alone. Optimized serving, through the techniques covered in Chapters 3 and 14, can reduce this cost dramatically without degrading the user experience.

Billing model choices also affect unit economics. Per-second billing charges for exact usage duration, while per-block billing charges for a minimum block even when actual usage is shorter. For workloads with many short interactions (voice assistants, IVR systems), the billing model can meaningfully impact whether margins are positive or negative. Chapter 13 covers usage metering and billing in detail.

The broader reality is that 2026 is the year organizations must get serious about AI unit economics. AI services without financial governance bleed margins [Source: OpenMeter, 2025]. Metering both revenue (what customers pay) and cost-to-serve (what the GPU compute costs) per customer and per feature is essential.

### Competitive Advantage

The inference serving landscape is intensely competitive. Deepgram, AssemblyAI, Google, Amazon, OpenAI, and ElevenLabs all compete on latency, accuracy, pricing, and developer experience. Infrastructure quality is a genuine competitive moat: better serving means lower costs per request, faster response times, and higher reliability, all of which compound into customer retention and market share.

Developer experience matters more than many infrastructure teams realize. Clean API contracts, predictable billing, comprehensive documentation, and responsive error messages win integrations. A technically superior model served behind a poorly designed API will lose to a slightly less accurate model with a great developer experience. Chapters 7-9 cover API design, streaming response contracts, versioning, and developer experience in depth.

## This Book's Approach

### Measurement-Driven

This book follows the empirical philosophy established in its companion, *Before the 3 AM Alert*: measure first, optimize with purpose, validate after changing. Every recommendation in this book is grounded in observable metrics. We do not recommend adding caching without measuring cache hit rates. We do not recommend switching serving frameworks without benchmarking both under realistic load. We do not declare an optimization successful without comparing post-change metrics against a baseline.

SLOs (Service Level Objectives) are the framework we use for deciding what to optimize and when to stop. A system meeting its SLO targets does not need further optimization, regardless of whether the team suspects it could be faster. A system missing its SLO targets needs focused attention on the specific SLI that is out of compliance, not a broad "make it faster" effort. Chapter 12 defines the streaming-specific SLIs and SLO targets for inference systems.

> **From Book 1:** For a deep dive on the empirical approach to performance optimization, including the optimization loop, the Five Conditions, and the core principles, see "Before the 3 AM Alert" Chapter 1: The Empirical Discipline.

### Serving, Not Training

The scope boundary of this book is crisp. We begin where the trained model artifact is handed off. We assume the reader has a working model, whether trained in-house or obtained from a provider, and the challenge is making it production-ready. Training pipelines, data labeling, feature stores, experiment tracking, and model architecture design are all out of scope. This is not because those topics are unimportant; it is because they are already well covered elsewhere, and the serving side of the problem is not.

### Audio as Running Example

We use speech and audio as the primary running example throughout this book because audio inference combines the hardest serving constraints: streaming connections, real-time latency budgets, codec-dependent processing, bidirectional communication, and high stakes for dropped data. The patterns we develop for audio, from protocol selection to pipeline architecture to SLO definition, generalize readily to simpler workloads like text generation, image processing, and recommendation inference.

Real-world APIs are referenced throughout. When we discuss streaming protocols, we examine how Deepgram, Google Cloud Speech, and OpenAI architect their APIs. When we discuss billing, we compare per-second and per-block pricing models with real numbers. When we discuss latency targets, we cite the benchmarks that production providers publish. This is not a theoretical exercise; it is a practical guide grounded in the systems that serve real traffic today.

## What's Ahead

The book is organized into five parts, each building on the foundations laid here.

**Part I: Foundations (Chapters 2-3)** completes the foundational material. Chapter 2 surveys the serving framework landscape in detail, with benchmark data and a decision framework for choosing between vLLM, SGLang, TensorRT-LLM, Triton, KServe, and BentoML. Chapter 3 covers GPU optimization in depth: utilization measurement, continuous batching mechanics, KV cache management, quantization techniques, and cold start mitigation strategies.

**Part II: Audio Streaming (Chapters 4-6)** dives into real-time audio architecture. Chapter 4 covers streaming audio architecture: audio codecs, chunk-based processing, voice activity detection, and the client-server interaction model. Chapter 5 addresses protocol selection: WebSocket, gRPC bidirectional streaming, WebRTC, and emerging protocols like WebTransport. Chapter 6 builds streaming inference pipelines by composing the components from the preceding chapters into end-to-end systems.

**Part III: API Design (Chapters 7-9)** covers ML API design patterns. Chapter 7 addresses endpoint design, request and response schemas, and the patterns established by Google AIPs and the OpenAI API. Chapter 8 defines streaming response contracts: how to structure partial results, final results, error events, and completion signals. Chapter 9 covers API versioning, backward compatibility, and developer experience.

**Part IV: Enterprise (Chapters 10-13)** addresses the operational requirements that separate prototypes from production. Chapter 10 covers security for audio and ML workloads. Chapter 11 addresses compliance and data governance, including the EU AI Act timeline. Chapter 12 defines SLOs for streaming ML systems, including TTFT, TPOT, RTF, goodput, and error budgets. Chapter 13 covers usage metering and billing infrastructure.

**Part V: Scale (Chapters 14-15)** brings everything together. Chapter 14 covers GPU-aware auto-scaling, multi-region deployment, edge inference, and cost optimization strategies. Chapter 15 synthesizes the entire book into a complete inference platform architecture, walking through the design decisions for a production system that incorporates every pattern we have discussed.

## Common Pitfalls

- **Optimizing training, not serving.** Teams invest heavily in model accuracy and training infrastructure but treat serving as a deployment problem to solve later. Serving is not a deployment problem; it is a continuous engineering discipline with its own tools, metrics, and trade-offs. Underfunding serving infrastructure is one of the most common reasons AI products fail to scale.

- **Ignoring GPU utilization.** Many teams deploy models on expensive GPU instances without measuring how effectively those GPUs are used. A fleet running at 15% utilization is burning 85% of its GPU budget on idle time. Monitoring GPU utilization, KV cache pressure, and batch fill rates is as important as monitoring CPU and memory for traditional services.

- **Treating all inference as request-response.** Not all inference fits the request-response model. Streaming workloads require persistent connections, stateful sessions, and bidirectional communication. Teams that force streaming workloads into request-response architectures end up with high latency, broken connections, and frustrated users.

- **Assuming latency is a single number.** "Our p50 latency is 150ms" tells you almost nothing about the user experience. The p95 and p99 matter more: they tell you what the worst 5% and 1% of users experience. A system with 150ms p50 and 3 seconds p99 is not meeting a 300ms SLO for a significant fraction of users. Always measure and report percentiles.

- **Skipping cold start planning.** Teams that test only with warm instances are surprised when production auto-scaling events cause 30-60 second response times. Plan for cold starts from the beginning: warm pools, readiness probes, model caching, and graceful degradation during scale-up events.

- **Not metering cost alongside performance.** A system that meets its latency SLOs at 3x the necessary GPU cost is not well-optimized. Performance and cost are two sides of the same coin. Track cost per inference request alongside latency, and optimize for the combination.

- **Measuring the wrong interval.** Instrumenting latency with off-the-shelf HTTP middleware and connection gauges with default settings can produce metrics that are technically correct but operationally useless. Point-in-time gauge sampling at 60-second intervals misses all sub-second events: an active connections gauge reads zero despite hundreds of requests per second. Middleware that measures to headers-sent reports microsecond latencies for streaming requests that take minutes of GPU time. The lesson: instrument the full request lifecycle, not just the checkpoint that existing tooling makes easy. Chapters 6 and 12 cover the specific patterns.

## Summary

- ML inference serving is a distinct engineering discipline at the intersection of API engineering, ML infrastructure, and GPU optimization
- The serving engineer bridges the gap between trained models and production APIs, a gap where most organizations struggle
- Five characteristics make inference serving hard: high GPU costs, tight latency budgets, painful cold starts, continuous model lifecycle, and a cross-disciplinary talent gap
- Speech and audio inference is among the most demanding serving workloads: streaming, real-time, codec-dependent, bidirectional, and intolerant of dropped data
- The 300ms rule for voice AI is the anchor latency target throughout this book
- Key innovations since 2022 (continuous batching, PagedAttention, quantization, speculative decoding) have dramatically improved throughput and reduced cost per token
- Three generations of serving frameworks have consolidated into a landscape where LLM-optimized engines handle transformer workloads and multi-framework platforms serve general ML
- The business case spans user experience (latency determines usability), cost (GPU inference is the largest line item), and competitive advantage (infrastructure quality is a moat)
- This book takes a measurement-driven approach, focuses on serving not training, and uses audio as the running example because it combines the hardest constraints

## References

1. AssemblyAI (2025). "The 300ms Rule: Why Latency Makes or Breaks Voice AI." assemblyai.com/research/the-300ms-rule
2. Google (2024). "RAIL Performance Model." web.dev/rail
3. Ankur's Newsletter (2025). "The Real Price of AI: Pre-Training Vs. Inference Costs." ankursnewsletter.com
4. CloudZero (2025). "Your Guide To Inference Cost (And Turning It Into Margin Advantage)." cloudzero.com/blog/inference-cost
5. NVIDIA (2025). "LLM Inference Benchmarking: Performance Tuning with TensorRT-LLM." developer.nvidia.com/blog/llm-inference-benchmarking-performance-tuning-with-tensorrt-llm
6. vLLM (2025). "Inside vLLM: Anatomy of a High-Throughput LLM Inference System." blog.vllm.ai/2025/09/05/anatomy-of-vllm.html
7. OpenMeter (2025). "Real-Time Usage Metering." openmeter.io/docs

---

**Next: [Chapter 2: Model Serving Frameworks](./02-model-serving-frameworks.md)**
