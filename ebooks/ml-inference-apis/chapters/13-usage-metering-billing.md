# Chapter 13: Usage Metering & Billing

<!-- DIAGRAM: ch13-opener.html - Chapter 13 Opener -->

\newpage

## Overview

- **Ground the reader**: explain what usage metering is and why it is harder for ML APIs than for traditional web services. Metering is the process of measuring how much of a service each customer uses so you can charge them accurately. For a typical SaaS API, you might count API calls or data transferred. For ML inference APIs, the picture is more complex: a 10-second audio transcription request consumes far more GPU compute than a 1-second request, so flat per-request pricing would either overcharge small requests or lose money on large ones. The metering system must track the right unit (audio seconds, tokens, GPU time) at high throughput, aggregate it reliably, and feed it into a billing system, all without losing or double-counting events.
- How to meter, aggregate, and bill for ML inference usage; the infrastructure that connects API calls to revenue
- The billing models used by speech/audio and LLM providers (per-second, per-block, per-character, per-token, per-hour) and when each makes sense
- Modern metering infrastructure: Stripe Meters API, OpenMeter, and the architecture of idempotent event collection and real-time aggregation

## Bridging the Gap

This chapter draws on concepts from both ML infrastructure and API engineering. If you have not encountered these before, this section provides the context you will need.

**From the ML side**, this chapter covers usage-based billing infrastructure, which connects API consumption to revenue. Metering events are records of what each customer consumed (e.g., 47.3 audio seconds processed at the "nova-3" model tier). These events flow through a pipeline: collection (emitted from the inference server at request completion) → aggregation (summing per customer per billing period) → invoicing (through Stripe, a custom billing system, or similar). Idempotency keys on metering events prevent double-billing when network retries cause the same event to be submitted twice. Rate limiting tied to billing tiers means a free-tier customer gets fewer concurrent streams or lower priority than an enterprise customer paying for dedicated capacity.

**From the API side**, ML metering is harder than traditional API metering because request cost varies dramatically. A single API call can vary 60x in resource consumption. A 1-second audio transcription uses a fraction of the GPU time that a 60-second one does, unlike web requests where cost per request is roughly uniform. Flat per-request pricing loses money on long requests and overcharges short ones. Feature-based pricing (base rate plus increments for diarization, speaker identification, PII redaction, etc.) means the metering system must track which features were enabled per request, not just the request itself. Per-block billing (charging in 15-second increments) simplifies metering but can overcharge by 36% on short-utterance workloads like voice commands.

## What to Meter

### Audio-Specific Metering Units

- **Audio seconds/minutes**: the most intuitive unit for speech APIs; Deepgram charges $0.0043-0.0077/min depending on model tier, AssemblyAI charges $0.15/hr ($0.0025/min) base
- **Audio seconds processed vs audio seconds submitted**: processed excludes silence detected by VAD; submitted includes everything; this distinction affects cost by 30-70%
- **Channels**: stereo audio (2 channels) may be metered as 2x mono; important for call center use cases with agent + caller channels
- **Sample rate and bit depth**: higher quality audio (48kHz/32-bit) requires more compute than lower quality (8kHz/16-bit); some providers factor this into pricing

### LLM and Text Metering Units

- **Tokens**: the standard LLM metering unit; input tokens and output tokens often priced differently (output tokens 2-4x more expensive due to autoregressive generation cost)
- **Characters**: ElevenLabs charges per character for TTS; simpler to understand but does not account for varying compute cost across languages
- **API calls**: flat per-call pricing regardless of input size; simple but misaligned with actual compute cost, penalizes small requests
- **Compute time (GPU-seconds)**: the most cost-aligned unit; charges for actual GPU time consumed; but difficult for clients to predict and budget

### Composite Metering

- Real-world usage often combines multiple units: audio minutes for transcription + API calls for metadata retrieval + storage duration for retained results
- Feature-based metering: AssemblyAI's base rate of $0.0025/min can 3-4x with added features (PII redaction, speaker diarization, sentiment analysis, summarization)
- Each feature adds an increment to the per-minute cost; the total per-minute rate is base + sum of feature increments
- The metering system must track which features were enabled for each request to calculate the correct rate

## Billing Models Compared

### Per-Second Billing

- Charges for exact duration of audio processed, rounded to the nearest second
- Provider example: Deepgram at $0.0043-0.0077/min, AssemblyAI at $0.0025/min; both use per-second granularity
- Advantage: most fair for variable-length audio; a 3-second utterance costs proportionally less than a 60-second one
- Best for: APIs serving many short utterances (voice assistants, command recognition, IVR systems)

### Per-Block Billing

