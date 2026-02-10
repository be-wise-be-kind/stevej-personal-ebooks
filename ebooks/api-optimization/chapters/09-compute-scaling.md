# Chapter 9: Compute and Scaling Patterns

![Chapter 9 Opener](../assets/ch09-opener.html)

\newpage

## Overview

As API traffic grows, we face a fundamental question: how do we handle more requests without degrading performance? The intuitive answer is to add more servers. But scaling is often a premature optimization.

Before reaching for more compute, ask a harder question: do you actually understand where your performance bottleneck is? Chapter 3 established that observability is the foundation of optimization. Without distributed traces showing where time is spent, without metrics revealing which resources are saturated, you are guessing. And guessing at scale is expensive.

The pattern we see repeatedly: a team scales horizontally to handle load, only to discover their database was the bottleneck all along. More application servers just meant more connections competing for the same slow queries. The fix was an index, not an autoscaling policy. Or the issue was a missing index, a connection pool misconfiguration, a missing cache layer (Chapter 6), or work that should have been asynchronous (Chapter 8). These optimizations can deliver 10x improvements. Scaling delivers linear improvements at linear cost.

This is not to say scaling does not matter. When you have genuinely exhausted optimization opportunities, when your traces show time is spent in application code rather than waiting on I/O, when your load tests (Chapter 13) confirm that more instances actually improve throughput, then scaling becomes the right tool.

But scaling is not one-dimensional. "Add more servers" is only one answer. When your database is the bottleneck, read replicas or sharding may provide more leverage than any amount of compute scaling. When traffic is unpredictable, serverless platforms handle scaling automatically without capacity planning. When content is cacheable, CDNs and edge caching scale delivery without touching your origin servers. The right scaling strategy depends on where the constraint lies.

This chapter covers all these dimensions. We begin with fundamental scaling concepts that apply regardless of platform, then examine platform-specific implementations (Kubernetes, serverless, VM-based auto scaling), and conclude with hybrid patterns that scale different parts of the system independently.

## Key Concepts

### Horizontal vs Vertical Scaling

When a service reaches its capacity limits, we have two fundamental options: make the existing instance bigger (vertical scaling) or add more instances (horizontal scaling).

**Vertical scaling** (scaling up) involves adding more resources (CPU, memory, faster storage) to an existing server. This approach has the advantage of simplicity: the application code requires no changes, there is no distributed coordination, and debugging remains straightforward. However, vertical scaling has hard limits. Eventually, we cannot buy a bigger machine, or the cost becomes prohibitive. Single-machine architectures also create a single point of failure.

**Horizontal scaling** (scaling out) involves adding more instances of a service behind a load balancer. This approach offers near-linear capacity growth and improved fault tolerance: if one instance fails, others continue serving traffic. However, horizontal scaling introduces complexity: we must handle distributed state, coordinate between instances, and manage the load balancer itself.

![Horizontal vs Vertical Scaling Comparison](../assets/ch09-scaling-comparison.html)

The choice between these approaches depends on several factors:

| Factor | Favors Vertical | Favors Horizontal |
|--------|-----------------|-------------------|
| Application state | Stateful, hard to distribute | Stateless or externalized state |
| Traffic pattern | Predictable, steady | Variable, spiky |
| Cost sensitivity | Lower traffic volumes | Higher traffic volumes |
| Fault tolerance | Less critical | Critical |
| Development complexity | Limited resources | Dedicated platform team |

In practice, most production systems use a hybrid approach: right-sized instances (vertical) combined with multiple replicas (horizontal). The Twelve-Factor App methodology established the principle that modern applications should scale horizontally via the process model.

### Stateless Service Design

Horizontal scaling requires stateless services. A stateless service does not store any client-specific data between requests, so each request can be handled by any instance without coordination.

This does not mean our applications have no state. Rather, we **externalize** state to dedicated storage systems:

- **Session data** moves from server memory to Redis or a database
- **File uploads** go to object storage (S3, GCS) rather than local disk
- **User preferences** live in a database, not in-memory caches

The benefits of stateless design extend beyond scaling. Stateless services are easier to deploy (no session draining), easier to debug (requests are independent), and more resilient (any instance can serve any request).

The key insight is that any instance can retrieve or update session data because Redis (or another external store) serves as the single source of truth.

### Auto-scaling Fundamentals

