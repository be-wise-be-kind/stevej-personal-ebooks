# Chapter 7: Streaming Inference Pipelines

<!-- DIAGRAM: ch07-opener.html - Chapter 6 Opener -->

\newpage

## Overview

- **Ground the reader**: explain what a "pipeline" means here. An inference pipeline is a sequence of processing steps that data flows through on its way to becoming a result. For speech recognition, raw audio bytes arrive from the network, get decoded from their compressed format, pass through voice activity detection (which identifies when someone is actually speaking), get batched together for efficient GPU use, run through the ML model, and then the model's output gets post-processed into readable text before being sent back to the client. Each step has different performance characteristics and failure modes.
- How to connect the transport layer (Chapters 5-6) to the inference layer (Chapters 2-3) through a coherent streaming pipeline
- The end-to-end journey of audio data: from network arrival through queuing, inference, post-processing, and response streaming
- Managing multiple concurrent streams on shared GPU resources while maintaining latency SLOs and graceful degradation under load

## Bridging the Gap

This chapter draws on concepts from both ML infrastructure and API engineering. If you have not encountered these before, this section provides the context you will need.

**From the ML side**, this chapter uses distributed tracing and queue theory concepts from backend engineering. Distributed tracing (OpenTelemetry) tracks a request across multiple services by attaching a unique trace ID; each processing step creates a "span" with timing data, so you can see exactly where latency accumulates. Queue theory describes requests waiting for processing: queue depth (how many are waiting) is a key load signal, and Little's Law relates average queue size to arrival rate and processing time. Backpressure means the system pushes back on incoming requests when it cannot keep up, rather than accepting unbounded work that would eventually crash the pipeline or blow latency SLOs.

**From the API side**, this chapter describes what happens inside the GPU during inference. The model processes audio through multiple "layers" of computation. Each layer reads intermediate results (stored in the KV cache), performs matrix multiplications on the input, and writes new results for the next layer. Batching groups multiple audio streams so these matrix operations process all of them in a single GPU pass, dramatically improving throughput at the cost of slightly higher per-request latency. Pipeline parallelism means overlapping CPU preprocessing of the next audio chunk with GPU inference on the current chunk, so neither the CPU nor GPU is idle waiting for the other.

## Bridging Transport and Inference

### The Pipeline Abstraction

- A streaming inference pipeline is a directed graph of processing stages, each with its own latency budget and failure modes
- The fundamental tension: transport layers deal in bytes and frames, inference layers deal in tensors and batches; the pipeline bridges this impedance mismatch
- Pipeline stages: network receive -> codec decode -> VAD -> chunking -> batching -> GPU inference -> post-processing -> response encoding -> network send
- Each stage can be synchronous or asynchronous, CPU-bound or GPU-bound; the pipeline scheduler must account for both

### Where Chapters 4-5 End and Chapter 6 Begins

- Chapters 4-5 establish how audio bytes arrive (WebSocket frames, gRPC streams, WebTransport datagrams) and how connections are managed
- This chapter covers what happens after the transport layer delivers audio data to the application: queuing, scheduling, inference, and response formation
- The handoff point: a decoded audio chunk in a normalized format (e.g., 16kHz 16-bit PCM) ready for inference processing

> **From Book 1:** For a deep dive on distributed tracing fundamentals and span propagation, see "Before the 3 AM Alert" Chapter 3.

## Request Queuing and Scheduling

### Queue Architecture for Streaming Workloads

- Streaming inference cannot use simple FIFO queues; chunks from the same stream must maintain ordering while chunks from different streams can be interleaved
- Per-stream ordering guarantee: chunks within a single audio stream are processed sequentially; parallelism happens across streams
- Queue depth as a load signal: when queue depth exceeds a threshold, the system should begin shedding load rather than accumulating unbounded latency
- Memory-bounded queues: each queued audio chunk consumes memory; unbounded queues during load spikes can cause OOM before the GPU becomes the bottleneck

### Priority Scheduling

- Not all streams are equal: paid tiers, real-time vs batch, short utterances vs long-form transcription
- Priority classes: interactive (sub-300ms SLO), standard (sub-1s SLO), batch (best-effort)
- Starvation prevention: even low-priority streams must make forward progress; use weighted fair queuing rather than strict priority
- Priority inversion risk: a long-running low-priority inference on the GPU can block a high-priority request if preemption is not supported

### Continuous Batching for Streaming

- Static batching (wait for N requests, process together) adds latency incompatible with real-time streaming
- Continuous batching (Chapter 1 concept applied here): as each inference completes, immediately replace it with the next queued chunk
- Batch formation for audio: group chunks by model type and configuration (language, sample rate) to enable efficient GPU execution
- The batch size vs latency tradeoff: larger batches improve GPU utilization but increase queue wait time for individual chunks

