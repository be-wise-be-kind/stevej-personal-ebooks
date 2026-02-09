# Chapter 3: Observability - The Foundation of Optimization

![Chapter 3 Opener](../assets/ch03-opener.html)

\newpage

## Overview

You cannot optimize what you cannot measure. This principle, while seemingly obvious, is violated constantly in software engineering. Teams attempt to improve performance through intuition, guesswork, or cargo-cult adoption of techniques that worked elsewhere. The result is wasted effort, introduced complexity, and often no measurable improvement.

Observability provides the foundation for the empirical approach we advocate throughout this book. Before we can optimize database queries, tune connection pools, or implement caching strategies, we must first understand where time is being spent, which operations fail, and how our systems behave under real-world conditions. The instrumentation we build in this chapter will guide every optimization decision in subsequent chapters.

The modern observability stack has converged around three complementary signal types (metrics, logs, and traces) plus a fourth pillar that is increasingly recognized as essential: continuous profiling. Together, these four pillars provide complete visibility into system behavior, from high-level service health down to individual function execution times. We will explore each pillar, understand when to use which signal type, and implement practical instrumentation using OpenTelemetry and the Grafana stack.

<!-- DIAGRAM: The four pillars of observability showing Metrics (aggregated numbers over time), Logs (discrete timestamped events), Traces (request flow across services), and Profiling (code-level execution analysis) with arrows showing how trace_id correlates logs and traces -->

![The Four Pillars of Observability](../assets/ch03-four-pillars.html)

## Key Concepts

### The Four Pillars of Observability

Observability differs from traditional monitoring in a fundamental way: monitoring tells us *when* something is wrong, while observability helps us understand *why*. The Google SRE team formalized this distinction in their Site Reliability Engineering book, establishing patterns that have become industry standard [Source: Google SRE Book, 2016].

**Metrics** are numeric measurements aggregated over time. They answer questions like "what is our p95 latency?" or "how many requests per second are we handling?" Metrics excel at showing trends, triggering alerts, and providing dashboard visualizations. However, they lose individual request details through aggregation.

**Logs** are discrete, timestamped events that capture what happened at a specific moment. They provide rich context for debugging but can be expensive to store at high volumes. Structured logging with consistent fields transforms logs from human-readable text into queryable data.

**Traces** follow a single request as it traverses multiple services. Each operation becomes a "span" with timing information, and spans connect to form a complete picture of request flow. Traces excel at identifying which service or operation causes latency in distributed systems.

**Profiling** captures code-level execution details: which functions consume CPU time, where memory allocations occur, and how call stacks nest. Continuous profiling in production reveals optimization opportunities that synthetic benchmarks miss. We cover profiling in depth later in this chapter.

### When to Use Which Pillar

Each pillar serves distinct purposes. Understanding their strengths prevents both gaps in visibility and redundant instrumentation:

| Signal | Best For | Limitations |
|--------|----------|-------------|
| Metrics | Alerting, dashboards, trend analysis | Loses individual request details |
| Logs | Debugging, audit trails, error context | High storage costs at scale |
| Traces | Request flow analysis, latency breakdown | Sampling may miss rare events |
| Profiling | Code optimization, hotspot identification | Overhead concerns at high frequency |

### Distributed Tracing Concepts

Distributed tracing originated at Google with their Dapper system, described in the foundational 2010 paper [Source: Sigelman et al., "Dapper, a Large-Scale Distributed Systems Tracing Infrastructure", 2010]. The concepts introduced (traces, spans, and context propagation) remain the foundation of modern tracing systems.

A **trace** represents the complete journey of a single request through your system. Each trace has a unique identifier (trace ID) that follows the request across service boundaries.

A **span** represents a single unit of work within a trace. Spans have:
- A span ID (unique within the trace)
- A parent span ID (linking to the calling operation)
- Start and end timestamps
- Attributes (key-value pairs with context)
- Status (success, error, etc.)

**Context propagation** ensures trace information travels with requests. When Service A calls Service B, the trace ID and parent span ID must transfer via HTTP headers, message metadata, or similar mechanisms. OpenTelemetry standardizes this propagation through the W3C Trace Context specification.

The propagation logic follows this pattern:

```
on outgoing request:
    trace_id = current trace ID (or generate new if none exists)
    span_id = generate new unique span ID
    add headers: traceparent = trace_id + span_id
    record span start time and operation name

    make the outbound request

    record span end time, status code, and any error info
```

<!-- DIAGRAM: Distributed trace waterfall view showing a request spanning 4 services: API Gateway (50ms total) -> User Service (30ms) -> Auth Service (15ms) -> Database (10ms), with parent-child span relationships and timing breakdown -->

![Distributed Trace Waterfall View](../assets/ch03-trace-waterfall.html)

**How Spans Become Traces**

Each service in your system independently sends its spans to the trace backend (Tempo, Jaeger, or similar). Services do not communicate with each other about tracing. They simply emit their spans as they complete work.

The trace backend assembles complete traces from these independent span submissions. When the API Gateway processes a request, it creates a span and sends it to Tempo. When the User Service handles its portion, it creates its own span (with the same trace ID) and also sends it to Tempo. The backend uses the shared trace_id to group spans together, and the parent_span_id to reconstruct the tree structure.

This architecture means spans arrive at the backend out of order. The database query span might arrive before the API Gateway span that initiated the request. The backend buffers incoming spans briefly (typically 30-60 seconds) before assembling them into a viewable trace. This buffering window explains why traces are not visible immediately after a request completes.

![Example Distributed Trace](../assets/ch03-example-trace.html)

**Clock Synchronization**

Since each service timestamps its own spans, clock drift between servers can produce confusing traces where child spans appear to start before their parents. NTP (Network Time Protocol) synchronization across your infrastructure is essential for accurate trace visualization. In Kubernetes environments, all pods typically share the host's clock, minimizing this issue.

**Sampling Strategies and Trade-offs**

Tracing every request at scale is prohibitively expensive. A service handling 10,000 requests per second generates 864 million traces per day. At $0.01 per thousand traces (typical managed pricing), that costs $8,640 daily just for storage. Sampling makes distributed tracing economically viable, but the choice of sampling strategy affects what you can learn.

