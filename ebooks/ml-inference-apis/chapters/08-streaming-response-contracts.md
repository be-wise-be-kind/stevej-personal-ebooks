# Chapter 8: Streaming Response Contracts

![Chapter 8 Opener](../assets/ch08-opener.html)

\newpage

## Overview

- What streaming inference messages actually look like on the wire -- the event schemas, message framing, and lifecycle signals that clients consume on top of SSE, WebSocket, and gRPC transports
- Chapter 5 (Protocol Selection) answers "which transport?" -- this chapter answers "what do the messages look like on top of that transport?"
- Connection lifecycle management, backpressure, and reconnection strategies that make streaming APIs reliable in production

## Server-Sent Events (SSE) -- The OpenAI Pattern

### The Chat Completions Streaming Contract

- SSE uses a single long-lived HTTP connection with `text/event-stream` content type -- server pushes events, client listens
- The original OpenAI Chat Completions pattern: each chunk is a line prefixed with `data:` containing a JSON object with `choices[].delta.content`
- Stream termination: `data: [DONE]` signal indicates the server has finished generating -- the client should close the connection
- Advantages: works through HTTP proxies and CDNs, built-in browser support via `EventSource`, simple to implement

### The Responses API Streaming Contract

- The newer OpenAI Responses API introduces structured event types with explicit lifecycle semantics
- Event types: `response.created`, `response.in_progress`, `response.output_text.delta`, `response.output_text.done`, `response.completed`
- Each event carries a typed payload -- `response.output_text.delta` includes `{ "delta": "partial text" }`, `response.completed` includes the full response object
- Advantage over Chat Completions: the event type field makes it trivial to route events to different handlers without inspecting the payload structure

### SSE Design Patterns for ML APIs

- Event naming convention: `resource.action` pattern (e.g., `transcription.created`, `transcription.word.delta`, `transcription.completed`) gives clients a predictable taxonomy
- Include a sequence number or event ID in each SSE event -- enables `Last-Event-ID` header for reconnection without data loss
- Intermediate metadata events: emit `transcription.metadata` events mid-stream with running totals (words processed, confidence, duration metered) for progress tracking
- Limitations: unidirectional (server to client only), no binary data support (must base64-encode audio), text-only framing adds overhead for non-text payloads

## WebSocket Messages -- The Deepgram/AssemblyAI Pattern

### JSON-Framed Message Design

- WebSocket enables bidirectional streaming: client sends audio chunks, server sends transcription results, simultaneously
- Deepgram message schema: `{ "type": "Results", "channel_index": [0, 1], "is_final": true, "channel": { "alternatives": [{ "transcript": "...", "confidence": 0.98 }] } }`
- AssemblyAI message schema: `{ "message_type": "FinalTranscript", "text": "...", "words": [...], "confidence": 0.97 }` with separate `PartialTranscript` for interim results
- Type discriminator field (`type` or `message_type`) is essential -- it allows the client to dispatch messages to the correct handler without parsing the full payload

### Binary Audio Frames vs JSON Control Messages

- A single WebSocket connection carries both binary frames (raw audio from client to server) and text frames (JSON messages in both directions)
- Client sends: binary audio frames (PCM, Opus, FLAC bytes) interleaved with JSON control messages (start, stop, configure)
- Server sends: JSON result messages (interim/final transcripts) interleaved with JSON control messages (ready, error, close)
- Frame type discrimination: WebSocket's built-in opcode distinguishes binary (0x2) from text (0x1) -- no application-layer framing needed for this split

### Interim and Final Results Pattern

- Interim results: tentative transcription that may change as more audio context arrives -- useful for real-time display but not for persistence
- Final results: committed transcription emitted after a speech endpoint (pause, VAD trigger, forced timeout) -- stable and safe to persist
- The `is_final` boolean (Deepgram) or `message_type` discrimination (AssemblyAI `PartialTranscript` vs `FinalTranscript`) signals result stability
- Client rendering strategy: display interim results in a mutable buffer, replace with finals when they arrive, append new interims after the last final

![Interim vs Final Results in Streaming Transcription](../assets/ch08-interim-final-results.html)

\newpage

## gRPC Streaming -- The Google Pattern

### Bidirectional Streaming Contract

- gRPC supports four streaming modes: unary, server-streaming, client-streaming, bidirectional streaming
- Google Cloud Speech bidirectional streaming: client streams `StreamingRecognizeRequest` (audio chunks + config), server streams `StreamingRecognizeResponse` (transcription results)
- The first client message carries `StreamingRecognitionConfig` (model, language, encoding, sample rate); subsequent messages carry `audio_content` bytes
- Server responses include `results[]` with `alternatives[]`, `is_final`, `stability` score, and `result_end_time` -- similar semantics to WebSocket but with protobuf typing

### Protobuf Message Design for Inference

- Protobuf serialization: strongly typed, compact binary encoding, automatic code generation for client libraries in every major language
- Message schema evolution: adding new optional fields to a protobuf message is backward-compatible -- old clients ignore unknown fields
- Oneof fields for polymorphic messages: use `oneof` to represent different event types in a single message (e.g., `oneof streaming_response { result, error, end_of_utterance }`)
- Advantages: type safety catches schema mismatches at compile time, efficient serialization reduces bandwidth, built-in flow control via HTTP/2

