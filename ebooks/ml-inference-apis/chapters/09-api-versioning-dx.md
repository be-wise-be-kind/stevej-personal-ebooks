# Chapter 9: API Versioning & Developer Experience

<!-- DIAGRAM: ch09-opener.html - Chapter 9 Opener -->

\newpage

## Overview

- **Ground the reader**: explain the versioning challenge specific to ML APIs. Most web APIs have one thing that changes: the API contract (endpoints, request/response formats). ML APIs have two things that change independently: the API contract and the underlying model. A team might ship a new, more accurate speech recognition model without changing the API, or restructure the API without changing the model. Clients need to know which model version produced their results (for reproducibility) and which API version they are calling (for compatibility). This "two-axis" problem is what makes ML API versioning harder than traditional API versioning.
- How to version ML inference APIs when both the API contract and the underlying model evolve independently; the two-axis versioning problem
- SDK design, documentation patterns, and developer onboarding strategies that determine whether developers adopt your API or a competitor's
- Multimodality as a design consideration for 2025+ APIs; how to extend single-modality APIs to handle text, audio, and images without breaking existing clients

## API Versioning Strategies

### URL Path Versioning

- The most common and most explicit strategy: `/v1/audio:transcribe`, `/v2/audio:transcribe`
- Deepgram, AssemblyAI, OpenAI, and most ML API providers use URL path versioning for their public APIs
- Advantages: version is visible in every request, easy to route at the load balancer/gateway, simple for clients to understand
- Disadvantage: incrementing the major version is a heavy operation; requires migrating all clients, maintaining two versions in parallel

### Header Versioning

- Azure OpenAI's pattern: `api-version: 2025-03-31` header with date-stamped versions
- Allows the same URL to serve multiple API versions based on the header value; useful for APIs that evolve frequently with backward-compatible changes
- The rolling date model: each date stamp represents a snapshot of the API surface; Azure documents which features are available in each version
- Advantage: avoids URL proliferation; disadvantage: version is hidden in headers, harder to discover and debug

### Content Negotiation and Query Parameter

- Content negotiation (`Accept: application/vnd.api+json;version=2`): rarely used for ML APIs; too complex for the benefit
- Query parameter (`?api_version=2025-03-31`): simpler than headers, visible in URLs, but pollutes the query string
- Recommendation: URL path versioning for public ML APIs (clarity and discoverability), header versioning for APIs with frequent backward-compatible evolution

<!-- DIAGRAM: ch09-versioning-strategies.html - API Versioning Strategy Comparison -->

\newpage

## The Two-Axis Versioning Problem

### Model Versions and API Versions Are Independent

- The API contract defines input/output schemas; the model version determines the quality and accuracy of the output
- A model upgrade may improve accuracy without changing the API shape; the same `POST /v1/audio:transcribe` returns better results with a newer model
- An API change may add new request fields or restructure the response without changing the model; the same Whisper model served through a different schema
- These two axes evolve on different timelines: models may update weekly, API versions change yearly

### Model Version Selection Patterns

- Allow clients to pin a specific model version: `model=whisper-large-v3`; guarantees reproducible results
- Provide floating aliases for convenience: `model=whisper-latest` or `model=nova-3`; always points to the current best version
- OpenAI's approach: model parameter selects the model family and version (`gpt-4o`, `gpt-4o-2024-11-20`) with snapshot versions for pinning
- Google's approach: model field in the request with explicit version identifiers (`chirp_2`, `long`) and a `latest` alias
- Azure's approach: model deployment names that can be updated to point to newer model versions independently of the API version

### When Model Changes Require API Changes

- Non-breaking model change: improved accuracy, lower latency, new language support; deploy under existing API version
- Breaking model change: new output fields (e.g., adding word-level timestamps where only full text existed), changed confidence score range (0-1 to 0-100), removed output fields
- Breaking model changes require a new API version; the API contract must be stable across model updates within the same version
- Versioned model output schemas: document which output schema applies to each API version, even when the same model serves both