**Head-Based Sampling** decides at request entry whether to trace. The first service (typically the API gateway) makes a probabilistic decision: 10% sample rate means 10% of traces are captured. This decision propagates downstream via trace context headers. All participating services either trace or don't trace a request together.

Head-based sampling is simple and predictable. You know exactly what percentage of traffic you're capturing. The limitation: interesting requests (errors, slow responses) are sampled at the same rate as boring ones. With 10% sampling, you capture only 10% of errors, potentially missing rare but important failure modes.

**Tail-Based Sampling** delays the sampling decision until the request completes. The OpenTelemetry Collector buffers all spans for a brief window (typically 30-60 seconds), then evaluates rules to decide which traces to keep. Common rules include:

- Keep 100% of traces with errors (any span with error status)
- Keep 100% of traces exceeding latency thresholds (p99 outliers)
- Keep 5% of successful, normal-latency traces
- Keep 100% of traces matching specific attributes (specific endpoints, user IDs)

Tail-based sampling requires buffering at the collector layer, which increases memory usage and operational complexity. The collector must see all spans before making decisions, so it becomes a bottleneck if undersized. However, the ability to capture all errors and latency outliers often justifies the complexity.

**Adaptive Sampling** adjusts rates based on traffic volume. During normal traffic, sample at 10%. During traffic spikes, reduce to 1% to prevent collector overload. This maintains cost control while preserving debug capability during typical operation. The OpenTelemetry Collector supports probabilistic sampling with rate limiting to implement adaptive behavior.

**Cost Implications**

| Strategy | Storage Cost | Error Coverage | Complexity |
|----------|--------------|----------------|------------|
| Head 10% | Predictable | 10% of errors | Simple |
| Head 1% | Very low | 1% of errors | Simple |
| Tail-based | Higher (buffering) | 100% of errors | Complex |
| Adaptive | Variable | Varies | Moderate |

For most API optimization work, tail-based sampling with 100% error capture provides the best debugging capability. Accept the operational complexity of running the collector with adequate resources. The ability to investigate every error is worth the investment.

### Correlating Signals Across Pillars

The four pillars are not independent tools - they form a connected system. The key to effective observability is moving fluidly between pillars during investigation, using each signal type for what it does best. This correlation is enabled by a universal identifier: the **trace ID**.

![Correlating Signals Across Pillars](../assets/ch03-pillar-correlation.html)

#### The Trace ID as Universal Correlator

Every request entering your system should receive a trace ID that follows it everywhere: through service calls, into log statements, attached to metrics as exemplars, and associated with profiling data. This single identifier is the thread that connects all your observability data.

```
on request entry at API gateway:
    trace_id = extract from incoming headers OR generate new

    // Trace: automatically attached to all spans
    start_span(trace_id, "api-gateway")

    // Logs: explicitly include in every log entry
    log.info("Request received", trace_id=trace_id, path=request.path)

    // Metrics: attach as exemplar for drill-down
    request_counter.increment(labels={endpoint: path}, exemplar={trace_id: trace_id})

    // Profiling: tag profiling samples with trace context
    profiler.tag_current_execution(trace_id=trace_id)
```

Without consistent trace ID propagation, you have four separate data silos. With it, you can navigate seamlessly between pillars.

#### Metric to Trace: Finding the Needles

Metrics tell you something is wrong; traces tell you why. When a metric alert fires (p95 latency exceeded, error rate spiked), you need to find representative traces from that time window.

**Exemplars** bridge this gap. An exemplar is a trace ID attached to a specific metric observation. When you record a histogram bucket for a 2-second response, you also record which trace ID produced that measurement. Later, clicking on that histogram spike in Grafana can jump directly to a trace that contributed to it.

```
// When recording latency metric, attach the trace as an exemplar
latency_histogram.observe(
    value=response_time_ms,
    labels={endpoint: "/api/orders", status: 200},
    exemplar={trace_id: current_trace_id()}
)
```

Without exemplars, you query traces by time window and hope to find a slow one:

```
// Tempo query: find slow traces in the last hour
{ duration > 2s } | select(traceid, duration, name)
```

With exemplars, you click the metric spike and land directly on a problematic trace.

#### Trace to Logs: Getting the Details

Traces show the shape of a request - which services were called, how long each took, where errors occurred. Logs provide the details: the actual error message, the query that was executed, the decision that was made.

When examining a trace in Tempo or Jaeger, you identify a slow or errored span. The next step is pulling logs for that specific request:

```
// Loki query: all logs for a specific trace
{service="checkout-service"} | json | trace_id="abc123def456"

// Or across all services
{} | json | trace_id="abc123def456"
```

This query returns every log entry generated during that request's execution, across all services, in chronological order. You see the complete story: what was attempted, what failed, what the error details were.

For this to work, every log statement must include the trace ID. Most OpenTelemetry SDKs provide automatic trace context injection into logging frameworks. If not, add it explicitly:

```
// Manual trace context injection
log.error("Payment failed",
    trace_id=current_span().trace_id,
    span_id=current_span().span_id,
    error=exception.message,
    payment_provider="stripe",
    amount_cents=order.total)
```

#### Trace to Profile: Finding the Hot Code

When a trace shows a span that took 500ms but you cannot see why from the span attributes alone, profiling reveals what code was executing during that time.

Continuous profiling tools like Pyroscope can correlate profiling samples with trace spans. You click a slow span and see a flame graph of exactly what code was running during that span's execution. This pinpoints whether the time was spent in your code, a library, garbage collection, or waiting for I/O.

The correlation requires two things:
1. **Continuous profiling running in production** - sampling CPU, memory, or allocations constantly
2. **Span-to-profile linking** - associating profiling samples with the trace context active when they were taken

Not all profiling setups support this correlation. Pyroscope with OpenTelemetry integration enables it. When available, this capability transforms debugging: instead of staring at a slow span wondering what it was doing, you see the actual call stack.

#### Logs and Metrics to Profile: Identifying Hot Paths