- Charges in fixed time blocks (typically 15 seconds); any audio within a block is charged as the full block
- Provider example: AWS Transcribe charges per 15-second block; a 1-second utterance costs the same as a 15-second one
- The overcharge problem: per-block billing can cost up to 36% more than per-second billing on workloads with many short utterances
- Advantage: simpler to implement and predict; the number of blocks is easy to calculate
- Best for: long-form transcription where individual segments are consistently longer than the block size

### Per-Character Billing

- Charges per character of text input or output; common for TTS (text-to-speech) services
- Provider example: ElevenLabs charges per character for speech synthesis
- Advantage: directly proportional to output length; predictable for text-heavy workflows
- Complication: character count varies by language for equivalent semantic content (e.g., Chinese vs English); some providers normalize by "character equivalent"

### Per-Token Billing

- Charges per token (input and/or output); the standard for LLM APIs
- Provider examples: OpenAI, Anthropic, Google all use per-token pricing with separate input/output rates
- Token counting is model-specific (different tokenizers produce different token counts for the same text); the API must report actual token usage in the response
- Advantage: most aligned with actual compute cost for transformer models; longer context windows cost more

### Per-Hour / Flat Rate Billing

- Charges a flat hourly rate for access to a dedicated or reserved inference capacity
- Provider example: AssemblyAI offers $0.15/hr for real-time streaming as an alternative to per-minute pricing
- Advantage: predictable cost for sustained, high-volume usage; no per-request cost uncertainty
- Best for: always-on streaming applications (live captioning, 24/7 monitoring) where utilization is consistently high

<!-- DIAGRAM: ch13-billing-model-comparison.html - Billing Model Comparison -->

\newpage

## Metering Architecture

### Idempotent Event Collection

- Every metered event must have a unique, client-generated idempotency key; network retries must not cause double-billing
- Event schema: `{ "event_id": "uuid", "timestamp": "iso8601", "customer_id": "...", "meter": "audio_seconds", "value": 3.7, "metadata": { "model": "nova-3", "features": ["diarization"] } }`
- At-least-once delivery with idempotent processing: the collection layer accepts duplicate events but the aggregation layer deduplicates by event_id
- Event immutability: once collected, events are append-only; corrections are handled by submitting adjustment events, not by modifying originals

### Collection Patterns

- **Inline collection**: the inference server emits a metering event synchronously after each inference completes; simplest but adds latency to the response path
- **Async sidecar**: the inference server writes events to a local buffer, a sidecar process flushes them to the metering backend asynchronously; decouples metering latency from inference latency
- **Event streaming**: events are published to a message queue (Kafka, SQS, Pub/Sub) and consumed by the metering service; highest reliability, highest complexity
- Recommendation: async sidecar for single-server deployments, event streaming for distributed deployments

### Aggregation Pipelines

- Raw events are aggregated into billing-period summaries: hourly rollups, daily rollups, monthly totals
- Aggregation windows must align with billing periods; if billing is monthly, the aggregation must produce exact monthly totals at billing cycle boundaries
- Pre-aggregation vs query-time aggregation: pre-aggregation (materialized rollups) is faster to query but harder to correct; query-time aggregation is slower but always accurate
- Hybrid approach: pre-aggregate for dashboard display, query raw events for invoice generation to ensure accuracy

### Real-Time vs Batch Metering

- **Real-time metering**: events are aggregated within seconds of collection; enables real-time usage dashboards, instant quota enforcement, mid-cycle alerts
- **Batch metering**: events are collected and aggregated on a schedule (hourly, daily); simpler, cheaper, but usage data is delayed
- Real-time is necessary for: rate limiting tied to billing tiers, prepaid balance enforcement, usage alerts
- Batch is sufficient for: monthly invoicing, cost reporting, usage analytics
- Most production systems use both: real-time for enforcement, batch for invoicing and reconciliation

<!-- DIAGRAM: ch13-metering-architecture.html - Metering Architecture: Event Collection to Billing -->

\newpage

## Stripe Meters API

### The New Standard for Usage Billing

- Stripe's Meters API (replacing legacy usage records, which were removed in API v2025-03-31) is purpose-built for usage-based billing
- A Meter defines what is being counted (e.g., "audio_seconds"), how it aggregates over billing periods (sum, max, last), and what event key identifies the customer
- Meter Events: submit raw usage events to Stripe, which handles deduplication, aggregation, and invoice line item generation
- Advantage over legacy usage records: real-time aggregation, built-in deduplication, native support for multiple metering dimensions

### Stripe Token Billing

- Purpose-built for LLM and AI metering: Stripe's token billing feature handles the input/output token split natively
- Integrates with Stripe's LLM proxy feature: call models through Stripe and have usage automatically recorded and billed
- Pricing tiers: configure volume-based pricing (first 1M tokens at rate A, next 10M at rate B) or graduated pricing directly in Stripe
- Advantage: eliminates the custom metering-to-billing integration; Stripe handles the entire flow from event to invoice

