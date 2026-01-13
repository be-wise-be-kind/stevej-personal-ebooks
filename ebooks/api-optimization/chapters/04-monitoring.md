# Chapter 4: Monitoring - From Data to Action

![Chapter 4 Opener](../assets/ch04-opener.html)

\newpage

## Overview

Chapter 3 established the foundation: instrumenting our systems to emit traces, logs, metrics, and profiles. We now have observability, the capability to understand our system's internal state from its external outputs. But capability alone does not prevent outages, maintain SLOs, or wake engineers when latency degrades at 3 AM.

Monitoring is the operational practice of watching, alerting, and responding. It transforms raw telemetry into dashboards that answer questions, alerts that demand action, and runbooks that guide resolution. Where observability asks "can we understand what's happening?", monitoring asks "are we watching the right things, and will we know when something goes wrong?"

This distinction matters because teams often conflate the two. They instrument extensively, create beautiful dashboards, and still get blindsided by outages because no one was watching, or because alerts fired but were ignored. Effective monitoring requires not just data, but judgment about what matters, discipline about what deserves attention, and processes for responding when things break.

In this chapter, we cover the operational side of performance management: dashboard design that surfaces actionable insights, alerting strategies that page when necessary without causing fatigue, incident response practices that minimize user impact, and continuous validation that catches regressions before users do.

<!-- DIAGRAM: The monitoring feedback loop showing: Instrumentation (Chapter 3) -> Telemetry Data -> Dashboards & Alerts -> Human Response -> System Changes -> back to Instrumentation. Annotations: "Observability enables", "Monitoring acts" -->

## Key Concepts

### Observability vs Monitoring: The Crucial Distinction

Observability and monitoring serve different purposes and require different investments. Conflating them leads to gaps in both.

**Observability** is a property of your system. A system is observable if you can understand its internal state by examining its outputs. Good observability means you can answer novel questions about system behavior without deploying new code. When an unknown failure mode occurs, observability lets you investigate: "Why did latency spike for users in Brazil at 2:47 PM?"

**Monitoring** is a practice performed by humans and automated systems. Monitoring means actively watching key indicators, setting thresholds that trigger alerts, routing those alerts to responders, and following procedures when alerts fire. Monitoring answers: "Is the system healthy right now? Will someone know if it becomes unhealthy?"

You can have observability without monitoring: comprehensive instrumentation that no one watches. You can attempt monitoring without observability: alerts that fire but provide no diagnostic capability. Neither alone is sufficient. Effective operations require both: the capability to understand (observability) and the practice of watching and responding (monitoring) [Source: Charity Majors, "Observability vs Monitoring", 2018].

