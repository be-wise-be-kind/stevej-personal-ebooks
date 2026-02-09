# Chapter 4: Streaming Audio Architecture

<!-- DIAGRAM: ch04-opener.html - Chapter 4 Opener -->

\newpage

## Overview

- Streaming audio inference is among the most demanding real-time workloads: continuous data arrival, tight latency budgets, codec-specific requirements, and bidirectional communication
- This chapter covers the end-to-end architecture from microphone capture to inference response, including the audio fundamentals every serving engineer must understand
- Reference architectures from production providers (Deepgram, AssemblyAI, Google, Amazon, OpenAI) illustrate the design space and trade-offs

## End-to-End Architecture

### The Full Request Path

- Client captures audio from microphone or file, encodes into the chosen codec (PCM, Opus, FLAC)
- Transport layer delivers audio chunks to the inference server over a persistent connection (WebSocket, gRPC, WebRTC)
- Server receives chunks, buffers as needed, feeds into the inference pipeline (VAD -> ASR -> post-processing)
- Inference results (partial transcripts, final transcripts, events) stream back to the client over the same connection
- Client renders results in real-time; partial results appearing word-by-word, final results replacing partials

<!-- DIAGRAM: ch04-e2e-architecture.html - End-to-End Streaming Audio Architecture -->

\newpage

### Stateful Connections

- Unlike stateless HTTP request/response, streaming audio requires a persistent, stateful connection for the duration of the session
- Session state includes: audio buffer, decoder context, partial transcript accumulator, VAD state, KV cache for the model
- Connection lifecycle: open -> configure (sample rate, encoding, language) -> stream audio -> receive results -> close
- Graceful shutdown: clients send an end-of-stream signal; the server flushes remaining audio through the pipeline and returns final results
- Failure handling: reconnection must restore session state or clearly indicate that context was lost

### Backpressure and Flow Control

- Audio arrives at a constant rate (e.g., 16,000 samples/second at 16kHz), but inference processing time varies
- If inference falls behind, audio chunks queue up; unbounded queues lead to memory exhaustion and increasing latency
- Backpressure strategies: drop oldest chunks (acceptable for live captioning), slow the client (not possible for real-time microphone), increase batch size
- WebSocket lacks built-in flow control; application-level signaling is necessary to manage overload
- gRPC provides flow control via HTTP/2 stream-level windowing; a built-in advantage for high-throughput audio

## Audio Fundamentals for Serving Engineers

### Sample Rates

- 8kHz: telephone-quality audio, legacy telephony integrations (G.711); minimum viable for speech recognition
- 16kHz: the recommended standard for ASR; captures the full frequency range of human speech with manageable bandwidth
- 24kHz: used by OpenAI Realtime API for higher-fidelity speech-to-speech; captures more detail for TTS output
- 44.1kHz/48kHz: music and broadcast quality; overkill for speech recognition, wastes bandwidth and compute
- Practical guidance: default to 16kHz for ASR workloads; use 24kHz only when TTS output quality demands it

### Bit Depth and Channels

- 16-bit signed integer (PCM16): the standard for speech; 96dB dynamic range, sufficient for all voice applications
- 32-bit float: used internally by some models but rarely needed on the wire; adds bandwidth cost with no perceptual benefit for speech
- Mono vs stereo: speech recognition almost always uses mono; stereo doubles bandwidth with no benefit for single-speaker ASR
- Multi-channel: relevant for speaker diarization or spatial audio; requires channel-aware pipeline design

### Codecs

- **PCM (uncompressed)**: raw audio samples, no compression; simplest to process, highest bandwidth (256 kbps at 16kHz/16-bit mono)
- **Opus**: modern lossy codec preferred by OpenAI; excellent quality at low bitrates (16-64 kbps), built-in packet loss concealment, sub-5ms codec latency
- **FLAC**: lossless compression; ~50% size reduction over PCM with zero quality loss, higher CPU cost to decode
- **G.711 (mu-law/A-law)**: legacy telephony codec; 64 kbps at 8kHz, required for PSTN/SIP integrations
- Codec selection impacts: bandwidth, latency (encode/decode time), audio quality, provider compatibility

### Bandwidth Planning

- Raw PCM at 16kHz/16-bit mono: 256 kbps (32 KB/s); the baseline calculation
- Opus at 16 kbps: ~94% bandwidth reduction over PCM; critical for mobile and bandwidth-constrained clients
- Per-session bandwidth multiplied by concurrent sessions determines your network infrastructure requirements
- Don't forget the return path: TTS responses or audio playback add bandwidth in the server-to-client direction

## Chunk Size Selection

### The Latency vs Accuracy Trade-off

