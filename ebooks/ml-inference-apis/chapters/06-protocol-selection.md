# Chapter 6: Protocol Selection for Audio

<!-- DIAGRAM: ch06-opener.html - Chapter 5 Opener -->

\newpage

## Overview

- **Ground the reader**: briefly explain what "protocol" means in this context. A protocol is the set of rules that govern how a client and server communicate: how a connection is established, how data is framed and sent, and how each side knows when the other is done. HTTP is the protocol most backend engineers know; streaming audio needs different protocols because HTTP's request-response model does not support continuous bidirectional data flow efficiently.
- Protocol selection for audio streaming is not a general-purpose decision; it is constrained by client capabilities, provider requirements, latency targets, and browser support
- This chapter focuses on the audio-specific application of protocols, not their general mechanics; Book 1 covers the fundamentals
- The production reality: WebSocket dominates, gRPC is Google's ecosystem, WebRTC is for browser audio, and WebTransport/MoQ are future technologies not yet production-ready

> **From Book 1:** For a deep dive on WebSocket, SSE, gRPC, and WebTransport fundamentals (handshakes, framing, multiplexing, flow control), see "Before the 3 AM Alert" Chapter 5: Network and Connection.

## Bridging the Gap

This chapter draws on concepts from both ML infrastructure and API engineering. If you have not encountered these before, this section provides the context you will need.

**From the ML side**, this chapter explains why protocol choice matters for inference APIs. Protocols define how data moves between client and server: the rules for establishing connections, sending data, and signaling completion. Load balancers distribute incoming traffic across multiple server instances and must understand the protocol to route correctly; a load balancer that does not support WebSocket will silently break persistent audio connections. Proxies (reverse proxies, API gateways) sit between clients and servers and may interfere with long-lived connections by enforcing idle timeouts. Flow control is a mechanism where the receiver tells the sender to slow down when it cannot keep up, which is critical when GPU inference is the bottleneck and audio chunks arrive faster than the model can process them.

**From the API side**, this chapter explains why audio streaming cannot use standard HTTP request-response. Audio is a continuous, unbounded stream with no single "request" to send and no single "response" to wait for. The system must send and receive data simultaneously (bidirectional communication) because the client is still recording while the server is already returning transcription results. Binary framing means sending raw audio bytes directly rather than text-encoding them, which matters because base64-encoding audio for JSON transmission adds 33% bandwidth overhead and measurable CPU cost on both client and server.

## WebSocket for Audio Streaming

### Why WebSocket Dominates

- Persistent, full-duplex connection over a single TCP socket; the natural fit for bidirectional audio streaming
- Universal client support: every browser, every mobile platform, every server-side language has WebSocket libraries
- Deepgram, AssemblyAI, Amazon Transcribe, and OpenAI (server-to-server) all use WebSocket as their primary protocol
- Simpler operational model than gRPC: standard HTTP/1.1 upgrade, works through most proxies and load balancers without special configuration

### Binary Framing for Audio

- WebSocket natively supports binary frames; send raw audio bytes without any encoding overhead
- Base64 encoding (used by some providers like AssemblyAI) adds 33% bandwidth overhead; 256 kbps of PCM becomes 341 kbps
- Binary framing at 16kHz/16-bit PCM: 3,200 bytes per 100ms chunk; small enough for a single WebSocket frame
- Always prefer binary framing when the provider supports it; the bandwidth savings compound across thousands of concurrent sessions

<!-- DIAGRAM: ch06-binary-vs-base64.html - Binary vs Base64 Bandwidth Comparison -->

\newpage

### Connection Lifecycle for Audio

- Handshake: HTTP upgrade with authentication (API key in header or query parameter) and session configuration
- Configuration phase: client sends a configuration message specifying sample rate, encoding, language, features (interim results, diarization, etc.)
- Streaming phase: client sends binary audio frames; server sends JSON result messages (partial transcripts, final transcripts, metadata)
- Termination: client sends a close-stream message; server flushes remaining audio, sends final results, then closes the connection
- Keep-alive: send periodic ping/pong frames to prevent proxy/load balancer timeouts (typical timeout: 60-120 seconds idle)

### WebSocket Limitations for Audio

- No built-in flow control: if the server falls behind, audio frames queue up in the send buffer with no protocol-level backpressure signal
- Head-of-line blocking: TCP guarantees in-order delivery; a single lost packet stalls all subsequent frames until retransmitted
- No multiplexing: one WebSocket connection = one audio stream; multi-stream scenarios require multiple connections or application-level multiplexing
- Proxy traversal: while most proxies support WebSocket upgrades, some corporate firewalls still block or interfere with long-lived connections