<!-- DIAGRAM: ch07-streaming-pipeline.html - Streaming Inference Pipeline Architecture -->

\newpage

## Partial Results and Incremental Decoding

### Interim vs Final Results

- Streaming transcription produces two result types: interim (tentative, may change) and final (committed, stable)
- Interim results give the user immediate feedback (words appearing as spoken) but can be revised as more audio context arrives
- Final results are emitted after an endpoint is detected (pause in speech, VAD trigger, forced timeout) and represent the system's best output
- The Deepgram/AssemblyAI pattern: stream interim results continuously, emit final results on speech endpoints, allow client to display either

### Incremental Decoding Strategies

- Token-by-token streaming: emit each decoded token as it is produced by the model; lowest latency, highest message overhead
- Chunk-based streaming: accumulate tokens until a natural boundary (word, phrase, sentence) and emit as a group; lower overhead, slightly higher latency
- Hybrid approach: emit token-by-token for the first few tokens (to show responsiveness), then switch to chunk-based for efficiency
- Buffering and debouncing: avoid sending updates faster than the client can render; 50-100ms debounce is common for transcription UIs

### Handling Revisions and Corrections

- Streaming ASR models may revise earlier tokens as more audio context arrives (the "look-ahead" effect)
- Revision protocol: each interim result includes a sequence number and character offset, allowing the client to replace previously displayed text
- The stability guarantee: providers like Deepgram offer a `stability` parameter that controls how aggressively interim results are emitted vs held for accuracy
- Client-side complexity: handling revisions requires the client to maintain a mutable transcript buffer, not just append

## Concurrent Stream Management

### Memory Multiplexing Across Streams

- Each active stream consumes GPU memory for its model state (KV cache for transformers, hidden states for RNNs/CTC models)
- The memory budget determines the maximum number of concurrent streams per GPU: total GPU memory / per-stream memory footprint
- Example: a Whisper-large model with 1.5GB base + ~50MB per active stream context allows roughly 20-30 concurrent streams on an A100 (80GB)
- Memory fragmentation: streams starting and ending at different times create fragmented GPU memory; PagedAttention concepts (Chapter 1) help here

### Compute Multiplexing

- GPU compute is shared across streams via batching; more streams in a batch means better utilization but higher per-stream latency
- The compute budget: total GPU FLOPS / per-chunk inference FLOPS determines maximum sustained throughput
- CUDA streams for overlapping: use separate CUDA streams to overlap data transfer (CPU-to-GPU) with computation on the previous batch
- CPU-bound stages (VAD, codec decode, post-processing) should be parallelized on CPU cores to avoid becoming the bottleneck for GPU-bound inference

### Stream Lifecycle Management

- Stream creation: allocate per-stream state (buffers, sequence counters, model context); this allocation must be fast to avoid first-chunk latency spikes
- Stream maintenance: track per-stream metrics (chunks processed, cumulative latency, error count) for SLO monitoring
- Stream teardown: release GPU memory and buffers promptly on stream close to free resources for new streams
- Zombie stream detection: streams that stop sending audio but never close the connection; implement idle timeouts (e.g., 30s of silence) to reclaim resources

<!-- DIAGRAM: ch07-concurrent-streams.html - Concurrent Streams Sharing GPU Resources -->

\newpage

## Graceful Degradation Under Load

### Load Detection Signals

- Queue depth: the most direct signal; if chunks are accumulating faster than inference can process them, the system is overloaded
- GPU utilization: sustained >90% utilization with growing queue depth indicates saturation
- Per-stream latency: if p95 latency exceeds the SLO threshold, the system should proactively shed load before SLO breach
- Memory pressure: approaching GPU memory limits means new streams cannot be accepted

### Quality Reduction Strategies

- Lower sample rate: downsample 48kHz to 16kHz before inference; reduces compute per chunk at the cost of some accuracy
- Simpler model variant: switch from a large model to a distilled/smaller variant; e.g., Whisper-large to Whisper-small
- Reduced post-processing: skip optional enrichment steps (punctuation restoration, speaker diarization) to reduce pipeline latency
- Lower interim update frequency: reduce how often interim results are emitted to save compute on partial decoding

### Request Rejection Strategies

- HTTP 503 with Retry-After header: tell the client exactly when to retry; prevents thundering herd on recovery
- Connection admission control: reject new stream connections at the transport layer before they consume any GPU resources
- Selective rejection by priority: shed batch and standard-tier streams before interactive-tier streams
- Circuit breaker pattern: if error rate exceeds a threshold, temporarily reject all new streams and drain existing ones

### The Degradation Decision Tree