<!-- DIAGRAM: ch09-two-axis-versioning.html - The Two-Axis Versioning Problem: Model Version vs API Version -->

\newpage

## Deprecation and Sunset Policies

### Announcing Deprecation

- Announce deprecation at least 6 months before removal; communicate via API response headers (`Sunset: Sat, 01 Mar 2027 00:00:00 GMT`, `Deprecation: true`)
- In-band deprecation warnings: include a `Warning` header or a `deprecation` field in the response body on every request to a deprecated endpoint
- Out-of-band notifications: email, changelog, status page announcements, SDK warning logs
- Developer dashboard: show deprecation status and migration timelines prominently in the API management console

### Model Version Deprecation

- When a model version is deprecated, return a warning header but continue serving until the sunset date
- Model deprecation timeline: typically 3-6 months from deprecation announcement to removal; shorter than API version deprecation because model updates are more frequent
- The Azure OpenAI model: rolling `api-version` dates with a documented retirement schedule; each version has a known end-of-life date published in advance
- Automatic upgrade path: when a pinned model version is deprecated, document which newer version is the recommended replacement and what behavioral differences to expect

### Migration Support

- Migration guides: provide clear documentation mapping old API patterns to new ones; request/response schema diffs, changed behavior, new defaults
- Automated migration tools for SDK users: version-specific SDK packages or migration scripts that update client code
- Dual-serving period: serve both old and new API versions in parallel during the migration window; do not force-migrate before the sunset date
- Usage monitoring: track how many clients are still using deprecated versions and proactively reach out to high-volume users

## Breaking vs Non-Breaking Changes for ML APIs

### Non-Breaking Changes (Safe Within an API Version)

- Adding a new optional request parameter with a default value
- Adding a new field to the response body (clients should ignore unknown fields)
- Improving model accuracy without changing the output schema
- Adding support for a new audio codec or language
- Increasing rate limits or quota allocations

### Breaking Changes (Require a New API Version)

- Removing or renaming a response field
- Changing the type of an existing field (e.g., string to integer)
- Changing the semantics of an existing field (e.g., confidence from 0-1 to percentage 0-100)
- Requiring a previously optional parameter
- Changing the default behavior of an existing parameter
- Removing support for an audio codec or model version without deprecation

### The Gray Area: Accuracy Changes

- A model update that changes transcription output for the same audio is technically a behavioral change; but not a schema change
- Most providers treat accuracy improvements as non-breaking; clients should expect outputs to evolve
- For clients that require reproducibility (legal transcription, medical records), model version pinning is essential
- Document the expectation: "outputs may vary across model versions; pin a model version for deterministic results"

## SDK Design and Client Libraries

### Language Coverage Strategy

- Official SDKs in the top 3-5 languages used by your customers; at minimum Python, JavaScript/TypeScript, and one systems language (Go, Rust, Java)
- Prioritize by customer base: if your API serves primarily data scientists, Python is the most critical; if web developers, JavaScript/TypeScript
- Community-maintained SDKs for secondary languages; provide OpenAPI specs to enable auto-generation
- Versioned SDK releases that track API versions; `sdk-python v1.x` for API v1, `sdk-python v2.x` for API v2

### Auto-Generated vs Hand-Crafted SDKs

- Auto-generated from OpenAPI/protobuf: consistent, complete, low maintenance cost; but often produce awkward ergonomics (deep nesting, verbose method names)
- Hand-crafted: excellent ergonomics, idiomatic to each language; but expensive to maintain across multiple languages and API versions
- Hybrid approach: auto-generate the core HTTP/gRPC layer, hand-craft high-level convenience methods on top (streaming helpers, file upload wrappers, retry logic)
- OpenAI's approach: hand-crafted SDKs with streaming iterators, automatic retries, and typed response objects; sets the ergonomic standard for ML API SDKs

