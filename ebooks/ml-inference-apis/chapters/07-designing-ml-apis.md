# Chapter 7: Designing ML-Facing APIs

![Chapter 7 Opener](../assets/ch07-opener.html)

\newpage

## Overview

- How to design APIs specifically for ML inference workloads -- where request payloads are large, processing is expensive, and responses may stream incrementally
- The three interaction patterns (synchronous, asynchronous/long-running, streaming) and when to use each based on inference latency and client requirements
- Industry-standard patterns from Google AIPs, OpenAI, Deepgram, and AssemblyAI that have become the de facto conventions for ML APIs

## Resource-Oriented Design for Inference

### Applying Google AIP Principles

- Google's API Improvement Proposals (AIPs) provide the most rigorous framework for ML API design -- AIP-121 (resource-oriented design), AIP-133 (standard methods), AIP-136 (custom methods)
- Resource-oriented design means modeling ML concepts as resources: `models`, `deployments`, `predictions`, `transcriptions`, `operations`
- Standard methods (Create, Get, List, Update, Delete) apply to management resources -- a `Model` resource supports CRUD, a `Deployment` resource tracks where models are served
- Custom methods handle inference actions that do not map to CRUD -- `:predict`, `:transcribe`, `:synthesize` as custom methods on resources per AIP-136

### Naming Conventions for ML Resources

- Use nouns for resources (`/v1/models/{model_id}`, `/v1/transcriptions/{transcription_id}`) and verbs for custom methods (`/v1/models/{model_id}:predict`)
- Collection resources use plural nouns: `/v1/models`, `/v1/deployments`, `/v1/transcriptions`
- Inference endpoints as custom methods: `POST /v1/audio:transcribe`, `POST /v1/audio:synthesize` -- the colon indicates a custom method per AIP convention
- Avoid verb-only endpoints like `POST /transcribe` -- they lack resource context and make the API harder to extend

### Resource Lifecycle for Inference Artifacts

- Transcriptions, predictions, and generated outputs should be first-class resources with their own lifecycle
- Create a transcription resource on request, update its status as processing progresses, make results available via GET
- Retention policies: inference results should have configurable TTLs -- not all clients need results stored indefinitely
- Idempotency: inference requests should support idempotency keys to prevent duplicate processing on network retries

## Synchronous vs Asynchronous Patterns

### Synchronous Inference (Sub-Second)

- Appropriate for inference that completes within the client's timeout window -- typically under 1-2 seconds
- Pattern: `POST /v1/audio:transcribe` with audio payload, receive full transcription in the HTTP response body
- Advantages: simplest client integration, no polling or callback infrastructure needed
- Limitations: HTTP timeouts (typically 30-60 seconds) cap the maximum inference time; large audio files will timeout
- Use cases: short utterance transcription, single-image classification, embedding generation, real-time moderation

### Long-Running Operations (AIP-151 Pattern)

- For inference that takes seconds to minutes: batch transcription, document processing, video analysis
- Pattern: `POST /v1/audio:transcribe` returns an `Operation` resource immediately with `{ "name": "operations/abc123", "done": false }`
- Client polls `GET /v1/operations/abc123` until `done: true`, then reads the result from the `response` field
- Analogous to `Future` in Python, `Promise` in JavaScript -- the operation represents a handle to an eventual result
- Completion notification: support webhooks as an alternative to polling -- `POST` to a client-specified callback URL when the operation completes
- Cancellation: `POST /v1/operations/abc123:cancel` allows clients to abort expensive inference they no longer need

### Choosing Between Sync and Async

- Decision factors: expected inference duration, client tolerance for waiting, payload size, cost of tying up a connection
- Rule of thumb: if p99 latency exceeds 10 seconds, use long-running operations; if sub-second, use sync; between 1-10 seconds, consider the client's tolerance
- Batch inference is always async: processing hours of audio or thousands of images should return an operation, not hold a connection
- Some providers offer both: Deepgram supports sync transcription for short audio and async for files via a URL reference

![Sync vs Async vs Streaming Decision Tree](../assets/ch07-sync-vs-async-decision.html)

\newpage

## Streaming Response Design

### Server-Sent Events (SSE) -- The OpenAI Pattern

