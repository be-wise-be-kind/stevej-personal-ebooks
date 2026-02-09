# Chapter 9: Security for Audio ML APIs

![Chapter 9 Opener](../assets/ch09-opener.html)

\newpage

## Overview

- Security for ML inference APIs inherits all the challenges of traditional API security and adds streaming-specific, GPU-aware, and audio-specific concerns
- Audio data is uniquely sensitive -- it contains voice biometrics, background conversations, and emotional states alongside any explicit content
- This chapter covers auth for persistent connections, API key lifecycle, rate limiting for expensive compute, and PII handling in transcripts

## Authentication for Streaming Connections

### The Streaming Auth Challenge

- Traditional request/response auth (bearer tokens per request) does not map cleanly to long-lived streaming connections
- A WebSocket or gRPC stream may last minutes to hours -- re-authenticating every message is wasteful and latency-adding
- The core tension: authenticate once at connection time vs. continuous validation for long-lived sessions
- Revocation problem: if a token is revoked mid-stream, when does the connection terminate?

> **From Book 1:** For a deep dive on auth fundamentals (JWT structure, OAuth2 flows, API key patterns), see "Before the 3 AM Alert" Appendix A.

### WebSocket Authentication Patterns

- **Token in query parameter**: pass JWT or session token as `?token=xxx` during the WebSocket upgrade handshake
  - Simple to implement but tokens appear in server logs and URL histories
- **Token in first message**: establish the WebSocket connection, then send an auth message before any data frames
  - Keeps tokens out of URLs but requires server-side connection state management before auth completes
- **Upgrade header authentication**: pass the token in the `Authorization` header during the HTTP upgrade request
  - Cleanest approach but not supported by all WebSocket client libraries (browser limitations)
- Comparison of trade-offs: security, client compatibility, implementation complexity

### gRPC Authentication Patterns

- **Per-RPC metadata headers**: attach auth tokens as gRPC metadata on each call -- works for unary and streaming
- **Channel credentials**: TLS + token credentials set once at channel creation, applied to all RPCs on that channel
- **Call credentials**: per-stream tokens passed as metadata, allowing different auth per stream on the same channel
- gRPC interceptors for centralized auth validation -- intercept before the handler sees the request
- Bidirectional streaming auth: initial metadata carries the token, server validates before processing any messages

### Session Tokens for Long-Lived Connections

- Short-lived JWTs (5-15 min) with a refresh mechanism for streams that outlast the token lifetime
- Token refresh without disconnection: client sends a new token on the existing stream, server validates and extends the session
- Session binding: tie the token to the specific connection/stream ID to prevent token replay on other streams
- Graceful degradation: if a refresh fails, allow the current operation to complete before terminating the connection

![Streaming Auth Flow](../assets/ch09-streaming-auth-flow.html)

\newpage

## API Key Management

### Key Generation and Structure

- API keys as the primary auth mechanism for server-to-server ML inference access
- Key format considerations: opaque random strings (e.g., `sk_live_...`) vs. structured tokens with embedded metadata
- Prefix conventions for identifying key type and environment: `sk_live_`, `sk_test_`, `pk_`
- Entropy requirements: minimum 256 bits of randomness to prevent brute-force attacks

### Key Scoping

- **Per-model scoping**: restrict a key to specific models (e.g., only STT, not TTS) -- limits blast radius of compromise
- **Per-feature scoping**: restrict to specific capabilities (e.g., transcription but not speaker diarization)
- **Per-environment scoping**: separate keys for development, staging, production -- prevent test traffic from hitting production models
- Rate limit tiers attached to key scope -- premium keys get higher GPU allocation
- Scoping granularity trade-offs: fine-grained scoping increases security but adds management overhead

### Key Rotation

- Rotation cadence: 90 days is common, shorter for high-sensitivity deployments
- Overlap period: new key active alongside old key for a grace period (24-72 hours) to avoid breaking active integrations
- Automated rotation: integrate with secrets managers (Vault, AWS Secrets Manager, GCP Secret Manager)
- Rotation without downtime: dual-key acceptance during the transition window

### Key Revocation

- Immediate revocation for compromised keys -- propagation time matters (cache invalidation across API gateways)
- Revocation propagation: push-based (webhook to gateways) vs. pull-based (short TTL cache, eventual consistency)
- Audit trail: log who revoked, when, and why -- compliance requirement for SOC 2
- Cascading effects: revoking a key mid-stream should gracefully terminate active connections, not silently drop audio

![API Key Lifecycle](../assets/ch09-api-key-lifecycle.html)

\newpage

## OAuth 2.0 Flows for ML API Access

### Client Credentials Flow (Server-to-Server)