The practical implication: instrument broadly for observability (you never know what you'll need to investigate), but monitor narrowly and deliberately (every alert should demand action).

### Dashboard Design Principles

Dashboards fail when they display data without purpose. A wall of charts that no one understands does not improve operations. Effective dashboards answer specific questions for specific audiences.

**The Four Golden Signals as Foundation**

Every service dashboard should begin with the four golden signals from Chapter 2: latency, traffic, errors, and saturation. These provide the minimum viable view of service health.

- **Latency**: Show p50, p95, and p99 as separate lines. Display both successful requests and errors (which may have different latency characteristics). Include a time-series view and a heatmap for distribution visibility.
- **Traffic**: Requests per second, broken down by endpoint if cardinality permits. Show both total traffic and per-endpoint to identify which endpoints drive load.
- **Errors**: Error rate as a percentage, not absolute count. A service handling 1000 RPS with 10 errors/second (1%) differs from one handling 10 RPS with 10 errors/second (100%). Break down by error type (4xx vs 5xx, specific error codes).
- **Saturation**: CPU usage, memory usage, connection pool utilization, queue depths. Show both current values and trends.

<!-- DIAGRAM: Golden signals dashboard layout showing four quadrants: top-left Latency (line chart with p50/p95/p99), top-right Traffic (stacked area chart by endpoint), bottom-left Errors (line chart with percentage), bottom-right Saturation (multiple gauges for CPU, memory, connections) -->

**Layered Dashboard Hierarchy**

Dashboards should form a hierarchy from overview to detail:

1. **Service Overview**: One dashboard per service showing golden signals, SLO compliance, and recent deployments. This is the starting point for on-call investigation.
2. **Component Dashboards**: Deeper views for specific subsystems (database, cache, message queue). Linked from the overview dashboard.
3. **Instance Dashboards**: Individual host or container metrics. Used only when investigating specific instance problems.

Each level links to the next. An on-call engineer starts at overview, notices elevated latency, clicks through to the database component dashboard, identifies connection pool exhaustion, and drills to the specific instance causing problems.

**Avoiding Dashboard Sprawl**

Dashboard sprawl occurs when teams create dashboards without governance. Someone creates a dashboard for an investigation, never deletes it, and the catalog grows until no one knows which dashboards matter. Combat sprawl through:

- **Ownership**: Every dashboard has an owner responsible for its accuracy and relevance
- **Lifecycle**: Dashboards created for investigations should be marked temporary and deleted after resolution
- **Canonical dashboards**: Designate authoritative dashboards for each service; others are supplementary
- **Regular review**: Quarterly review to archive unused dashboards

**Actionable vs Vanity Metrics**

Vanity metrics make us feel good but do not drive action. Total users, lifetime requests, cumulative revenue: these may matter for business reporting but do not help on-call engineers. Dashboard space is limited; every chart should earn its place.

Ask of every dashboard element: "What action would someone take based on this?" If the answer is "none," the metric is informational at best, distracting at worst. Reserve dashboards for actionable metrics; put informational metrics in reports.

### Traffic and Throughput Monitoring

Chapter 2 introduced throughput as requests per second (RPS), transactions per second (TPS), or bytes per second. Here we cover how to instrument, visualize, and act on throughput metrics in practice.

#### Instrumenting Throughput

Throughput is measured using **counters**, which are monotonically increasing values that track total requests. The monitoring system calculates rate (requests per second) by computing the delta over time windows.

The standard approach uses labeled counters. Define a counter metric with labels for method, endpoint, and status code. In each request handler, increment the counter with the appropriate labels.

Key instrumentation decisions:

- **Increment on response, not request**: Count completed requests to avoid inflating counts with abandoned connections
- **Label granularity**: Include method, endpoint, and status code. Avoid high-cardinality labels (user IDs, request IDs) which explode metric storage
- **Separate success and error counts**: Enables calculating both total throughput and success rate

#### Per-Endpoint Throughput

Aggregate RPS can mask problems. If your API handles 10,000 RPS total but the `/checkout` endpoint (critical path) only handles 50 RPS while `/health` handles 8,000 RPS, the aggregate number is misleading.

Dashboard design for per-endpoint visibility:

- **Top-N chart**: Show the N highest-traffic endpoints dynamically
- **Critical endpoint panel**: Pin business-critical endpoints regardless of traffic volume
- **Long-tail summary**: Aggregate remaining endpoints into "other" to avoid chart clutter

In PromQL, use `sum(rate(http_requests_total[5m])) by (endpoint)` to get per-endpoint RPS, `topk()` to show the highest-traffic endpoints, and label selectors to filter to specific critical endpoints.

#### Establishing Throughput Baselines

Throughput varies predictably. Most APIs exhibit patterns:

- **Diurnal patterns**: Higher traffic during business hours, lower overnight
- **Weekly patterns**: Different weekday vs weekend traffic
- **Seasonal patterns**: E-commerce spikes during holidays

Baseline calculation approaches:

- **Static baselines**: Simple but brittle. "Normal" is 5,000-8,000 RPS during business hours
- **Rolling baselines**: Compare current throughput to same time last week. Accommodates growth
- **Seasonal decomposition**: Statistical methods that separate trend, seasonal, and residual components

For alerting, compare current throughput against baseline. For example, alert if traffic drops below 50% of the same time last week using the `offset` modifier in PromQL. Traffic drops often indicate problems users haven't reported yet: DNS issues, client bugs, or upstream failures preventing requests from reaching your service.

#### Throughput and Capacity

Throughput monitoring connects directly to capacity planning (covered in Chapter 9). Key relationships:

- **Throughput ceiling**: The maximum sustainable RPS before latency degrades. Found through load testing
- **Current headroom**: Ceiling minus current throughput. Alerts when headroom drops below safety margin
- **Growth projection**: Current throughput × growth rate. Triggers capacity planning when projected throughput approaches ceiling

A well-designed traffic dashboard answers: "How much traffic are we handling, is it normal, and how much headroom do we have?"

### Latency Monitoring

Latency is the golden signal users feel most directly. A throughput drop might go unnoticed; a latency spike makes every user wait. Effective latency monitoring requires understanding how to instrument, interpret, and act on latency data.

#### Instrumenting Latency

Latency measurement starts with choosing the right metric type. Prometheus offers two options:

**Histograms** bucket observations into predefined ranges. A histogram with buckets at 50ms, 100ms, 250ms, 500ms, 1s counts how many requests fall into each bucket. Percentiles are calculated at query time by interpolating between buckets.

**Summaries** calculate percentiles on the client side before sending to Prometheus. They're more accurate for a single instance but cannot be aggregated across instances—you cannot combine p99s from multiple pods to get a fleet-wide p99.

For most API monitoring, histograms are the better choice. They aggregate across instances, support flexible queries, and allow retroactive analysis. The trade-off is bucket configuration: too few buckets lose precision, too many increase cardinality.

```
// Recording latency with a histogram
latency_histogram = create_histogram(
    name="http_request_duration_seconds",
    buckets=[0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0, 10.0],
    labels=["endpoint", "method", "status_code"]
)

on request complete:
    duration = end_time - start_time
    latency_histogram.observe(duration, labels={
        endpoint: request.path,
        method: request.method,
        status_code: response.status
    })
```

Configure buckets based on your SLO targets. If your SLO requires p95 under 200ms, you need buckets around that threshold (100ms, 150ms, 200ms, 250ms) for accurate measurement.

#### Percentile Interpretation

Different percentiles answer different questions:

| Percentile | What It Reveals | When to Use |
|------------|-----------------|-------------|
| p50 (median) | Typical user experience | Baseline performance understanding |
| p90 | Experience for most users | Identifying emerging issues |
| p95 | SLO threshold for many services | Standard SLO target |
| p99 | Worst-case for typical users | Tail latency investigation |
| p99.9 | Extreme outliers | Identifying systematic issues vs noise |

The gap between percentiles tells a story. When p50 and p99 are close, latency is consistent. When p99 is 10x higher than p50, something causes occasional severe delays—investigate tail latency causes.

Avoid using averages for latency monitoring. A bimodal distribution (half at 50ms, half at 5s) shows a 2.5s average that describes no actual user's experience. Percentiles reveal what averages hide.

![Latency Monitoring Dashboard](../assets/ch04-latency-dashboard.html)

#### Per-Endpoint Latency Analysis

Aggregate latency metrics mask endpoint-specific problems. A slow `/reports/generate` endpoint might be acceptable at 3 seconds, while `/api/search` at 300ms is a crisis. Break down latency by:

- **Endpoint**: Each API path has different acceptable latency ranges
- **Method**: GET requests are typically faster than POST; monitor separately
- **Status code**: Error responses (5xx) may be faster (failing quickly) or slower (timeouts)

Latency heatmaps reveal patterns invisible in line charts. A heatmap shows request distribution over time, revealing:
- Bimodal distributions (two distinct latency clusters)
- Gradual degradation (distribution shifting rightward over hours)
- Periodic spikes (correlating with cron jobs or batch processes)

#### Latency Baselines and Anomalies

Latency varies with time of day, day of week, and business cycles. A static threshold of "alert if p95 > 200ms" will either fire constantly during peak hours or miss problems during quiet periods.

Establish baselines by:
1. Recording latency over at least two weeks to capture weekly patterns
2. Comparing current latency to the same time period (hour of day, day of week) in history
3. Alerting on deviation from baseline rather than absolute threshold

```
// Baseline comparison in PromQL
// Alert if current p95 is 50% higher than same time last week
histogram_quantile(0.95, rate(http_request_duration_seconds_bucket[5m]))
  >
histogram_quantile(0.95, rate(http_request_duration_seconds_bucket[5m] offset 1w)) * 1.5
```

Early warning comes from detecting degradation before SLO breach. If your SLO allows p95 of 200ms and current p95 is 180ms but was 120ms yesterday, the trend indicates a problem even though the SLO is still met.

#### Tail Latency Causes

When p99 latency spikes while p50 remains stable, investigate these common causes:

**Garbage collection pauses**: GC events block request processing. Correlate latency spikes with GC logs or metrics. Long GC pauses appear as latency outliers with otherwise normal distributions.

**Lock contention**: Requests waiting for locks show increased latency under load. CPU profiling may show low utilization while latency climbs—a signature of contention.

**Cold caches**: After deployments, cache misses cause initial requests to be slower. Latency should improve as caches warm. If it doesn't, investigate cache hit rates.

**Connection pool exhaustion**: When pools are exhausted, requests queue waiting for connections. Saturation metrics (covered in the next section) reveal this pattern.

**Downstream dependencies**: A slow database or external service affects your latency. Trace analysis (Chapter 3) identifies which dependency is responsible.

Not all tail latency requires investigation. Occasional outliers are normal in distributed systems. Focus on persistent patterns or outliers affecting SLO compliance.

### Errors Monitoring

Errors are the golden signal that most directly indicates something is broken. While latency degradation frustrates users, errors prevent them from completing their tasks entirely. Effective error monitoring distinguishes signal from noise and connects errors to business impact.

#### Error Categorization

Not all errors indicate system problems:

**5xx errors** (server errors) almost always indicate issues requiring investigation:
- 500 Internal Server Error: Unhandled exception or application bug
- 502 Bad Gateway: Upstream service failure
- 503 Service Unavailable: Overload or maintenance
- 504 Gateway Timeout: Upstream service too slow

**4xx errors** (client errors) require nuanced interpretation:
- 400 Bad Request: Could indicate API misuse or validation bugs
- 401/403 Unauthorized/Forbidden: Normal for protected resources; spikes may indicate auth system issues
- 404 Not Found: Normal for user typos; spikes may indicate broken links or routing changes
- 429 Too Many Requests: Rate limiting working as designed; high volume may indicate attack or misconfigured client

For system health monitoring, focus on 5xx errors. Track 4xx separately to identify client integration issues or API usability problems.

```
// Error rate query in PromQL - 5xx only
sum(rate(http_requests_total{status_code=~"5.."}[5m]))
  /
sum(rate(http_requests_total[5m]))
```

#### Error Rate Calculation

Express error rates as percentages rather than absolute counts. "50 errors per minute" means nothing without knowing total traffic; 50 errors in 10,000 requests (0.5%) differs vastly from 50 errors in 100 requests (50%).

Calculate error rates at multiple granularities:
- **Global error rate**: Overall API health
- **Per-endpoint error rate**: Identifying problematic endpoints
- **Per-status-code breakdown**: Understanding error types

Exclude expected errors from health calculations. A 404 for a nonexistent resource isn't a system failure. Configure your metrics to distinguish:

```
// Success rate excluding expected 4xx errors
sum(rate(http_requests_total{status_code=~"2.."}[5m]))
  /
sum(rate(http_requests_total{status_code!~"4(00|04|29)"}[5m]))
```

![Errors Monitoring Dashboard](../assets/ch04-errors-dashboard.html)

#### Error Budgets in Practice

Error budgets connect error rates to SLOs. If your SLO promises 99.9% availability, you have a 0.1% error budget—roughly 43 minutes of downtime per month or 8.7 hours per year.

Monitor error budget consumption rate:
- **Slow burn**: Consistently elevated error rate that gradually depletes budget
- **Fast burn**: Sudden spike that rapidly consumes budget
- **Budget remaining**: How much room remains before SLO breach

Multi-burn-rate alerting (introduced in Chapter 3) catches both patterns:

```
// Fast burn: 14x budget consumption over 1 hour = exhausts monthly budget in ~2 days
error_rate > (14 * monthly_error_budget) for 1 hour

// Slow burn: 2x budget consumption over 6 hours = exhausts monthly budget in ~15 days
error_rate > (2 * monthly_error_budget) for 6 hours
```

When error budget is exhausted or nearly so, shift priorities from feature development to reliability work. This is the organizational mechanism that balances velocity with stability.

#### Error Correlation

Errors rarely occur in isolation. Connecting errors to other signals accelerates diagnosis:

**Errors preceding latency**: Error spikes often precede latency degradation as retries and fallback logic add load. Early error detection prevents cascading failures.

**Errors correlated with deployments**: Track deployment events as annotations on error graphs. Sudden error rate changes aligned with deployments indicate the likely cause.

**Downstream vs origin errors**: Distinguish errors your service generates from errors returned by dependencies. A 502 may reflect your code's bug or an upstream service's failure. Trace analysis reveals the true source.

**Error clustering**: Multiple error types spiking simultaneously suggests a shared cause (infrastructure issue, configuration change) rather than multiple independent bugs.

### Per-Endpoint SLO Strategies

A single API often contains dozens or hundreds of endpoints with vastly different performance characteristics. A `/health` check returning in 1ms shares metrics with a `/reports/generate` call that legitimately takes 5 seconds. Aggregate SLOs mask these differences: an API might report 99.5% of requests under 200ms while critical user-facing endpoints fail to meet their individual targets.

#### Why Per-Endpoint SLOs Matter

Aggregate metrics create dangerous blind spots:

- **Dilution by volume**: High-traffic, fast endpoints (health checks, simple reads) statistically overwhelm low-traffic, critical endpoints (checkout, payment processing) in aggregate percentiles
- **Hidden degradation**: An important endpoint can degrade from 50ms to 500ms p99 without moving aggregate metrics if it represents only 1% of traffic
- **Misguided optimization**: Teams optimize the wrong endpoints because aggregate metrics point to high-volume paths rather than business-critical paths

Per-endpoint SLOs acknowledge that different endpoints have different importance and different performance expectations. A search autocomplete endpoint has stricter latency requirements than a nightly batch export. A payment confirmation needs higher reliability than a profile image upload.

#### Defining Endpoint-Level SLIs and SLOs

For each critical endpoint, define explicit targets:

| Endpoint | SLI | SLO | Rationale |
|----------|-----|-----|-----------|
| `POST /checkout` | Latency p99 | < 500ms | User is actively waiting, high conversion impact |
| `GET /products/:id` | Latency p95 | < 100ms | Frequent access, page load blocking |
| `POST /reports` | Success rate | > 99.5% | Async job, users tolerate some failures |
| `GET /search` | Latency p90 | < 200ms | High volume, some latency variance acceptable |

The SLI (Service Level Indicator) specifies what you measure. The SLO (Service Level Objective) specifies the target. Choose the right percentile for each endpoint: p99 for latency-critical paths where tail latency matters, p95 or p90 for high-volume endpoints where some variance is acceptable.

#### Cardinality Management for Multi-Endpoint Metrics

Naive per-endpoint metrics can explode cardinality and overwhelm time-series databases. An API with 500 endpoints across 10 regions and 5 status codes produces 25,000 time series per metric, and that is before adding instance labels.

Strategies for managing cardinality while preserving endpoint visibility:

**Tiered instrumentation**: Instrument critical endpoints with full detail (per-instance, per-status-code). Aggregate less critical endpoints into buckets. A well-designed system might have 20-30 endpoints with full visibility and the remaining 470 grouped by category (`/admin/*`, `/internal/*`, `/webhooks/*`).

**Dynamic top-N recording**: Record individual metrics only for the top N endpoints by traffic or error rate. This captures the endpoints most likely to matter while avoiding cardinality explosion. The top 50 endpoints typically represent 95%+ of traffic.

**Separate hot and cold storage**: Store high-cardinality per-endpoint metrics at shorter retention (7 days) while aggregating to lower cardinality for long-term storage. Full detail for recent investigation; trends for historical analysis.

**Pre-aggregation**: Calculate per-endpoint SLO compliance in the application or a streaming pipeline rather than at query time. Store the compliance percentage rather than every individual data point. This trades flexibility for efficiency.

#### Multi-Tenant Performance Visibility

A multi-tenant system is one where a single deployment serves multiple customers (tenants). Think of SaaS products like Slack, Salesforce, or Shopify: one codebase, one database cluster, thousands of companies using it simultaneously. The alternative—single-tenant—gives each customer their own dedicated deployment, which is simpler to reason about but more expensive to operate.

In multi-tenant systems, performance varies by tenant. A tenant with unusual data patterns (millions of records where others have thousands) or high request volume can experience different performance than others. Per-tenant visibility is essential for identifying tenant-specific issues, but naive tenant-labeling creates cardinality proportional to tenant count.

**Strategies for tenant-aware monitoring:**

- **Sample tenant labels**: Record tenant labels for a sample of requests rather than all requests. A 10% sample provides visibility with 10% of the cardinality cost.
- **Cohort-based labeling**: Group tenants into cohorts (enterprise, mid-market, free tier) and label by cohort rather than individual tenant. Monitor cohort performance; drill into individual tenants only when investigating.
- **Top-K tenant tracking**: Dynamically track metrics for the top K tenants by traffic or error rate. Most investigations concern high-activity tenants.
- **Exemplar-based diagnosis**: Use trace exemplars (links from metrics to specific traces) to investigate tenant-specific issues without storing tenant as a metric dimension. When p99 spikes, examine the trace exemplar to identify the affected tenant.

#### Implementing Per-Endpoint SLO Dashboards

A per-endpoint SLO dashboard differs from an aggregate dashboard:

**Compliance heatmap**: Show endpoint × time grid with color indicating SLO compliance (green = meeting target, yellow = at risk, red = breaching). This visualization immediately highlights which endpoints are struggling and when.

**Error budget burndown**: For each critical endpoint, show remaining error budget over the SLO window. An endpoint burning budget faster than expected warrants investigation even if still within SLO.

**Comparative percentiles**: Show p50, p95, p99 for selected endpoints on the same chart. Divergence between percentiles indicates tail latency problems for specific endpoints.

**Trend lines**: Track SLO compliance percentage over weeks and months. Gradual degradation suggests capacity or code debt accumulating; sudden drops indicate incidents or deployments.

In PromQL, calculate per-endpoint SLO compliance using histogram_quantile with endpoint labels, then compare against thresholds to produce compliance booleans that can be summed into compliance percentages.

### Measuring Saturation

Chapter 2 introduced saturation as the fourth golden signal and distinguished it from utilization: a resource at 100% utilization with no queue is efficiently used; the same resource with work waiting is saturated. Here we cover how to measure saturation for each resource type.

The key insight: **utilization tells you how busy a resource is; saturation tells you if work is waiting**. Most default dashboards show utilization. You must explicitly configure saturation metrics.

![Saturation Dashboard](../assets/ch04-saturation-dashboard.html)

A saturation dashboard monitors all resource types simultaneously, highlighting which resources have work waiting versus which are simply busy.

#### CPU Saturation

CPU utilization (the percentage of time CPUs are busy) is widely monitored but does not indicate saturation. A system at 95% CPU utilization with no runnable threads waiting is healthy. The same system with 50 threads in the run queue is saturated.

**Key metrics:**

- **Load average**: The average number of processes in runnable or uninterruptible state. On Linux, a load average exceeding the CPU count indicates saturation. A 4-core system with load average 6 has processes waiting.
- **Run queue length**: The instantaneous count of runnable threads waiting for CPU. Available via `/proc/stat` or node_exporter's `node_procs_running`.
- **CPU pressure (Linux 5.2+)**: Pressure Stall Information (PSI) metrics show the percentage of time processes are stalled waiting for CPU.

In PromQL, divide load average by CPU count to identify saturation (values above 1 indicate processes waiting). Linux 5.2+ systems expose PSI metrics showing the percentage of time tasks are stalled waiting for CPU.

#### Memory Saturation

Memory utilization (percentage of RAM used) is misleading because modern operating systems use available memory for caches. High memory utilization is often healthy. Saturation occurs when the system cannot allocate memory without reclaiming it.

**Key metrics:**

- **Swap usage**: Non-zero swap usage on a system configured to avoid swapping indicates memory pressure.
- **Page fault rate**: Major page faults (requiring disk I/O) indicate memory pressure. Minor faults are normal.
- **OOM events**: Out-of-memory killer invocations indicate severe saturation.
- **Memory pressure (Linux 5.2+)**: PSI metrics show time stalled on memory allocation.

In PromQL, track swap usage (should be near zero for most API servers), major page fault rate, and memory pressure metrics showing time stalled on allocation.

#### Connection Pool Saturation

Connection pools (database, HTTP client, Redis) can become saturated when demand exceeds pool size. Utilization is connections in use divided by pool size. Saturation is requests waiting to acquire a connection.

**Key metrics:**

- **Pool wait time**: Time requests spend waiting for an available connection. Non-zero indicates saturation.
- **Pool wait count**: Number of requests currently waiting. Should be zero under normal operation.
- **Acquire timeout errors**: Connection acquisition failures due to timeout indicate severe saturation.

Most connection pool libraries expose these metrics. For HikariCP (Java), monitor pending threads (connections waiting to be acquired) and average acquire time. For application-level pools, instrument acquire operations with a histogram for timing and a gauge for waiting requests.

#### Disk I/O Saturation

Disk utilization (percentage of time the disk is busy) does not capture saturation. Modern SSDs can handle many concurrent operations; a disk at 100% utilization with deep queue depth may perform well. Saturation appears as increasing latency due to queuing.

**Key metrics:**

- **I/O queue depth (avgqu-sz)**: Average number of requests waiting. High values indicate saturation.
- **I/O wait time (await)**: Average time for I/O requests including queue time. Rising await with stable service time indicates queuing.
- **I/O pressure (Linux 5.2+)**: PSI metrics for I/O stalls.

In PromQL, calculate average I/O queue depth by dividing weighted I/O time by total I/O time. Linux 5.2+ systems expose PSI metrics showing the percentage of time tasks are stalled on I/O.

#### Network Saturation

Network interfaces can saturate when traffic approaches link capacity. Utilization is bytes per second relative to link speed. Saturation manifests as dropped packets and TCP retransmissions.

**Key metrics:**

- **Dropped packets**: Non-zero drop counts indicate the kernel is discarding traffic.
- **TCP retransmissions**: High retransmission rates indicate network congestion or saturation.
- **Socket backlog**: Listen queue overflows indicate the application cannot accept connections fast enough.

In PromQL, track receive drops per second and TCP retransmissions per second to identify network saturation.

#### Saturation Dashboard Design

A saturation-focused dashboard complements utilization metrics:

| Resource | Utilization Metric | Saturation Metric |
|----------|-------------------|-------------------|
| CPU | CPU % busy | Load average, run queue, PSI |
| Memory | Memory % used | Swap usage, major faults, PSI |
| Connection Pool | Connections in use / max | Wait count, wait time |
| Disk | Disk % busy | Queue depth, await time, PSI |
| Network | Bytes/sec vs capacity | Drops, retransmits, backlog |

Alert on saturation metrics rather than utilization. A database connection pool at 90% utilization is fine; one with requests waiting is a problem regardless of utilization percentage.

### Alerting Strategies

Alerts bridge automated monitoring and human response. Every alert represents a choice: this condition is important enough to interrupt a human. Getting this balance right is critical. Too few alerts and problems go unnoticed. Too many and responders become desensitized.

**SLO-Based Alerting**

Traditional alerting sets static thresholds: "Alert if CPU exceeds 80%." This approach has fundamental problems. Why 80%? What if the system functions fine at 90%? What if 70% CPU correlates with degraded latency?

SLO-based alerting inverts the model: alert when the error budget burns too fast. If your SLO is 99.9% availability over 30 days, you have an error budget of 43.2 minutes of downtime. An alert fires when you're consuming that budget at an unsustainable rate, not when an arbitrary threshold is crossed [Source: Google SRE Workbook, "Alerting on SLOs", 2018].

The multi-burn-rate approach uses different time windows and consumption rates:

| Severity | Burn Rate | Time Window | Meaning |
|----------|-----------|-------------|---------|
| Page | 14.4x | 1 hour | Budget exhausted in 2 days if sustained |
| Page | 6x | 6 hours | Budget exhausted in 5 days if sustained |
| Ticket | 1x | 3 days | On track to exhaust budget this month |

This approach pages only when user impact is significant and sustained, not for transient spikes that self-resolve.

The threshold evaluation logic follows this pattern:

```
on metric window complete:
    if metric > critical_threshold:
        fire alert immediately
    else if metric > warning_threshold:
        if above warning for N consecutive windows:
            fire alert
    else:
        clear any pending alerts
```

**Symptom-Based vs Cause-Based Alerts**

Symptom-based alerts focus on user-visible impact: high latency, elevated error rates, reduced availability. Cause-based alerts focus on internal conditions: high CPU, low memory, queue depth.

Prefer symptom-based alerts for paging. Users do not care about CPU usage; they care about slow responses. High CPU that does not affect latency should not wake anyone up. Cause-based metrics belong on dashboards for diagnosis, not in pager routing.

The exception: cause-based alerts as leading indicators. If database connection pool exhaustion historically precedes latency degradation by 10 minutes, alerting on pool saturation gives responders time to act before user impact occurs.

**Alert Fatigue and How to Prevent It**

Alert fatigue occurs when responders receive so many alerts that they stop paying attention. Studies of clinical alarm fatigue in healthcare found that 72-99% of alarms were false positives, leading staff to disable or ignore them [Source: Sendelbach & Funk, "Alarm Fatigue: A Patient Safety Concern", 2013]. The same dynamic affects software operations.

Symptoms of alert fatigue:
- Alerts that fire but are routinely ignored or snoozed
- On-call handoff with "just ignore that one, it's always firing"
- Alert counts in the dozens per shift
- Responders disabling notifications

Prevention requires discipline:

1. **Every alert must be actionable**: If an alert fires and requires no action, it should not be an alert. Convert to a dashboard metric or eliminate it.
2. **Tune thresholds based on data**: Set thresholds based on historical baseline behavior and SLO requirements, not arbitrary percentages.
3. **Consolidate related alerts**: One alert for "service degraded" rather than separate alerts for each symptom. Include context about which symptoms are present.
4. **Use severity levels correctly**: Page for user impact requiring immediate action. Ticket for issues that can wait until business hours.
5. **Regular review and pruning**: Review alert history monthly. Any alert that never fired in 6 months should be questioned. Any alert that fired but required no action should be tuned or eliminated.

**Alert Routing and Escalation**

Not all alerts need the same responder. Alert routing directs alerts to appropriate teams based on the affected service, severity, and time. Escalation ensures alerts are not lost when primary responders are unavailable.

Routing considerations:
- Service ownership: Route to the team that owns the service
- Severity-based: Critical alerts to on-call, warnings to Slack channel
- Time-based: Business hours to team channel, after-hours to on-call pager
- Dependency-aware: If a dependency is down, suppress dependent service alerts

Escalation ensures response:
- **Primary timeout**: If primary on-call does not acknowledge within 10 minutes, escalate to secondary
- **Secondary timeout**: If secondary does not acknowledge, escalate to team lead
- **Full escalation**: After all escalations, alert to broader group or management

### Incident Response

When alerts fire and confirm a real problem, incident response begins. Effective incident response minimizes user impact through rapid detection, organized triage, and systematic resolution.

**The Incident Lifecycle**

Incidents progress through distinct phases:

1. **Detection**: An alert fires, a user reports a problem, or monitoring reveals an anomaly. The faster detection occurs, the faster mitigation can begin. SLO-based alerting improves detection time for user-impacting issues.

2. **Triage**: Assess severity and impact. How many users are affected? Is the system fully down or degraded? What is the blast radius? Triage determines urgency and who needs to be involved.

3. **Mitigation**: Take immediate action to reduce user impact, even if the root cause is unknown. Rollback a deployment, redirect traffic, enable a feature flag, scale up capacity. Mitigation prioritizes user experience over investigation.

4. **Resolution**: After mitigation stabilizes the system, work toward full resolution. This might mean fixing the underlying bug, completing the rollback, or restoring full functionality.

5. **Postmortem**: After resolution, conduct a blameless postmortem to understand what happened, why it happened, and how to prevent recurrence. Document timeline, root cause, and action items.

<!-- DIAGRAM: Incident lifecycle as a horizontal flow: Detection (alert/report) -> Triage (severity/impact assessment) -> Mitigation (reduce user impact) -> Resolution (fix underlying issue) -> Postmortem (learn and prevent). Arrows show progression, with feedback loop from Postmortem back to improved Detection -->

**Runbooks and Playbooks**

Runbooks provide step-by-step procedures for common incident scenarios. When an alert fires at 3 AM, the on-call engineer should not need to figure out the investigation steps from scratch.

Effective runbooks include:

- **Alert context**: What this alert means, what SLO it protects, historical false-positive rate
- **Initial assessment**: Commands to run, dashboards to check, logs to examine
- **Common causes**: Ranked list of likely causes with diagnostic steps for each
- **Mitigation steps**: Actions to reduce user impact (rollback commands, traffic shifting procedures, scaling instructions)
- **Escalation criteria**: When to page additional responders, when to declare a major incident

Playbooks are broader procedures for incident types (database outage, security incident, regional failure). They coordinate multiple teams and define communication protocols.

Every alert should link to a runbook. An alert without a runbook is incomplete.

**Runbook Template**

A well-structured runbook follows a consistent format:

```
RUNBOOK: High API Latency Alert
Last Updated: 2024-01-15
Owner: Platform Team

ALERT CONTEXT
- Fires when: p95 latency > 500ms for 5 minutes
- SLO impact: Degrades user experience SLO (p95 < 200ms)
- False positive rate: ~5% (usually during batch jobs)

INITIAL ASSESSMENT
1. Check Grafana dashboard: [link]
2. Run: kubectl get pods -n api | grep -v Running
3. Check recent deployments: [link to deployment history]
4. Review error rate (correlated latency/error spikes suggest code issue)

COMMON CAUSES (check in order)
1. Database connection pool exhaustion
   - Check: SELECT count(*) FROM pg_stat_activity;
   - Fix: Scale up connection pool or restart stuck connections

2. Memory pressure causing GC pauses
   - Check: Grafana panel "JVM GC Pause Duration"
   - Fix: Restart affected pods, investigate memory leak if recurring

3. Downstream service degradation
   - Check: Trace view for slow spans
   - Fix: Enable circuit breaker, contact downstream team

MITIGATION OPTIONS
- Rollback: kubectl rollout undo deployment/api
- Scale up: kubectl scale deployment/api --replicas=10
- Shed load: Enable rate limiting via feature flag X

ESCALATION
- If not mitigated in 15 minutes: page secondary on-call
- If customer-facing impact confirmed: notify support team
- If data integrity risk: page database team immediately
```

**Communication During Incidents**

Incidents require coordinated communication across multiple audiences:

- **Responders**: Need shared context, coordination on who is doing what, real-time updates on actions taken
- **Stakeholders**: Leadership, customer success, support teams need status updates without joining the war room
- **Customers**: May need external communication for significant incidents

Best practices for incident communication:

- **Dedicated channel**: Create an incident-specific channel (e.g., #incident-2024-01-15-api-latency) to avoid noise in general channels
- **Incident commander**: Designate one person to coordinate response, triage incoming information, and delegate tasks
- **Regular updates**: Post status updates at regular intervals (every 15-30 minutes during active incidents) even if just "still investigating"
- **External status page**: Update public status page for customer-visible incidents with honest, jargon-free language

**Status Update Templates**

Consistent status updates reduce confusion during incidents. Use templates to ensure completeness:

*Initial acknowledgment (within 5 minutes of alert):*
```
INCIDENT DECLARED: [Brief description]
Severity: [P1/P2/P3]
Impact: [What users are experiencing]
Status: Investigating
Incident Commander: [Name]
Next update: [Time, typically 15-30 min]
```

*Progress update (every 15-30 minutes):*
```
UPDATE [Incident Name] - [Time]
Current status: [Investigating/Mitigating/Monitoring]
Actions taken: [What we've done]
Current hypothesis: [What we think is wrong]
Next steps: [What we're trying next]
ETA to resolution: [If known, or "Unknown"]
```

*Resolution announcement:*
```
RESOLVED: [Incident Name] - [Time]
Duration: [Start to end]
Impact: [Users affected, errors generated, revenue impact if known]
Root cause: [Brief description]
Resolution: [What fixed it]
Follow-up: [Postmortem scheduled for X, action items being tracked]
```

### On-Call as an Optimization Signal

On-call data is one of the most valuable inputs for optimization prioritization. Every page represents a system asking for human help—and an opportunity to make the system better.

**Incident Patterns Reveal Optimization Priorities**

Track and categorize every alert:

- **By root cause**: Database overload, memory pressure, downstream timeouts, deployment regressions
- **By affected component**: Which services page most frequently?
- **By time of day**: Are problems correlated with traffic patterns, batch jobs, or maintenance windows?
- **By resolution type**: What percentage require code fixes vs. operational responses vs. false positives?

When the same alert fires repeatedly, it signals a systemic issue worth optimizing. A service that pages twice per week for connection pool exhaustion is telling you to either increase the pool, optimize query patterns, or add connection pooling at the application layer.

**Post-Incident Optimization**

Every incident should produce optimization candidates:

- **Performance incidents**: Latency spikes and timeouts reveal bottlenecks. Add the specific optimization (query optimization, caching, connection pooling) to the backlog.
- **Capacity incidents**: Traffic spikes that overwhelmed the system indicate where autoscaling, caching, or load shedding could help.
- **Cascading failures**: When one service failure brings down others, circuit breakers, bulkheads, or timeout tuning can prevent recurrence.

The postmortem process should explicitly ask: "What optimization would prevent this incident class?" Track these items alongside feature work.

**Measuring Optimization Success Through Alert Reduction**

Alert volume is a lagging indicator of optimization effectiveness:

- **Pages per week**: Should trend downward as optimizations land
- **Mean time to resolution**: Faster resolution suggests runbooks and tooling improvements
- **Repeat incidents**: Same root cause appearing multiple times indicates incomplete optimization

A healthy optimization program creates a virtuous cycle: incidents reveal problems, optimization fixes them, alert volume decreases, engineers have more time to optimize proactively rather than reactively.

The goal is not zero alerts—some alerting is healthy confirmation that monitoring works. The goal is eliminating preventable incidents through systematic optimization.

### Continuous Performance Validation

Monitoring in production catches problems after deployment. Continuous validation catches problems before they reach all users.

**Canary Deployments**

Canary deployments route a small percentage of traffic to new versions before full rollout. If the canary exhibits degraded performance, the deployment can be halted before affecting most users.

Effective canary analysis requires:

- **Baseline comparison**: Compare canary metrics against the stable version, not against historical averages
- **Statistical significance**: Ensure sufficient traffic for meaningful comparison. A canary with 10 requests cannot prove much.
- **Multi-signal analysis**: Compare latency, error rate, and resource usage. A canary might have good latency but elevated memory usage.
- **Automated rollback**: If canary metrics deviate beyond thresholds, automatically halt deployment

Canary analysis compares the new version against the stable baseline using statistical testing to avoid false positives from random variation.

**Performance Regression Detection**

Beyond canary deployments, continuous performance testing in CI/CD pipelines catches regressions before they reach production.

Approaches include:

- **Benchmark suites**: Automated performance tests that run on every commit or merge. Compare results against baseline with statistical significance testing.
- **Load test gates**: Run load tests before production deployment. Fail the deployment if latency or error rate exceeds thresholds.
- **Continuous profiling comparison**: Compare production profiles before and after deployment to identify new hotspots.

**Anomaly Detection**

Not all problems manifest as threshold violations. Anomaly detection identifies unusual patterns that might indicate problems.

Simple approaches include:

- **Standard deviation bands**: Alert when metrics deviate more than N standard deviations from the rolling mean
- **Seasonal decomposition**: Account for daily and weekly patterns (traffic is lower on weekends, higher during business hours)
- **Rate of change**: Alert on sudden changes in trend, not just absolute values

A rolling statistics approach can detect values that deviate significantly from recent history by tracking mean and standard deviation over a sliding window.

## Common Pitfalls

- **Alert without runbook**: Alerts that fire without documented investigation steps lead to slower response and responder frustration. Every alert should link to a runbook explaining what it means and what to do.

- **Threshold cargo-culting**: Copying thresholds like "80% CPU" from blog posts without understanding your system's behavior. Base thresholds on observed baseline behavior and actual SLO requirements.

- **Alerting on causes, not symptoms**: Paging on-call for high CPU when latency is fine. Users experience symptoms (latency, errors), not causes (CPU, memory). Page on user impact.

- **Dashboard overload**: Cramming every possible metric onto dashboards until they become unreadable. Each dashboard should answer specific questions. Remove metrics that do not drive action.

- **Ignoring alert fatigue**: Dismissing frequent alerts as "that always fires" instead of fixing the underlying issue or tuning the threshold. Fatigued responders miss real problems.

- **Postmortem blame**: Focusing on who made the mistake rather than what allowed the mistake to cause an outage. Blameful postmortems discourage transparency and prevent learning.

- **Missing canary validation**: Deploying to 100% of traffic without canary analysis. One bad deployment affects all users instead of a small percentage.

- **Static baselines for anomaly detection**: Using fixed thresholds for anomaly detection without accounting for daily and weekly traffic patterns. Normal weekend traffic might look anomalous compared to weekday baselines.

- **Incident communication gaps**: Responding to incidents without updating stakeholders. Support teams get blindsided by customer complaints, leadership learns about outages from Twitter.

- **On-call burnout**: Overloading a few individuals with on-call while others avoid it. Track and balance on-call burden across the team.

## Summary

- Observability is the capability to understand system state; monitoring is the practice of watching, alerting, and responding. Both are necessary; neither alone is sufficient.

- Dashboard design should answer specific questions. Use the four golden signals as the foundation, layer dashboards from overview to detail, and avoid sprawl through ownership and lifecycle management.

- Throughput monitoring requires counters with appropriate labels (method, endpoint, status). Track per-endpoint RPS to avoid masking problems in aggregate metrics. Establish baselines that account for diurnal and weekly patterns.

- Saturation measurement differs from utilization. Monitor queue depths, wait times, and pressure metrics, not just resource usage percentages. A connection pool at 90% utilization is fine; one with requests waiting is saturated regardless of utilization.

- SLO-based alerting focuses on error budget burn rate rather than arbitrary thresholds. Alert when user impact threatens SLO compliance, not when internal metrics cross arbitrary lines.

- Alert fatigue degrades response quality. Combat it by ensuring every alert is actionable, tuning thresholds based on data, consolidating related alerts, and regularly reviewing and pruning.

- Incident response follows a lifecycle: detection, triage, mitigation, resolution, postmortem. Prioritize mitigation (reducing user impact) over investigation during active incidents.

- Runbooks provide step-by-step procedures for common scenarios. Every alert should link to a runbook. Update runbooks after each incident with lessons learned.

- On-call sustainability requires fair rotation, proper compensation, and continuous investment in reducing alert burden through automation and fixing root causes.

- Canary deployments catch regressions before full rollout. Use statistical comparison against baseline and automated rollback when thresholds are exceeded.

- Anomaly detection identifies unusual patterns that threshold-based alerts might miss. Account for seasonal patterns to avoid false positives.

## References

1. **Majors, Charity** (2018). "Observability vs Monitoring." https://thenewstack.io/monitoring-and-observability-whats-the-difference-and-why-does-it-matter/

2. **Google SRE Workbook** (2018). "Alerting on SLOs." https://sre.google/workbook/alerting-on-slos/

3. **Sendelbach, S., & Funk, M.** (2013). "Alarm Fatigue: A Patient Safety Concern." AACN Advanced Critical Care, 24(4), 378-386.

4. **Google SRE Book** (2016). "Monitoring Distributed Systems." https://sre.google/sre-book/monitoring-distributed-systems/

5. **Google SRE Book** (2016). "Effective Troubleshooting." https://sre.google/sre-book/effective-troubleshooting/

6. **Limoncelli, T., et al.** "The Practice of Cloud System Administration." Addison-Wesley, 2014.

7. **Allspaw, J., & Robbins, J.** "Web Operations: Keeping the Data On Time." O'Reilly Media, 2010.

8. **PagerDuty Incident Response Documentation**. "Incident Response Process." https://response.pagerduty.com/

## Next: [Chapter 5: Network and Connection Optimization](./05-network-connections.md)

With monitoring infrastructure in place, we can now measure the impact of our optimizations. Chapter 5 tackles the network layer, where connection pooling, HTTP protocol selection, compression, and keep-alive tuning can yield significant latency reductions.