### Integration Architecture

- The inference server submits meter events to Stripe via the Meters API after each inference completes
- Stripe aggregates events per customer per billing period and generates invoice line items automatically
- Webhook-driven reconciliation: Stripe sends `invoice.created` and `invoice.finalized` events; the application verifies totals match internal records
- Failure handling: if Stripe event submission fails, buffer locally and retry; idempotency keys prevent double-billing on retry

<!-- DIAGRAM: ch13-stripe-integration.html - Stripe Meters API Integration Flow -->

\newpage

## OpenMeter

### Open-Source Real-Time Metering

- OpenMeter is an open-source metering engine designed for real-time usage tracking; acquired by Kong in 2025
- Provides real-time aggregation with sub-second latency; enables instant usage dashboards and quota enforcement
- Used in production by Lever, Apollo GraphQL, and Google; proven at scale for AI/ML metering use cases
- Architecture: event ingestion via HTTP/Kafka, ClickHouse-based storage and aggregation, REST API for queries

### OpenMeter + Stripe Integration

- Native Stripe integration: OpenMeter can push aggregated usage to Stripe Meters, combining real-time visibility with Stripe's billing infrastructure
- The pattern: inference server -> OpenMeter (real-time aggregation, dashboards, rate limiting) -> Stripe (invoicing, payment processing)
- Advantage: real-time metering granularity (OpenMeter) plus production-grade billing (Stripe) without building either from scratch
- OpenMeter handles the high-volume event ingestion and aggregation; Stripe handles the customer-facing billing and payment

### Self-Hosted vs Managed

- OpenMeter Cloud: managed service with SLA; simplest path to production real-time metering
- Self-hosted: deploy OpenMeter on your own infrastructure; more control, no vendor dependency, but requires operating ClickHouse
- Decision factors: event volume (self-hosted makes sense above ~100M events/month), data residency requirements, team operational capacity

## Rate Limiting Tied to Billing Tiers

### Tier-Based Rate Limits

- Each billing tier defines its own rate limits: free tier (10 req/min, 1 concurrent stream), pro tier (100 req/min, 10 streams), enterprise (custom)
- Rate limits should be enforced at the API gateway layer, informed by the customer's current billing tier from the metering system
- Dynamic tier changes: when a customer upgrades mid-cycle, rate limits should update within seconds; requires the gateway to check tier in near-real-time
- Overage handling: some tiers allow overage at a higher per-unit rate; others hard-cap usage at the tier limit

### Quota Enforcement

- Quotas differ from rate limits: rate limits control instantaneous throughput, quotas control total consumption within a billing period
- Example: a customer on the $50/month plan gets 100 hours of transcription; the metering system must track cumulative usage and enforce the cap
- Soft quotas: warn the customer at 80% and 90% of their allocation via email/webhook, allow usage to continue
- Hard quotas: block requests at 100% of allocation; return 429 with a clear message about the quota limit and upgrade options

### Prepaid Balance Management

- Prepaid credits: customers purchase a credit balance (e.g., $500 in transcription credits) and draw down as they use the API
- Real-time balance checking: every inference request must verify sufficient credit balance before processing; stale balance data risks delivering unpaid inference
- Low balance alerts: notify customers when their balance drops below configurable thresholds
- Balance expiration: prepaid credits often have an expiry date; the metering system must track both balance and expiration

> **From Book 1:** For a deep dive on rate limiting algorithms (token bucket, sliding window, leaky bucket) and their implementation, see "Before the 3 AM Alert" Chapter 10.

## Feature-Based Pricing

### The Add-On Model

- Base inference has a base rate; additional features (diarization, PII redaction, sentiment analysis, translation, summarization) each add an increment
- AssemblyAI example: base transcription at $0.0025/min, speaker diarization adds $0.0010/min, PII redaction adds $0.0015/min, sentiment adds $0.0008/min; a fully-featured request may cost 3-4x the base rate
- The metering system must track which features were enabled for each request to calculate the correct total rate
- Feature flags in the inference request map directly to metering dimensions; the pipeline composition from Chapter 6 directly affects billing

### Pricing Page Design

- Transparent pricing: list each feature's incremental cost clearly; developers prefer predictable pricing they can calculate themselves
- Cost calculator: interactive tool that lets customers estimate monthly cost based on volume and feature selection
- Commitment discounts: lower per-unit rates for annual commitments or minimum monthly spend; common for enterprise tiers
- Free tier: essential for developer adoption; offer enough free usage for evaluation and prototyping without requiring payment information

### Unit Economics Awareness