- The primary OAuth flow for ML inference APIs -- no human in the loop
- Client authenticates with client ID + secret, receives an access token scoped to specific inference capabilities
- Token lifetime considerations: short-lived tokens (15-60 min) with refresh, or longer-lived for batch processing
- Audience and scope claims: encode model access, rate limit tier, and feature permissions in the token

### Authorization Code Flow (User-Facing Applications)

- When end users interact directly with ML inference (e.g., a voice assistant app)
- User authenticates via identity provider, app receives a token to call inference APIs on the user's behalf
- Per-user rate limiting and usage tracking -- attribute inference costs to individual users
- PKCE (Proof Key for Code Exchange) as mandatory for public clients (mobile apps, SPAs)

### Token Design for ML APIs

- Custom claims for ML-specific context: allowed models, max audio duration, allowed codecs, usage quota remaining
- Token introspection vs. self-contained JWTs: introspection adds a network call but enables instant revocation
- Token size considerations for streaming: large JWTs in every gRPC metadata header add per-message overhead

> **From Book 1:** For a deep dive on auth performance patterns and token validation strategies, see "Before the 3 AM Alert" Chapter 11.

## Rate Limiting and Abuse Prevention

### GPU-Aware Rate Limiting

- Traditional rate limiting (requests per second) is insufficient for ML APIs -- a 30-second audio file costs 100x more GPU than a 1-second file
- GPU-aware rate limiting: measure cost in compute units (GPU-seconds) rather than request count
- Example: a rate limit of 600 GPU-seconds per minute allows 10 requests of 60s audio or 600 requests of 1s audio
- Dynamic rate limiting: adjust limits based on current GPU utilization -- tighten when cluster is hot, relax when idle

### Per-Key and Per-Tier Limits

- Tiered rate limits: free tier (low concurrency, short audio), standard tier, enterprise tier (high concurrency, unlimited duration)
- Concurrent stream limits: cap the number of simultaneous streaming connections per key -- prevents a single customer from monopolizing GPU resources
- Per-model limits: more expensive models (large whisper variants) get lower default rate limits than lightweight models

### Burst Handling

- Token bucket algorithm for burst tolerance: allow short bursts above the steady-state rate
- Queue-based burst absorption: accept requests into a queue with a max depth, process as GPU capacity becomes available
- Backpressure signaling: return `429 Too Many Requests` with `Retry-After` header indicating when capacity will be available
- Graceful degradation: offer reduced-quality inference (smaller model, lower accuracy) when at capacity rather than hard rejecting

### Abuse Detection

- Pattern detection: unusually long audio streams, repeated identical requests (replay attacks), geographic anomalies
- Audio content abuse: using inference APIs to process prohibited content -- not the same problem as text abuse detection
- Cost-based anomaly detection: flag keys whose GPU consumption spikes unexpectedly relative to historical patterns

## Securing Audio Data

### Encryption in Transit