- SSE uses a single long-lived HTTP connection with `text/event-stream` content type -- server pushes events, client listens
- The original OpenAI Chat Completions pattern: `data:` prefix on each line, `data: [DONE]` signal for stream end
- The newer OpenAI Responses API introduces structured event types: `response.created`, `response.output_text.delta`, `response.output_text.done`, `response.completed`
- Advantages: works through HTTP proxies and CDNs, built-in browser support via `EventSource`, simple to implement
- Limitations: unidirectional (server to client only), no binary data support (must base64-encode audio), reconnection requires client-side state management

### WebSocket Messages -- The Deepgram/AssemblyAI Pattern

- WebSocket enables bidirectional streaming: client sends audio chunks, server sends transcription results, simultaneously
- JSON-framed messages with type discriminators: `{ "type": "Results", "channel": { "alternatives": [...] } }` for Deepgram, `{ "message_type": "FinalTranscript", "text": "..." }` for AssemblyAI
- Advantages: bidirectional (essential for real-time audio), binary support (send raw audio bytes without encoding), lower per-message overhead than HTTP
- Limitations: does not traverse HTTP-only proxies well, requires explicit connection management (heartbeats, reconnection), no built-in browser reconnection
- Best for: real-time audio streaming, speech-to-speech, any bidirectional ML inference

### gRPC Streaming -- The Google Pattern

- gRPC supports four streaming modes: unary, server-streaming, client-streaming, bidirectional streaming
- Bidirectional streaming for audio: client streams `StreamingRecognizeRequest` (audio chunks), server streams `StreamingRecognizeResponse` (transcription results)
- Protobuf serialization: strongly typed, compact binary encoding, automatic code generation for client libraries
- Advantages: type safety, efficient serialization, built-in flow control, multiplexing via HTTP/2
- Limitations: not natively supported in browsers (requires grpc-web proxy), higher setup complexity, less tooling for debugging (binary protocol)
- Best for: server-to-server communication, high-throughput internal APIs, Google Cloud Speech integration

### Comparing the Three Patterns

- SSE: simplest for server-to-client text streaming -- choose when the client only receives results (e.g., LLM text generation)
- WebSocket: best for bidirectional streaming -- choose when the client sends continuous data and receives continuous results (e.g., real-time audio)
- gRPC: best for typed, high-throughput server-to-server streaming -- choose when both sides are backend services with protobuf toolchains
- All three can carry the same semantic content -- the choice is about transport characteristics, not capabilities

![Streaming Response Pattern Comparison](../assets/ch07-streaming-response-patterns.html)

\newpage

## Error Handling for ML-Specific Failures

### ML-Specific HTTP Status Codes

- **400 Bad Request**: invalid audio format, unsupported codec, malformed input -- include specific error codes like `INVALID_AUDIO_FORMAT` or `UNSUPPORTED_SAMPLE_RATE`
- **404 Not Found**: requested model version does not exist or has been deprecated -- `MODEL_NOT_FOUND` with available versions in the error body
- **408 Request Timeout**: client took too long to send audio data on a streaming connection -- distinct from server-side inference timeout
- **413 Payload Too Large**: audio file exceeds the maximum size for synchronous processing -- suggest using async/batch endpoint
- **429 Too Many Requests**: rate limit exceeded -- include `Retry-After` header and indicate which limit was hit (requests/second, concurrent streams, daily quota)
- **503 Service Unavailable**: model not loaded, GPU unavailable, or system overloaded -- `MODEL_NOT_LOADED`, `GPU_UNAVAILABLE`, `SYSTEM_OVERLOADED` with `Retry-After`
- **504 Gateway Timeout**: inference exceeded the server-side timeout -- `INFERENCE_TIMEOUT` with the timeout value and suggestion to use async for long audio

### Error Response Structure

- Consistent error envelope: `{ "error": { "code": "MODEL_NOT_LOADED", "message": "...", "details": [...] } }` following Google AIP-193 error conventions
- Machine-readable error codes (for programmatic handling) plus human-readable messages (for developer debugging)
- The `details` array carries structured metadata: which model version was requested, what formats are supported, what the retry window is
- Streaming error events: on WebSocket/SSE streams, errors are sent as typed events (`{ "type": "error", "code": "...", "message": "..." }`) -- the stream may or may not close depending on severity

