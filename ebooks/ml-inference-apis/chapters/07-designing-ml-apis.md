# Chapter 7: Designing ML-Facing APIs

<!-- DIAGRAM: ch07-opener.html - Chapter 7 Opener -->

\newpage

## Overview

- **Ground the reader**: explain what makes ML APIs different from the web APIs most backend engineers are used to building. A typical web API receives a small JSON request, does a database lookup or some business logic, and returns a small JSON response in milliseconds. An ML inference API receives a large payload (an audio file, an image, a long text prompt), runs it through a neural network on a GPU (which may take hundreds of milliseconds to seconds), and may return results progressively as a stream rather than all at once. The request is expensive to process, hard to retry, and the response format depends on whether the caller wants real-time streaming or a complete result.
- How to design APIs specifically for ML inference workloads; where request payloads are large, processing is expensive, and responses may arrive synchronously, asynchronously, or as a stream
- Resource-oriented design principles from Google AIPs applied to inference, the sync vs async vs streaming decision framework, and long-running operations for batch workloads
- ML-specific error handling patterns that go beyond standard HTTP errors; model not loaded, GPU OOM, inference timeout, and how to communicate them clearly to clients

## Resource-Oriented Design for Inference

### Applying Google AIP Principles

- Google's API Improvement Proposals (AIPs) provide the most rigorous framework for ML API design; AIP-121 (resource-oriented design), AIP-133 (standard methods), AIP-136 (custom methods)
- Resource-oriented design means modeling ML concepts as resources: `models`, `deployments`, `predictions`, `transcriptions`, `operations`
- Standard methods (Create, Get, List, Update, Delete) apply to management resources; a `Model` resource supports CRUD, a `Deployment` resource tracks where models are served
- Custom methods handle inference actions that do not map to CRUD; `:predict`, `:transcribe`, `:synthesize` as custom methods on resources per AIP-136

### Naming Conventions for ML Resources

- Use nouns for resources (`/v1/models/{model_id}`, `/v1/transcriptions/{transcription_id}`) and verbs for custom methods (`/v1/models/{model_id}:predict`)
- Collection resources use plural nouns: `/v1/models`, `/v1/deployments`, `/v1/transcriptions`
- Inference endpoints as custom methods: `POST /v1/audio:transcribe`, `POST /v1/audio:synthesize`; the colon indicates a custom method per AIP convention
- Avoid verb-only endpoints like `POST /transcribe`; they lack resource context and make the API harder to extend

### Resource Lifecycle for Inference Artifacts

- Transcriptions, predictions, and generated outputs should be first-class resources with their own lifecycle
- Create a transcription resource on request, update its status as processing progresses, make results available via GET
- Retention policies: inference results should have configurable TTLs; not all clients need results stored indefinitely
- Idempotency: inference requests should support idempotency keys to prevent duplicate processing on network retries

## Synchronous vs Asynchronous vs Streaming Decision Framework

### Synchronous Inference (Sub-Second)

- Appropriate for inference that completes within the client's timeout window; typically under 1-2 seconds
- Pattern: `POST /v1/audio:transcribe` with audio payload, receive full transcription in the HTTP response body
- Advantages: simplest client integration, no polling or callback infrastructure needed
- Limitations: HTTP timeouts (typically 30-60 seconds) cap the maximum inference time; large audio files will timeout
- Use cases: short utterance transcription, single-image classification, embedding generation, real-time moderation

### Long-Running Operations (AIP-151 Pattern)

- For inference that takes seconds to minutes: batch transcription, document processing, video analysis
- Pattern: `POST /v1/audio:transcribe` returns an `Operation` resource immediately with `{ "name": "operations/abc123", "done": false }`
- Client polls `GET /v1/operations/abc123` until `done: true`, then reads the result from the `response` field
- Analogous to `Future` in Python, `Promise` in JavaScript; the operation represents a handle to an eventual result
- Completion notification: support webhooks as an alternative to polling; `POST` to a client-specified callback URL when the operation completes
- Cancellation: `POST /v1/operations/abc123:cancel` allows clients to abort expensive inference they no longer need