- TLS 1.3 as the mandatory baseline for all audio transmission -- WebSocket (wss://), gRPC (with TLS), HTTPS
- Certificate management for streaming endpoints: certificate rotation without dropping active WebSocket/gRPC connections
- Mutual TLS (mTLS) for high-security deployments: both client and server authenticate -- common in healthcare and financial services
- End-to-end encryption considerations: encrypting audio from client device through to model inference, with decryption only at the inference node

### Encryption at Rest

- AES-256 encryption for any stored audio data -- at the storage layer (disk encryption) and at the application layer (envelope encryption)
- Key management: customer-managed encryption keys (CMEK) vs. provider-managed keys
- Ephemeral processing: decrypt audio into memory for inference, never write plaintext to disk
- Encryption for model artifacts: the models themselves may be proprietary and require at-rest encryption

### Why Audio Data Is Uniquely Sensitive

- Voice biometrics: a person's voice is a biometric identifier -- audio recordings can be used for speaker identification or voice cloning
- Background conversations: audio captures not just the intended speaker but everyone nearby -- incidental collection of third-party data
- Emotional states: tone, pitch, speaking rate reveal emotional information that the speaker may not intend to share
- Combined sensitivity: a single audio file can contain PII (names, addresses spoken aloud), biometrics (voiceprint), health information (coughing, slurred speech), and emotional state simultaneously

## PII in Transcripts

### The PII Challenge for Speech AI

- Transcription converts audio PII into text PII -- names, addresses, phone numbers, SSNs, credit card numbers spoken aloud become searchable text
- Dual PII surface: the original audio contains biometric PII, and the transcript contains textual PII -- both must be protected
- Real-time vs. post-processing redaction: redacting in the streaming pipeline vs. redacting after full transcription is complete
- False positives and false negatives: over-redaction loses useful data, under-redaction leaks PII -- tuning the threshold is domain-specific

### Detection and Redaction Patterns

- NER-based detection: use named entity recognition models to identify PII entities in transcript text
- Regex-based detection: pattern matching for structured PII (SSNs, phone numbers, credit card numbers, email addresses)
- Hybrid approach: NER for unstructured PII (names, addresses) + regex for structured PII -- most production systems use both
- Redaction strategies: replace with entity type (`[PHONE_NUMBER]`), replace with asterisks (`***-***-1234`), or remove entirely
- Audio-level redaction: beep or silence over the audio segment corresponding to detected PII -- requires word-level timestamps

### Provider Comparison

- **Deepgram**: zero-retention defaults (audio not stored after processing), configurable redaction with sub-300ms pipeline latency, PII redaction as a built-in feature
- **AssemblyAI**: HIPAA-compliant with Business Associate Agreement (BAA), automatic PHI redaction for healthcare, PII policies configurable per request
- **Voicegain**: 95%+ PII detection accuracy, redaction in both audio and text outputs, on-premise deployment option for maximum data control
- Feature comparison: what each provider redacts by default, what is configurable, and what requires custom implementation

![PII Redaction Pipeline](../assets/ch09-pii-redaction-pipeline.html)

\newpage

## Audio-Specific Privacy Risks

### Biometric Voiceprints

- A voice recording is a biometric identifier under GDPR, BIPA (Illinois), and emerging state privacy laws
- Speaker identification and voice cloning risks: audio data can be used to impersonate the speaker
- Voiceprint storage: if your system performs speaker diarization or verification, the derived voiceprint data requires biometric-level protection
- Consent requirements: explicit opt-in consent for biometric data collection is legally required in many jurisdictions

### Background Conversations and Incidental Collection

- Audio recordings in shared spaces capture conversations of non-consenting third parties
- Legal implications: wiretapping laws (one-party vs. two-party consent states/countries) apply to audio capture
- Technical mitigation: voice activity detection (VAD) to isolate the target speaker, audio zone filtering
- Data minimization: process the minimum audio necessary -- trim silence, discard non-target speaker segments when possible

### Emotional and Health State Inference

- Emotion detection from voice is an active area of AI -- tone, pitch, and cadence reveal stress, anger, sadness
- Health indicators: speech patterns can indicate cognitive decline, intoxication, respiratory conditions
- EU AI Act implications: emotion recognition in workplace and educational contexts is restricted (effective Aug 2026)
- Ethical considerations: even if technically possible, inferring emotional or health states without explicit consent raises significant ethical concerns

## Common Pitfalls

- **Treating audio like text for security purposes**: audio is biometric data with stricter legal requirements than text -- the same security controls that suffice for text APIs are insufficient for audio
- **Auth at connection time only with no re-validation**: long-lived streams can outlast token expiration -- implement periodic re-validation or token refresh
- **Rate limiting by request count instead of compute cost**: a single 60-second audio inference request consumes orders of magnitude more GPU than a 1-second request -- rate limit by GPU-seconds
- **Storing audio "just in case"**: every stored audio file is a liability -- default to zero-retention and require explicit justification for any storage
- **Ignoring incidental audio capture**: background conversations in audio recordings create privacy obligations for people who never consented to data collection
- **Treating PII redaction as an afterthought**: bolt-on redaction is fragile -- build it into the inference pipeline from day one

## Summary

- Streaming auth requires different patterns than request/response: token-in-first-message for WebSockets, metadata headers for gRPC, with session tokens and refresh for long-lived connections
- API key lifecycle (generation, scoping, rotation, revocation) is critical infrastructure -- scope keys per-model and per-feature to limit blast radius
- GPU-aware rate limiting measures cost in compute units, not request count -- a 60-second audio file is not equivalent to a 1-second file
- Audio data is uniquely sensitive: it contains biometrics, background conversations, emotional states, and spoken PII simultaneously
- PII exists in both the audio (biometric) and the transcript (textual) -- both surfaces require detection and redaction
- Provider approaches vary: Deepgram (zero-retention), AssemblyAI (HIPAA/BAA), Voicegain (95%+ accuracy, audio+text redaction)
- Default to zero-retention, encrypt everything in transit (TLS 1.3) and at rest (AES-256), and build PII redaction into the pipeline from the start

## References

*To be populated during chapter authoring. Initial sources:*

1. Deepgram (2025). "Standard Compliance Speech-to-Text: HIPAA, SOC 2, GDPR."
2. Deepgram (2025). Security best practices documentation.
3. AssemblyAI (2025). "HIPAA Compliance and PII Redaction for Speech AI."
4. Voicegain (2025). "PII Redaction in Audio and Text Transcription."
5. OWASP (2025). "API Security Top 10."
6. IETF RFC 6455 (2011). "The WebSocket Protocol" -- security considerations.
7. gRPC (2025). "Authentication Guide -- gRPC."

---

**Next: [Chapter 10: Compliance & Data Governance](./10-compliance-data-governance.md)**