Regardless of platform, auto-scaling systems share common concepts. Understanding these fundamentals helps you configure any scaling system effectively.

#### The Scaling Decision Loop

Every auto-scaling system follows the same basic loop:

1. **Collect metrics** from running instances (CPU, memory, request rate, queue depth)
2. **Evaluate** metrics against configured thresholds or targets
3. **Decide** whether to scale up, scale down, or maintain current capacity
4. **Execute** the scaling action (add/remove instances)
5. **Wait** for stabilization before re-evaluating

```
periodically:
    current_value = measure metric (CPU, RPS, queue depth)
    desired_replicas = current_replicas * (current_value / target_value)

    if desired_replicas > current_replicas:
        scale up immediately
    if desired_replicas < current_replicas:
        wait stabilization window
        then scale down gradually
```

The specifics vary by platform, but this loop is universal.

![Auto-scaling Feedback Loop](../assets/ch09-autoscaling-loop.html)

#### Reactive vs Predictive Scaling

**Reactive scaling** responds to current conditions. When CPU exceeds 70%, add instances. When queue depth drops below 10, remove workers. This approach is simple and handles unexpected load, but it has inherent latency: by the time new instances are provisioned and warmed up, the spike may have already caused degraded performance.

**Predictive scaling** anticipates demand based on historical patterns. If traffic reliably increases at 9 AM on weekdays, scale up at 8:45 AM. If Black Friday traffic is 10x normal, pre-provision capacity the night before. Predictive scaling eliminates provisioning latency but requires predictable traffic patterns.

Most production systems combine both: predictive scaling handles known patterns while reactive scaling handles unexpected spikes.

#### Metrics for Scaling Decisions

The choice of scaling metric determines how well your system responds to load:

| Metric | Best For | Considerations |
|--------|----------|----------------|
| CPU utilization | Compute-bound workloads | Simple but may lag actual demand |
| Memory utilization | Memory-intensive applications | Often indicates resource leaks rather than load |
| Request rate (RPS) | HTTP APIs | Direct measure of demand |
| Queue depth | Async workers | Shows work backlog |
| Response latency | User-facing APIs | Ties scaling to user experience |
| Concurrent connections | WebSocket servers, databases | Shows active sessions |
| Custom business metrics | Domain-specific workloads | Most accurate but requires instrumentation |

A common mistake is scaling on a single metric. A service might have low CPU but high latency due to database contention. Multi-metric scaling considers several signals to make better decisions.

#### Scale-Up vs Scale-Down Asymmetry

Scaling up and scaling down have different risk profiles:

- **Scaling up too slowly** causes degraded performance or failures during traffic spikes
- **Scaling up too aggressively** wastes money but does not cause outages
- **Scaling down too slowly** wastes money but does not cause outages
- **Scaling down too aggressively** causes failures when traffic returns

This asymmetry suggests a strategy: scale up quickly, scale down gradually. Most auto-scaling systems support different thresholds and delays for scale-up versus scale-down actions.

#### Stabilization Windows and Cooldown

**Stabilization windows** prevent scaling decisions based on transient metric spikes. Rather than scaling immediately when a threshold is crossed, the system waits to confirm the condition persists. A 60-second stabilization window means CPU must stay above 70% for a full minute before triggering scale-up.

**Cooldown periods** prevent thrashing (rapid scale-up followed by immediate scale-down). After a scaling action, the system ignores metrics for a configured period, allowing the new capacity to absorb load before re-evaluating. Without cooldown, a system might add instances, see metrics drop, immediately remove them, see metrics spike, and repeat indefinitely.

Typical values range from 1-5 minutes for stabilization and 3-10 minutes for cooldown, but optimal values depend on your provisioning speed and traffic patterns.

#### Scale-to-Zero

Some platforms support scaling to zero instances when there is no traffic. This dramatically reduces costs for intermittent workloads (webhook handlers, batch processors, development environments) but introduces **cold start latency**: the delay while the platform provisions capacity to handle the first request.

Scale-to-zero is appropriate when:
- Workloads are truly intermittent (hours between requests)
- Cold start latency is acceptable (background jobs, async processing)
- Cost savings outweigh latency impact

Scale-to-zero is inappropriate when:
- Low latency is critical (user-facing APIs with SLOs)
- Traffic is continuous (always some requests in flight)
- Cold start time is long (heavy initialization, slow runtimes)

#### Right-Sizing: Vertical Scaling of Resources