### Streaming Inference (Continuous)

- For inference where results arrive incrementally over the lifetime of the connection; real-time transcription, LLM text generation, TTS audio playback
- Pattern: client opens a persistent connection and receives a series of partial result events as inference progresses
- Three transport options for streaming: SSE, WebSocket, gRPC; the choice depends on directionality, payload type, and ecosystem (detailed in Chapter 8)
- The decision of sync vs async vs streaming hinges on: expected inference duration, client tolerance for waiting, payload size, whether results are incremental or all-at-once

### The Decision Framework

- If p99 latency is sub-second and the result is a single atomic response: synchronous
- If p99 latency exceeds 10 seconds and the result is delivered all-at-once: long-running operation (AIP-151)
- If results arrive incrementally as inference progresses (word-by-word transcription, token-by-token generation): streaming
- Between 1-10 seconds with an atomic result: consider the client's tolerance; mobile clients prefer async, server-to-server can tolerate sync
- Batch workloads (hours of audio, thousands of images) are always long-running operations; never hold a connection

<!-- DIAGRAM: ch07-sync-vs-async-decision.html - Sync vs Async vs Streaming Decision Tree -->

\newpage

## Request and Response Schema Design

### Inference Request Schemas

- Minimal required parameters: an inference endpoint should work with just the input data; model version, language, and options should have sensible defaults
- Input formats: raw binary (audio bytes in request body), base64-encoded (audio in JSON), URL reference (audio hosted externally and fetched server-side)
- Configuration parameters: model version, language/locale, optional features (diarization, punctuation, PII redaction); all optional with defaults
- Request metadata: idempotency key, client-generated request ID for tracing, callback URL for async completion notifications

### Inference Response Schemas

- Consistent response envelope: every endpoint returns the same top-level structure; `{ "result": {...}, "metadata": {...} }`; even if some fields are empty
- Response metadata: request ID, model version used, processing duration, token/audio-second usage (for client-side cost tracking)
- Pagination for large results: batch inference may produce results too large for a single response; use cursor-based pagination on the result resource
- Content-type negotiation: support JSON for structured results and binary for audio output; use `Accept` header to let clients choose

### Schema Evolution Principles

- Additive-only changes within an API version: new optional fields can be added to responses without breaking clients
- Required fields are forever: once a field is marked required, it cannot be removed without a new API version
- Default values for new optional fields ensure existing clients that do not send the field get backward-compatible behavior
- Forward reference: the full versioning strategy (URL path, header, model version pinning) is covered in Chapter 9

## Error Handling for ML-Specific Failures

### ML-Specific HTTP Status Codes

- **400 Bad Request**: invalid audio format, unsupported codec, malformed input; include specific error codes like `INVALID_AUDIO_FORMAT` or `UNSUPPORTED_SAMPLE_RATE`
- **404 Not Found**: requested model version does not exist or has been deprecated; `MODEL_NOT_FOUND` with available versions in the error body
- **408 Request Timeout**: client took too long to send audio data on a streaming connection; distinct from server-side inference timeout
- **413 Payload Too Large**: audio file exceeds the maximum size for synchronous processing; suggest using async/batch endpoint
- **429 Too Many Requests**: rate limit exceeded; include `Retry-After` header and indicate which limit was hit (requests/second, concurrent streams, daily quota)
- **503 Service Unavailable**: model not loaded, GPU unavailable, or system overloaded; `MODEL_NOT_LOADED`, `GPU_UNAVAILABLE`, `SYSTEM_OVERLOADED` with `Retry-After`
- **504 Gateway Timeout**: inference exceeded the server-side timeout; `INFERENCE_TIMEOUT` with the timeout value and suggestion to use async for long audio

<!-- DIAGRAM: ch07-error-handling-taxonomy.html - ML API Error Handling Taxonomy -->

\newpage

### Error Response Structure

