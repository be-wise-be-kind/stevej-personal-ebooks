# Chapter 13: SLOs for Streaming ML Systems

<!-- DIAGRAM: ch13-opener.html - Chapter 12 Opener -->

\newpage

## Overview

- **Ground the reader**: explain what SLOs and SLIs are for readers who may not have read Book 1. An SLI (Service Level Indicator) is a specific metric you measure, like "the time until the first word of a transcript appears." An SLO (Service Level Objective) is a target you set for that metric, like "the first word appears within 300 milliseconds for 99% of requests." An SLA (Service Level Agreement) is a contractual commitment to meet certain SLOs, with financial consequences if you miss them. SLOs are how a team defines "good enough" and tracks whether the system is meeting user expectations.
- Streaming ML systems require different SLIs than request/response APIs; time-to-first-token, inter-token latency, and real-time factor matter more than simple response time
- This chapter focuses on WHAT to measure and WHAT targets to set for ML inference, building on the observability fundamentals covered in Book 1
- The 300ms rule for voice AI is the anchor target, with specific SLIs and error budget strategies to achieve it

> **From Book 1:** For a deep dive on observability fundamentals (OpenTelemetry, distributed tracing, log aggregation), see "Before the 3 AM Alert" Chapters 3-4. For SLO fundamentals (SLI/SLO/SLA definitions, error budgets, burn rates), see "Before the 3 AM Alert" Chapter 2.

## Bridging the Gap

This chapter draws on concepts from both ML infrastructure and API engineering. If you have not encountered these before, this section provides the context you will need.

**From the ML side**, this chapter builds on SLI/SLO/SLA definitions that are standard in site reliability engineering. An SLI (Service Level Indicator) is a metric you measure, like response time or availability. An SLO (Service Level Objective) is a target for that metric, like "99% of requests complete within 300ms." An SLA (Service Level Agreement) is a contractual commitment with financial consequences if the SLO is missed. Error budgets are the allowed failure rate derived from the SLO. A 99.9% availability target means you can fail 0.1% of the time, which works out to approximately 43 minutes of downtime per month. Burn rate measures how fast you are consuming your error budget; a burn rate of 2x means you will exhaust the budget in half the expected time.

**From the API side**, streaming ML systems require SLIs that differ fundamentally from traditional API metrics. TTFT (Time to First Token) measures when the first output appears. For voice AI, this is more important than total duration because it determines perceived responsiveness. TPOT (Time Per Output Token) measures generation speed after the first token, capturing whether the stream keeps up. RTF (Real-Time Factor) equals processing time divided by audio duration; it must be below 1.0 or the system falls behind the live audio stream. Goodput is the percentage of requests that meet ALL SLO criteria simultaneously, a quality-adjusted throughput metric that is more meaningful than raw requests per second. KV cache pressure (GPU memory consumed by intermediate computation state for active requests) limits concurrency before compute saturates, making it a leading indicator of capacity exhaustion.

## Streaming-Specific SLIs

### Time to First Token / Time to First Byte (TTFT)

- TTFT measures the time from request submission to the first output token or byte; the user's perception of system responsiveness
- For speech-to-text: time from first audio chunk received to first transcript word returned
- For text-to-speech: time from text input to first audio byte of the synthesized speech
- TTFT is the single most important latency metric for interactive applications; it determines whether the system "feels" responsive
- Target: TTFT <= 100ms for interactive applications ("feels instantaneous" per RAIL model and MDN guidelines), TTFT <= 300ms for voice AI (the primary voice AI threshold)

### Time Per Output Token (TPOT)

- TPOT measures the inter-token generation speed after the first token; how fast subsequent tokens are produced
- For LLM text generation: the time between successive token emissions in a streaming response
- For speech-to-text: the time between successive transcript word updates
- Target: TPOT < 15ms for smooth streaming output that keeps pace with real-time playback
- TPOT directly affects perceived fluency; inconsistent TPOT causes stuttering in TTS and choppy transcript updates in STT

### Inter-Token Latency and Jitter