Beyond adding or removing instances, systems benefit from right-sizing individual instance resources. An instance with too little memory pages to disk; one with too much wastes money. An instance with too few CPU cores queues requests; one with too many sits idle.

Right-sizing involves:
1. **Observing** actual resource usage over time
2. **Analyzing** usage patterns (steady, spiky, growing)
3. **Recommending** resource allocations that balance performance and cost
4. **Applying** recommendations (manually or automatically)

Some platforms automate this process; others require manual tuning based on monitoring data.

#### Two-Tier Scaling: Application and Infrastructure

In container orchestration and VM-based platforms, scaling happens at two levels:

1. **Application tier**: Scaling the number of application instances (pods, containers, tasks)
2. **Infrastructure tier**: Scaling the underlying compute capacity (nodes, VMs)

These tiers interact: application scaling can be blocked if infrastructure lacks capacity, and infrastructure scaling is triggered when application demand exceeds available resources. Effective scaling requires configuring both tiers to work together.

![Two-Tier Scaling Architecture](../assets/ch09-two-tier-scaling.html)

### Understanding Traffic Patterns

Effective scaling requires understanding your traffic patterns. The shape of your traffic determines which scaling strategy works best.

#### Diurnal Patterns

Most B2B APIs exhibit diurnal (daily) patterns tied to business hours. Traffic rises when offices open, peaks mid-morning, dips during lunch, peaks again in the afternoon, and drops overnight. The ratio between peak and trough can be 10:1 or higher.

Diurnal patterns are highly predictable, making them ideal for scheduled scaling. Scale up before the morning ramp begins, maintain capacity through business hours, and scale down after evening traffic subsides.

#### Weekly Patterns

Consumer-facing APIs often show weekly patterns: higher weekend traffic for entertainment services, higher weekday traffic for productivity tools. E-commerce sees traffic spikes on specific days (higher on Mondays for B2B, weekends for B2C).

Weekly patterns require longer baseline windows. Compare this Tuesday to last Tuesday, not to yesterday.

#### Burst Patterns

Some traffic arrives in unpredictable bursts: viral content, marketing campaigns, external events (news mentions, API integrations going live). Burst traffic can exceed baseline by 100x or more within minutes.

Bursts challenge reactive scaling because provisioning cannot keep pace. Mitigation strategies:

- **Headroom**: Maintain capacity above typical baseline (e.g., 2x average)
- **Pre-scaling**: Scale up before known events (product launches, marketing emails)
- **Rate limiting**: Protect the system when demand exceeds capacity (Chapter 10)
- **Queue-based buffering**: Absorb bursts into queues for processing at sustainable rates (Chapter 8)

#### Seasonal Patterns

Longer cycles affect capacity planning: holiday shopping seasons, back-to-school periods, tax season, annual events. These patterns are predictable but require advance planning because capacity additions may have lead times.

#### Traffic Pattern Analysis

Before choosing a scaling strategy, analyze your traffic:

1. **Collect baseline data**: At least 4 weeks of traffic data at 1-minute granularity
2. **Identify patterns**: Plot traffic by hour-of-day, day-of-week, and look for recurring shapes
3. **Measure variability**: Calculate coefficient of variation (standard deviation / mean) for different time windows
4. **Identify bursts**: Look for traffic spikes that exceed 3× the rolling average

Low variability with clear diurnal patterns → scheduled scaling works well. High variability with unpredictable bursts → reactive scaling with generous headroom. Predictable growth with seasonal peaks → capacity planning with reserved instances.

### Cost-Performance Tradeoffs

Optimization decisions are ultimately economic. Engineering time spent optimizing code has a cost; infrastructure resources have a cost; performance degradation has a cost in user experience and revenue. Effective optimization requires evaluating these tradeoffs explicitly.

#### The Optimization ROI Framework

Before investing engineering effort in optimization, estimate the return:

**Cost of engineering time**: A week of senior engineer time might cost $5,000-10,000 fully loaded. Will the optimization save more than that in infrastructure or user impact?

**Infrastructure savings**: Calculate current monthly spend on the bottleneck (compute, database, bandwidth). Realistic optimization might reduce usage by 20-50%. Is 20% of monthly spend greater than the engineering investment?

**User impact value**: Latency improvements affect conversion and engagement. Studies suggest 100ms latency improvement can increase revenue by 1% for e-commerce [Source: Akamai, 2017]. Quantify your traffic and conversion rates to estimate impact.

