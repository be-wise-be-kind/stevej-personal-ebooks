# Chapter 5: Streaming Audio Architecture

![Chapter 5 Opener](../assets/ch05-opener.html)

\newpage

## Overview

The first four chapters of this book addressed infrastructure: which serving framework to choose, how to optimize GPU performance, and how to organize deployments. All of that work assumed a simple request-response model where a client sends data and waits for a result. Streaming audio breaks that assumption entirely. Instead of uploading a complete file and waiting, the client sends audio in small chunks, typically 100 milliseconds at a time, while the recording is still happening, and the server returns results continuously as audio arrives. This is how live captioning, real-time voice assistants, and phone call transcription work.

Streaming audio inference is among the most demanding real-time workloads in production systems. Data arrives at a constant rate dictated by physics: a 16kHz microphone produces 16,000 samples per second regardless of whether the server is ready. The entire pipeline from microphone to displayed transcript must complete within roughly 300 milliseconds to feel responsive [Source: AssemblyAI, 2025]. That 300ms budget is not arbitrary: it is the threshold at which users perceive a voice AI system as conversational rather than laggy, analogous to the 100ms RAIL guideline for interactive web responses [Source: Google, 2024]. Every architectural decision in a streaming audio system (codec selection, chunk size, buffering strategy, protocol choice) is shaped by this constraint.

This chapter covers the end-to-end architecture from microphone capture to inference response. We start with the full request path, then work through audio fundamentals that determine data rates and pipeline design, chunk size selection, voice activity detection, and buffering strategies. We close with reference architectures from five production providers (Deepgram, AssemblyAI, Google Cloud, Amazon, and OpenAI) that illustrate the design space and trade-offs.

## Bridging the Gap

This chapter draws on concepts from both ML infrastructure and API engineering. If you have not encountered these before, this section provides the context you will need.

**From the ML side**, this chapter introduces persistent connections, a networking model that differs from standard HTTP. In a typical HTTP interaction, the client sends a request, the server returns a response, and the connection is done. Streaming audio requires a connection that stays open for seconds to minutes, with data flowing continuously in both directions. WebSocket and gRPC provide this persistent, bidirectional communication. Codecs (Opus, FLAC, PCM) are compression formats for audio data that trade bandwidth for decode cost and quality, and the choice of codec affects the entire pipeline from network transfer to GPU preprocessing. Bandwidth planning matters because audio generates a steady, predictable stream of bytes per second per connection, and the aggregate bandwidth across thousands of concurrent streams is a hard infrastructure constraint.

**From the API side**, this chapter covers audio signal processing fundamentals that determine data rates, memory requirements, and GPU workload. A sample rate (e.g., 16kHz) means 16,000 audio measurements per second. Bit depth (e.g., 16-bit) means each measurement is represented with 16 bits of precision. Together they determine the raw data rate: 16kHz × 16-bit = 256 kbps for mono audio. Voice Activity Detection (VAD) is a lightweight model that detects when someone is actually speaking versus silence or background noise, which saves GPU compute by skipping segments where there is nothing to transcribe.

## End-to-End Architecture

### The Full Request Path

A streaming audio system follows a clear pipeline. The client captures audio from a microphone or file and encodes it into the chosen codec: PCM for simplicity, Opus for bandwidth efficiency, or FLAC for lossless compression. The encoded audio is segmented into chunks, typically 100ms each, and sent over a persistent connection (WebSocket, gRPC, or WebRTC) to the inference server. The server receives chunks into a buffer, decodes the audio if compressed, runs it through voice activity detection to identify speech segments, feeds those segments to the ASR (automatic speech recognition) model for inference, and applies post-processing such as punctuation and formatting. Results stream back over the same connection: partial transcripts appear word-by-word as audio is processed, and final transcripts replace the partials once the speaker finishes an utterance.