- Inter-token latency is the variance in time between consecutive tokens; ideally consistent, not spiky
- Jitter: the standard deviation of inter-token latency; high jitter means unpredictable delivery even if average latency is acceptable
- Jitter causes perceptual quality degradation: a stream with consistent 20ms inter-token latency feels smoother than one with 5ms-50ms variation
- Measurement: track P50, P95, and P99 of inter-token intervals, plus jitter as the standard deviation

### Connection Drop Rate

- Percentage of streaming connections that terminate unexpectedly before the client closes them
- Causes: GPU OOM (out of memory), inference timeout, network interruption, server crash, load balancer timeout
- Drop rate is a reliability SLI distinct from latency; a fast system that drops 5% of connections is not production-ready
- Target: connection drop rate < 0.1% (99.9% connection reliability)

### Active Connection Count

- Active concurrent connections (WebSocket sessions, gRPC streams) is a critical capacity and scaling signal for streaming ML systems
- Unlike request rate, active connections directly reflects GPU memory commitment: each open stream typically holds a KV cache allocation for the duration
- **Measurement pitfall: point-in-time gauge sampling.** An OpenTelemetry `ObservableGauge` with a callback that reads `len(active_connections)` at each 60-second export interval will read zero for all requests shorter than the interval. For speech-to-text with sub-second utterances or short commands, the gauge systematically reports zero even under heavy load
- **Solution: peak-tracking (high-water mark) counter.** Increment a counter on connection open, track the peak concurrent count within each export interval, and reset the peak after export. This captures the true maximum concurrency regardless of request duration
- Alternatively, use a histogram of concurrent connection counts sampled at sub-second granularity, which preserves distribution information
- Impact on auto-scaling: if the active-connections metric reads zero, the auto-scaler never triggers a scale-up event regardless of actual load; this is a silent failure that only manifests under traffic spikes when scaling is most needed
- Target: depends on GPU memory and model size; a common starting point is alerting when active connections exceed 80% of the maximum supported by the deployed model's KV cache budget

### Real-Time Factor (RTF)

- RTF = processing time / audio duration; must be < 1.0 for real-time streaming (the system processes faster than real-time)
- Example: RTF of 0.3 means 1 second of audio is processed in 0.3 seconds; the system has 0.7 seconds of headroom
- RTF > 1.0 means the system falls behind real-time; audio buffers grow unboundedly, latency increases continuously
- RTF as a capacity planning metric: as load increases, RTF approaches 1.0; this is the signal to scale out before crossing the threshold
- Target: RTF < 0.5 under normal load (50% headroom), with alerting when RTF > 0.8

<!-- DIAGRAM: ch13-streaming-sli-taxonomy.html - Streaming SLI Taxonomy -->

\newpage

## Target Numbers from Research

### Interactive Latency Thresholds

- 100ms: "feels instantaneous"; the RAIL model target for user input response [Source: Google RAIL, 2024]
- 300ms: the voice AI threshold; responses within 300ms feel conversational; beyond 300ms, users perceive delay [Source: AssemblyAI, 2025]
- 1 second: the attention-sustaining threshold; users maintain focus but notice the wait
- 10 seconds: the abandonment threshold; users leave or retry

### Speech-to-Text Targets

- P95 final transcript latency <= 800ms for 3-second utterances; the full pipeline from audio to final transcript
- TTFT (first partial transcript) <= 300ms; the user sees initial words appearing within the conversational threshold
- Word Error Rate (WER) is not a latency SLI but interacts with SLO targets; a fast system with high WER is not meeting quality objectives
- End-to-end latency < 2 seconds for the complete pipeline including post-processing (punctuation, formatting, PII redaction)

### LLM Inference Targets

- TTFT <= 100ms for interactive chat applications
- TPOT < 15ms for smooth streaming text generation (approximately 67 tokens per second)
- P99 end-to-end latency < 5 seconds for complex prompts with long outputs
- These targets assume optimized infrastructure (continuous batching, quantized models, warm GPU pools)

### Target Summary Table