| Engineering Time | Monthly Infra Cost | Realistic Savings | Payback Period |
|------------------|-------------------|-------------------|----------------|
| 1 week ($7,500) | $10,000 | 30% ($3,000/mo) | 2.5 months |
| 2 weeks ($15,000) | $5,000 | 40% ($2,000/mo) | 7.5 months |
| 1 week ($7,500) | $50,000 | 20% ($10,000/mo) | < 1 month |

Quick wins with large infrastructure spend pay back fast. Complex optimizations with modest savings may never recoup investment.

#### When to Optimize vs When to Scale

Sometimes the right answer is more instances, not better code:

**Scale when**:
- Traffic is growing and optimization only defers the scaling problem
- Optimization complexity risks reliability (premature optimization)
- Engineering time is more valuable elsewhere (opportunity cost)
- The bottleneck is not your code (database, third-party API)

**Optimize when**:
- Resource costs are significant and growing
- Latency SLOs are threatened and scaling cannot reduce per-request latency
- The optimization is straightforward with clear payoff
- Technical debt from inefficient code will compound

A practical heuristic: if adding 30% more instances solves the problem for less than one week of engineering time, scale first. Optimize later when you have bandwidth and clearer data on bottlenecks.

#### Right-Sizing for Cost and Performance

Over-provisioning wastes money. Under-provisioning degrades performance. Right-sizing finds the balance.

**Utilization targets vary by resource:**

| Resource | Target Utilization | Rationale |
|----------|-------------------|-----------|
| CPU | 60-70% average | Headroom for traffic spikes |
| Memory | 70-80% average | Avoid OOM while maximizing cache |
| Database connections | 50-70% of max | Reserve for bursts |
| Network | < 50% of capacity | TCP performance degrades near saturation |

**Right-sizing process:**

1. **Measure actual usage**: Collect CPU, memory, network metrics at p50 and p95 over representative periods (include peak traffic)
2. **Identify over-provisioning**: Resources consistently below 30% utilization are oversized
3. **Test smaller sizes**: Reduce instance size or count and monitor performance metrics
4. **Iterate**: Continue until utilization approaches targets without SLO impact

Cloud provider tools (AWS Compute Optimizer, GCP Recommender) provide right-sizing recommendations based on observed usage. These recommendations are starting points. Validate with load testing before production changes.

**Reserved capacity vs on-demand:**

Committed use discounts (reserved instances, committed use contracts) offer 30-70% savings over on-demand pricing in exchange for 1-3 year commitments. The tradeoff:

- **On-demand**: Full flexibility, highest cost
- **Reserved/committed**: Lower cost, reduced flexibility
- **Savings plans**: Balance of savings and flexibility (commit to spend, not instance types)

For stable baseline capacity that will exist for 1+ years, reserved pricing significantly reduces costs. For variable or uncertain capacity, on-demand provides flexibility to right-size without stranded commitments.

### Cost Optimization with Spot Instances

Cloud providers offer significant discounts on spare compute capacity through spot instances (AWS), preemptible VMs (Google Cloud), and spot VMs (Azure). These instances cost 60-90% less than on-demand pricing but can be reclaimed with short notice when the provider needs the capacity.

![Spot Instance Fleet Architecture](../assets/ch09-spot-fleet-architecture.html)

Spot instances work well for workloads with these characteristics:

- **Stateless**: No data loss when instances terminate
- **Fault-tolerant**: Applications handle instance loss gracefully
- **Flexible timing**: Work can tolerate brief interruptions
- **Horizontally scalable**: Multiple small instances rather than single large ones

The primary challenge is handling interruptions. AWS provides a two-minute warning; Google Cloud provides 30 seconds. Applications must respond by completing in-flight work and checkpointing state.

**Instance diversification** is the key strategy for reliable spot usage. Rather than requesting a single instance type, specify multiple types across instance families and sizes. When one type is unavailable, the autoscaler uses alternatives.

A common architecture combines on-demand and spot capacity:

- **On-demand baseline**: Minimum instances for guaranteed capacity
- **Spot scaling layer**: Additional capacity for cost-effective burst handling
- **On-demand fallback**: Automatic fallback when spot is unavailable

### Graceful Shutdown and Health Checks

Regardless of platform, scaling down requires graceful shutdown. Abrupt termination drops in-flight requests, potentially corrupting data or leaving operations incomplete.