- Consistent error envelope: `{ "error": { "code": "MODEL_NOT_LOADED", "message": "...", "details": [...] } }` following Google AIP-193 error conventions
- Machine-readable error codes (for programmatic handling) plus human-readable messages (for developer debugging)
- The `details` array carries structured metadata: which model version was requested, what formats are supported, what the retry window is
- Streaming error events: on WebSocket/SSE streams, errors are sent as typed events (`{ "type": "error", "code": "...", "message": "..." }`); the stream may or may not close depending on severity

### Partial Failure in Streaming

- A streaming inference session may encounter errors mid-stream (e.g., a corrupted audio chunk) without the entire session failing
- Recoverable errors: skip the bad chunk, log a warning, continue processing; the client receives a gap in results but the stream continues
- Fatal errors: model crash, GPU fault, OOM; the stream must close with a clear error event and the client should reconnect
- The error severity contract: document which errors are recoverable (stream continues) vs fatal (stream closes) in the API specification

### Retryability Guidance

- Each error code should clearly indicate whether the client should retry, and if so, after how long
- Retryable errors: 503 (model not loaded; may recover after warm-up), 504 (timeout; may succeed with a shorter input), 429 (rate limited; retry after the specified window)
- Non-retryable errors: 400 (bad input; fix the request), 404 (model not found; check the model name), 413 (payload too large; use async)
- Include `Retry-After` header for all retryable errors; clients need a machine-readable signal, not just the status code

> **From Book 1:** For a deep dive on rate limiting algorithms and traffic management for APIs, see "Before the 3 AM Alert" Chapter 10.

## Common Pitfalls

- **Designing sync-only APIs for long-running inference**: any inference that can exceed 10 seconds needs an async/LRO pattern; clients will timeout and retry, creating duplicate work
- **Inconsistent error responses**: every error path (validation, inference, timeout, rate limit) should use the same error envelope; inconsistency breaks client error handling
- **No streaming error protocol**: defining message formats for success but not for errors on streaming connections; clients need to know what an error event looks like
- **Overloading a single endpoint for sync and async**: separate the sync and async patterns cleanly; either return results directly or return an operation, not both from the same endpoint depending on input size
- **Missing idempotency keys**: without idempotency support, network retries cause duplicate inference; expensive for GPU resources and confusing for clients
- **Verb-only endpoint naming**: `POST /transcribe` is harder to extend than `POST /v1/audio:transcribe`; resource-oriented design pays off as the API grows
- **No retryability guidance in error responses**: clients should not have to guess whether an error is transient; make `Retry-After` and retryability explicit

## Summary

- Resource-oriented design (Google AIP principles) provides the most maintainable foundation for ML APIs; model inference as custom methods on resources
- Three interaction patterns: sync (sub-second inference), long-running operations (seconds to minutes), streaming (continuous incremental results); choose based on latency profile and result delivery pattern
- Long-running operations (AIP-151) return an `Operation` with `name` + `done`, the client polls until complete; analogous to a `Future` or `Promise`
- Request schemas should require minimal parameters with sensible defaults; response schemas should use a consistent envelope with metadata
- ML-specific error handling requires domain-aware status codes (model not loaded 503, GPU OOM 503 with retry, inference timeout 504, invalid audio format 400, model version not found 404)
- Every error should include a machine-readable code, a human-readable message, and clear retryability guidance with `Retry-After` when applicable
- Forward reference: streaming response message design (SSE, WebSocket, gRPC) is covered in Chapter 8; versioning and developer experience in Chapter 9

## References

*To be populated during chapter authoring. Initial sources:*

1. Google AIP (2025). AIP-121: Resource-oriented design. aip.dev/121
2. Google AIP (2025). AIP-133: Standard methods. aip.dev/133
3. Google AIP (2025). AIP-136: Custom methods. aip.dev/136
4. Google AIP (2025). AIP-151: Long-running operations. aip.dev/151
5. Google AIP (2025). AIP-193: Errors. aip.dev/193

---

**Next: [Chapter 8: Streaming Response Contracts](./08-streaming-response-contracts.md)**