The bidirectional nature of this pipeline is what makes streaming fundamentally different from batch processing. Audio flows client-to-server while results flow server-to-client simultaneously over the same connection. Neither side waits for the other to finish. The system must process audio fast enough to keep up with real time while returning results with minimal delay.

![End-to-End Streaming Audio Architecture](../assets/ch05-e2e-architecture.html)

\newpage

### Stateful Connections

Unlike stateless HTTP request-response pairs, streaming audio requires a persistent, stateful connection for the duration of the session. The server maintains several pieces of state across the connection lifetime: the audio buffer holding recently received chunks, the codec decoder context needed to correctly decompress audio frames, the partial transcript accumulator tracking words-in-progress, the VAD state tracking whether the current audio segment contains speech, and the model's KV cache for autoregressive inference.

The connection lifecycle follows a predictable pattern: open the connection, configure parameters (sample rate, encoding, language), stream audio chunks, receive results, and close. Graceful shutdown matters because when the client sends an end-of-stream signal, the server must flush remaining buffered audio through the pipeline and return final results before closing. Without this flush, the last few seconds of speech are lost.

Failure handling is where stateful connections get complex. If the connection drops mid-session, all that accumulated state (decoder context, partial transcript, VAD state) is lost. Reconnection must either restore the session state from a checkpoint or clearly indicate to the client that context was lost and a new session has begun. Most production systems take the simpler approach: accept the state loss, start a new session, and let the client handle the gap in the transcript.

### Backpressure and Flow Control

Audio arrives at a constant rate dictated by the sample rate: 16,000 samples per second at 16kHz, regardless of whether the inference pipeline is keeping up. If inference falls behind, audio chunks queue up in the server's buffer. Unbounded queues lead to two cascading failures: memory exhaustion as the buffer grows without limit, and increasing latency as each chunk waits longer in the queue before being processed.

Backpressure strategies depend on the use case. For live captioning where real-time matters more than completeness, dropping the oldest unprocessed chunks keeps latency bounded at the cost of missing some speech. For recorded audio played back at real-time speed, the client can be slowed down. For live microphone input, slowing the client is not possible because the audio arrives when it arrives, so the only options are dropping chunks or scaling the inference pipeline to keep up.

The protocol choice affects flow control directly. WebSocket lacks built-in flow control mechanisms; if the server is overwhelmed, the application must implement its own signaling to manage overload. gRPC provides flow control via HTTP/2 stream-level windowing, where the receiver can signal the sender to slow down at the protocol level [Source: gRPC, 2025]. This built-in advantage makes gRPC a better fit for high-throughput server-to-server audio streaming, though WebSocket remains dominant for browser-to-server connections. Chapter 6 covers protocol selection in detail.

## Audio Fundamentals for Serving Engineers

### Sample Rates

The sample rate determines how many audio measurements are captured per second, and it directly controls the frequency range of the captured audio (via the Nyquist theorem: maximum captured frequency equals half the sample rate). For speech recognition, the practical choices are:

**8kHz** is telephone-quality audio, the standard for legacy telephony integrations using G.711 codecs. It captures frequencies up to 4kHz, enough for speech intelligibility but not for high-quality recognition. Use 8kHz only when integrating with PSTN or SIP systems that mandate it.

**16kHz** is the recommended standard for ASR workloads. It captures the full frequency range of human speech (up to 8kHz), providing the information the model needs for accurate recognition without wasting bandwidth on frequencies above the speech range. This is the default for Deepgram, AssemblyAI, and Google Cloud Speech-to-Text [Source: Deepgram, 2026; Source: AssemblyAI, 2026; Source: Google Cloud, 2025].

**24kHz** is used by OpenAI's Realtime API for higher-fidelity speech-to-speech applications [Source: OpenAI, 2025]. The extra frequency range above 8kHz captures more detail that matters for TTS (text-to-speech) output quality, where the generated speech needs to sound natural.

**44.1kHz and 48kHz** are music and broadcast standards. For speech recognition, they waste bandwidth and compute: the model discards the high-frequency information during preprocessing anyway.