- Consolidation of all targets in a single reference table: SLI, target value, applicable use case, source
- Emphasize that targets are starting points; adjust based on user research and business requirements
- More aggressive targets increase infrastructure cost; relaxed targets reduce cost but may degrade user experience

<!-- DIAGRAM: ch13-slo-target-framework.html - SLO Target Framework -->

\newpage

## Goodput

### Defining Goodput

- Goodput: the percentage of inference requests that meet ALL SLO criteria; latency within target, correct output, no errors
- Goodput = (requests meeting SLOs) / (total requests); a quality-adjusted throughput metric
- Distinction from raw throughput: a system serving 1000 requests/second with 30% exceeding latency targets has a throughput of 1000 but a goodput of 700
- Goodput captures the user's actual experience better than any single metric

### Why Goodput Matters for ML Inference

- ML inference has highly variable per-request cost; a batch of 10 short prompts has very different GPU utilization than 1 long prompt
- Raw throughput can be gamed: serve short requests fast and let long requests queue; throughput looks great, user experience suffers
- Goodput forces the conversation about quality: "We serve 1000 req/s" vs. "700 of our 1000 req/s meet all SLOs"
- Academic foundation: "Revisiting SLO and Goodput Metrics in LLM Serving" (2024) formalizes goodput as the primary metric for LLM inference evaluation

### Measuring Goodput in Practice

- Define the SLO criteria that constitute "good": TTFT < X, TPOT < Y, no errors, output complete
- Instrument the inference pipeline to tag each request as meeting or not meeting each criterion
- Calculate goodput as a rolling window metric (e.g., 5-minute, 1-hour) for real-time monitoring
- Report goodput alongside raw throughput in all capacity planning and performance discussions

## Setting SLO Targets

### User Experience vs. Infrastructure Cost

- Tighter SLOs require more infrastructure: lower latency targets mean more GPU headroom, more replicas, more expensive instance types
- The diminishing returns curve: going from 500ms to 300ms TTFT is much cheaper than going from 300ms to 100ms
- Cost modeling: estimate the infrastructure cost at each SLO tier and map to business impact (conversion rate, user retention, customer satisfaction scores)
- The 300ms rule for voice AI is not arbitrary; it is the threshold where user-perceived quality changes discontinuously

### The SLO Negotiation Process

- Start with user research: what latency do users actually notice? What error rate causes complaints?
- Propose SLO targets to stakeholders with cost estimates for each tier
- Negotiate: business may accept relaxed latency targets in exchange for lower infrastructure spend
- Document the agreed SLOs, their rationale, and the cost implications; this is the contract between engineering and business

### SLOs for Different Use Cases

- Real-time voice agents: TTFT <= 300ms, RTF < 0.5, connection drop rate < 0.1%; the strictest targets
- Batch transcription: P99 end-to-end < 5x audio duration, no real-time requirement; optimize for throughput and cost
- Live captioning: TTFT <= 500ms, RTF < 0.8; real-time but with more tolerance than voice agents
- Offline analytics: completion within SLA window (hours), no per-request latency target; maximize GPU utilization

## Error Budgets for ML

### The Error Budget Concept Applied to ML

- Error budget: the allowed failure rate derived from the SLO; a 99.9% availability SLO gives a 0.1% error budget (43 minutes/month)
- For ML inference, error budgets cover more than just uptime: latency violations, accuracy degradation, and dropped connections all consume the budget
- Error budget policy: what happens when the budget is exhausted; freeze deployments, reduce traffic, escalate

> **From Book 1:** For a deep dive on error budget fundamentals and burn rate alerting, see "Before the 3 AM Alert" Chapter 2.

### Model Accuracy Interacting with Infrastructure Reliability

- A 99% accurate model on 99.9% reliable infrastructure yields 98.9% end-to-end quality (the probabilities multiply)
- This means infrastructure reliability must be significantly higher than model accuracy to avoid compounding degradation
- Example: targeting 95% end-to-end quality with a 97% accurate model requires 97.9% infrastructure reliability; achievable but not trivial
- Error budgets must account for both dimensions: model quality errors and infrastructure errors

### Spending Error Budgets Wisely