## gRPC Bidirectional Streaming

### Google Cloud Speech's Exclusive Protocol

- Google Cloud Speech-to-Text uses gRPC bidirectional streaming exclusively; no WebSocket option available
- Client opens a bidirectional stream: sends `StreamingRecognizeRequest` messages (config + audio), receives `StreamingRecognizeResponse` messages
- Built on HTTP/2: multiplexed streams, header compression (HPACK), stream-level flow control
- Protobuf serialization: efficient binary encoding for both audio data and metadata; no JSON parsing overhead

### Audio-Specific gRPC Considerations

- 25KB per-message limit for Google Cloud Speech; at 16kHz/16-bit PCM, this is ~781ms of audio per message
- For larger chunks, you must fragment audio across multiple gRPC messages; adds application-level complexity
- Protobuf wrapping of audio bytes adds minimal overhead (~2-5 bytes per message for the field tag and length)
- Deadline propagation: gRPC deadlines flow through the call chain; useful for enforcing end-to-end latency budgets

### gRPC Advantages for Server-to-Server

- HTTP/2 multiplexing: multiple audio streams over a single TCP connection; reduces connection management overhead
- Built-in flow control: HTTP/2 stream-level and connection-level flow control prevents sender from overwhelming the receiver
- Streaming semantics are first-class: the protobuf service definition explicitly declares bidirectional streaming; client code generation handles the complexity
- Load balancing: gRPC supports client-side load balancing with service discovery; important for distributing audio streams across inference servers

### gRPC Limitations for Audio

- Browser support requires gRPC-Web proxy (Envoy); adds an extra hop and limits streaming to server-streaming only (no client-streaming in the browser)
- Operational overhead: HTTP/2 is more complex to debug, monitor, and proxy than HTTP/1.1 WebSocket
- Not supported by most audio API providers; if you're integrating with Deepgram, AssemblyAI, or Amazon, you need WebSocket regardless
- Learning curve: protobuf schema management and gRPC toolchain add complexity for teams unfamiliar with the ecosystem

## WebRTC for Browser Audio

### When WebRTC Is the Right Choice

- OpenAI Realtime API uses WebRTC as the primary protocol for browser and mobile clients; purpose-built for real-time media
- Built-in audio capture and playback: `getUserMedia()` API handles microphone access, echo cancellation, noise suppression, and automatic gain control
- NAT traversal via ICE (STUN/TURN): works through firewalls and NATs without requiring the client to expose a public IP
- Designed for sub-100ms latency: UDP transport, jitter buffers, and codec negotiation are built into the protocol

### WebRTC Audio Features

- Opus codec negotiation: WebRTC peers negotiate codec parameters during session setup; no manual codec configuration
- Adaptive bitrate: automatically adjusts audio quality based on network conditions; degrades gracefully on poor connections
- Built-in jitter buffer: absorbs network timing variability and produces smooth audio playback; no application-level buffering needed
- Echo cancellation and noise suppression: processed by the browser before audio reaches your application; cleaner input to the inference model

### WebRTC Limitations

- Overkill for server-to-server: WebRTC's NAT traversal, codec negotiation, and media pipeline add unnecessary complexity when both endpoints are in the same datacenter
- TURN server infrastructure: when direct peer connections fail (30-40% of corporate networks), TURN relays are required; adds operational cost and latency
- Complexity: SDP offer/answer exchange, ICE candidate gathering, DTLS-SRTP key exchange; significantly more complex than opening a WebSocket
- Not suitable for non-real-time workloads: the overhead of WebRTC's media pipeline is wasted on batch or near-real-time processing

### When to Use WebRTC vs WebSocket

- WebRTC: browser/mobile clients needing live audio capture with built-in echo cancellation, NAT traversal, and ultra-low latency
- WebSocket: server-to-server, pre-recorded audio streaming, or any scenario where you control both endpoints
- OpenAI's approach: WebRTC for browser clients, WebSocket for server-to-server; the right protocol for each context
- If you need both: implement a gateway that accepts WebRTC from browsers and forwards audio over WebSocket to your inference backend

## WebTransport: The Future Protocol

### What WebTransport Offers

- Built on QUIC (HTTP/3): multiplexed streams without head-of-line blocking; each audio stream is independent
- Unreliable datagrams: QUIC datagrams allow sending audio without guaranteed delivery; mimics UDP semantics over QUIC
- For audio: lost audio frames can be skipped rather than retransmitted; reduces latency spikes caused by TCP retransmission
- Lower connection setup time: QUIC's 0-RTT or 1-RTT handshake vs TCP's 3-way handshake + TLS; faster session establishment