**Graceful shutdown** follows a sequence:

1. **Receive termination signal** (SIGTERM, platform-specific hook)
2. **Stop accepting new requests** (deregister from load balancer)
3. **Complete in-flight requests** (with a reasonable timeout)
4. **Close connections and release resources**
5. **Exit the process**

```
on SIGTERM received:
    stop accepting new requests
    set health check to unhealthy

    wait for in-flight requests to complete
        (up to grace period timeout)

    close database connections
    close other resources
    exit process
```

Most platforms provide a grace period between the termination signal and forced termination. Applications must complete shutdown within this window.

![Graceful Shutdown Lifecycle](../assets/ch09-graceful-shutdown.html)

**Health checks** communicate service status to load balancers and orchestrators. Two types serve different purposes:

- **Liveness checks**: "Is this instance alive?" Failure triggers restart. Use for detecting deadlocks or unrecoverable states.
- **Readiness checks**: "Can this instance serve traffic?" Failure removes from load balancer without restart. Use during startup or when dependencies are unavailable.

Implementing these patterns correctly requires coordinating application state, signal handling, and health endpoints.

## Scaling by Platform

The fundamentals above apply universally. This section examines how major platforms implement them, with platform-specific considerations and configurations.

### Kubernetes

Kubernetes provides sophisticated scaling capabilities through multiple autoscalers that can be combined for different workload patterns.

#### Horizontal Pod Autoscaler (HPA)

HPA scales the number of pod replicas based on observed metrics. It queries the Metrics API (for CPU/memory) or custom metrics adapters (for application-specific metrics) and adjusts replica counts to maintain target values.

The core scaling formula: `desiredReplicas = ceil(currentReplicas × (currentMetricValue / targetMetricValue))`

HPA supports multiple metrics simultaneously, scaling based on whichever metric requires the most capacity. This multi-metric approach handles scenarios where CPU is low but request rate is high.

Key configuration parameters:

| Parameter | Purpose | Guidance |
|-----------|---------|----------|
| minReplicas | Floor for scaling | Set based on fault tolerance requirements |
| maxReplicas | Ceiling for scaling | Set based on downstream capacity and budget |
| targetCPUUtilizationPercentage | CPU target | 50-70% leaves headroom for spikes |
| scaleDown.stabilizationWindowSeconds | Delay before scale-down | 300 seconds default; prevents thrashing |
| scaleUp.stabilizationWindowSeconds | Delay before scale-up | 0 default; immediate response to load |

#### Event-Driven Autoscaling with KEDA

The Kubernetes Event-Driven Autoscaler (KEDA) extends HPA to scale based on external event sources: message queues, databases, monitoring systems. KEDA supports 65+ scalers covering Kafka, SQS, RabbitMQ, Prometheus, and more.

![KEDA Architecture](../assets/ch09-keda-architecture.html)

KEDA's defining capability is **scale-to-zero**: reducing replicas to zero when no events are pending. For intermittent workloads, this can reduce compute costs by 70-90%.

| Parameter | Purpose | Guidance |
|-----------|---------|----------|
| pollingInterval | How often to check event sources | 15-30 seconds for most workloads |
| cooldownPeriod | Delay before scaling to zero | 300+ seconds; shorter risks premature scale-down |
| minReplicaCount | Floor (usually 0 or 1) | Use 1 if cold start latency is unacceptable |
| maxReplicaCount | Ceiling | Set based on downstream capacity |

#### Vertical Pod Autoscaler (VPA)

VPA right-sizes pod resource requests based on observed usage. It analyzes historical consumption and recommends (or applies) appropriate CPU and memory requests.

![VPA Components](../assets/ch09-vpa-components.html)

VPA operates in three modes:

| Mode | Behavior | Use Case |
|------|----------|----------|
| Off | Recommendations only | Evaluation, manual tuning |
| Initial | Apply only at pod creation | New pods right-sized; running pods unchanged |
| Auto | Continuously update pods | Fully automated (requires Pod Disruption Budgets) |

The critical limitation: VPA must evict pods to apply new requests, since Kubernetes does not support modifying running pods. Configure Pod Disruption Budgets to prevent simultaneous evictions.

**Combining HPA and VPA**: These can conflict when both scale on CPU. The recommended pattern is HPA on custom metrics (RPS, latency) with VPA managing resource sizing.

#### Cluster-Level Scaling