- Use error budget for high-value changes: model upgrades, framework migrations, infrastructure improvements
- Avoid wasting budget on routine changes: test thoroughly in staging to avoid consuming production error budget on preventable issues
- Error budget as a deployment gate: if remaining budget is below threshold, block non-critical deployments until budget replenishes
- Monthly error budget review: track consumption by category (model errors vs. infrastructure errors vs. configuration errors) to focus improvement efforts

## Voice Agent Metrics (2026)

### Speed: TTFT as the Primary Metric

- For voice agents (conversational AI), TTFT is the single most important metric; it determines turn-taking latency
- Competitive landscape (2026): leading voice agents target TTFT < 200ms for a natural conversational cadence
- TTFT budget breakdown: network transit (20-50ms) + speech recognition (50-100ms) + LLM processing (50-100ms) + speech synthesis (50-100ms) = 170-350ms total
- Every component in the chain must be optimized; one slow stage blows the entire budget

### Accuracy: Word Error Rate (WER)

- WER = (substitutions + insertions + deletions) / total words; the standard accuracy metric for speech-to-text
- Production WER targets: < 5% for clean speech, < 15% for noisy environments, < 10% for medical/legal domains with custom vocabulary
- WER and latency trade-off: more accurate models are often larger and slower; find the accuracy-latency frontier for your use case
- WER monitoring in production: compare against baseline WER continuously, alert on regression

### Processing Efficiency: RTF

- RTF as the efficiency metric: lower RTF means more headroom for additional processing (PII redaction, formatting) within the latency budget
- RTF varies by model size, hardware, and batch size; benchmark your specific configuration
- RTF trends over time: monitor RTF under increasing load to predict when scaling is needed
- RTF as a cost metric: lower RTF means fewer GPU-hours per audio-hour processed

## Monitoring and Alerting on SLO Burn Rate

### Multi-Window Burn Rate Alerts

- Single-window alerts are noisy: a brief spike triggers an alert that may resolve before anyone responds
- Multi-window burn rate: compare short-window burn rate (e.g., 5 minutes) against long-window burn rate (e.g., 1 hour); alert only when both indicate a problem
- Fast burn (5-min window, 14.4x budget consumption rate): pages on-call for acute incidents
- Slow burn (6-hour window, 6x budget consumption rate): creates a ticket for investigation within hours
- Very slow burn (3-day window, 1x budget consumption rate): weekly review; the system is slowly degrading

### Error Budget Consumption Dashboards

- Real-time visualization of error budget remaining for each SLO (availability, latency, goodput)
- Burn-down chart: projected date of budget exhaustion at current consumption rate
- Budget consumption by category: separate infrastructure errors from model quality errors from configuration errors
- Historical comparison: overlay current month's budget consumption against previous months to identify trends

### Alerting Thresholds for ML-Specific SLIs

- TTFT alert: P95 TTFT exceeds target for > 5 minutes; indicates GPU saturation, model loading, or network issues
- RTF alert: RTF exceeds 0.8 for > 2 minutes; system approaching real-time boundary, scale out immediately
- Goodput alert: goodput drops below 90% for > 10 minutes; significant quality degradation
- Connection drop rate alert: drop rate exceeds 1% for > 5 minutes; infrastructure reliability issue

### Label Consistency Across Telemetry Pillars

- Metrics, traces, and logs must use identical label names for service identification; otherwise cross-pillar correlation breaks silently
- **Concrete failure mode**: if the OpenTelemetry SDK exports traces with resource attribute `service_name=inference-api` but Grafana dashboards query Prometheus metrics with `{service="inference-api"}`, all dashboard panels show "no data" despite telemetry flowing correctly to every backend
- This failure is silent and insidious: empty panels look the same whether the system is healthy (no problems) or the labels are wrong (no data). Teams waste days debugging "missing telemetry" that is actually present but queried under the wrong label
- For ML inference systems with multiple services (API gateway, inference worker, post-processing, model registry), the risk multiplies: each service must use the same label name convention across all three pillars
- **Prevention**: define a service naming convention early. Use OpenTelemetry resource attributes (`service.name`, `deployment.environment`) as the canonical source. Ensure Prometheus metric labels, Tempo trace resource attributes, Loki structured log fields, and Grafana dashboard template variables all reference the same label names
- Include a "telemetry integration test" in CI: emit a test request through the pipeline, verify that the service label appears in metrics, traces, and logs under the expected name