- Smaller chunks (50-100ms): lower latency but less audio context per inference pass; may reduce recognition accuracy
- Larger chunks (200-500ms): better accuracy from more context but higher latency before any result is returned
- 100ms chunks: recommended by Deepgram for optimal balance; provides rapid partial results without significant accuracy loss
- 200-250ms chunks: used by providers optimizing for accuracy on longer utterances

<!-- DIAGRAM: ch04-chunk-size-tradeoff.html - Chunk Size: Latency vs Accuracy Trade-off -->

\newpage

### Chunk Alignment Considerations

- Audio samples must align to frame boundaries; a 100ms chunk at 16kHz is exactly 1,600 samples (3,200 bytes at 16-bit)
- Opus operates on fixed frame sizes (2.5, 5, 10, 20, 40, 60ms); chunks must be multiples of the Opus frame size
- Misaligned chunks cause decoder errors or require padding/buffering; a common source of subtle bugs
- Implement chunk validation at the server: reject or re-align chunks that don't match the configured frame size

### Adaptive Chunking

- Fixed chunk size is simplest but not always optimal; silence periods don't need the same granularity as active speech
- Adaptive approaches: larger chunks during silence, smaller during speech; reduces processing overhead without sacrificing latency during active speech
- VAD-driven chunking: use Voice Activity Detection to determine when to send audio for inference vs when to buffer
- Trade-off: adaptive chunking adds complexity and introduces edge cases around speech onset detection

## Voice Activity Detection (VAD)

### Why VAD Matters

- Without VAD, the inference pipeline processes silence, background noise, and music; wasting GPU compute
- VAD segments the audio stream into speech and non-speech regions, sending only speech to the expensive inference model
- Reduces inference cost proportionally to the silence ratio; in many call center scenarios, silence is 40-60% of the audio
- Also drives endpoint detection: identifying when a speaker has finished their utterance to trigger final results

### VAD Approaches

- **Energy-based**: simple threshold on audio amplitude; fast but easily fooled by background noise
- **Model-based (Silero VAD)**: lightweight neural network trained on speech detection; robust, <1ms per chunk, widely adopted
- **WebRTC VAD**: built into the WebRTC stack; suitable for browser-based applications, moderate accuracy
- **Provider-integrated**: Deepgram, AssemblyAI include VAD in their pipeline; no separate implementation needed

### Endpointing and Utterance Segmentation