- Step 1: Is queue depth growing? If yes, proceed to step 2
- Step 2: Can quality be reduced (model variant, sample rate)? If yes, apply quality reduction and monitor
- Step 3: Is the system still overloaded after quality reduction? If yes, begin rejecting new low-priority streams
- Step 4: Still overloaded? Reject all new streams with 503 + Retry-After, continue serving existing streams
- Step 5: Memory pressure critical? Begin gracefully closing longest-running low-priority streams

<!-- DIAGRAM: ch07-degradation-strategies.html - Degradation Strategy Decision Tree -->

\newpage

## End-to-End Latency Tracing

### Adapting Distributed Tracing for Continuous Streams

- Traditional request/response tracing (one span per request) does not fit streaming; a single stream may last minutes to hours
- Per-chunk tracing: create a span for each audio chunk as it passes through the pipeline; link all chunk spans to a parent stream span
- The parent stream span captures the entire stream lifecycle (connect, first chunk, last chunk, close) while child spans capture per-chunk processing
- Span attributes for streaming: `stream.id`, `chunk.sequence_number`, `chunk.duration_ms`, `model.variant`, `batch.size`

> **From Book 1:** For the fundamentals of OpenTelemetry tracing, span context propagation, and trace collection, see "Before the 3 AM Alert" Chapter 3.

### Key Latency Breakpoints to Instrument

- Chunk arrival to queue entry: measures transport layer overhead
- Queue entry to batch formation: measures queue wait time; the primary indicator of load
- Batch formation to GPU submission: measures CPU-side batch preparation
- GPU submission to inference complete: measures model execution time; varies with batch size and model complexity
- Inference complete to response sent: measures post-processing and response serialization
- Total chunk-to-response latency: the end-to-end metric clients care about

### Streaming-Specific Metrics

- Time to first result (TTFR): how long from the first audio chunk arriving to the first interim result being sent; the "perceived latency" for users
- Interim result freshness: the age of the most recent audio data reflected in the latest interim result
- Final result delay: time between the speech endpoint and the final result emission
- Stream setup latency: time from connection establishment to readiness to accept audio; includes model loading if applicable
- Jitter: variance in per-chunk processing time; high jitter causes stuttering in real-time playback scenarios

### Pure ASGI Middleware for Streaming Measurement