### Bit Depth and Channels

**16-bit signed integer (PCM16)** is the standard for speech. It provides 96dB of dynamic range, more than sufficient for any voice application, from quiet conversation to shouting in a noisy environment. Every major speech provider uses 16-bit as their default or recommended format.

**32-bit float** is used internally by some models during processing but is rarely needed on the wire. Sending 32-bit audio doubles bandwidth compared to 16-bit with no perceptible benefit for speech recognition.

**Mono audio** is correct for almost all speech recognition workloads. Stereo doubles the data rate with no benefit for single-speaker ASR. The exception is multi-channel recording for speaker diarization, where separate channels allow the pipeline to attribute speech to specific speakers or locations. This requires a channel-aware pipeline design, which adds complexity.

### Codecs

The codec determines how audio is represented on the wire, and the choice cascades through the entire pipeline: bandwidth consumption, encode/decode latency, audio quality, and provider compatibility.

**PCM (uncompressed)** sends raw audio samples with no compression. At 16kHz, 16-bit mono, this produces 256 kbps (32 KB/s). PCM is the simplest to process because there is no decode step and no codec latency, making it the right choice when bandwidth is not a constraint and simplicity matters.

**Opus** is a modern codec designed for interactive audio, preferred by OpenAI and increasingly supported across providers [Source: OpenAI, 2025]. Opus scales from 6 kbit/s narrowband speech to 510 kbit/s fullband stereo, with speech sweet spots at 8-12 kbit/s for narrowband, 16-20 kbit/s for wideband, and 28-40 kbit/s for fullband quality [Source: RFC 6716, 2012]. It includes built-in packet loss concealment and achieves an algorithmic delay as low as 5ms in restricted low-delay mode [Source: RFC 6716, 2012]. Opus operates on fixed frame sizes of 2.5, 5, 10, 20, 40, or 60ms, and chunks must be multiples of these frame sizes.

**FLAC** provides lossless compression, meaning identical audio quality to PCM with reduced file size. FLAC typically reduces audio to 50-70% of its original size [Source: Xiph.Org, 2025], yielding a 30-50% bandwidth saving over PCM at the cost of higher CPU usage for encoding and decoding. Use FLAC when audio quality must be bit-perfect and bandwidth is a secondary concern.

**G.711 (mu-law/A-law)** is the legacy telephony codec, producing 64 kbps at 8kHz [Source: ITU-T, 1988]. It is required for PSTN and SIP integrations and has negligible encode/decode overhead. If you are building a system that interfaces with telephone networks, G.711 support is non-negotiable.

### Bandwidth Planning

Bandwidth planning starts with the raw data rate and works outward. At 16kHz, 16-bit mono PCM, the baseline is 256 kbps (32 KB/s) per stream. Opus at 32 kbps reduces this to roughly 4 KB/s, an 87% reduction that matters significantly when multiplied across thousands of concurrent streams.

Per-session bandwidth multiplied by concurrent sessions determines network infrastructure requirements. A system handling 10,000 concurrent streams at 32 KB/s (PCM) consumes 320 MB/s of inbound bandwidth. The same system using Opus at 4 KB/s per stream consumes 40 MB/s, a constraint that fits comfortably on standard network infrastructure.

Do not forget the return path. If the system also generates TTS responses or streams audio playback to clients, the server-to-client direction adds bandwidth. A full-duplex voice AI system sends and receives audio simultaneously, roughly doubling the per-session bandwidth requirement compared to unidirectional transcription.

## Chunk Size Selection

### The Latency vs Accuracy Trade-off

Chunk size (the amount of audio sent in each network message) is the primary knob for tuning the latency-accuracy trade-off in streaming ASR. Smaller chunks mean the server receives audio sooner and can begin inference sooner, reducing time-to-first-result. Larger chunks give the model more audio context per inference pass, potentially improving recognition accuracy.