### The Cross-Pillar Debugging Workflow

- The payoff of four-pillar observability (metrics, traces, logs, profiling) is a connected debugging workflow for ML inference latency issues
- **The full chain**: Dashboard shows P99 latency spike → Click exemplar link embedded in the metric → Jump to trace waterfall showing the specific slow request → Filter correlated logs by `trace_id` from the trace → Open flame graph (CPU/GPU profile) for the slow span
- Each link in the chain requires a specific instrumentation capability:
  - **Metric → Trace (exemplars)**: requires tracing middleware wrapping metrics middleware so the request's active span is available during metric recording; without correct middleware ordering, metrics lack span context and exemplar links are impossible
  - **Trace → Logs**: requires consistent `trace_id` and `span_id` propagation into structured log fields; every log line emitted during a request must carry the W3C trace context
  - **Trace → Profile**: requires profiling SDK that correlates profiles with trace spans (e.g., Pyroscope with `trace_id` / `span_id` tags)
- **For ML inference specifically**, this chain answers: "Why was this particular audio transcription slow?" Was it GPU contention (visible in trace span timing for the inference stage)? Model loading (visible in logs showing cache miss)? A long input (visible in span attributes like `chunk.duration_ms` or `input.token_count`)? Queue wait (visible as gap between request arrival and inference start in the trace waterfall)?
- Without this chain, debugging reduces to staring at aggregate dashboards and guessing; with it, you can diagnose a single slow request end-to-end in minutes

### Validate Telemetry Format Assumptions

- Before writing dashboard queries, verify the actual format of emitted telemetry by inspecting raw data at the collector
- **Concrete failure mode**: LogQL queries written for JSON-formatted logs (`{job="app"} | json | level="error"`) return "no data" when the application SDK emits logfmt-formatted logs (`level=error msg="request failed"`). The query parser silently fails to match
- This is especially common when assembling observability from multiple components: the inference service emits JSON, the ASGI middleware emits logfmt, the GPU exporter emits plaintext, each requiring different LogQL parsing pipelines
- **Prevention**: emit a test request through the full pipeline, check raw telemetry at the collector (e.g., query Loki with `{job="app"} | line_format "{{.}}"` to see raw lines), then write queries that match the actual format. Do this for every new telemetry source before building dashboards

<!-- DIAGRAM: ch13-burn-rate-alerting.html - Burn Rate Alerting -->

\newpage

## Jitter Buffers

### Why Jitter Buffers Exist

- Network packet arrival is inherently variable; packets take different paths, encounter different congestion
- For streaming audio and real-time inference results, variable arrival times cause audible artifacts (clicks, gaps, stuttering)
- Jitter buffers smooth variable arrival by introducing a small, controlled delay; trade a fixed delay for consistent playback

### Jitter Buffers in ML Inference Pipelines

- WebRTC pipelines: client-side jitter buffers smooth received audio and inference results; typically 20-200ms
- gRPC streaming: application-level buffering to smooth token delivery; accumulate N tokens before flushing to the client
- WebSocket pipelines: client-side buffer to smooth transcript word delivery; prevents single-word flicker
- The fundamental trade-off: larger jitter buffer = smoother delivery but higher end-to-end latency

### Impact on SLO Measurement

- Jitter buffers add latency that is invisible to server-side metrics; measure SLIs at the client, not just at the server
- TTFT measured at the server may be 100ms, but TTFT experienced by the user includes jitter buffer delay (potentially 100ms + 50ms buffer = 150ms)
- SLO targets should account for jitter buffer overhead; if the user-facing target is 300ms and the jitter buffer adds 50ms, the server-side target is 250ms
- Adaptive jitter buffers: dynamically adjust buffer size based on network conditions; smaller buffer on good networks, larger on poor networks