### Partial Failure in Streaming

- A streaming inference session may encounter errors mid-stream (e.g., a corrupted audio chunk) without the entire session failing
- Recoverable errors: skip the bad chunk, log a warning, continue processing -- the client receives a gap in results but the stream continues
- Fatal errors: model crash, GPU fault, OOM -- the stream must close with a clear error event and the client should reconnect
- The error severity contract: document which errors are recoverable (stream continues) vs fatal (stream closes) in the API specification

## API Versioning for ML Services

### Versioning Strategies

- **URL path versioning** (`/v1/`, `/v2/`): most common, most explicit -- Deepgram, AssemblyAI, and most ML providers use this
- **Header versioning** (`API-Version: 2025-03-31`): Azure OpenAI pattern -- allows the same URL to serve multiple API versions based on a date-stamped header
- **Content negotiation** (`Accept: application/vnd.api+json;version=2`): rarely used for ML APIs -- too complex for the benefit
- Recommendation: URL path versioning for public APIs (clarity), header versioning for APIs that evolve frequently with backward-compatible changes

### Model Version to API Version Mapping

- API versions and model versions are independent concerns -- an API v1 can serve model v1, v2, or v3
- The API contract defines input/output schemas; the model version determines the quality/accuracy of the output
- Model version selection: allow clients to pin a model version (`model=whisper-large-v3`) or use a floating alias (`model=whisper-latest`)
- Breaking changes: a new model version that changes output schema (e.g., adding a new field, changing confidence score range) requires a new API version
- Non-breaking changes: a new model version that improves accuracy without changing the output schema can be deployed under the existing API version

### Deprecation and Sunset Policy

- Announce deprecation at least 6 months before removal -- communicate via API response headers (`Sunset: Sat, 01 Mar 2027 00:00:00 GMT`, `Deprecation: true`)
- Model version deprecation: when a model version is deprecated, return a warning header but continue serving until the sunset date
- Migration guides: provide clear documentation mapping old API patterns to new ones -- automated migration tools for SDK users
- The Azure OpenAI model: rolling `api-version` dates (e.g., `2025-03-31`) with a latest alias and documented retirement schedule

![API Versioning and Model Version Mapping](../assets/ch07-versioning-strategies.html)

\newpage

## SDK and Developer Experience

### Client Library Design

- Official SDKs in the top 3-5 languages used by your customers -- at minimum Python, JavaScript/TypeScript, and one systems language (Go, Rust, Java)
- SDK generation from OpenAPI specifications: tools like openapi-generator produce consistent, type-safe clients across languages
- Streaming SDK design: provide high-level abstractions (async iterators, callback handlers) that hide connection management details
- Error handling in SDKs: translate HTTP error codes into language-idiomatic exceptions/errors with rich context

### Documentation Patterns

- Interactive API reference (Swagger UI, Redoc) with runnable examples -- essential for inference APIs where developers need to test with real data
- Quick-start guides for each use case: "Transcribe a file in 5 minutes", "Set up real-time streaming", "Batch process audio files"
- Code samples in every supported language for every endpoint -- inference APIs are evaluated by developers during trials, and poor docs lose deals
- Streaming documentation requires special attention: show connection lifecycle, message formats, error handling, and reconnection logic

### Making Inference APIs Easy to Integrate

- Sensible defaults: if a client does not specify a model version, use the latest stable; if no language is specified, auto-detect
- Minimal required parameters: an inference endpoint should work with just the input data -- everything else should have defaults
- Consistent response shapes: every endpoint returns the same top-level structure (even if some fields are empty) -- reduces client-side conditional logic
- Playground/sandbox environment: let developers test inference without billing -- crucial for evaluation and debugging

## Multimodality as First-Class Design

### The 2025+ API Landscape

- Modern inference APIs must handle multiple modalities: text, audio, image, video -- often in the same request
- OpenAI's approach: unified input format where content can be text, image URL, or audio -- the model handles multimodal input natively
- Google's approach: Vertex AI Gemini API accepts interleaved text, image, audio, and video in a single prompt
- Design implication: API schemas should use a content-type-aware input format rather than modality-specific endpoints