At 50ms chunks, the system sends audio 20 times per second. Latency is minimized, but each chunk contains only 800 samples (at 16kHz), providing limited context for the model. At 500ms chunks, the system sends only twice per second. The model gets 8,000 samples of context, but the minimum latency before any result can be returned is 500ms, already exceeding the 300ms budget before network and inference time are even counted.

The recommended default is 100ms chunks. Deepgram's documentation explicitly recommends streaming buffer sizes between 20ms and 250ms, with 100ms as the sweet spot [Source: Deepgram, 2025]. At 16kHz, a 100ms chunk contains exactly 1,600 samples (3,200 bytes at 16-bit), providing enough context for accurate partial results while keeping chunk latency at a fraction of the 300ms budget.

A natural question arises: 100ms is not long enough to contain a complete spoken word, so how does the model recognize speech that spans chunk boundaries? Streaming ASR models do not process each chunk in isolation. Architectures like RNN-Transducer (used by Deepgram and Google) maintain internal encoder state across chunks, so when chunk N arrives, the model carries forward what it learned from chunks 0 through N-1. CTC-based models use a sliding window with overlap, where each inference pass includes the current chunk plus retained context from previous chunks. In both cases, a word like "streaming" that begins in one chunk and ends in the next is recognized because the model's state spans the boundary. The partial-to-final transcript pattern is the user-facing consequence: the model emits its best guess as a partial transcript ("strea..."), then revises it to the complete word ("streaming") once enough audio context has arrived.

![Chunk Size: Latency vs Accuracy Trade-off](../assets/ch05-chunk-size-tradeoff.html)

\newpage

### Chunk Alignment Considerations

Audio samples must align to codec frame boundaries. A 100ms chunk at 16kHz is exactly 1,600 samples, and this divides evenly, causing no issues for PCM. But codecs like Opus operate on fixed frame sizes (2.5, 5, 10, 20, 40, or 60ms), and chunks must be exact multiples of the chosen frame size [Source: RFC 6716, 2012]. A 100ms chunk works with Opus frames of 2.5, 5, 10, 20, or 50ms (50 is not a valid Opus frame size, but 100 divides evenly by 10 and 20). A 150ms chunk would work with 2.5, 5, 10, and 30ms frames but not 20ms, a mismatch that causes decoder errors or requires padding.

Misaligned chunks are a common source of subtle bugs: audio that plays back with clicks at chunk boundaries, decoder state corruption that degrades quality over time, or outright errors that the client never sees because the server silently pads or truncates. Implement chunk validation at the server: verify that incoming chunks match the configured codec frame size and reject or re-align chunks that do not.

### Adaptive Chunking

Fixed chunk sizes work for the common case, but they are not always optimal. During silence or background noise, sending 100ms chunks for inference wastes processing time on audio that contains no speech. During active speech, smaller chunks could provide faster partial results.

Adaptive chunking adjusts chunk size based on audio content: larger chunks during silence (or no chunks at all, if VAD suppresses them), smaller chunks during speech. VAD-driven chunking is the most common implementation, where the VAD model determines when to send audio for inference versus when to buffer quietly. The trade-off is complexity: adaptive chunking introduces edge cases around speech onset detection (the first syllable of a new utterance may be clipped if the system is in "silence mode" with large chunks) and requires careful state management at chunk boundaries.

For most production systems, fixed 100ms chunks with server-side VAD filtering provides the best balance of simplicity and performance. Adaptive chunking is worth the complexity only when processing cost or bandwidth savings justify the engineering investment.

## Voice Activity Detection (VAD)

### Why VAD Matters

Without VAD, the inference pipeline processes every chunk regardless of content: silence, background noise, music between speakers, HVAC hum. This wastes GPU compute on audio that produces no useful transcript and generates garbage output (hallucinated words from noise patterns that superficially resemble speech). In conversational audio, a substantial fraction of the stream contains no speech. Studies of telephony systems show that VAD can save approximately 35% of bandwidth on average across concurrent calls [Source: Cisco, 2025], and speech science research indicates that pauses account for roughly 50% of monologue and up to 60-70% of dialogue [Source: ITU-T P.59, 1993]. For call center audio where hold time and agent lookup pauses are common, the savings can be even higher.