### gRPC-Specific Considerations

- Status codes: gRPC uses its own status code system (OK, CANCELLED, DEADLINE_EXCEEDED, RESOURCE_EXHAUSTED) -- map to HTTP equivalents for documentation
- Metadata (headers/trailers): carry request IDs, model version, and billing metadata in gRPC metadata rather than in the message payload
- Deadlines: gRPC deadlines propagate through the call chain -- set appropriate deadlines for streaming sessions that may last minutes
- Limitations: not natively supported in browsers (requires grpc-web proxy), higher setup complexity, less tooling for debugging (binary protocol)

## Comparing the Three Streaming Patterns

### Decision Framework

- **SSE**: simplest for server-to-client text streaming -- choose when the client only receives results (e.g., LLM text generation, non-interactive transcription playback)
- **WebSocket**: best for bidirectional streaming -- choose when the client sends continuous data and receives continuous results (e.g., real-time audio transcription, speech-to-speech)
- **gRPC**: best for typed, high-throughput server-to-server streaming -- choose when both sides are backend services with protobuf toolchains (e.g., internal microservice calls, Google Cloud integration)
- All three can carry the same semantic content -- the choice is about transport characteristics, not message capabilities

### Message Schema Portability

- Design your logical message schema independently of transport -- define `TranscriptionResult`, `Error`, `SessionEnd` as abstract message types
- Serialize to JSON for SSE and WebSocket, to protobuf for gRPC -- the same logical contract, different wire formats
- This abstraction makes it practical to offer multiple transports for the same API without duplicating business logic
- Test contracts by defining a transport-agnostic test suite that validates message sequences regardless of wire format

![SSE vs WebSocket vs gRPC Streaming Response Patterns](../assets/ch08-streaming-response-patterns.html)

\newpage

## Connection Lifecycle Management

### Connection Establishment and Session Initialization

- SSE: client sends GET with `Accept: text/event-stream`, server responds with 200 and begins streaming -- session parameters via query string or headers
- WebSocket: HTTP upgrade handshake, then first JSON message carries session configuration (model, language, encoding, features)
- gRPC: channel establishment + first `StreamingRecognizeRequest` carries `StreamingRecognitionConfig`
- In all three patterns, the first exchange establishes the inference session before any data flows -- separate the "configure" phase from the "data" phase

### Keepalive and Heartbeat

- Long-lived connections are killed by idle timeouts at load balancers, proxies, and firewalls -- typically 60-120 seconds of inactivity
- Server-side keepalive: emit periodic heartbeat events (SSE: `event: keepalive\ndata: {}\n\n`, WebSocket: ping frames or `{ "type": "KeepAlive" }`, gRPC: HTTP/2 PING frames)
- Client-side keepalive: clients should send periodic signals on bidirectional connections (WebSocket audio frames or explicit keepalive messages)
- Keepalive interval should be shorter than the shortest idle timeout in the network path -- 30 seconds is a safe default

### Reconnection Strategies

- SSE: built-in reconnection via `Last-Event-ID` header -- the server resumes from the last acknowledged event, no data loss if events are buffered
- WebSocket: no built-in reconnection -- client must detect disconnection (close event, ping timeout), reconnect, and resend session configuration
- gRPC: client detects stream closure, reopens the stream, resends configuration -- no built-in resume semantics
- Session resumption: for WebSocket and gRPC, include a `session_id` that the server can use to recover in-progress state after reconnection

### Graceful and Ungraceful Termination

- Graceful close: client sends an explicit end signal (WebSocket: `{ "type": "CloseStream" }`, gRPC: half-close the client stream), server sends final results and closes
- Server-initiated close: server sends a termination event with a reason code (timeout, error, shutdown) before closing the connection
- Ungraceful close: network drop, client crash, server crash -- both sides must handle missing close signals via timeouts
- Resource cleanup: on any termination, the server must release GPU memory, flush pending results, emit final metering events

![Connection Lifecycle: Establishment, Data Flow, and Termination](../assets/ch08-connection-lifecycle.html)

\newpage

## Backpressure and Flow Control

### The Slow Consumer Problem

- If the server produces results faster than the client can consume them, buffered data grows without bound -- eventually causing memory exhaustion or message drops
- SSE: no application-level flow control -- relies on TCP backpressure, which can stall the entire server-side connection when the client's receive buffer fills
- WebSocket: no built-in flow control above TCP -- the server must monitor send buffer depth and take action when it grows
- gRPC: built-in HTTP/2 flow control with per-stream window sizes -- the most robust option for backpressure management

### Server-Side Backpressure Strategies

- Buffer depth monitoring: track the number of unsent messages per connection -- if the buffer exceeds a threshold, take action
- Drop interim results: skip interim/partial results when the client is behind -- deliver only final results, which are the most important
- Reduce update frequency: dynamically throttle how often the server emits events to a slow client -- e.g., switch from per-token to per-sentence
- Disconnect: if the client falls too far behind (e.g., 30+ seconds of buffered data), close the connection with a backpressure error code and let the client reconnect