- Standard HTTP middleware (e.g., Starlette's `BaseHTTPMiddleware`) measures request duration only until response headers are sent, then returns control to the caller. The body streaming phase is invisible to the middleware's timing
- For streaming audio inference, the response body phase IS the inference: audio bytes or transcript chunks stream for seconds to minutes after headers are flushed. A streaming transcription request that consumes 30 seconds of GPU time shows as sub-millisecond latency in header-only metrics
- **Solution**: implement pure ASGI middleware that wraps the full `await app(scope, receive, send)` call. This captures the entire request lifecycle including all response body chunks, connection close, and any streaming errors
- The middleware intercepts the `send` callable to capture the status code from the `http.response.start` message, then records the total duration after the final `http.response.body` message (or after the ASGI app returns for WebSocket/streaming connections)
- This is not optional for streaming ML APIs: every SLO target, latency alert, and capacity plan depends on accurate duration measurement. Header-only timing makes every downstream decision wrong
- For batch/synchronous endpoints where the full response is sent in a single body chunk, the difference is negligible; the middleware handles both cases transparently

### Middleware Ordering for Exemplar Support

- For Python ASGI frameworks (FastAPI, Starlette), middleware executes in LIFO order: the last middleware added wraps the outermost layer of the request lifecycle
- **Tracing middleware must wrap metrics middleware** (i.e., tracing is added after metrics in code, making it outermost in execution) so that the request's active span is available during metric recording
- Without correct ordering, metrics are recorded outside any span context: OpenTelemetry exemplars cannot attach a `trace_id` to histogram observations, and the link from a metric spike to the specific trace that caused it is impossible
- **For ML inference debugging, this is critical**: when P99 latency spikes on the golden signals dashboard, exemplars let you click directly from the metric graph to the trace waterfall of the specific slow request. Without exemplars, you can see that latency spiked but cannot determine which request caused it or which pipeline stage was responsible
- Recommended ordering (innermost to outermost in execution): routing → metrics middleware → tracing middleware → authentication
- Verify the setup by checking that histogram metric observations include exemplar metadata (`trace_id`, `span_id`) in your metrics backend (e.g., Mimir, Prometheus with exemplar support enabled)

## Pipeline Composition

### The Standard Audio Inference Pipeline

- **Stage 1; VAD (Voice Activity Detection)**: detect speech segments within the audio stream, skip silence; reduces unnecessary inference by 30-70% depending on the audio
- **Stage 2; Chunking**: segment continuous audio into inference-sized chunks (typically 1-30 seconds) based on VAD boundaries and maximum chunk length
- **Stage 3; Pre-processing**: resample, normalize volume, apply noise reduction if configured; CPU-bound, parallelizable
- **Stage 4; Inference**: the GPU-bound core; run the ML model on the prepared chunk, produce raw output (logits, tokens, embeddings)
- **Stage 5; Post-processing**: decode model output into human-readable form; apply punctuation restoration, capitalization, formatting, confidence scoring
- **Stage 6; Response streaming**: serialize the result and send it back through the transport layer (WebSocket message, gRPC response, SSE event)

### Pipeline Parallelism

- Pipeline stages can overlap: while Stage 4 processes chunk N on the GPU, Stage 1-3 can prepare chunk N+1 on the CPU
- The pipeline throughput is limited by its slowest stage; usually GPU inference (Stage 4)
- Pre-fetching: begin preparing the next chunk before the current inference completes to minimize GPU idle time between batches
- Pipeline depth: deeper pipelines (more stages) increase total latency but enable better resource utilization through parallelism

### Dynamic Pipeline Configuration

- Not all streams need the same pipeline: a simple transcription stream can skip diarization and NER stages
- Feature flags on the pipeline: client-specified options (e.g., `enable_diarization=true`) add or remove pipeline stages at stream creation time
- Cost implications: each additional stage increases compute time and cost; this feeds directly into metering (Chapter 14)
- Runtime reconfiguration: some systems allow changing pipeline configuration mid-stream (e.g., enabling punctuation after stream start)

### Error Handling Across Pipeline Stages

- Each stage should fail independently: a post-processing failure should not crash the inference stage
- Retry semantics differ by stage: VAD and pre-processing can be retried cheaply; GPU inference retries are expensive
- Dead letter handling: chunks that fail all retry attempts are logged with full context for debugging, and the stream receives an error event rather than a dropped result
- Partial pipeline failure: if an optional stage (e.g., diarization) fails, emit results without that enrichment rather than failing the entire chunk

## Common Pitfalls

- **Treating streaming as repeated request/response**: streaming pipelines require continuous state management, not stateless per-request processing; reusing a request/response framework leads to excessive overhead per chunk
- **Unbounded queue growth**: without queue depth limits and backpressure, a load spike causes OOM before the GPU becomes saturated
- **Ignoring pipeline stage imbalance**: if CPU-bound pre-processing is slower than GPU inference, the GPU sits idle between batches; profile each stage independently
- **No graceful degradation strategy**: systems that work perfectly at 80% load and crash at 100% load are missing the degradation layer between those points
- **Over-tracing in production**: per-chunk tracing at full fidelity generates enormous telemetry volume; use sampling (e.g., trace 1 in 100 streams) for production, full tracing for debugging
- **Zombie stream accumulation**: streams that stop sending audio but never disconnect slowly consume all available GPU memory and connection slots

## Summary

- A streaming inference pipeline bridges the transport layer (Chapters 4-5) and the inference layer (Chapters 2-3) through a multi-stage processing graph
- Request queuing must maintain per-stream ordering while enabling cross-stream parallelism through continuous batching
- Partial results (interim vs final) are essential for user experience; the Deepgram/AssemblyAI pattern of streaming interim results with endpoint-triggered finals is the industry standard
- Concurrent stream management requires careful GPU memory and compute budgeting; each stream has a per-stream memory footprint that limits concurrency
- Graceful degradation follows a hierarchy: quality reduction first (simpler model, lower sample rate), then selective rejection, then full load shedding with 503 + Retry-After
- End-to-end tracing for streams uses per-chunk spans linked to a parent stream span, with TTFR and jitter as streaming-specific metrics
- The standard pipeline is VAD -> chunking -> pre-processing -> inference -> post-processing -> response streaming, with pipeline parallelism overlapping CPU and GPU stages
- Pipeline composition is dynamic: client options add/remove stages, and each stage fails independently

## References

*To be populated during chapter authoring. Initial sources:*

1. vLLM Documentation (2025). "Continuous Batching and PagedAttention."
2. SGLang (2025). "RadixAttention for Efficient KV Cache Reuse."
3. Deepgram (2025). "Streaming API Reference; Interim and Final Results."
4. AssemblyAI (2025). "Real-Time Streaming Transcription Documentation."
5. BentoML (2025). "LLM Inference Handbook; Pipeline Composition."
6. OpenTelemetry (2025). "Distributed Tracing for Streaming Systems."

---

**Next: [Chapter 8: Designing ML-Facing APIs](./08-designing-ml-apis.md)**