VAD also drives endpoint detection: identifying when a speaker has finished their utterance so that the system can return a final transcript. Without endpointing, the system never knows when to commit a partial transcript to a final result.

### VAD Approaches

**Energy-based VAD** applies a simple amplitude threshold: if the audio signal exceeds a decibel level, it is classified as speech. This is fast and requires no model inference, but it is easily fooled by background noise (a door closing, keyboard typing) and misses quiet speech.

**Model-based VAD** uses a lightweight neural network trained specifically on speech detection. Silero VAD is the most widely adopted open-source option: a 2MB model that processes a single audio chunk (30ms or more) in less than 1ms on a single CPU thread [Source: Silero VAD, 2025]. The ONNX variant achieves 189 microseconds per chunk on commodity hardware [Source: Silero VAD, 2025]. This sub-millisecond overhead is negligible relative to the 100-200ms ASR inference time, making model-based VAD effectively free in the pipeline budget.

**WebRTC VAD** is built into the WebRTC stack and suitable for browser-based applications. It provides moderate accuracy without requiring a separate model deployment, but it is less robust than Silero VAD for production speech pipelines.

**Provider-integrated VAD** is included in the pipelines of Deepgram, AssemblyAI, and other providers. If you are using a hosted transcription service, VAD is handled for you with no separate implementation needed.

### Endpointing and Utterance Segmentation

Endpointing detects when a speaker has stopped talking: the transition from speech to silence that signals the end of an utterance. The system waits for a configurable duration of silence after the last detected speech, then commits the accumulated partial transcript as a final result.

Getting the silence threshold right is a balancing act. Too aggressive (short threshold, e.g., 100ms) and the system cuts speakers off mid-thought, splitting sentences into fragments. Too conservative (long threshold, e.g., 2000ms) and users wait unnecessarily for final results after they stop speaking. Most providers expose endpointing as a configurable parameter: Deepgram's `endpointing` parameter accepts a value in milliseconds, with a default of 10ms and practical values typically ranging from 200ms to 1000ms depending on the application [Source: Deepgram, 2025].

Interim results bridge the gap: partial transcripts stream to the client during speech, showing words as they are recognized. Final transcripts replace the partials after endpoint detection, potentially with corrections that benefit from the complete utterance context. This two-tier result pattern (fast partials for responsiveness, delayed finals for accuracy) is universal across streaming ASR providers.

## Buffering Strategies

### When to Buffer

Three sources of variability in streaming audio pipelines require buffering to smooth out.

**Network jitter** causes audio chunks to arrive at irregular intervals despite being generated at a constant rate. A jitter buffer accumulates a small reserve of chunks so that the pipeline always has audio to process even when a chunk arrives late. Without jitter buffering, late-arriving chunks cause gaps in the audio stream that degrade recognition quality.

**Inference variability** means GPU inference time fluctuates per chunk based on audio content, batch size, and GPU contention. Buffering incoming audio prevents the model from starving during slower inference passes. If a chunk takes 150ms to process instead of the typical 100ms, the buffer provides the next chunk immediately rather than waiting for the network.

**Cross-chunk context** is needed by some models that benefit from overlapping audio windows. The buffer retains the previous chunk's tail to prepend to the current chunk, providing the model with context that spans chunk boundaries. This overlap improves recognition of words that fall on chunk boundaries.

### Buffer Management

**Ring buffers** are fixed-size circular buffers that overwrite the oldest data when full. They are ideal for real-time streaming where old audio is expendable: if the pipeline falls behind, the oldest unprocessed audio is silently dropped to keep the buffer bounded. Ring buffers are simple, allocation-free after initialization, and predictable in memory usage.