### Streaming Helpers in SDKs

- Streaming APIs are the hardest to integrate; SDKs must provide high-level abstractions that hide connection management
- Async iterators: `async for event in client.transcribe_stream(audio_source)`; the SDK handles connection, keepalive, and reconnection internally
- Callback handlers: `client.on("transcript", handler)`; event-driven pattern familiar to JavaScript developers
- Error handling in streaming SDKs: translate transport-level errors (disconnection, timeout) into language-idiomatic exceptions with actionable messages

## Documentation Patterns

### API Reference

- Interactive API reference (Swagger UI, Redoc, or custom) with runnable examples; essential for inference APIs where developers need to test with real data
- Every endpoint documented with: description, request schema (with examples), response schema (with examples), error codes, rate limits
- Streaming endpoint documentation requires special treatment: show the event sequence, message schemas for each event type, and connection lifecycle
- Code samples in every supported language for every endpoint; inference APIs are evaluated by developers during trials, and poor docs lose deals

### Quickstart Guides

- "Transcribe a file in 5 minutes"; the fastest path from zero to a working API call
- "Set up real-time streaming"; step-by-step for the more complex streaming integration
- "Batch process audio files"; long-running operation pattern with polling and webhook options
- Each quickstart should be copy-paste runnable; include API key setup, dependency installation, and a complete working example

### Playground and Sandbox Environments

- Interactive API explorer: let developers paste audio or text and see inference results immediately in the browser; no SDK setup required
- Sandbox environment with test API keys: free-tier access for evaluation and debugging without billing commitment
- Recorded demo mode: pre-loaded examples that work without an API key; reduces friction for the earliest exploration phase
- Playground doubles as documentation: developers understand the API's capabilities by experimenting, not just reading

<!-- DIAGRAM: ch09-developer-journey.html - Developer Journey: Discovery to Production Integration -->

\newpage

## Multimodality as a Design Consideration

### The 2025+ API Landscape

- Modern inference APIs must handle multiple modalities: text, audio, image, video; often in the same request
- OpenAI's approach: unified input format where content can be text, image URL, or audio; the model handles multimodal input natively
- Google's approach: Vertex AI Gemini API accepts interleaved text, image, audio, and video in a single prompt
- Design implication: API schemas should use a content-type-aware input format rather than modality-specific endpoints

### Multimodal Input/Output Design

- Input union types: a `content` field that accepts `{ "type": "text", "text": "..." }` or `{ "type": "audio", "data": "base64...", "format": "wav" }` or `{ "type": "image", "url": "..." }`
- Output union types: responses should similarly support mixed modalities; a speech-to-text-to-speech pipeline returns both text and audio
- Format negotiation: clients specify desired output modalities; `output_modalities: ["text", "audio"]` allows the server to generate both
- Streaming multimodal: interleaved text and audio events on the same stream; OpenAI Realtime API demonstrates this pattern

### Backward-Compatible Multimodal Extensions

- Start with single-modality endpoints (e.g., `/v1/audio:transcribe`) and extend to multimodal by wrapping input in a content array
- Existing clients that send raw audio continue to work; the API treats a bare audio payload as `[{ "type": "audio", "data": ... }]`
- New multimodal-aware clients send the structured content format; the API handles both transparently
- This gradual evolution avoids a breaking API version change when adding multimodal support

## Developer Onboarding

### Time-to-First-API-Call as a Metric

- The single most important developer experience metric: how long from landing on the docs page to a successful API response
- Industry benchmarks: the best ML API providers achieve under 5 minutes for a simple inference call
- Measure and optimize: track the onboarding funnel (docs visit -> signup -> API key created -> first request -> first successful response) and identify drop-off points
- Every friction point in the onboarding flow costs potential customers; simplify signup, streamline API key provisioning, minimize required configuration

### API Key Provisioning

