# Chapter 9: Compute and Scaling Patterns

![Chapter 9 Opener](../assets/ch09-opener.html)

\newpage

## Overview

As API traffic grows, we face a fundamental question: how do we handle more requests without degrading performance? The answer lies in scaling our compute resources effectively. However, scaling is not simply about adding more servers. It requires careful architectural decisions that determine whether our systems can grow gracefully or collapse under load.

This chapter explores the two primary scaling strategies---horizontal and vertical scaling---and examines the architectural patterns that make each approach effective. We will investigate stateless service design as the foundation for horizontal scaling, auto-scaling strategies that respond to demand, serverless considerations including the often-overlooked cold start problem, and the critical importance of graceful shutdown and health checks.

The key insight is that scalability is not an afterthought we bolt on later. It is an architectural property we design for from the beginning. Systems that scale well share common characteristics: they externalize state, they handle failures gracefully, and they communicate their health status accurately. Let us examine each of these principles in depth.

## Key Concepts

### Horizontal vs Vertical Scaling

When a service reaches its capacity limits, we have two fundamental options: make the existing instance bigger (vertical scaling) or add more instances (horizontal scaling).

**Vertical scaling** (scaling up) involves adding more resources---CPU, memory, faster storage---to an existing server. This approach has the advantage of simplicity: the application code requires no changes, there is no distributed coordination, and debugging remains straightforward. However, vertical scaling has hard limits. Eventually, we cannot buy a bigger machine, or the cost becomes prohibitive. Single-machine architectures also create a single point of failure.

**Horizontal scaling** (scaling out) involves adding more instances of a service behind a load balancer. This approach offers near-linear capacity growth and improved fault tolerance---if one instance fails, others continue serving traffic. However, horizontal scaling introduces complexity: we must handle distributed state, coordinate between instances, and manage the load balancer itself.

<!-- DIAGRAM: Horizontal vs Vertical scaling comparison: Vertical shows one server growing larger with added CPU/RAM; Horizontal shows multiple identical servers behind a load balancer, with requests distributed across them -->

![Horizontal vs Vertical Scaling Comparison](../assets/ch08-scaling-comparison.html)

The choice between these approaches depends on several factors:

| Factor | Favors Vertical | Favors Horizontal |
|--------|-----------------|-------------------|
| Application state | Stateful, hard to distribute | Stateless or externalized state |
| Traffic pattern | Predictable, steady | Variable, spiky |
| Cost sensitivity | Lower traffic volumes | Higher traffic volumes |
| Fault tolerance | Less critical | Critical |
| Development complexity | Limited resources | Dedicated platform team |

In practice, most production systems use a hybrid approach: right-sized instances (vertical) combined with multiple replicas (horizontal). The Twelve-Factor App methodology, published by Heroku in 2011, established the principle that modern applications should scale horizontally via the process model [Source: Heroku, 2011].

### Stateless Service Design

Horizontal scaling requires stateless services. A stateless service does not store any client-specific data between requests---each request can be handled by any instance without coordination.

This does not mean our applications have no state. Rather, we **externalize** state to dedicated storage systems:

- **Session data** moves from server memory to Redis or a database
- **File uploads** go to object storage (S3, GCS) rather than local disk
- **User preferences** live in a database, not in-memory caches

The benefits of stateless design extend beyond scaling. Stateless services are easier to deploy (no session draining), easier to debug (requests are independent), and more resilient (any instance can serve any request).

A complete implementation of externalized session state demonstrates this pattern in practice. The key insight is that any instance can retrieve or update session data because Redis serves as the single source of truth (see Example 9.1).

### Auto-scaling Strategies and Metrics

Auto-scaling automatically adjusts the number of service instances based on demand. The goal is to maintain performance during traffic spikes while avoiding over-provisioning during quiet periods.

**Reactive auto-scaling** responds to current metrics. When CPU utilization exceeds a threshold, more instances are added. The challenge is latency: by the time new instances are provisioned (typically one to several minutes), the traffic spike may have already caused degraded performance or failures.