Beyond individual request investigation, you can use aggregate signals to identify code worth profiling. If metrics show CPU saturation, continuous profiling reveals which functions consume the most CPU across all requests. If logs show frequent garbage collection pauses, allocation profiling shows which code paths create the most objects.

This is a different correlation pattern - not following a single trace, but using aggregate signals to guide optimization efforts. Profiling answers "what code is responsible for this resource consumption?" which metrics and logs cannot answer.

#### The Investigation Workflow

A typical investigation flows through the pillars:

1. **Alert fires** (metrics): p95 latency exceeded SLO for `/api/checkout`
2. **Find affected traces** (metrics → traces): Use exemplars or time-window query to find slow checkout requests
3. **Identify slow span** (traces): Trace waterfall shows payment service span taking 2 seconds
4. **Get error details** (traces → logs): Query logs by trace ID, find "connection timeout to payment provider"
5. **Check if systemic** (logs → metrics): Query payment service error rate, see it spiked at same time
6. **Find root cause** (metrics): Payment provider status page confirms outage

Or for a performance optimization:

1. **Dashboard shows high CPU** (metrics): Service running at 80% CPU
2. **Examine profiles** (metrics → profiling): Flame graph shows 40% of CPU in JSON serialization
3. **Find affected endpoints** (profiling → traces): Trace the hot functions to specific API endpoints
4. **Verify with metrics** (traces → metrics): Those endpoints have highest request volume
5. **Optimize and validate** (profiling): After fix, flame graph shows JSON serialization dropped to 5%

#### Tooling Integration

Modern observability platforms automate much of this correlation. In Grafana:

- Clicking a metric data point with an exemplar opens the linked trace in Tempo
- Trace view includes a "Logs" tab showing Loki results filtered by trace ID
- Pyroscope integration shows flame graphs for individual spans
- Shared time selectors keep all panels synchronized

The key is ensuring your instrumentation produces the connected data. Automatic correlation in the UI only works when trace IDs flow through all your telemetry.

#### How Trace Context Reaches Your Logs

A common question: when you write `logger.info("Processing order")`, how does the trace ID get attached? The answer involves context propagation, a mechanism that makes the current trace available throughout your code without passing it explicitly.

OpenTelemetry stores the active span in thread-local storage (or language-specific equivalents like Python's `contextvars` or Go's `context.Context`). When your code executes within a traced request, the current span is always accessible:

```
// The trace context is available anywhere in your request handling code
from opentelemetry import trace

def process_order(order):
    current_span = trace.get_current_span()
    span_context = current_span.get_span_context()

    // These IDs are what you need for correlation
    trace_id = format(span_context.trace_id, '032x')
    span_id = format(span_context.span_id, '016x')

    logger.info("Processing order",
        extra={"trace_id": trace_id, "span_id": span_id, "order_id": order.id})
```

This works because the OpenTelemetry SDK automatically manages context. When middleware creates a span for an incoming request, that span becomes "current" for all code executing in that request's thread or async context. You never pass the span explicitly; you retrieve it when needed.

**Automatic injection** eliminates even this manual step. OpenTelemetry provides logging integrations that automatically add trace fields to every log record:

```
// Python: one-time setup injects trace context into all logs
from opentelemetry.instrumentation.logging import LoggingInstrumentor
LoggingInstrumentor().instrument()

// Now every logger.info() automatically includes trace_id and span_id
logger.info("Processing order")  // trace fields added automatically
```

```
// Java: configure logback/log4j to read from MDC
// OpenTelemetry auto-instrumentation populates MDC automatically
// logback.xml pattern:
%d{HH:mm:ss} [%thread] %-5level %logger - trace_id=%X{trace_id} - %msg%n
```

The pattern is consistent across languages: OpenTelemetry manages context, and logging integrations read from that context automatically. Once configured, every log statement includes trace correlation without code changes.

#### Correlating Metrics with Traces

Metrics and traces serve different purposes: metrics show aggregate behavior over time, while traces show individual request flow. Correlating them answers questions like "which specific requests contributed to this latency spike?"

**Exemplars** bridge this gap. An exemplar is a specific trace ID attached to a metric data point, providing a concrete example of what that metric measured:

```
// When recording a histogram observation, attach an exemplar
histogram.record(
    latency_ms,
    attributes={"endpoint": "/api/checkout"},
    exemplar={"trace_id": current_trace_id}  // links this data point to a trace
)
```

In Prometheus/Grafana, clicking a histogram bucket shows exemplars as dots. Clicking a dot opens the linked trace, letting you investigate a specific slow request that contributed to elevated p99 latency.

**Instance-level correlation** works differently. Traces include attributes identifying where they executed (host, pod, region). To see resource metrics for a traced request:

1. Find the trace and note its `service.instance.id` or `host.name` attribute
2. Query metrics filtered to that instance and the trace's time window
3. Examine CPU, memory, and other resource metrics for that specific instance during that request

This is inherently approximate. A trace shows a request took 500ms on instance `pod-abc`. The instance's CPU metric shows 80% utilization during that second. You cannot prove causation, but the correlation guides investigation.

```
// Grafana query: CPU for the instance that handled a slow trace
rate(process_cpu_seconds_total{instance="pod-abc"}[1m])
// Time range: the 30 seconds around when the trace occurred
```

The key insight: **traces identify WHERE to look; metrics show WHAT was happening there**. You cannot attach a trace ID to a CPU metric (metrics aggregate across all requests), but you can use trace attributes to narrow metrics to the relevant instance and time window.

#### Finding Root Causes Across Traces

Following one exemplar to one trace tells you what happened to a single request. But the more powerful question is: "across all slow requests, which attributes correlate with slowness?" If every slow trace hit the same database replica or ran on the same host, that pattern points to root cause — but you will not find it by inspecting traces one at a time.

**Trace analytics** tools let you query across traces the way you would query a database. Instead of examining individual traces, you ask aggregate questions:

```
// Honeycomb-style query: group slow traces by replica
WHERE duration_ms > 2000
GROUP BY db.replica
CALCULATE count, avg(duration_ms)
```

This might reveal that `db-read-3` accounts for 80% of slow traces while handling only 20% of total traffic. Some tools go further: Honeycomb's BubbleUp automatically compares slow traces against fast traces and highlights which attributes differ between the two populations. You select the latency spike on a chart, and it surfaces that `db.replica=read-3` and `host.az=us-east-1c` are overrepresented in the slow group.