Pod autoscaling operates within cluster capacity constraints. When pods cannot be scheduled, cluster-level autoscalers provision nodes.

**Cluster Autoscaler** works with predefined node groups. It watches for pending pods and scales up the appropriate node group.

**Karpenter** provisions nodes dynamically without predefined groups. It evaluates pending pod requirements and provisions precisely-sized nodes, offering faster scale-up (30-60 seconds vs minutes) and better bin-packing efficiency.

| Aspect | Cluster Autoscaler | Karpenter |
|--------|-------------------|-----------|
| Node selection | Predefined node groups | Dynamic per-pod |
| Scale-up latency | Minutes | 30-60 seconds |
| Bin-packing | Limited by group granularity | High (right-sized nodes) |
| Platform support | All major clouds | AWS primary, GCP beta |

### Serverless Platforms

Serverless platforms (AWS Lambda, Google Cloud Functions, Azure Functions, Cloud Run, Cloudflare Workers) handle scaling automatically. You deploy code; the platform provisions capacity as needed.

#### The Serverless Scaling Model

Serverless scaling differs fundamentally from instance-based scaling:

- **Per-request provisioning**: Each request can get its own execution environment
- **Automatic concurrency**: Platform manages how many requests run simultaneously
- **Pay-per-use**: Billing based on invocations and duration, not reserved capacity
- **No infrastructure management**: No nodes to provision or maintain

This model excels for variable, unpredictable workloads. A function receiving 10 requests per hour and one receiving 10,000 requests per second can coexist without capacity planning.

#### The Cold Start Challenge

The trade-off is **cold starts**: the delay when the platform provisions a new execution environment.

![Serverless Cold Start Timeline](../assets/ch09-cold-start-timeline.html)

Cold start duration varies by runtime:
- Lightweight functions (Python, Node.js, Go): 100-500ms
- Heavier runtimes (Java, .NET): 500ms-3s
- Functions with many dependencies: Can exceed 5s

#### Mitigation Strategies

**Provisioned concurrency** (AWS Lambda) or **minimum instances** (Cloud Run) keep environments initialized, eliminating cold starts but incurring continuous cost.

**Keep-warm patterns** send periodic requests to prevent environment recycling. Cost-effective but does not help during traffic spikes.

**Initialization optimization** moves expensive operations outside the request handler. Database clients, SDK instances, and connection pools initialized at module level persist across invocations.

**Package size reduction** speeds loading. Remove unused dependencies, use tree-shaking, consider lighter frameworks.

**Runtime selection**: When cold start latency is critical, prefer runtimes with faster startup (Python, Node.js, Go).

#### When Serverless Scaling Works Well

Serverless is ideal for:
- Variable, unpredictable traffic patterns
- Event-driven workloads (webhooks, queue processors)
- APIs with tolerance for occasional latency spikes
- Development and staging environments

Serverless is less suitable for:
- Consistent high-throughput workloads (always-on is cheaper)
- Strict latency SLOs that cold starts would violate
- Long-running processes (platform time limits apply)

### VM Auto Scaling Groups

Traditional VM-based auto scaling remains widely used, especially for workloads not containerized or where teams prefer infrastructure-level abstraction.

#### Platform Services

- **AWS Auto Scaling Groups (ASG)**: Manages EC2 instance pools
- **Google Cloud Managed Instance Groups (MIG)**: Manages Compute Engine VMs
- **Azure VM Scale Sets (VMSS)**: Manages Azure VM pools

These services manage pools of identical VM instances, automatically adding or removing based on scaling policies.

#### Scaling Policies

**Target tracking policies** maintain a metric at a target value. "Keep average CPU at 50%" automatically adjusts instance count. This is the simplest approach and works well for steady-state scaling.

**Step scaling policies** define specific actions for metric ranges. "If CPU > 70%, add 2 instances. If CPU > 90%, add 5 instances." This provides more control but requires more configuration.

**Scheduled scaling** adjusts capacity on a schedule. "Scale to 20 instances at 8 AM, scale to 5 instances at 8 PM." This handles predictable patterns without metric lag.

**Predictive scaling** (AWS) uses machine learning to forecast demand based on historical patterns, pre-provisioning capacity before predicted traffic increases.

#### Configuration Parameters