The Kubernetes Horizontal Pod Autoscaler (HPA) exemplifies reactive scaling. According to the Kubernetes documentation, HPA uses a stabilization window to prevent "thrashing"---rapid scaling fluctuations. The default scale-down stabilization is 300 seconds (5 minutes), while scale-up is immediate [Source: Kubernetes Documentation, 2024].

The core HPA scaling formula is:


```
desiredReplicas = ceil(currentReplicas * (currentMetricValue / desiredMetricValue))
```

A 10% tolerance threshold prevents scaling for minor metric fluctuations.

**Predictive auto-scaling** uses historical patterns to anticipate demand. If traffic predictably increases every weekday at 9 AM, we can scale up proactively rather than reactively. AWS, Google Cloud, and Azure all offer predictive scaling options that use machine learning to forecast demand.

<!-- DIAGRAM: Auto-scaling feedback loop: Metrics collected (CPU, memory, request rate, queue depth) -> Scaling controller evaluates against thresholds -> Decision to scale up/down/maintain -> Instance count adjusted -> Metrics change -> loop continues -->

![Auto-scaling Feedback Loop](../assets/ch08-autoscaling-loop.html)

**Key metrics for scaling decisions:**

| Metric | Best For | Considerations |
|--------|----------|----------------|
| CPU utilization | Compute-bound workloads | Simple but may lag actual demand |
| Memory utilization | Memory-intensive applications | Often indicates resource leaks |
| Request rate (RPS) | HTTP APIs | Direct measure of demand |
| Queue depth | Async workers | Shows work backlog |
| Response latency | User-facing APIs | Ties scaling to user experience |

A common mistake is scaling on a single metric. A service might have low CPU but high latency due to database contention. Multi-metric scaling considers several signals, combining resource metrics like CPU with application-specific metrics like requests per second. A well-configured HPA also uses asymmetric behavior: scaling up aggressively to handle spikes while scaling down gradually to prevent thrashing (see Example 9.2).

### Understanding Traffic Patterns

Chapter 2 introduced the concept that different endpoints have different traffic patterns. Effective scaling requires understanding these patterns in detail, because the shape of your traffic determines which scaling strategy works best.

#### Diurnal Patterns

Most B2B APIs exhibit diurnal (daily) patterns tied to business hours. Traffic rises when offices open, peaks mid-morning, dips during lunch, peaks again in the afternoon, and drops overnight. The ratio between peak and trough can be 10:1 or higher.

Diurnal patterns are highly predictable, making them ideal for scheduled scaling. Scale up before the morning ramp begins, maintain capacity through business hours, and scale down after evening traffic subsides. Predictive auto-scaling excels here.


```yaml
# Kubernetes CronJob-based scaling
# Scale up at 7:45 AM before traffic arrives
apiVersion: batch/v1
kind: CronJob
metadata:
  name: scale-up-morning
spec:
  schedule: "45 7 * * 1-5"  # Weekdays at 7:45 AM
  jobTemplate:
    spec:
      template:
        spec:
          containers:
          - name: scaler
            command: ["kubectl", "scale", "deployment/api", "--replicas=20"]
```

#### Weekly Patterns

Consumer-facing APIs often show weekly patterns: higher weekend traffic for entertainment services, higher weekday traffic for productivity tools. E-commerce sees traffic spikes on specific days (higher on Mondays for B2B, weekends for B2C).

Weekly patterns require longer baseline windows. Compare this Tuesday to last Tuesday, not to yesterday. Scaling decisions should account for day-of-week variation.

#### Burst Patterns

Some traffic arrives in unpredictable bursts: viral content, marketing campaigns, external events (news mentions, API integrations going live). Burst traffic can exceed baseline by 100x or more within minutes.

Bursts challenge reactive scaling because provisioning cannot keep pace. Mitigation strategies:

- **Headroom**: Maintain capacity above typical baseline (e.g., 2x average)
- **Pre-scaling**: Scale up before known events (product launches, marketing emails)
- **Rate limiting**: Protect the system when demand exceeds capacity (Chapter 10)
- **Queue-based buffering**: Absorb bursts into queues for processing at sustainable rates (Chapter 8)

#### Seasonal Patterns

Longer cycles affect capacity planning: holiday shopping seasons, back-to-school periods, tax season, annual events. These patterns are predictable but require advance planning because capacity additions (especially hardware) have lead times.