This approach depends on rich span attributes. The more context you attach to spans (replica ID, availability zone, feature flags, customer tier), the more dimensions you can slice across when investigating. Chapter 6 revisits this in the context of database performance, where identifying a hot replica or slow query pattern across traces is a common debugging workflow.

**Trace-derived metrics** offer a complementary approach. Instead of querying raw traces at investigation time, you configure your collector to generate metrics from span attributes as traces flow through:

```
// OpenTelemetry Collector: generate a histogram from span data
connectors:
  spanmetrics:
    dimensions:
      - name: db.replica
      - name: host.name
    histogram:
      explicit:
        buckets: [100, 250, 500, 1000, 2500]
```

This produces a standard latency histogram broken down by `db.replica` and `host.name`, queryable in Prometheus or Grafana without touching the trace store. You see replica-level latency distributions directly in dashboards, and anomalies surface through normal metric alerting rather than requiring ad hoc trace investigation.

The tradeoff is flexibility: trace-derived metrics only include dimensions you configured in advance, while trace analytics tools let you slice by any attribute after the fact. Teams often use both — trace-derived metrics for known-important dimensions in dashboards, and trace analytics for exploratory investigation when something unexpected happens.

### Practical Logging Strategies

Logs are deceptively simple. Unlike metrics that require understanding aggregation semantics or traces that demand distributed context propagation, logs appear straightforward: something happens, write it down. This apparent simplicity leads teams to either log too little (missing critical debugging context) or log too much (drowning in noise and storage costs). Effective logging requires deliberate strategy.

#### Log Levels and Their Purpose

Most logging frameworks provide a hierarchy of severity levels. Understanding when to use each level ensures logs remain useful without overwhelming operators:

| Level | Purpose | Example Use Cases | Production Default |
|-------|---------|-------------------|-------------------|
| FATAL | Unrecoverable errors requiring immediate attention | Database connection permanently lost, out of memory, configuration prevents startup | Always enabled |
| ERROR | Failures requiring attention but service continues | Payment processor timeout, invalid authentication token, external API unavailable | Always enabled |
| WARN | Anomalies that may indicate developing problems | Retry succeeded after failure, cache miss rate elevated, deprecated API usage | Always enabled |
| INFO | Normal operational events worth recording | Request completed, service started, configuration loaded, job finished | Usually enabled |
| DEBUG | Detailed diagnostic information for troubleshooting | Query parameters, cache keys, method entry/exit, decision branch taken | Disabled by default |
| TRACE | Extremely detailed execution flow | Every function call, full request/response bodies, internal state dumps | Rarely enabled |

The guiding principle: every log statement should earn its place. ERROR and above indicate problems requiring human attention. WARN signals conditions that may become problems. INFO documents significant events in normal operation. DEBUG and TRACE exist for troubleshooting specific issues.

A common mistake is logging routine events at INFO level. "User logged in" at INFO generates enormous volume for popular services with no actionable insight. Reserve INFO for events worth reviewing during normal operations: service startup, configuration changes, significant state transitions.

#### Structured Logging

Unstructured logs like `User 12345 purchased item ABC for $99.00` require text parsing to analyze. Structured logging transforms logs into queryable data:

```
{
  "timestamp": "2024-01-15T10:23:45.123Z",
  "level": "INFO",
  "message": "Purchase completed",
  "trace_id": "abc123def456",
  "span_id": "789xyz",
  "user_id": "12345",
  "item_id": "ABC",
  "amount_cents": 9900,
  "currency": "USD",
  "service": "checkout-service",
  "environment": "production"
}
```

This structure enables queries like "show all purchases over $50 from user 12345 in the last hour" without regex gymnastics. Consistent field naming across services allows cross-service queries and automated analysis.

The `trace_id` field is particularly important. Including the distributed trace ID in every log entry enables jumping from a slow trace directly to all logs generated during that request, bridging the logs and traces pillars.

#### Dynamic Log Level Configuration

The tension with log levels: DEBUG logs provide essential troubleshooting context but generate prohibitive volume if always enabled. The solution is dynamic configuration that allows runtime adjustment without redeployment.

Configuration sources, checked in precedence order:

```
on determining effective log level:
    if per_request_debug_header present AND debug_headers_enabled:
        return DEBUG
    if runtime_config.log_level is set:
        return runtime_config.log_level
    if environment_variable LOG_LEVEL is set:
        return environment_variable value
    return default_level from code
```

Each source serves different needs:

- **Environment variables**: Set at deployment, require restart to change. Simple and secure, suitable for baseline configuration.
- **Configuration file with watching**: External file reloaded periodically or on change signal. Allows level changes without restart but requires file system access.
- **Runtime API endpoint**: Immediate changes via authenticated API call. Useful for incident response when minutes matter.
- **Feature flag service**: Per-request or per-user granularity via external service. Most flexible but adds dependency and latency.

#### Selective Logging by Context

Global DEBUG logging is rarely what you need. More often, you want DEBUG logs for a specific problematic request, user, or endpoint while keeping production volume manageable.

```
on incoming request:
    effective_level = default_log_level

    if request.header["X-Debug-Level"] AND debug_headers_enabled:
        effective_level = DEBUG
    else if request.user_id in debug_user_list:
        effective_level = DEBUG
    else if request.path matches debug_endpoint_patterns:
        effective_level = DEBUG

    attach effective_level to request context

on log statement at level L:
    if L >= request_context.effective_level:
        emit log entry
```

This pattern enables support scenarios: "Customer X is experiencing issues, enable DEBUG logging for their requests." The debug_user_list can be stored in Redis or a configuration service, allowing runtime updates without deployment.

Caution: per-request header overrides create a security consideration. An attacker could send debug headers to trigger expensive logging or expose sensitive information. Either disable this feature entirely, require authentication, or limit it to internal networks.

#### Avoiding Debug Overhead

Even when DEBUG logging is disabled, careless implementation can impact performance:

```
// Anti-pattern: string formatting executes even when DEBUG is disabled
log.debug("User details: " + serialize_to_json(user_object))

// Better: check level before expensive operations
if log.is_debug_enabled():
    log.debug("User details: " + serialize_to_json(user_object))

// Best: logging framework handles lazy evaluation
log.debug("User details: {}", () => serialize_to_json(user_object))
```

The first example serializes the user object to JSON on every call, even if the DEBUG statement is ultimately discarded. For hot paths, this overhead accumulates. Modern logging frameworks support lazy evaluation where the message construction only occurs if the log level is enabled.

#### Log Sampling at High Volume

Some services generate such high request volume that even INFO-level logging becomes expensive. Log sampling reduces volume while maintaining statistical visibility:

```
sample_rate = 0.1  // log 10% of requests

on log statement at level L with request context:
    if L >= WARN:
        emit log entry  // never sample errors or warnings
    else:
        hash = deterministic_hash(request.trace_id)
        if hash mod 100 < (sample_rate * 100):
            emit log entry
```

Using `trace_id` for sampling ensures consistency: either all logs for a request are sampled or none are. Random per-statement sampling would create incomplete request traces, making debugging impossible.

Adaptive sampling adjusts rates based on current conditions. During normal operation, sample aggressively. When error rates increase, reduce sampling to capture more context around failures.

#### Configuration Approach Trade-offs

| Approach | Restart Required | Granularity | Security Risk | Complexity |
|----------|-----------------|-------------|---------------|------------|
| Environment variables | Yes | Global | Low | Minimal |
| Config file watching | No | Global | Low | Low |
| Admin API | No | Per-instance | Medium | Moderate |
| Feature flags | No | Per-request | Medium | Higher |
| Request header override | No | Per-request | High | Low |

Most production systems benefit from layered configuration: environment variables for baseline levels, feature flags for temporary per-user debugging, and an admin API for incident response.

### Continuous Profiling in Practice

Profiling captures what code is actually executing—which functions consume CPU time, where memory allocations occur, and how call stacks nest. While metrics tell you *that* CPU is high and traces tell you *which request* is slow, profiling tells you *what code* is responsible.

#### Flame Graphs

Flame graphs provide the standard visualization for profiling data. Each horizontal bar represents a function in the call stack, with wider bars indicating more time spent in that function. The vertical axis shows call depth: functions at the bottom called functions stacked above them.

![CPU Flame Graph Example](../assets/ch03-flame-graph.html)

Reading a flame graph:
- **Width matters**: Look for wide bars—these are where time is spent
- **Plateaus indicate hotspots**: A wide bar with no children means that function itself is doing the work
- **Narrow towers are fine**: Deep call stacks with narrow bars indicate little time spent at each level
- **Compare before/after**: Flame graphs are most useful when comparing optimized vs. unoptimized versions

#### Profiling Blind Spots

Profilers do not capture everything. Understanding what profilers miss prevents misguided optimization:

- **I/O wait time**: CPU profilers measure time spent executing code, not time waiting for I/O. A function that blocks for 500ms on a network call may appear fast in a CPU profile because the CPU was idle during the wait. For I/O-bound services, CPU profiles show little. Use tracing to measure actual wall-clock time.

- **Lock contention**: Time spent waiting to acquire locks does not always appear clearly in CPU profiles. The thread is blocked, not executing, so the profiler may not attribute time to the contended code path. Specialized lock contention profilers or off-CPU profilers are needed for lock analysis.

- **Garbage collection overhead**: GC pauses stop application threads, but this pause time may not be clearly attributed in application profiles. GC logs and runtime metrics reveal pause duration and frequency that CPU profiles may miss.

- **Kernel and system calls**: User-space profilers only see user-space execution. Time spent in kernel syscalls (especially slow ones like synchronous disk I/O) may be underreported. `perf` on Linux captures both user and kernel stacks but requires additional privileges.

- **Sampling bias**: Statistical profilers sample call stacks periodically (typically 100-1000 Hz). Short, fast functions that complete between samples may be underrepresented. Extremely hot spots are captured accurately; moderately warm paths may be missed.

For complete performance visibility, combine CPU profiling (what code is executing), tracing (what requests are doing end-to-end), and wall-clock analysis (total elapsed time). Each tool reveals blind spots in the others.

#### Continuous Profiling vs. Ad-Hoc Profiling

Traditional profiling is ad-hoc: attach a profiler during debugging, capture samples, detach. This misses production-only behavior—the hot paths that only appear under real load with real data.

Continuous profiling runs always-on in production at low overhead (typically 1-2% CPU). Tools like Pyroscope, Datadog Continuous Profiler, or Google Cloud Profiler sample constantly, building a historical record of where CPU time goes. When metrics show CPU saturation, you query the profiler for that time window and see exactly what code was responsible.

The combination of continuous profiling with trace correlation (covered in "Correlating Signals Across Pillars") enables a powerful workflow: click a slow span in a trace, see the flame graph of exactly what code executed during that span.

### OpenTelemetry: The Industry Standard

OpenTelemetry has emerged as the vendor-neutral standard for observability instrumentation. Formed from the merger of OpenTracing and OpenCensus projects, it provides APIs, SDKs, and conventions for generating telemetry data. The CNCF (Cloud Native Computing Foundation) graduated OpenTelemetry, signifying its maturity and broad adoption [Source: CNCF, 2021].

OpenTelemetry provides:
- **APIs** for instrumenting application code
- **SDKs** implementing those APIs for specific languages
- **Automatic instrumentation** for common frameworks and libraries
- **The Collector** for receiving, processing, and exporting telemetry
- **Semantic conventions** ensuring consistent attribute naming

The Collector deserves special attention. Rather than sending telemetry directly from applications to backends, the Collector acts as an intermediary that can:
- Aggregate data from multiple applications
- Transform or filter telemetry
- Export to multiple backends simultaneously
- Handle backpressure and buffering

<!-- DIAGRAM: OpenTelemetry architecture: Applications (with SDKs) -> OpenTelemetry Collector (processors, exporters) -> Multiple backends (Prometheus, Grafana Tempo, Loki, Jaeger) -->