### Multimodal Input/Output Design

- Input union types: a `content` field that accepts `{ "type": "text", "text": "..." }` or `{ "type": "audio", "data": "base64...", "format": "wav" }` or `{ "type": "image", "url": "..." }`
- Output union types: responses should similarly support mixed modalities -- a speech-to-text-to-speech pipeline returns both text and audio
- Format negotiation: clients specify desired output modalities -- `output_modalities: ["text", "audio"]` allows the server to generate both
- Streaming multimodal: interleaved text and audio events on the same stream -- OpenAI Realtime API demonstrates this pattern

### Backward Compatibility with Multimodal Extensions

- Start with single-modality endpoints (e.g., `/v1/audio:transcribe`) and extend to multimodal by wrapping input in a content array
- Existing clients that send raw audio continue to work -- the API treats a bare audio payload as `[{ "type": "audio", "data": ... }]`
- New multimodal-aware clients send the structured content format -- the API handles both transparently
- This gradual evolution avoids a breaking API version change when adding multimodal support

> **From Book 1:** For a deep dive on rate limiting algorithms and traffic management for APIs, see "Before the 3 AM Alert" Chapter 10.

## Common Pitfalls

- **Designing sync-only APIs for long-running inference**: any inference that can exceed 10 seconds needs an async/LRO pattern -- clients will timeout and retry, creating duplicate work
- **Conflating model version with API version**: changing a model should not require clients to update their integration -- keep the API contract stable across model versions
- **Inconsistent error responses**: every error path (validation, inference, timeout, rate limit) should use the same error envelope -- inconsistency breaks client error handling
- **No streaming error protocol**: defining message formats for success but not for errors on streaming connections -- clients need to know what an error event looks like
- **Building WebSocket APIs when SSE would suffice**: if the client only receives data (text generation, non-interactive transcription), SSE is simpler and more compatible
- **Ignoring SDK ergonomics**: a well-designed HTTP API with a poorly designed SDK will frustrate developers more than a mediocre API with a great SDK
- **No deprecation policy**: removing or changing endpoints without notice breaks production integrations and erodes trust

## Summary

- Resource-oriented design (Google AIP principles) provides the most maintainable foundation for ML APIs -- model inference as custom methods on resources
- Three interaction patterns: sync (sub-second inference), long-running operations (seconds to minutes), streaming (continuous bidirectional) -- choose based on latency profile
- SSE (OpenAI pattern) for server-to-client text streaming, WebSocket (Deepgram pattern) for bidirectional audio, gRPC (Google pattern) for typed server-to-server communication
- ML-specific error handling requires domain-aware status codes (model not loaded, GPU OOM, inference timeout) in a consistent error envelope
- API versioning and model versioning are independent -- URL path versioning for API contracts, client-specified model versions for inference quality
- SDK quality and documentation are as important as API design -- developers evaluate inference APIs through their integration experience
- Multimodal input/output is becoming table stakes -- design APIs with content-type-aware schemas that extend gracefully from single-modality to multimodal
- Forward reference: metering and billing for these API patterns is covered in Chapter 8

## References

*To be populated during chapter authoring. Initial sources:*

1. Google AIP (2025). AIP-121: Resource-oriented design. aip.dev/121
2. Google AIP (2025). AIP-133: Standard methods. aip.dev/133
3. Google AIP (2025). AIP-136: Custom methods. aip.dev/136
4. Google AIP (2025). AIP-151: Long-running operations. aip.dev/151
5. OpenAI (2025). "API Reference -- Chat Completions and Responses API Streaming."
6. OpenAI (2025). "OpenAI for Developers in 2025." openai.com/index/openai-for-developers-in-2025
7. Deepgram (2025). "Streaming API Reference." developers.deepgram.com
8. AssemblyAI (2025). "Real-Time Streaming API." assemblyai.com/docs
9. Azure OpenAI (2025). "API versioning and model deprecation." learn.microsoft.com

---

**Next: [Chapter 8: Usage Metering & Billing](./08-usage-metering-billing.md)**