### Current State (2026)

- Browser support: Chrome and Edge; no Safari or Firefox support as of early 2026
- No major speech API provider has adopted WebTransport as a production protocol
- Server-side support: limited to a few frameworks (Go, Rust); not yet mainstream in Python/Node.js ecosystems
- The gap: WebTransport is technically superior for audio streaming, but ecosystem maturity is insufficient for production use

### When WebTransport Will Matter

- Once Safari adopts WebTransport (or a critical mass of browsers support it), the browser-support blocker disappears
- Unreliable datagrams are a game-changer for live audio: lossy delivery with bounded latency is exactly what real-time audio needs
- WebTransport may eventually replace WebSocket for audio streaming; but that transition is years away, not months
- Plan for it: design your audio pipeline with a transport abstraction layer so you can adopt WebTransport when the ecosystem is ready

## Media over QUIC (MoQ)

### What MoQ Promises

- IETF draft protocol for low-latency media delivery over QUIC; targeting 300ms RTT plus encode/decode time
- Designed for both live streaming and real-time communication; sits between WebRTC (ultra-low latency) and HLS/DASH (high latency)
- Relay architecture: media passes through relays rather than direct peer-to-peer, enabling scalable distribution
- Publish/subscribe model: producers publish named tracks, consumers subscribe; natural fit for multi-party audio scenarios

### Current State (2026)

- NOT production-ready: still in IETF draft stage with active specification changes
- Red5 has announced planned support; one of the first media server vendors to commit
- No speech API provider has adopted or announced MoQ support
- Limited reference implementations available for experimentation

### MoQ and WebRTC Will Coexist

- MoQ is not a WebRTC replacement; they serve different use cases
- WebRTC: direct peer-to-peer communication, browser media capture, interactive conversations
- MoQ: scalable media distribution, one-to-many and many-to-many scenarios with relay infrastructure
- For inference APIs: MoQ's relay model could enable scalable audio distribution to multiple inference backends; but this is speculative, not current practice

## The Decision Framework

### Client Constraints

- Browser client with live microphone -> WebRTC (built-in media capture, NAT traversal) or WebSocket (simpler, wider provider support)
- Server-to-server -> WebSocket (simplest, widest support) or gRPC (if using Google ecosystem)
- Mobile app -> WebSocket (universal support) or WebRTC (if built-in audio pipeline is needed)
- Telephony/SIP integration -> SIP gateway to WebSocket or gRPC backend

### Latency Targets

- Sub-100ms (interactive voice, speech-to-speech) -> WebRTC for browser, WebSocket with optimized backend for server-to-server
- Sub-300ms (real-time transcription, the voice AI threshold) -> WebSocket or gRPC; both achieve this with proper implementation
- Seconds-tolerant (near-real-time captioning, async) -> Any protocol including HTTP chunked transfer

### Provider Compatibility

- Deepgram -> WebSocket
- AssemblyAI -> WebSocket
- Google Cloud Speech -> gRPC only
- Amazon Transcribe -> WebSocket or HTTP/2
- OpenAI Realtime -> WebRTC (browser), WebSocket (server), SIP (telephony)
- Building your own -> WebSocket as the default; add gRPC if your clients are server-side and your team has gRPC experience

<!-- DIAGRAM: ch06-protocol-decision-tree.html - Protocol Decision Tree for Audio -->

\newpage

### The 300ms Rule

- AssemblyAI specifically identifies 300ms as the threshold for voice AI; beyond this, the interaction feels laggy and users disengage [Source: AssemblyAI, 2025]
- Protocol choice contributes to this budget: connection setup, frame encoding, network transit, server-side processing, response serialization
- WebSocket and gRPC both comfortably achieve sub-300ms when deployed in the same region as the client
- WebRTC adds NAT traversal and DTLS setup time but compensates with lower per-frame latency once established
- The protocol itself is rarely the bottleneck; inference time and network distance dominate the latency budget

## Protocol Comparison Summary

<!-- DIAGRAM: ch06-protocol-comparison-table.html - Protocol Comparison Table -->

\newpage

### WebSocket

- Strengths: universal support, simple implementation, binary framing, works through proxies
- Weaknesses: no flow control, head-of-line blocking, no multiplexing
- Production status: dominant; used by 4 of 5 major speech API providers
- Recommendation: the default choice unless you have a specific reason to use something else