- Endpointing: detecting that a speaker has stopped talking; typically 300-1000ms of silence after speech
- Too aggressive (short silence threshold): cuts off speakers mid-thought, splitting utterances incorrectly
- Too conservative (long silence threshold): adds unnecessary latency before final results are returned
- Configurable endpointing: most providers expose endpoint sensitivity as a parameter (e.g., Deepgram's `endpointing` parameter in ms)
- Interim results: return partial transcripts during speech, final transcript after endpoint detection

## Buffering Strategies

### When to Buffer

- Network jitter: audio chunks arrive at irregular intervals despite being generated at a constant rate; a jitter buffer smooths playback
- Inference variability: GPU inference time varies per chunk; buffer incoming audio to avoid starving the model during slower passes
- Cross-chunk context: some models benefit from overlapping audio windows; buffer the previous chunk's tail to prepend to the current chunk

### Buffer Management

- Ring buffer: fixed-size circular buffer that overwrites oldest data when full; suitable for real-time where old audio is expendable
- Dynamic buffer: grows and shrinks based on network conditions; more complex but avoids both underrun and excessive memory use
- Buffer size calculation: jitter buffer = max expected jitter (typically 50-200ms); inference buffer = max inference time variance
- Monitor buffer occupancy: consistently full buffers indicate the pipeline is falling behind; consistently empty indicates over-provisioning

### Dropping vs Interpolating

- When the pipeline is overloaded, you must choose: drop audio chunks (lossy) or interpolate/skip (degraded accuracy)
- Drop strategy: discard oldest unprocessed chunks to keep latency bounded; acceptable for live captioning where real-time matters more than completeness
- Skip strategy: process every Nth chunk to maintain real-time pace; reduces accuracy proportionally
- Never silently drop audio without logging: monitor drop rate as a key health metric and alert when it exceeds thresholds

## Reference Architectures

### Deepgram

- Protocol: WebSocket with binary audio frames (no base64 encoding overhead)
- Models: Nova-3 (latest, highest accuracy), Nova-2 (production stable)
- Latency: sub-200ms end-to-end for streaming recognition
- Audio: supports PCM, Opus, FLAC, MP3, and others; 8kHz-48kHz sample rates
- Features: interim results, utterance detection, smart formatting, diarization, language detection
- Billing: per-second of audio processed; economical for short utterances
- Distinguishing characteristic: emphasis on developer experience, comprehensive WebSocket API

### AssemblyAI

- Protocol: WebSocket with base64-encoded audio in JSON messages
- Models: Universal-2 (accuracy leader on many benchmarks), Slam-1 (fast, cost-optimized)
- Latency: sub-300ms end-to-end for real-time transcription
- Audio: 16kHz PCM recommended; supports Opus and other formats via preprocessing
- Features: real-time PII redaction (unique differentiator), interim results, speaker diarization
- Billing: per-second of audio processed
- Distinguishing characteristic: built-in PII redaction and the 300ms voice AI threshold as a design principle [Source: AssemblyAI, 2025]

### Google Cloud Speech-to-Text

- Protocol: gRPC bidirectional streaming only; no WebSocket option
- Models: Chirp 3 (latest universal model), plus specialized models for telephony, medical
- Latency: varies by model; Chirp 3 optimized for accuracy over speed
- Audio: 16kHz recommended; 8kHz for telephony; maximum 25KB per gRPC message
- Features: automatic punctuation, speaker diarization, word-level timestamps, multi-language
- Billing: per 15-second block; coarser granularity than per-second billing
- Distinguishing characteristic: only major provider requiring gRPC; best for server-to-server in Google Cloud ecosystem

### Amazon Transcribe

- Protocol: WebSocket or HTTP/2 streaming
- Models: proprietary models with domain-specific customization via Custom Language Models
- Latency: moderate; optimized for throughput and accuracy over ultra-low latency
- Audio: PCM, FLAC, Opus; 8kHz (telephony) and 16kHz (general) sample rates
- Features: custom vocabulary, content redaction, channel identification for multi-party calls
- Billing: per 15-second block; same coarse granularity as Google
- Distinguishing characteristic: deep AWS ecosystem integration, custom vocabulary for domain-specific terms

### OpenAI Realtime API

- Protocol: WebRTC (browser/mobile), WebSocket (server-to-server), SIP (telephony); most protocol options of any provider
- Models: GPT-4o Realtime; multimodal, supporting speech-to-speech without intermediate text
- Audio: PCM 24kHz/16-bit mono, Opus; base64-encoded over WebSocket, raw binary over WebRTC
- Features: function calling, conversation context, voice selection, interrupt handling
- Billing: per-token (input and output audio tokens); different pricing model than per-second
- Distinguishing characteristic: speech-to-speech without ASR+TTS pipeline; the model natively understands and generates audio

<!-- DIAGRAM: ch04-provider-comparison.html - Provider Comparison Matrix -->

\newpage

### Choosing a Provider vs Building In-House

- Build in-house when: you need custom models, have unique latency requirements, process sensitive audio that cannot leave your infrastructure, or volume justifies the engineering investment
- Use a provider when: time-to-market matters, the provider's accuracy meets your needs, and per-second/per-token pricing is viable at your volume
- Hybrid approach: use providers for general transcription, build custom pipelines for domain-specific or compliance-sensitive workloads
- Migration path: start with a provider to validate the product, build in-house once traffic volume and requirements justify it

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

- Streaming audio inference follows a clear path: client capture -> codec encoding -> transport -> server buffering -> VAD -> inference -> results streaming -> client rendering
- Audio fundamentals matter: 16kHz/16-bit mono PCM is the sweet spot for ASR; Opus for bandwidth-constrained paths; 24kHz for speech-to-speech
- Chunk size is a latency-accuracy trade-off: 100ms chunks recommended for streaming ASR, with VAD to avoid processing silence
- Voice Activity Detection reduces inference cost by 40-60% in typical scenarios and drives endpoint detection for utterance segmentation
- Buffering strategies (jitter buffer, inference buffer, ring buffer) smooth out variability in network and inference timing
- Five major providers offer distinct trade-offs: Deepgram (speed + DX), AssemblyAI (accuracy + PII redaction), Google (gRPC + ecosystem), Amazon (AWS integration + custom vocab), OpenAI (speech-to-speech + multimodal)
- Billing models vary significantly: per-second (Deepgram, AssemblyAI), per-15-second-block (Google, Amazon), per-token (OpenAI); architecture decisions impact unit economics
- Build vs buy depends on volume, compliance requirements, model customization needs, and time-to-market constraints

## References

*To be populated during chapter authoring. Initial sources:*

1. AssemblyAI (2026). "Top APIs and Models for Real-Time Speech Recognition."
2. Deepgram (2026). "Best Speech-to-Text APIs: Comparing Deepgram, AssemblyAI, Google, AWS, and OpenAI."
3. OpenAI (2025). "Realtime API Documentation; Audio Formats and Protocols."
4. Google Cloud (2025). "Speech-to-Text Streaming Recognition; gRPC API Reference."
5. Amazon Web Services (2025). "Amazon Transcribe Streaming Transcription."
6. AssemblyAI (2025). "The 300ms Rule: Why Latency Makes or Breaks Voice AI."

---

**Next: [Chapter 5: Protocol Selection for Audio](./05-protocol-selection.md)**