| Parameter | Purpose | Typical Value |
|-----------|---------|---------------|
| Min size | Minimum instances | Based on fault tolerance |
| Max size | Maximum instances | Based on budget and downstream capacity |
| Health check grace period | Ignore health during startup | 300+ seconds for slow-starting apps |
| Cooldown | Delay between scaling actions | 300 seconds |
| Warm pool | Pre-initialized stopped instances | Reduces scale-up latency |

**Warm pools** keep stopped (but initialized) instances ready to start quickly. This reduces scale-up latency from minutes (full provisioning) to seconds (just starting the VM).

#### Lifecycle Hooks

Lifecycle hooks run scripts at key moments:
- **Launch hooks**: Run after instance starts but before receiving traffic (install agents, warm caches)
- **Termination hooks**: Run before instance terminates (drain connections, save state)

These hooks implement graceful startup and shutdown at the infrastructure level.

### Hybrid Scaling Patterns

Real-world scaling often combines compute scaling with data and architectural patterns. These hybrid approaches scale different dimensions of the system independently.

#### Read Replicas

When read traffic exceeds write traffic (common in most applications), read replicas scale the read path without affecting write capacity. The primary database handles all writes; replicas receive changes through replication and serve read queries.

**How it works:**
- Write queries go to the primary database
- Read queries are distributed across replicas
- Replication lag means replicas may be slightly behind (eventual consistency)

**When to use:**
- Read-heavy workloads (10:1 or higher read-to-write ratio)
- Reporting and analytics queries that should not impact production writes
- Geographic distribution (replicas closer to users)

**Considerations:**
- Replication lag can cause stale reads; design for eventual consistency
- Connection routing adds complexity (application or proxy must route appropriately)
- Cross-region replication adds latency to writes if synchronous

#### CQRS (Command Query Responsibility Segregation)

CQRS separates read and write models entirely, allowing each to scale independently with optimized data structures.

**How it works:**
- Commands (writes) update a write-optimized store
- Events propagate changes to read-optimized projections
- Queries read from projections tailored to specific use cases

**When to use:**
- Complex domains where read and write models differ significantly
- High-scale reads with complex aggregations
- Event-sourced systems where projections provide different views

**Considerations:**
- Eventual consistency between write and read models
- Increased system complexity
- More infrastructure to manage

#### Database Sharding

Sharding horizontally partitions data across multiple database instances. Each shard contains a subset of the data, determined by a shard key.

**How it works:**
- A shard key (e.g., user_id, tenant_id) determines which shard holds the data
- Queries including the shard key route to a single shard
- Cross-shard queries require scatter-gather across all shards

**When to use:**
- Dataset exceeds single-instance capacity
- Write throughput exceeds single-instance limits
- Multi-tenant systems with natural partition boundaries

**Considerations:**
- Cross-shard queries are expensive; design access patterns around the shard key
- Resharding (adding shards) is operationally complex
- Transactions across shards require distributed coordination

#### CDN and Edge Caching

Content Delivery Networks scale content delivery by caching at edge locations worldwide. This offloads traffic from origin servers and reduces latency for users.

**How it works:**
- Static content (images, JS, CSS) cached indefinitely at edge
- Dynamic content cached with appropriate TTLs and invalidation
- Edge can handle TLS termination, compression, and basic request filtering

**When to use:**
- Static assets (always)
- API responses that are cacheable (same response for same request)
- Geographic user distribution

**Considerations:**
- Cache invalidation complexity
- Cache key design affects hit rates
- Origin shield can reduce origin load for cache misses

Chapter 12 covers edge computing patterns in depth.

#### Service Decomposition

As systems grow, decomposing monoliths into services allows independent scaling of different functions.

**How it works:**
- Identify bounded contexts or high-load components
- Extract into separate services with clear APIs
- Scale each service based on its specific load characteristics

**When to use:**
- Different components have vastly different scaling needs
- Team autonomy requires independent deployments
- Specific functions bottleneck the entire system

**Considerations:**
- Network calls replace in-process calls (latency, failure modes)
- Distributed systems complexity
- Start with a monolith; decompose when needed, not preemptively

## Common Pitfalls

- **Scaling before profiling**: Adding instances when the real bottleneck is database queries, missing indexes, or inefficient code. Always profile first.

- **Storing state in memory**: Session data stored in server memory breaks when requests hit different instances. Always externalize state.

- **Single-metric auto-scaling**: Scaling only on CPU misses memory pressure, database connection exhaustion, or upstream saturation. Use multiple metrics.