### gRPC

- Strengths: flow control, multiplexing, Protobuf efficiency, deadline propagation
- Weaknesses: browser support requires proxy, operational complexity, limited provider adoption
- Production status: mature; used exclusively by Google Cloud Speech
- Recommendation: use when integrating with Google Cloud or in server-to-server architectures where your team already uses gRPC

### WebRTC

- Strengths: built-in media pipeline, NAT traversal, adaptive bitrate, echo cancellation
- Weaknesses: complexity, TURN infrastructure, overkill for server-to-server
- Production status: mature for its use case; used by OpenAI Realtime for browser clients
- Recommendation: use for browser/mobile clients that need live audio capture with built-in audio processing

### WebTransport

- Strengths: QUIC-based, no head-of-line blocking, unreliable datagrams, fast setup
- Weaknesses: no Safari support, no provider adoption, limited server-side ecosystem
- Production status: experimental; not recommended for production audio streaming in 2026
- Recommendation: monitor and prototype, but do not depend on it for production workloads

### Media over QUIC (MoQ)

- Strengths: scalable relay architecture, publish/subscribe model, designed for low-latency media
- Weaknesses: IETF draft, no production implementations, no provider support
- Production status: not production-ready
- Recommendation: track the specification progress; relevant for future multi-party audio architectures

## Common Pitfalls

- **Choosing WebRTC for server-to-server audio**: WebRTC's media pipeline, NAT traversal, and codec negotiation add complexity with zero benefit when both endpoints are servers in the same network
- **Using base64 over WebSocket when binary frames are available**: 33% bandwidth overhead multiplied across thousands of concurrent sessions is significant; always check if the provider supports binary framing
- **Betting on WebTransport or MoQ for near-term production**: neither protocol has sufficient browser support or provider adoption for production use in 2026; plan for them, don't depend on them
- **Ignoring the 25KB gRPC message limit**: Google Cloud Speech enforces a 25KB per-message limit that truncates audio; fragment long chunks across messages or reduce chunk size
- **Assuming protocol choice determines latency**: the protocol adds 1-5ms to total latency; inference time (10-100ms) and network distance (10-100ms) dominate the budget
- **Not implementing reconnection logic**: persistent connections (WebSocket, gRPC streams, WebRTC) will fail; clients must reconnect and ideally resume session state without losing audio context
- **Overlooking proxy and firewall behavior**: some corporate networks block WebSocket upgrades, throttle long-lived connections, or interfere with gRPC; test against realistic network conditions

## Summary

- WebSocket is the dominant protocol for audio streaming in production; used by Deepgram, AssemblyAI, Amazon, and OpenAI (server-to-server)
- Binary framing over WebSocket saves 33% bandwidth compared to base64 encoding; always prefer binary when supported
- gRPC bidirectional streaming is Google Cloud Speech's exclusive protocol; best for server-to-server in the Google ecosystem, with built-in flow control and multiplexing
- WebRTC is purpose-built for browser audio with built-in capture, echo cancellation, and NAT traversal; used by OpenAI Realtime for browser/mobile clients
- WebTransport offers compelling advantages (QUIC datagrams, no head-of-line blocking) but lacks Safari support and provider adoption; not production-ready in 2026
- Media over QUIC (MoQ) is an IETF draft targeting scalable low-latency media; years from production relevance for inference APIs
- The decision framework: client constraints (browser vs server) and provider compatibility narrow the choice; WebSocket is the safe default
- The 300ms voice AI threshold is achievable with any mature protocol; inference time and network distance matter more than protocol choice
- Design your audio pipeline with a transport abstraction layer to accommodate future protocol adoption without rewriting the inference stack

## References

*To be populated during chapter authoring. Initial sources:*

1. GetStream (2025). "WebRTC vs WebSocket: Key Differences and When to Use Each."
2. VideoSDK (2025). "What is Replacing WebSockets? Modern Alternatives Compared."
3. Red5 (2025). "MOQ vs WebRTC: Understanding the Differences."
4. WINK (2025). "Media over QUIC: Implementation and Practical Considerations."
5. AssemblyAI (2025). "The 300ms Rule: Why Latency Makes or Breaks Voice AI."
6. OpenAI (2025). "Realtime API Protocol Reference; WebRTC, WebSocket, and SIP."
7. Google Cloud (2025). "Speech-to-Text gRPC Streaming API Reference."

---

**Next: [Chapter 7: Streaming Inference Pipelines](./07-streaming-inference-pipelines.md)**