**Dynamic buffers** grow and shrink based on network conditions and processing speed. They avoid both underrun (buffer empty, pipeline starved) and excessive memory use, but they add complexity: the system must decide when to grow, when to shrink, and what maximum size to allow before triggering backpressure.

Buffer size calculation depends on the source of variability. For jitter buffering, the buffer should accommodate the maximum expected network jitter. Adaptive jitter buffers in WebRTC implementations typically range from 20-40ms for stable networks up to 100-200ms for unstable connections [Source: WebRTC, 2025]. For inference buffering, size the buffer to absorb the maximum variance in inference time: if P99 inference time is 200ms and P50 is 100ms, a 100ms buffer absorbs all but the most extreme fluctuations.

Monitor buffer occupancy as a health metric. Consistently full buffers indicate the pipeline is falling behind real time, a signal to scale up inference capacity. Consistently empty buffers indicate over-provisioning or that buffering is unnecessary for the current load.

### Dropping vs Interpolating

When the pipeline is truly overloaded and buffering cannot absorb the gap, the system must choose between lossy strategies.

**Dropping** discards the oldest unprocessed chunks to keep latency bounded. This is the right strategy for live captioning where real-time display matters more than completeness, since missing a few words is preferable to showing a transcript that lags 10 seconds behind the speaker.

**Skip processing** runs inference on every Nth chunk to maintain real-time pace, reducing accuracy proportionally. This maintains continuous coverage of the audio stream but with lower fidelity, suitable for scenarios where approximate transcription is acceptable during load spikes.

Never silently drop audio without logging. The drop rate is a key health metric: alert when it exceeds thresholds (e.g., dropping more than 1% of chunks sustained over a minute), and use it as a scaling signal to add inference capacity.

## Reference Architectures

### Deepgram

Deepgram's architecture is built around developer experience and raw speed. Their WebSocket API accepts binary audio frames directly with no base64 encoding overhead and no JSON wrapping for audio data [Source: Deepgram, 2026]. The Nova-3 model (their latest, highest-accuracy option) and Nova-2 (production-stable) both support streaming with sub-300ms end-to-end latency [Source: Deepgram, 2026]. Audio format support is broad: PCM, Opus, FLAC, MP3, and others across sample rates from 8kHz to 48kHz. Deepgram recommends 100ms streaming buffer sizes and provides detailed documentation on measuring and optimizing streaming latency [Source: Deepgram, 2025]. Billing is per-second of audio processed with no rounding, so 61 seconds of audio is charged as exactly 61 seconds [Source: Deepgram, 2026]. Features include interim results, utterance detection, smart formatting, diarization, and language detection.

### AssemblyAI

AssemblyAI's distinguishing feature is real-time PII (personally identifiable information) redaction: the ability to detect and mask sensitive information in the transcript as it is generated, without a separate post-processing step [Source: AssemblyAI, 2026]. Their WebSocket API uses base64-encoded audio in JSON messages (rather than binary frames), which adds approximately 33% bandwidth overhead but simplifies integration for clients that cannot send binary WebSocket frames. The Universal-2 model leads on many accuracy benchmarks, while the Slam-1 model is optimized for speed and cost. AssemblyAI explicitly designs around the 300ms voice AI threshold as a core latency target [Source: AssemblyAI, 2025], delivering sub-300ms end-to-end streaming latency. Audio format: 16kHz PCM recommended, with Opus support via preprocessing. Billing is per-second of audio processed.

### Google Cloud Speech-to-Text

Google Cloud is the only major provider that requires gRPC for streaming. There is no WebSocket endpoint [Source: Google Cloud, 2025]. Streaming uses gRPC bidirectional streaming, where the client sends `StreamingRecognizeRequest` messages and receives `StreamingRecognizeResponse` messages over the same RPC. This choice reflects Google's server-to-server orientation: gRPC's built-in flow control, strong typing via Protocol Buffers, and native integration with Google Cloud infrastructure make it the natural fit for their ecosystem. The Chirp 3 model is their latest universal model, optimized for accuracy over speed, with specialized models available for telephony and medical domains. Audio constraints include 16kHz recommended (8kHz for telephony) and a 25KB limit per gRPC message for streaming audio content [Source: Google Cloud, 2025]. Billing uses per-second granularity [Source: Google Cloud, 2025].