- 2026 is the year of AI unit economics; organizations are realizing that AI services without financial governance bleed margins [Source: OpenMeter, 2025]
- Cost per inference must be tracked alongside revenue per inference to maintain positive unit economics
- GPU cost attribution: allocate GPU costs to specific customers and features to understand which usage patterns are profitable
- Margin alerts: automated monitoring that flags when a customer's usage pattern yields negative margins (e.g., heavy use of compute-expensive features on a low-cost tier)

## Audit Trail for Usage Disputes

### Event-Level Audit Logs

- Every metering event must be retained in an immutable audit log for the billing dispute window (typically 90 days to 1 year)
- Audit log schema: event_id, timestamp, customer_id, meter, value, inference_request_id, model_version, features_enabled, raw_input_metadata
- The audit log must be independently queryable; not just a side effect of the aggregation pipeline; so that support teams can investigate specific usage events
- Storage considerations: raw metering events at scale (millions per day) require cost-effective storage; compressed columnar formats (Parquet) or tiered storage (hot/warm/cold)

### Dispute Resolution Workflow

- Customer disputes a charge: support queries the audit log by customer_id + time range to find the specific metering events
- Common dispute patterns: duplicate events (idempotency failure), metering during errors (should not bill for failed inference), incorrect feature attribution
- Adjustment mechanism: submit credit events that offset the disputed charges; never modify the original events
- Automated dispute detection: monitor for anomalies (sudden usage spikes, billing for error responses, duplicate event_ids) and flag for review before the customer complains

### Reconciliation

- Monthly reconciliation: compare internal metering totals against Stripe invoice totals against customer-reported usage
- Discrepancy investigation: any difference above a threshold (e.g., 0.1%) triggers an automated investigation
- Clock skew handling: metering events from distributed servers may have slightly different timestamps; the aggregation layer must handle events that arrive out of order or at billing period boundaries
- Multi-system consistency: if metering data flows through OpenMeter and Stripe, both must agree on totals; run periodic consistency checks

## Common Pitfalls

- **Billing for failed inference**: if the model returns an error or times out, the customer should not be charged; ensure metering events are only emitted for successful completions
- **Per-block billing for short-utterance workloads**: per-15-second blocks can overcharge by 36% on workloads with many sub-5-second utterances; per-second billing is fairer and more competitive
- **No idempotency in event collection**: without idempotency keys, network retries cause double-billing; this erodes customer trust faster than any other billing issue
- **Batch-only metering with real-time rate limits**: if metering is hourly but rate limits are per-second, the rate limiter cannot enforce quota accurately; real-time metering is needed for real-time enforcement
- **Opaque pricing**: hiding the true cost behind complex tier structures frustrates developers; transparent, calculable pricing wins adoption
- **Ignoring unit economics**: tracking revenue without tracking cost-to-serve per customer leads to unprofitable growth; meter both sides of the equation
- **No audit trail**: when a customer disputes a charge and you cannot produce the underlying events, you lose the dispute and the customer's trust

## Summary

- Metering units vary by modality: audio seconds/minutes for speech, tokens for LLMs, characters for TTS, compute time for general inference
- Per-second billing is fairest for variable-length audio workloads and up to 36% cheaper than per-block for short utterances
- Feature-based pricing (base + per-feature increments) is the dominant model for speech APIs; the pipeline composition from Chapter 6 directly drives billing
- Metering architecture requires idempotent event collection, aggregation pipelines aligned with billing periods, and both real-time (for enforcement) and batch (for invoicing) processing
- Stripe Meters API is the modern standard for usage billing; handles event deduplication, aggregation, and invoice generation with native token billing support
- OpenMeter provides open-source real-time metering with sub-second aggregation and native Stripe integration; combines real-time visibility with production-grade billing
- Rate limiting must be tied to billing tiers and quotas; enforce at the gateway layer using near-real-time tier and balance data
- Audit trails for every metering event are non-negotiable; dispute resolution, reconciliation, and trust depend on event-level traceability
- 2026 is the year organizations must get serious about AI unit economics; metering both revenue and cost-to-serve per customer and per feature

## References

*To be populated during chapter authoring. Initial sources:*

1. Stripe (2025). "Meters API Reference." docs.stripe.com/api/billing/meter
2. Stripe (2025). "Token Billing for AI and LLM Applications." docs.stripe.com/billing/subscriptions/usage-based/token-billing
3. OpenMeter (2025). "Real-Time Usage Metering." openmeter.io/docs
4. Deepgram (2025). "Pricing; Pay-as-you-go." deepgram.com/pricing
5. AssemblyAI (2025). "Pricing and Feature Add-ons." assemblyai.com/pricing
6. BrasTranscripts (2025). "Speech-to-Text API Pricing Comparison."
7. ElevenLabs (2025). "Pricing; Per-character TTS." elevenlabs.io/pricing

---

**Next: [Chapter 14: Scaling Inference Globally](./14-scaling-inference-globally.md)**