![OpenTelemetry Architecture](../assets/ch03-otel-architecture.html)

**SDK Configuration for Performance**

OpenTelemetry SDKs, while lightweight, do consume resources. Misconfigured SDKs can add measurable latency or cause memory issues under load. Key configuration parameters affect this trade-off:

**Batch sizes** control how many spans or metrics are buffered before export. Small batches (10-50 items) provide low latency but high export overhead. Large batches (5000+ items) reduce overhead but delay telemetry visibility and consume more memory. Default batch sizes (typically 512 spans) work for most applications. Increase batch size for high-throughput services; decrease for low-latency requirements where immediate visibility matters.

**Export timeouts** determine how long the SDK waits for the collector to accept data. Short timeouts (1-5 seconds) fail fast but may drop data during collector hiccups. Long timeouts (30+ seconds) increase reliability but can cause memory pressure if the collector is unreachable and spans accumulate. A 10-second timeout with appropriate retry logic balances these concerns.

**Queue sizes** limit buffered telemetry when export is slow. When the queue fills, the SDK must either drop new telemetry or block the application. Blocking adds latency; dropping loses data. Configure queue sizes based on your tolerance: larger queues (10,000+ items) for reliability-focused systems, smaller queues (500-1000 items) for latency-focused systems with drop-on-overflow.

**Resource attributes** identify your application in telemetry. Always set `service.name`, `service.version`, and `deployment.environment`. These enable filtering in dashboards and alerts. Missing resource attributes make traces nearly impossible to analyze at scale.

**Common SDK pitfalls to avoid:**

- **Synchronous export**: Always use asynchronous exporters. Synchronous export blocks request processing while waiting for the collector, adding latency to every traced request.
- **Excessive span creation**: Creating hundreds of spans per request overwhelms collectors and makes traces unreadable. Aim for 10-50 spans per typical request, covering meaningful operations rather than every function call.
- **Missing span status**: Always set span status to ERROR on failures. This enables tail-based sampling to capture errors and makes error traces identifiable in the UI.

### Choosing an Observability Stack

OpenTelemetry provides vendor-neutral instrumentation, but you still need backends to store and visualize telemetry. The observability market offers many options, from fully managed platforms to self-hosted open-source solutions.

**Commercial Platforms**

Fully managed observability platforms handle infrastructure complexity at the cost of per-seat or per-volume pricing:

- **Datadog**: Comprehensive platform with strong APM, infrastructure monitoring, and log management. Known for ease of setup and extensive integrations.
- **New Relic**: Full-stack observability with AI-assisted anomaly detection. Offers a generous free tier.
- **Dynatrace**: AI-driven platform popular in enterprise environments. Excels at automatic discovery and root cause analysis.
- **Splunk**: Originally a log analysis tool, now offers full observability. Strong in security and compliance use cases.
- **Honeycomb**: Designed around high-cardinality trace analysis. Excellent for debugging complex distributed systems.

**Open-Source Stacks**

For organizations preferring self-hosted solutions or avoiding vendor lock-in:

- **Grafana Stack** (Grafana, Prometheus, Loki, Tempo, Pyroscope): Comprehensive and tightly integrated. We use this throughout the book.
- **Jaeger**: CNCF project for distributed tracing. Lightweight and Kubernetes-native.
- **Zipkin**: One of the original distributed tracing systems, still widely used.
- **Elasticsearch/Kibana (ELK Stack)**: Powerful log aggregation and search. Often combined with Beats for metrics.
- **InfluxDB/Telegraf**: Time-series database with strong metrics capabilities.
- **VictoriaMetrics**: Prometheus-compatible metrics backend with better resource efficiency.

**Cloud Provider Options**

Major cloud providers offer integrated observability:

- **AWS**: CloudWatch for metrics and logs, X-Ray for tracing
- **Google Cloud**: Cloud Monitoring, Cloud Logging, Cloud Trace
- **Azure**: Azure Monitor, Application Insights, Log Analytics

The key insight is that OpenTelemetry decouples instrumentation from backends. Instrument your code once with OpenTelemetry, and you can export to any supported backend or switch backends later without changing application code.

### The Grafana Stack

Grafana Labs has assembled a comprehensive observability stack:

- **Grafana**: Visualization and dashboarding, serving as the central interface for exploring all telemetry types
- **Prometheus/Mimir**: Metrics storage and querying using PromQL. Prometheus stores metrics on local disk; Mimir extends it with horizontally-scalable, multi-tenant storage backed by object storage. Both use the same query language, and Mimir is wire-compatible with Prometheus, so the rest of the stack treats them interchangeably
- **Loki**: Log aggregation and querying using LogQL, designed for cost-effective storage
- **Tempo**: Distributed trace storage with no indexing required
- **Pyroscope**: Continuous profiling with flame graph visualization

Tempo, Loki, Mimir, and Pyroscope all store data to object storage (S3, GCS, or Azure Blob) for long-term retention. This matters for optimization work: object storage is cheap enough to retain months of telemetry history, which lets you compare performance across releases, track gradual degradation, and revisit traces from incidents long after they occurred. Prometheus stores to local disk by default, but Mimir extends it with horizontally-scalable object storage. Grafana queries all four backends and serves as the single interface for exploring metrics, traces, logs, and profiles together.

This stack offers both open-source deployment and managed cloud options (Grafana Cloud). The tight integration between components enables seamless correlation: clicking a trace in Tempo can jump to related logs in Loki and metrics in Prometheus, all filtered by the same trace ID.

### How Telemetry Flows Through the System

Understanding the data flow from application to dashboard helps with debugging and capacity planning.

![Telemetry Data Flow](../assets/ch03-data-flow.html)

The flow follows this pattern:

1. **Instrumentation**: Application code generates telemetry via OpenTelemetry SDKs. Automatic instrumentation captures HTTP requests, database calls, and framework operations. Manual instrumentation adds business-specific spans and metrics.

2. **Collection**: The OpenTelemetry Collector receives telemetry over OTLP (OpenTelemetry Protocol). It batches, filters, and transforms data before export. Running the Collector as a sidecar or daemon reduces application resource usage.