## Common Pitfalls

- **Measuring latency only at the server**: client-experienced latency includes network transit, jitter buffer delay, and client processing; server-side metrics systematically underestimate user-perceived latency
- **Using average latency instead of percentiles**: P50 hides tail latency; a system with 100ms P50 and 5s P99 is not meeting a 300ms SLO for 1% of users
- **Ignoring goodput in favor of raw throughput**: a system processing 1000 req/s is meaningless if 30% of those requests miss SLO targets; goodput is the metric that matters
- **Setting SLOs without user research**: engineering-driven SLO targets may be too tight (wasting infrastructure) or too loose (degrading user experience); ground targets in user behavior data
- **Treating RTF > 1.0 as a latency problem**: RTF > 1.0 means the system fundamentally cannot keep up; no amount of latency optimization fixes a capacity problem
- **Alerting on every SLO violation individually**: multi-window burn rate alerts prevent alert fatigue; a single spike that self-resolves should not page anyone
- **Forgetting that model accuracy compounds with infrastructure reliability**: 99% model accuracy on 99.9% infrastructure yields 98.9% end-to-end quality; account for both in error budget planning
- **Point-in-time sampling of connection gauges for fast requests**: an `ObservableGauge` sampled at 60-second intervals reads zero for all sub-second streams; the metric is useless for capacity planning and auto-scaling. Use peak-tracking counters or high-frequency histograms instead
- **Measuring streaming latency at response headers instead of response completion**: standard HTTP middleware (e.g., Starlette's `BaseHTTPMiddleware`) reports latency only to headers-sent, then returns. For streaming ML responses, the entire inference duration occurs during body streaming. A request consuming 30 seconds of GPU time shows as 1ms in header-only metrics. Use ASGI-level instrumentation that captures the full `send()` lifecycle (see Chapter 7)
- **Dashboard queries targeting labels that don't match exporter configuration**: if traces export `service_name` but dashboards query by `service`, every panel silently shows "no data." Always verify label names across metrics, traces, and logs before building dashboards
- **Writing LogQL/PromQL queries before verifying emitted format**: queries built for JSON parsing (`| json`) fail silently against logfmt-emitting applications. Test against actual raw telemetry output before scaling query patterns across dashboards

## Summary

- Streaming ML systems require specialized SLIs: TTFT, TPOT, inter-token jitter, connection drop rate, RTF, and goodput
- Key targets: TTFT <= 100ms (interactive) or <= 300ms (voice AI), TPOT < 15ms, RTF < 0.5 (normal load), connection drop rate < 0.1%
- Goodput (percentage of requests meeting ALL SLOs) is a more meaningful metric than raw throughput for ML inference
- Error budgets for ML must account for both model accuracy and infrastructure reliability; the probabilities multiply
- The 300ms rule for voice AI is the primary target; every component in the inference pipeline must be optimized to fit within this budget
- Multi-window burn rate alerting prevents alert fatigue while catching both acute incidents and slow degradation
- Jitter buffers add latency invisible to server metrics; measure SLIs at the client and account for buffer overhead in server-side targets
- SLO targets should be grounded in user research and negotiated with business stakeholders based on cost-quality trade-offs

## References

*To be populated during chapter authoring. Initial sources:*

1. Zheng, L. et al. (2024). "Revisiting SLO and Goodput Metrics in LLM Serving." arXiv preprint.
2. Xie, X. et al. (2025). "JITServe: SLO-aware LLM Serving with Just-in-Time Scheduling." arXiv preprint.
3. Gladia (2025). "How to Measure Latency in Speech-to-Text Systems."
4. Anyscale (2025). "Understand LLM Latency and Throughput Metrics for Optimization."
5. AssemblyAI (2025). "The 300ms Rule: Why Latency Makes or Breaks Voice AI."
6. BentoML (2025). "Key Metrics for LLM Inference: A Comprehensive Guide."
7. Google (2024). "RAIL Performance Model."

---

**Next: [Chapter 14: Usage Metering & Billing](./14-usage-metering-billing.md)**