- Instant API key generation: developers should get a working key within seconds of signup; no manual approval, no email verification for sandbox access
- Key scoping: support project-level and environment-level keys (development, staging, production) from the start
- Key rotation: provide programmatic key rotation without service interruption; essential for security-conscious enterprise customers
- Forward reference: API key security, rotation policies, and access control are covered in depth in Chapter 10

### Free Tier Design

- Generous enough for meaningful evaluation: developers need to test with realistic data, not just "hello world"; 60 minutes of free transcription is more useful than 60 seconds
- No credit card required for the free tier; requiring payment information before the developer has validated the API's quality creates unnecessary friction
- Clear upgrade path: show usage against free tier limits and make upgrading to a paid tier a single click
- Rate limits on free tier should be restrictive enough to prevent abuse but permissive enough for genuine evaluation (e.g., 5 concurrent streams, 100 requests/minute)

> **From Book 1:** For a deep dive on rate limiting algorithms and their implementation at the API gateway layer, see "Before the 3 AM Alert" Chapter 10.

## Common Pitfalls

- **Conflating model version with API version**: changing a model should not require clients to update their integration; keep the API contract stable across model versions
- **No deprecation policy**: removing or changing endpoints without notice breaks production integrations and erodes trust
- **Ignoring SDK ergonomics**: a well-designed HTTP API with a poorly designed SDK will frustrate developers more than a mediocre API with a great SDK
- **Documentation without runnable examples**: static documentation that cannot be tested in-browser loses developers at the evaluation stage
- **Requiring credit card for sandbox access**: developers will choose a competitor with a frictionless free tier over a superior API that requires payment commitment upfront
- **Breaking changes disguised as non-breaking**: changing the semantics of a field (e.g., confidence score range) without a new API version breaks clients silently; worse than an explicit breaking change
- **No model version pinning**: clients that need reproducible results (legal, medical, compliance) cannot use an API that silently upgrades models; always offer version pinning

## Summary

- API versioning strategies: URL path versioning (`/v1/`) is the clearest for public APIs; header versioning (`api-version: 2025-03-31`) suits APIs with frequent backward-compatible evolution
- The two-axis problem: model versions and API versions evolve independently; a model upgrade should not break the API contract, and an API change should not require a model change
- Model version selection: pin a specific version for reproducibility (`whisper-large-v3`), use floating aliases for convenience (`whisper-latest`)
- Deprecation requires at least 6 months notice, in-band warnings (response headers), and out-of-band notifications; with migration guides and dual-serving during transition
- SDK design matters as much as API design; hand-crafted streaming helpers, async iterators, and language-idiomatic error handling set the standard
- Documentation must include interactive API reference, copy-paste quickstarts, and sandbox/playground environments; developers evaluate APIs by trying them, not reading about them
- Multimodal extensions should be backward-compatible; wrap existing single-modality payloads in a content array without requiring a new API version
- Time-to-first-API-call is the key onboarding metric; optimize for instant API key provisioning, no credit card for free tier, and minimal required configuration
- Forward reference: API key security, authentication, and access control for ML APIs are covered in Chapter 10

## References

*To be populated during chapter authoring. Initial sources:*

1. Google AIP (2025). AIP-181: Stability levels and versioning. aip.dev/181
2. Google AIP (2025). AIP-231: Batch methods. aip.dev/231
3. OpenAI (2025). "API Reference; Models and Versioning." platform.openai.com/docs/models
4. Azure OpenAI (2025). "API versioning and model deprecation." learn.microsoft.com/en-us/azure/ai-services/openai/api-version-deprecation
5. Deepgram (2025). "API Versioning and SDK Documentation." developers.deepgram.com
6. Stripe (2025). "API Versioning; How Stripe versions its API." stripe.com/docs/api/versioning
7. OpenAI (2025). "OpenAI Python SDK; Streaming." github.com/openai/openai-python

---

**Next: [Chapter 10: Security for Audio ML APIs](./10-security-audio-ml.md)**