3. **Processing**: The Collector's processor pipeline handles sampling, attribute enrichment, and data transformation. Tail-based sampling happens here, capturing all error traces regardless of sample rate.

4. **Storage**: Backends store each signal type: Prometheus/Mimir for metrics, Loki for logs, Tempo for traces, Pyroscope for profiles. Each backend optimizes for its data type's query patterns.

5. **Visualization**: Grafana queries all backends and correlates signals. A dashboard panel showing high latency can link to traces from that time window, which link to relevant logs.

### Building Effective Dashboards

Dashboards should answer questions, not just display data. The Google SRE book recommends organizing dashboards around the **Four Golden Signals**: latency, traffic, errors, and saturation [Source: Google SRE Book, 2016].

For API services, this translates to:
- **Latency**: p50, p95, p99 response times; breakdown by endpoint
- **Traffic**: Requests per second; breakdown by endpoint and status code
- **Errors**: Error rate as percentage; breakdown by error type
- **Saturation**: CPU usage, memory usage, connection pool utilization, queue depth

Brendan Gregg's **USE Method** (Utilization, Saturation, Errors) complements the Golden Signals for infrastructure resources [Source: Brendan Gregg, "The USE Method", 2012]. Apply USE to each resource: CPU, memory, network, disk.

The **RED Method** (Rate, Errors, Duration) simplifies service-level monitoring [Source: Tom Wilkie, "The RED Method", 2018]. RED focuses on what users experience rather than internal resources.

Effective dashboards have:
- Clear hierarchy (overview -> detail drilldown)
- Appropriate time ranges (last hour for incidents, last week for trends)
- Meaningful thresholds with visual indicators
- Correlation aids (shared time selectors, trace links)

![Example Golden Signals Dashboard](../assets/ch03-golden-signals-dashboard.html)

### Instrumenting Your Stack

Observability requires instrumentation at every layer. Application code is only part of the picture. Databases, caches, message queues, and infrastructure all generate valuable telemetry.

**Automatic vs. Manual Instrumentation**

OpenTelemetry's automatic instrumentation captures common operations without code changes. For Node.js, the `@opentelemetry/auto-instrumentations-node` package automatically traces HTTP requests, database queries, and framework operations. Python's `opentelemetry-instrumentation` provides similar coverage. Rust and Go require more explicit setup but have mature instrumentation libraries.

Automatic instrumentation covers the common cases. Manual instrumentation adds visibility into business-specific operations: "user completed checkout," "recommendation algorithm ran," or "payment processor responded." These custom spans provide context that automatic instrumentation cannot infer.

**Instrumenting Databases**

Databases require instrumentation both from the application side (query tracing) and the database side (server metrics):

*Application-side*: OpenTelemetry database instrumentation libraries automatically trace queries. They capture the SQL statement (sanitized of parameters), execution time, and connection pool behavior. For Python with SQLAlchemy, `opentelemetry-instrumentation-sqlalchemy` handles this automatically.

*Database-side*: The database server itself exports metrics:
- PostgreSQL: Enable `pg_stat_statements` for query statistics. Export via `postgres_exporter` to Prometheus.
- MySQL: The slow query log captures queries exceeding a threshold. The Performance Schema provides detailed metrics.
- Redis: `redis_exporter` provides hit rates, memory usage, and command latencies.

Send database logs to Loki for correlation with traces. When a trace shows a slow database span, you can jump directly to the query log for that time window.

**Instrumenting Message Queues**

Message queues break trace continuity because the producer and consumer run asynchronously. OpenTelemetry provides mechanisms to propagate trace context through message headers:

- Kafka: The `opentelemetry-instrumentation-kafka-python` (Python) or similar packages inject trace context into message headers. Consumers extract this context to continue the trace.
- RabbitMQ: Use message properties to carry trace context.
- AWS SQS: Message attributes can carry trace context, though this requires manual propagation.

The key is ensuring the consumer creates a span that links to the producer's trace, so you can follow a request from API call through queue to eventual processing.

**Instrumenting Infrastructure**

Infrastructure telemetry comes from specialized exporters:

- **Node Exporter**: System-level metrics (CPU, memory, disk, network) for Linux hosts
- **cAdvisor**: Container-level metrics for Docker and Kubernetes
- **kube-state-metrics**: Kubernetes object state (pod counts, deployment status)
- **NGINX/Envoy exporters**: Proxy and load balancer metrics

These exporters expose Prometheus-format metrics that integrate directly with the observability stack. Correlating infrastructure metrics with application traces helps identify whether performance issues stem from code or resource constraints.

### Alert Design Principles

Alerts should be actionable. Every alert that fires should require human intervention; if an alert can be ignored or auto-resolves frequently, it should not page on-call engineers.

**Symptom-based alerting** focuses on user-visible impact: "p95 latency exceeds SLO" rather than "CPU usage above 80%". Users do not care about CPU usage; they care about slow responses. High CPU that does not affect latency should not wake anyone up.

**Alert fatigue** occurs when too many alerts fire, causing engineers to ignore or dismiss them reflexively. Combat alert fatigue through:
- Consolidating related alerts (one alert for "service degraded" rather than separate alerts for each symptom)
- Setting thresholds based on actual impact, not arbitrary percentages
- Using severity levels appropriately (page for user impact, ticket for investigation items)
- Regularly reviewing and pruning alert rules

Multi-window, multi-burn-rate alerts provide sophisticated SLO monitoring. Rather than alerting on instantaneous threshold violations, these alerts fire when error budget consumption rate threatens the SLO over the compliance period. Google's SRE Workbook provides detailed guidance on this approach [Source: Google SRE Workbook, 2018].

Chapter 4 expands on alerting operations: routing and escalation procedures, runbook integration, and using incident patterns to drive optimization priorities.

### Case Study: Observability for an E-Commerce API

Consider a typical e-commerce backend: an API Gateway routes requests to Product, Order, and User services. PostgreSQL stores persistent data, Redis caches frequent queries, and Kafka handles async operations like order processing and email notifications.

**Setting Up the Stack**

Each service runs the OpenTelemetry SDK configured to export to a central Collector. The Collector runs as a DaemonSet in Kubernetes, receiving telemetry from all pods on each node. Its pipeline configuration routes traces to Tempo, metrics to Prometheus, and logs to Loki.