- **Identical scale-up and scale-down behavior**: Aggressive scale-down causes failures when traffic returns. Scale up quickly, scale down gradually.

- **Missing graceful shutdown**: Instances killed without draining in-flight requests cause errors. Always handle termination signals.

- **Health checks that lie**: A readiness probe returning healthy during startup causes failed requests. Only report ready when truly ready.

- **Health check tooling missing from container images**: Slim and distroless container images strip system utilities to reduce image size and attack surface. A health check command that relies on `curl` or `wget` silently fails when those tools are absent, and orchestrators like ECS or Kubernetes interpret the failure as an unhealthy container. The result is a crash loop: the container starts, passes no health checks, gets killed, restarts, and repeats, dropping connections and creating metric gaps every few minutes. Use the language runtime for health checks instead: Python's `urllib`, Node's `http.get`, Go's `net/http`, or a dedicated health check binary baked into the image. Never assume system tools exist in production images.

- **Ignoring cold start impact**: Serverless functions with slow initialization degrade user experience. Profile cold starts and consider provisioned concurrency.

- **Scaling without load testing**: Assuming more instances will help without validating linear scaling. Test scaling behavior before relying on it.

- **No infrastructure-level scaling**: Pod autoscaling cannot add capacity beyond cluster limits. Ensure cluster-level autoscaling is configured.

- **Critical workloads on spot instances**: Running databases or single points of failure on interruptible instances causes outages. Reserve spot for stateless, fault-tolerant workloads.

## Summary

- **Scaling is often premature optimization**. Profile first (Chapter 3), optimize bottlenecks (Chapters 6-8), then scale when compute is genuinely the constraint.

- **Horizontal scaling** adds instances and requires stateless services; **vertical scaling** adds resources to existing instances. Most systems use both.

- **Auto-scaling fundamentals** are universal: reactive vs predictive scaling, metric selection, stabilization windows, scale-up/scale-down asymmetry, and scale-to-zero trade-offs.

- **Traffic patterns** (diurnal, weekly, burst, seasonal) determine which scaling strategy works best. Analyze your patterns before configuring autoscaling.

- **Kubernetes** offers HPA (metric-based), KEDA (event-driven with scale-to-zero), VPA (right-sizing), and cluster autoscalers (node provisioning).

- **Serverless platforms** handle scaling automatically but introduce cold starts. Mitigate with provisioned concurrency, initialization optimization, and appropriate runtime selection.

- **VM auto scaling groups** remain effective for non-containerized workloads. Target tracking policies handle most cases; warm pools reduce scale-up latency.

- **Spot instances** offer 60-90% cost savings for fault-tolerant workloads. Diversify instance types and maintain on-demand baseline.

- **Hybrid scaling patterns** address real-world complexity: read replicas scale reads independently, CQRS separates read/write models, sharding partitions data, CDNs offload content delivery, and service decomposition enables independent scaling of components.

- **Graceful shutdown and health checks** are essential regardless of platform. Handle termination signals, drain connections, and report health accurately.

## References

1. **Heroku** (2011). "The Twelve-Factor App." https://12factor.net/

2. **Kubernetes Documentation** (2024). "Horizontal Pod Autoscaling." https://kubernetes.io/docs/tasks/run-application/horizontal-pod-autoscale/

3. **KEDA Documentation** (2024). "Scaling Deployments." https://keda.sh/docs/

4. **Kubernetes Documentation** (2024). "Vertical Pod Autoscaler." https://kubernetes.io/docs/concepts/workloads/autoscaling/

5. **Karpenter Documentation** (2024). https://karpenter.sh/docs/

6. **AWS Lambda Documentation**. "Operating Lambda: Performance optimization." https://docs.aws.amazon.com/lambda/latest/operatorguide/perf-optimize.html

7. **AWS Auto Scaling Documentation**. "Target tracking scaling policies." https://docs.aws.amazon.com/autoscaling/ec2/userguide/as-scaling-target-tracking.html

8. **Google Cloud Run Documentation**. "Configuring minimum instances." https://cloud.google.com/run/docs/configuring/min-instances

## Next: [Chapter 10: Traffic Management and Resilience](./10-traffic-management.md)

With our services scaling effectively, we now turn to protecting them from overload and cascading failures. The next chapter covers rate limiting, circuit breakers, and the resilience patterns that keep services stable under adverse conditions.