### Amazon Transcribe

Amazon Transcribe offers the most flexibility in transport protocols, supporting both WebSocket and HTTP/2 streaming [Source: AWS, 2025]. Its architecture is optimized for throughput and accuracy rather than ultra-low latency, making it a strong fit for use cases where completeness matters more than speed, including compliance recording, meeting transcription, and post-call analytics. The key differentiator is deep AWS ecosystem integration: custom language models for domain-specific vocabulary, content redaction, and channel identification for multi-party calls. Audio format support includes PCM, FLAC, and Opus at 8kHz (telephony) and 16kHz (general) sample rates. Billing uses per-second granularity [Source: AWS, 2025].

### OpenAI Realtime API

OpenAI's Realtime API takes a fundamentally different approach: instead of separating speech recognition and synthesis into ASR and TTS stages, the GPT-4o Realtime model natively understands and generates audio [Source: OpenAI, 2025]. This speech-to-speech architecture eliminates the ASR-to-text-to-TTS pipeline entirely. The API supports three protocols (WebRTC for browser and mobile clients, WebSocket for server-to-server, and SIP for telephony), providing the broadest protocol coverage of any provider. Audio format is PCM 24kHz/16-bit mono or Opus; WebSocket uses base64-encoded audio while WebRTC uses raw binary. Billing is per-token (both input and output audio tokens), a fundamentally different pricing model from per-second billing. Features include function calling, conversation context, voice selection, and interrupt handling.

![Provider Comparison Matrix](../assets/ch05-provider-comparison.html)

\newpage

### Choosing a Provider vs Building In-House

Build in-house when you need custom models trained on domain-specific data, have latency requirements that no provider meets, process sensitive audio that cannot leave your infrastructure for regulatory reasons, or when your audio volume is high enough that the engineering investment pays for itself compared to per-second API pricing.

Use a provider when time-to-market matters, when the provider's accuracy meets your requirements, and when per-second or per-token pricing is viable at your volume. The build-vs-buy calculus shifts as traffic grows: per-second pricing that is economical at 1,000 hours per month may be prohibitive at 100,000 hours per month, while the fixed cost of an in-house pipeline becomes relatively cheaper at scale. A common migration path is to start with a provider to validate the product and user experience, then build in-house once traffic volume and requirements justify the investment.

> **From Book 1:** For a deep dive on connection management patterns for persistent connections, see "Before the 3 AM Alert" Chapter 5: Network and Connection.

## Common Pitfalls

- **Sending base64-encoded audio over WebSocket when binary frames are supported**: base64 adds 33% bandwidth overhead; use binary framing whenever the protocol and provider support it
- **Ignoring codec latency**: encoding and decoding audio adds milliseconds per chunk; at 100ms chunks, a 10ms codec round-trip is 10% of your latency budget
- **Using 48kHz audio for speech recognition**: wastes bandwidth and compute; 16kHz captures the full speech frequency range
- **Not implementing VAD**: processing silence and background noise through the inference pipeline wastes GPU compute and generates garbage transcripts
- **Hardcoding chunk sizes without considering codec frame alignment**: leads to decoder errors or silent audio corruption at chunk boundaries
- **Treating audio streaming as stateless**: each connection has session state (decoder context, partial results, VAD state); losing this state mid-session is a user-visible failure
- **Ignoring backpressure**: unbounded audio queues during inference slowdowns lead to memory exhaustion and cascading latency

## Summary