The key configuration decisions:
- Tail-based sampling in the Collector captures 100% of error traces and traces exceeding 500ms, with 10% sampling for normal traffic
- Service name and environment labels are injected at the Collector level, ensuring consistency
- OTLP/gRPC transport between services and Collector minimizes overhead

**Tracing a Checkout Request**

When a user completes checkout, the trace begins at the API Gateway. The gateway creates a root span and propagates context to the Order Service. The Order Service creates child spans for:
- Validating the cart (call to Product Service)
- Checking user payment methods (call to User Service)
- Writing the order to PostgreSQL
- Publishing an event to Kafka

Each downstream service creates its own spans. The Product Service span shows inventory check latency. The PostgreSQL span reveals query execution time. Even the Kafka producer span is visible, and when the async consumer processes the event minutes later, it links back to the original trace.

**Investigating a Latency Spike**

A dashboard alert fires: p95 checkout latency exceeded 2 seconds. The engineer opens Grafana, sees the latency spike in the Golden Signals panel, and clicks to explore traces from that window.

The trace view immediately reveals the problem: the PostgreSQL span for inventory check takes 1.8 seconds when it normally takes 50ms. Clicking the database span shows the query: a missing index on `product_id` in the inventory table. The database metrics panel confirms high query latency correlating with increased write load from a batch import job.

The fix is straightforward: add the missing index and schedule batch imports during low-traffic windows. Without observability, this investigation might have taken hours of guessing. With correlated traces and metrics, root cause identification took minutes.

## Common Pitfalls

- **High-cardinality metrics**: Adding unbounded labels (user IDs, request IDs) to metrics explodes storage and query costs. Use traces for request-level data; keep metrics aggregated.

- **Logging sensitive data**: Accidentally including passwords, tokens, or PII in logs creates security and compliance risks. Implement scrubbing at the logging framework level. Be especially careful with DEBUG-level logs that capture full request payloads.

- **Expensive operations in disabled log statements**: String formatting and object serialization execute even when the log level is disabled unless you use lazy evaluation. On hot paths, this overhead accumulates significantly.

- **Inconsistent log levels across services**: If Service A logs successful requests at INFO and Service B logs them at DEBUG, cross-service analysis becomes confused. Establish team conventions for what each level means.

- **Sampling too aggressively**: Very low sample rates (0.1%) may miss rare but important events. Use tail-based sampling or always-sample rules for errors and slow requests.

- **Alert threshold cargo-culting**: Copying thresholds like "80% CPU" from elsewhere without understanding your system's behavior leads to false alerts. Base thresholds on observed baseline behavior and SLO requirements.

- **Ignoring collection overhead**: Overly frequent metrics scraping, verbose logging, or high profiling sample rates can themselves cause performance problems. Measure the cost of measurement.

- **Missing trace context propagation**: Forgetting to propagate trace context across async boundaries, message queues, or non-HTTP protocols creates incomplete traces. Audit all service boundaries.

- **Dashboard sprawl**: Creating many one-off dashboards that become unmaintained leads to confusion about which dashboards are authoritative. Establish clear dashboard ownership and lifecycle management.

- **Alerting on symptoms without runbooks**: Alerts that fire without documented investigation steps lead to slower incident response. Every alert should link to a runbook.

## Summary

- Observability comprises four complementary pillars: metrics, logs, traces, and profiling. Each serves distinct purposes, and effective observability requires all four.

- OpenTelemetry provides vendor-neutral instrumentation that exports to multiple backends. Use the OpenTelemetry Collector as an intermediary for flexibility and reliability.

- Distributed tracing follows requests across service boundaries through trace context propagation. Spans capture timing and metadata for each operation in the request path.

- The Grafana stack (Prometheus/Mimir, Loki, Tempo, Pyroscope) provides comprehensive, integrated observability with powerful query languages and visualization.

- The Four Golden Signals (latency, traffic, errors, saturation) guide what to measure. The RED Method (Rate, Errors, Duration) and USE Method (Utilization, Saturation, Errors) provide complementary frameworks.

- Effective dashboards answer questions, not just display data. Organize around user-visible service health, not just infrastructure metrics.

- Symptom-based alerts focus on user impact. Combat alert fatigue through consolidation, meaningful thresholds, and severity discipline.

- Continuous profiling in production reveals optimization opportunities that synthetic benchmarks miss. Flame graphs visualize where code time is spent.

## References

1. **Google SRE Book** (2016). "Monitoring Distributed Systems." https://sre.google/sre-book/monitoring-distributed-systems/

2. **Sigelman, B. H., et al.** (2010). "Dapper, a Large-Scale Distributed Systems Tracing Infrastructure." Google Technical Report. https://research.google/pubs/pub36356/

3. **Google SRE Workbook** (2018). "Alerting on SLOs." https://sre.google/workbook/alerting-on-slos/

4. **Gregg, Brendan** (2012). "The USE Method." https://www.brendangregg.com/usemethod.html

5. **Wilkie, Tom** (2018). "The RED Method: How to Instrument Your Services." https://grafana.com/blog/2018/08/02/the-red-method-how-to-instrument-your-services/

6. **CNCF** (2021). "OpenTelemetry Graduates to CNCF Incubating Project." https://www.cncf.io/blog/2021/08/26/opentelemetry-becomes-a-cncf-incubating-project/

7. **OpenTelemetry Documentation**. "Getting Started." https://opentelemetry.io/docs/

8. **Grafana Labs Documentation**. "Grafana Tempo." https://grafana.com/docs/tempo/latest/

9. **W3C** (2021). "Trace Context Specification." https://www.w3.org/TR/trace-context/

10. **Datadog Documentation**. "APM & Distributed Tracing." https://docs.datadoghq.com/tracing/

11. **Honeycomb Documentation**. "Introduction to Observability." https://docs.honeycomb.io/getting-started/

## Next: [Chapter 4: Monitoring and Alerting](./04-monitoring.md)

With observability infrastructure in place, the next chapter covers how to build effective monitoring dashboards and alerting strategies that surface problems before users notice them.