Seasonal planning combines historical data with business forecasts:


```
Expected peak = (last_year_peak) × (growth_rate) × (seasonal_factor)
```

Cloud providers offer reserved capacity or savings plans that balance cost with the flexibility needed for seasonal variation.

#### Traffic Pattern Analysis

Before choosing a scaling strategy, analyze your traffic:

1. **Collect baseline data**: At least 4 weeks of traffic data at 1-minute granularity
2. **Identify patterns**: Plot traffic by hour-of-day, day-of-week, and look for recurring shapes
3. **Measure variability**: Calculate coefficient of variation (standard deviation / mean) for different time windows
4. **Identify bursts**: Look for traffic spikes that exceed 3× the rolling average

Low variability with clear diurnal patterns → scheduled scaling works well. High variability with unpredictable bursts → reactive scaling with generous headroom. Predictable growth with seasonal peaks → capacity planning with reserved instances.

### Serverless Considerations: Cold Starts

Serverless platforms (AWS Lambda, Google Cloud Functions, Azure Functions, Cloudflare Workers) promise automatic scaling without infrastructure management. However, they introduce a unique performance challenge: **cold starts**.

A cold start occurs when a serverless platform must provision a new execution environment for a function. This involves allocating compute resources, loading the runtime, loading application code, and running initialization logic. During this time, the request waits.

<!-- DIAGRAM: Serverless cold start timeline showing: Request arrives -> Container provisioned (cold start delay: 100ms-2s) -> Runtime loaded -> Application code loaded -> Handler initialization -> Handler executes -> Response. Warm start path skips provisioning/loading steps. -->

![Serverless Cold Start Timeline](../assets/ch08-cold-start-timeline.html)

Cold start duration varies significantly by runtime and configuration. AWS Lambda cold starts for interpreted languages like Python and Node.js are generally faster than compiled languages with larger runtimes like Java or .NET. Cold starts typically range from under 100ms for lightweight functions to several seconds for complex applications with many dependencies.

**Mitigation strategies:**

1. **Provisioned concurrency**: Pre-warm a specified number of instances. AWS Lambda Provisioned Concurrency keeps execution environments initialized and ready. This eliminates cold starts but incurs continuous costs.

2. **Keep-warm requests**: Send periodic "ping" requests to prevent instance recycling. This is a cost-effective approach but does not help during traffic spikes that exceed warm capacity.

3. **Minimize initialization**: Move expensive initialization (database connections, SDK clients) outside the handler function. Most runtimes cache these between invocations.

4. **Choose lighter runtimes**: When cold start latency is critical, prefer runtimes with faster startup characteristics.

5. **Reduce package size**: Smaller deployment packages load faster. Remove unused dependencies and use tree-shaking where available.

The most impactful mitigation is initializing expensive resources outside the handler function. Database clients, SDK instances, and connection pools initialized at module level persist across invocations, so only the first request (the cold start) pays the initialization cost (see Example 9.3).

### Graceful Shutdown and Health Checks

When scaling down or deploying new versions, instances must shut down cleanly. Abrupt termination drops in-flight requests, potentially corrupting data or leaving operations incomplete.

**Graceful shutdown** follows a sequence:

1. **Receive termination signal** (SIGTERM in Unix systems, PreStop hook in Kubernetes)
2. **Stop accepting new requests** (mark as unhealthy, deregister from load balancer)
3. **Complete in-flight requests** (with a reasonable timeout)
4. **Close connections and release resources**
5. **Exit the process**

Kubernetes sends SIGTERM and waits for a grace period (default 30 seconds) before sending SIGKILL. We must complete shutdown within this window.

<!-- DIAGRAM: Kubernetes pod lifecycle for graceful shutdown: Pod receives SIGTERM -> PreStop hook runs (if configured) -> Container stops accepting new traffic -> In-flight requests complete (up to terminationGracePeriodSeconds) -> Container exits OR SIGKILL sent after grace period -->

![Kubernetes Pod Graceful Shutdown Lifecycle](../assets/ch08-graceful-shutdown.html)

**Health checks** communicate service status to orchestrators and load balancers. Two types serve different purposes:

- **Liveness probes**: "Is this instance alive?" Failure triggers instance restart. Use for detecting deadlocks or unrecoverable states.

- **Readiness probes**: "Can this instance serve traffic?" Failure removes instance from load balancer but does not restart it. Use during startup warmup or when dependencies are unavailable.

Implementing these patterns correctly requires coordinating application state, signal handling, and health endpoints. The graceful shutdown handler must set readiness to false immediately upon receiving SIGTERM, then wait for in-flight requests to complete before exiting (see Example 9.4).

For implementation examples related to these concepts, see the [Appendix: Code Examples](./13-appendix-code-examples.md).

## Common Pitfalls

- **Storing state in memory**: Session data, user context, or request state stored in server memory breaks when requests hit different instances. Always externalize state to Redis, a database, or similar shared storage.

- **Ignoring cold start impact**: Serverless functions with slow initialization degrade user experience during traffic spikes. Profile your cold start time and consider provisioned concurrency for latency-sensitive workloads.

- **Single-metric auto-scaling**: Scaling only on CPU misses memory pressure, database connection exhaustion, or upstream service saturation. Use multiple metrics and consider custom metrics tied to your SLOs.

- **Missing graceful shutdown**: Instances killed without draining in-flight requests cause errors and potential data corruption. Always handle SIGTERM and complete active requests before exiting.

- **Health checks that lie**: A readiness probe that returns 200 during startup, before the service can actually handle requests, causes failed user requests. Only report ready when you can truly serve traffic.

- **Scaling too aggressively on scale-up or too slowly on scale-down**: Aggressive scale-up without cooldown causes thrashing. Slow scale-down wastes resources. Tune stabilization windows based on your traffic patterns.

- **Forgetting startup probes in Kubernetes**: Without startup probes, Kubernetes may kill slow-starting containers before they initialize. Use startup probes for applications with variable initialization times.

## Summary

- **Horizontal scaling** adds more instances and requires stateless services; **vertical scaling** adds resources to existing instances and has hard limits. Most production systems use a hybrid approach.

- **Stateless service design** externalizes state to shared storage (Redis, databases), enabling any instance to handle any request and simplifying deployments.

- **Auto-scaling** should use multiple metrics (CPU, memory, request rate, latency) with appropriate stabilization windows to prevent thrashing. The Kubernetes HPA uses a 300-second default scale-down window.

- **Traffic patterns** (diurnal, weekly, burst, seasonal) determine which scaling strategy works best. Predictable patterns suit scheduled scaling; unpredictable bursts require headroom and reactive scaling with rate limiting as a safety valve.

- **Serverless cold starts** occur when platforms provision new execution environments. Mitigate with module-level initialization, provisioned concurrency, smaller packages, and appropriate runtime selection.

- **Graceful shutdown** requires handling SIGTERM, stopping new request acceptance, completing in-flight requests, and cleaning up resources---all within the termination grace period.

- **Health checks** serve different purposes: liveness probes detect dead processes, readiness probes indicate traffic-serving capability. Incorrect health checks cause cascading failures.

- **Kubernetes HPA** evaluates metrics every 15 seconds by default and uses a tolerance threshold to prevent scaling on minor fluctuations.

## References

1. **Heroku** (2011). "The Twelve-Factor App." https://12factor.net/

2. **Kubernetes Documentation** (2024). "Horizontal Pod Autoscaling." https://kubernetes.io/docs/tasks/run-application/horizontal-pod-autoscale/

3. **AWS Lambda Documentation**. "Operating Lambda: Performance optimization." https://docs.aws.amazon.com/lambda/latest/operatorguide/perf-optimize.html

4. **Google Cloud Run Documentation**. "Configuring minimum instances." https://cloud.google.com/run/docs/configuring/min-instances

5. **Kubernetes Documentation**. "Pod Lifecycle." https://kubernetes.io/docs/concepts/workloads/pods/pod-lifecycle/

## Next: [Chapter 10: Traffic Management and Resilience](./10-traffic-management.md)

With our services scaling effectively, we now turn to protecting them from overload and cascading failures. The next chapter covers rate limiting, circuit breakers, and the resilience patterns that keep services stable under adverse conditions.