### Client-Side Flow Control

- Clients should acknowledge processing capacity -- on WebSocket, periodically send a `{ "type": "Ack", "last_sequence": N }` message
- Consume events asynchronously: do not block the event loop while processing a result -- queue results for async processing
- Adaptive rendering: if results arrive faster than the UI can render, skip interim updates and display only the latest state
- Client-side buffering limits: set a maximum buffer size and drop the oldest unprocessed events when the buffer is full

## Partial Results and Incremental Decoding at the API Level

### How Streaming Transcription Appears Word-by-Word

- The client receives a series of interim results, each containing a progressively longer transcript as more audio is processed
- Example sequence: interim "hello" -> interim "hello world" -> interim "hello world how" -> final "Hello world, how are you?"
- The final result includes post-processing (capitalization, punctuation) that interim results lack -- clients should visually distinguish interim from final text
- Sequence numbering: each result includes a sequence number so the client can detect gaps from dropped messages

### Revision and Replacement Semantics

- Streaming ASR models may revise earlier tokens as more audio context arrives -- the "look-ahead" effect
- Revision protocol: each interim result includes a character offset or word index indicating where the revision starts -- the client replaces text from that point forward
- Providers like Deepgram offer a `stability` parameter that controls how aggressively interim results are emitted vs held for accuracy
- Client-side complexity: handling revisions requires the client to maintain a mutable transcript buffer, not just append

### LLM Token Streaming

- LLM streaming emits one token at a time -- each SSE event carries a small delta (`{ "delta": { "content": " world" } }`)
- Token boundaries do not align with word boundaries -- a token might be a partial word, a space, or punctuation
- The client accumulates deltas into a complete response -- simpler than ASR revisions because LLM tokens are append-only, never revised
- End-of-stream: the final event carries `finish_reason` (stop, length, tool_calls) indicating why generation ended

## Common Pitfalls

- **Building WebSocket APIs when SSE would suffice**: if the client only receives data (text generation, non-interactive transcription), SSE is simpler and more compatible with proxies and CDNs
- **No heartbeat/keepalive**: long-lived connections without keepalive will be killed by intermediate proxies -- clients experience unexplained disconnections
- **Missing reconnection strategy**: every streaming API must document how clients should reconnect and resume after a drop -- "just reconnect" without session resumption loses in-progress results
- **No backpressure handling**: assuming all clients consume at production speed -- mobile clients on slow networks will cause server-side buffer growth
- **Inconsistent message schemas across event types**: every message on the stream should share a common envelope with a type discriminator -- ad hoc schemas per event type break client parsers
- **No sequence numbers on events**: without sequence numbers, clients cannot detect gaps, order messages correctly, or resume after reconnection
- **Treating interim and final results identically**: clients that persist interim results will store inaccurate, unfinished transcriptions -- the API must clearly distinguish result stability

## Summary

- SSE (OpenAI pattern) is simplest for server-to-client streaming -- structured event types (`response.created`, `response.output_text.delta`, `response.completed`) provide clean lifecycle semantics
- WebSocket (Deepgram/AssemblyAI pattern) is essential for bidirectional audio streaming -- binary audio frames from client, JSON result messages from server, with `is_final` distinguishing interim from final results
- gRPC (Google pattern) provides typed bidirectional streaming with built-in flow control -- best for server-to-server communication with protobuf toolchains
- Design logical message schemas independently of transport -- the same `TranscriptionResult`, `Error`, and `SessionEnd` types can be serialized to JSON (SSE/WebSocket) or protobuf (gRPC)
- Connection lifecycle management requires keepalive (30-second intervals), documented reconnection strategies, session resumption via session IDs, and graceful termination protocols
- Backpressure is unavoidable -- monitor send buffer depth, drop interim results for slow clients, and disconnect clients that fall too far behind
- Interim results give real-time feedback but may be revised; final results are stable and safe to persist -- the API must make this distinction explicit with `is_final` or typed event names

## References

*To be populated during chapter authoring. Initial sources:*

1. OpenAI (2025). "API Reference -- Chat Completions Streaming." platform.openai.com/docs/api-reference/chat/create
2. OpenAI (2025). "Responses API Streaming Events." platform.openai.com/docs/api-reference/responses/streaming
3. Deepgram (2025). "Streaming API Reference -- WebSocket Message Types." developers.deepgram.com
4. AssemblyAI (2025). "Real-Time Streaming API -- Message Types." assemblyai.com/docs/speech-to-text/streaming
5. Google Cloud (2025). "Speech-to-Text Streaming Recognition." cloud.google.com/speech-to-text/docs/streaming-recognize
6. Mozilla (2025). "Server-Sent Events -- Web APIs." developer.mozilla.org/en-US/docs/Web/API/Server-sent_events
7. gRPC (2025). "Bidirectional Streaming RPC." grpc.io/docs/what-is-grpc/core-concepts

---

**Next: [Chapter 9: API Versioning & Developer Experience](./09-api-versioning-dx.md)**