- Streaming audio inference follows a clear path: client capture, codec encoding, transport, server buffering, VAD, inference, results streaming, and client rendering, all within a 300ms latency budget for voice AI applications
- Audio fundamentals matter: 16kHz/16-bit mono PCM is the default for ASR; Opus for bandwidth-constrained paths; 24kHz for speech-to-speech applications
- Chunk size is a latency-accuracy trade-off: 100ms chunks are recommended for streaming ASR, providing rapid partial results without significant accuracy loss
- Voice Activity Detection reduces inference cost by filtering silence and non-speech audio, and drives endpoint detection for utterance segmentation
- Buffering strategies (jitter buffer, inference buffer, ring buffer) smooth out variability in network and inference timing; monitor buffer occupancy as a health metric
- Five major providers offer distinct trade-offs: Deepgram (speed and developer experience), AssemblyAI (accuracy and real-time PII redaction), Google (gRPC-native and GCP ecosystem), Amazon (AWS integration and custom vocabulary), OpenAI (speech-to-speech without ASR/TTS split)
- Billing models vary significantly: per-second (Deepgram, AssemblyAI), per-second (Google, Amazon), per-token (OpenAI); architecture decisions impact unit economics
- Build vs buy depends on volume, compliance requirements, model customization needs, and time-to-market constraints

## What's Next

With streaming audio architecture established, the next chapter dives into the protocol layer that carries this audio. Chapter 6 covers protocol selection for audio, including WebSocket, gRPC, WebRTC, and emerging options like WebTransport, comparing their trade-offs for different streaming scenarios.

## References

1. **AssemblyAI** (2025). "The 300ms Rule: Why Latency Makes or Breaks Voice AI." https://www.assemblyai.com/blog/the-300ms-rule
2. **Google** (2024). "RAIL Performance Model." https://web.dev/rail
3. **RFC 6716** (2012). Valin, J.-M., Vos, K., & Terriberry, T. "Definition of the Opus Audio Codec." Internet Engineering Task Force. https://www.rfc-editor.org/rfc/rfc6716
4. **Xiph.Org Foundation** (2025). "FLAC: Free Lossless Audio Codec." https://xiph.org/flac/
5. **ITU-T** (1988). "G.711: Pulse Code Modulation (PCM) of Voice Frequencies." International Telecommunication Union.
6. **Silero VAD** (2025). "Silero VAD: Pre-trained Enterprise-Grade Voice Activity Detector." GitHub. https://github.com/snakers4/silero-vad
7. **Cisco** (2025). "Voice Over IP: Per Call Bandwidth Consumption." https://www.cisco.com/c/en/us/support/docs/voice/voice-quality/7934-bwidth-consume.html
8. **ITU-T P.59** (1993). "Artificial Conversational Speech." International Telecommunication Union.
9. **Deepgram** (2026). "Best Speech-to-Text APIs 2026." https://deepgram.com/learn/best-speech-to-text-apis
10. **Deepgram** (2025). "Measuring Streaming Latency." https://developers.deepgram.com/docs/measuring-streaming-latency
11. **Deepgram** (2025). "Endpointing." https://developers.deepgram.com/docs/endpointing
12. **AssemblyAI** (2026). "Top APIs and Models for Real-Time Speech Recognition 2026." https://www.assemblyai.com/blog/
13. **Google Cloud** (2025). "Speech-to-Text Streaming Recognition; gRPC API Reference." https://cloud.google.com/speech-to-text/docs
14. **Amazon Web Services** (2025). "Amazon Transcribe Streaming Transcription." https://docs.aws.amazon.com/transcribe/
15. **OpenAI** (2025). "Realtime API Documentation; Audio Formats and Protocols." https://platform.openai.com/docs/guides/realtime
16. **gRPC** (2025). "Flow Control." https://grpc.io/docs/guides/flow-control/
17. **WebRTC** (2025). "WebRTC Jitter Buffer and Audio Processing." https://webrtchacks.com/how-webrtcs-neteq-jitter-buffer-provides-smooth-audio/

---

**Next: [Chapter 6: Protocol Selection for Audio](./06-protocol-selection.md)**
