# Chapter 10: Traffic Management and Resilience

![Chapter 10 Opener](../assets/ch10-opener.html)

\newpage

## Overview

Even the most optimized API will eventually face conditions that exceed its capacity. Traffic spikes, dependency failures, network partitions, and resource exhaustion are not edge cases but inevitabilities in distributed systems. The difference between a system that gracefully handles these conditions and one that cascades into complete failure lies in deliberate traffic management and resilience engineering.

This chapter explores the patterns that protect our APIs when things go wrong. We will examine rate limiting algorithms that prevent resource exhaustion, circuit breakers that fail fast when dependencies are unhealthy, load balancing strategies that distribute work effectively, bulkhead patterns that isolate failures, and retry strategies that recover from transient errors without overwhelming recovering services. These patterns, pioneered by companies like Netflix and Amazon and now codified in libraries like Resilience4j, form the foundation of reliable distributed systems.

The philosophy here is pragmatic: we assume failures will happen and design our systems to contain their blast radius. Every pattern we discuss involves trade-offs between throughput, latency, resource utilization, and complexity. Our goal is to equip you with the knowledge to make informed decisions about which patterns to apply and how to configure them for your specific requirements.

<!-- DIAGRAM: High-level resilience architecture showing: Client requests -> Rate Limiter -> Load Balancer -> Circuit Breaker -> Bulkhead -> Service, with arrows showing where each pattern intervenes -->

![Resilience Architecture](../assets/ch10-resilience-architecture.html)

## Key Concepts

### Rate Limiting Algorithms

Rate limiting controls the number of requests a client or system can make within a time window. Without rate limiting, a single misbehaving client or sudden traffic spike can exhaust resources and deny service to everyone. The choice of algorithm affects how strictly we enforce limits and how we handle burst traffic.

#### Token Bucket Algorithm

Token bucket dominates rate limiting implementations because it matches how legitimate clients actually behave: idle periods followed by bursts of activity.

The mechanism has two parameters. The *refill rate* controls sustained throughput: 100 tokens per second means 100 requests per second over the long term. The *bucket capacity* controls burst tolerance: a capacity of 500 means a client can send 500 requests instantly if they have been idle, but then must wait for refills.

This two-parameter design is why token bucket works well for user-facing APIs. A mobile app that opens and makes 20 API calls in 2 seconds, then goes idle for a minute, behaves very differently from a script hammering the API at a steady 10 requests per second. Both average 0.33 RPS, but they feel completely different. Token bucket permits the bursty human pattern while throttling the steady automated pattern, which is usually the desired behavior.

The predictability also helps. Clients can calculate their own limits: idle time accumulates tokens up to the capacity cap, activity drains them at one per request. This transparency reduces the "why am I being rate limited?" support burden compared to algorithms whose behavior is harder to reason about.

#### Leaky Bucket Algorithm

The leaky bucket processes requests at a constant rate, regardless of input burstiness. Incoming requests enter a queue (the bucket), and requests leave the queue (leak out) at a fixed rate. If the queue fills up, new requests are rejected.

Unlike the token bucket, the leaky bucket smooths output rather than allowing bursts. This is valuable when downstream services require steady traffic or when we need to shape traffic to match a specific throughput limit. However, it introduces latency as requests wait in the queue.

The leaky bucket is commonly used in network traffic shaping and quality-of-service implementations where consistent throughput matters more than minimizing individual request latency.

#### Sliding Window Algorithm

Fixed window rate limiting divides time into discrete intervals (e.g., one-minute windows) and counts requests per window. The problem: a client could make their entire quota at the end of one window and the beginning of the next, effectively doubling their allowed rate across the boundary.

The sliding window algorithm addresses this by weighting requests from the previous window. A common approach calculates: `requests in current window + (requests in previous window * overlap percentage)`. This provides smoother rate limiting without the boundary spike problem.

Sliding window requires tracking requests across two windows, which increases memory usage slightly. However, the improved accuracy usually justifies the cost. Redis and similar systems provide efficient primitives for implementing sliding window rate limiting in distributed environments.

<!-- DIAGRAM: Comparison of fixed window vs sliding window rate limiting showing: Fixed window with boundary spike (requests clustered at window boundaries), Sliding window with smooth enforcement (consistent rate across boundaries) -->

![Rate Limiting Comparison](../assets/ch10-rate-limiting-comparison.html)

For rate limiting at the CDN edge, including distributed state challenges and edge-specific configuration patterns, see [Chapter 12: Edge Infrastructure](./12-edge-infrastructure.md).

### Adaptive Concurrency Limits

Static concurrency limits (hard-coded maximum connections or request rates) are educated guesses that rarely match actual system capacity. When traffic patterns change, deployments occur, or dependencies slow down, these fixed limits either reject valid requests unnecessarily or allow overload. Netflix pioneered an alternative: adaptive concurrency limits that automatically discover and adjust to the system's true capacity [Source: Netflix Tech Blog, 2018].

The foundation is Little's Law from queuing theory: at steady state, the number of requests in a system (L) equals the arrival rate (lambda) multiplied by the average time spent in the system (W). Rearranging: concurrency = arrival rate × latency. Any requests exceeding this concurrency cannot be immediately serviced. They must queue or be rejected. Without limits on this queue, systems accumulate requests until they exhaust memory or timeout, cascading into complete failure.

<!-- DIAGRAM: Adaptive concurrency feedback loop showing: Request arrives -> Check against current limit -> If under limit, process and measure latency -> Calculate new limit based on gradient algorithm (comparing sampleRTT to minRTT) -> Loop continues. Show reject path when over limit (HTTP 503) -->

![Adaptive Concurrency Feedback Loop](../assets/ch10-adaptive-concurrency.html)

Adaptive algorithms measure actual system performance and adjust limits dynamically:

**Gradient Algorithm**: The gradient algorithm maintains an estimate of the minimum round-trip time (minRTT) observed during healthy operation. Periodically, it samples recent request latencies (sampleRTT) and calculates a gradient: `gradient = minRTT / sampleRTT`. When latency increases (sampleRTT > minRTT), the gradient falls below 1.0, signaling congestion. The algorithm reduces the concurrency limit. When latency returns to baseline, the gradient approaches 1.0, and the limit can increase.

The concurrency limit update follows: `newLimit = currentLimit × gradient + queueSize`. The queueSize term allows gradual increase when capacity is available. A smoothing factor prevents oscillation from noisy measurements.

**AIMD (Additive Increase Multiplicative Decrease)**: Borrowed from TCP congestion control, AIMD increases limits linearly during success and decreases them multiplicatively on failure. This asymmetric response quickly backs off during overload while gradually probing for additional capacity during normal operation.

Netflix's open-source concurrency-limits library implements both algorithms with guidance on when to use each:

| Algorithm | Best For | Behavior |
|-----------|----------|----------|
| Vegas (Gradient) | Server-side limiting | Proactive, uses latency signals |
| AIMD | Client-side limiting | Reactive, uses error signals |

**Envoy's Implementation**: The Envoy proxy implements adaptive concurrency as an HTTP filter, making it available to any service without code changes. Envoy's implementation samples latency over configurable windows, calculates the gradient, and adjusts the maximum concurrent requests dynamically. Requests exceeding the limit receive HTTP 503 with a specific error message, enabling clients to back off appropriately [Source: Envoy Documentation, 2024].

The key insight is that adaptive concurrency limits serve a different purpose than rate limiting. Rate limiting protects against abusive clients by capping requests per time window. Adaptive concurrency protects the service itself by limiting how much work can be in flight simultaneously. Both are valuable; they operate at different points in the request lifecycle and address different failure modes.

**Comparison with static limits:**

| Aspect | Static Limits | Adaptive Limits |
|--------|--------------|-----------------|
| Configuration | Requires tuning per service | Self-adjusting |
| Response to change | Manual adjustment needed | Automatic adaptation |
| Overload behavior | May reject too early or too late | Rejects based on actual capacity |
| Cold start | Immediate enforcement | Needs warm-up period |
| Complexity | Simple to understand | More sophisticated |

When implementing adaptive concurrency, start with conservative initial limits and allow the algorithm time to converge. Monitor the limit values and rejection rates during deployment. In practice, services often discover they can handle 2-3x the traffic that static limits allowed, or conversely, that they were accepting requests they could not actually serve.

### Circuit Breaker Pattern

The circuit breaker pattern prevents an application from repeatedly trying to execute an operation that is likely to fail. Like an electrical circuit breaker, it "trips" when failures exceed a threshold, failing fast instead of waiting for timeouts.

The pattern originated at Netflix, documented in their Hystrix library. While Hystrix is now in maintenance mode, the patterns it established have been adopted by libraries like Resilience4j, Sentinel, and Polly, and are built into service meshes like Istio and Envoy [Source: Netflix Hystrix Wiki, 2018].

#### Circuit Breaker States

The naming convention for circuit breaker states confuses everyone initially because it describes the *circuit*, not the *gate*. An open circuit blocks flow; a closed circuit allows it. This is backwards from how we typically think about gates and doors.

The three states represent a progression from trust to distrust and back:

**Closed** means the breaker trusts the downstream service. Requests flow through while the breaker silently tracks outcomes. When failures cross a threshold (commonly 50% of the last 10-20 requests), trust is revoked and the state changes.

**Open** means the breaker has lost trust. Every request fails immediately with a predetermined error, typically within microseconds. No attempt is made to contact the downstream service. This instant failure sounds harsh, but it prevents threads from piling up waiting for timeouts from a service that cannot respond. After a cooling-off period (30-60 seconds is typical), the breaker cautiously tests whether trust can be restored.

**Half-Open** is the probationary period. A small number of requests (often just one) are permitted through. Success transitions back to Closed; failure returns to Open with the timer reset. This graduated recovery prevents a stampede of pent-up requests from immediately overwhelming a service that has just recovered.

<!-- DIAGRAM: Circuit breaker state machine: Closed (normal) -[failures exceed threshold]-> Open (fail fast) -[timeout expires]-> Half-Open (test) -[success]-> Closed OR -[failure]-> Open, with annotations for each transition condition -->

![Circuit Breaker State Machine](../assets/ch10-circuit-breaker-states.html)

#### Configuring Circuit Breakers

Effective circuit breaker configuration requires understanding your service's failure modes:

**Failure Rate Threshold**: The percentage of failures that trips the circuit. A threshold of 50% is common, but latency-sensitive services may use lower values (25-30%) to fail fast before users notice degradation.

**Minimum Request Volume**: The minimum number of requests before the failure rate is evaluated. This prevents the circuit from tripping on the first few requests. A value of 10-20 requests is typical for services with moderate traffic.

**Wait Duration in Open State**: How long to wait before testing recovery. Too short risks hammering a recovering service; too long delays recovery unnecessarily. Starting with 30-60 seconds and adjusting based on observed recovery times works well.

**Permitted Calls in Half-Open**: How many test requests to allow. One is safest but delays recovery confirmation. Three to five requests provide faster confirmation while limiting exposure.

### Deadline Propagation

Deadline propagation ensures that latency budgets flow through a distributed system. When a user-facing service has a 500ms SLO, downstream services need to know how much time remains, not just their individual timeout, but the overall deadline for the entire request chain.

#### The Problem with Independent Timeouts

Consider a request that passes through three services sequentially, each with a 200ms timeout: Gateway to Auth to Database. If Auth takes 150ms and Database takes 180ms, the total is 330ms. Each service "succeeded" within its individual timeout, but the gateway's 200ms timeout already fired. The user sees a timeout error even though every downstream call "worked."

Independent timeouts don't compose. Deadline propagation solves this by sharing a single end-to-end deadline across all services.

#### How Deadline Propagation Works

The originating service calculates an absolute deadline (current time plus SLO budget) and passes it to downstream services via a header such as `X-Request-Deadline` containing a Unix timestamp in milliseconds. Each downstream service:

1. **Reads the deadline** from the incoming request header
2. **Checks remaining time**: If the deadline has already passed, fail immediately without doing work
3. **Sets local timeout**: Use the remaining time (deadline minus current time) as the timeout for any operations
4. **Propagates the deadline**: Pass the same header to any further downstream calls

#### Header Conventions

Several conventions exist for deadline headers:

- **gRPC**: Uses `grpc-timeout` header with relative duration (e.g., `500m` for 500 milliseconds)
- **Custom HTTP**: `X-Request-Deadline` with absolute Unix timestamp is common
- **OpenTelemetry**: Baggage can carry deadline information alongside trace context

Absolute timestamps avoid clock drift issues when services run on different machines, provided clocks are synchronized via NTP.

#### Implementation Considerations

**Fail fast on expired deadlines**: When a request arrives with an already-passed deadline, return immediately. There is no point in doing work that the caller has already abandoned. The middleware should check the deadline header against current time and raise an exception if the deadline has passed.

**Reserve buffer time**: Don't use 100% of remaining time. If 50ms remains, set a 40ms timeout to allow for response transmission and processing. A common pattern reserves 10ms buffer while ensuring at least 1ms timeout remains.

**Propagate on async boundaries**: When requests cross message queues or spawn background tasks, the deadline must travel with the work. Include deadline in message metadata.

**Handle missing deadlines gracefully**: Not all callers will send deadlines. Fall back to default timeouts when the header is absent.

#### Deadline Propagation vs Circuit Breakers

These patterns complement each other:

- **Deadline propagation** handles the happy path: ensuring requests complete within budget even when services are healthy but slow
- **Circuit breakers** handle the failure path: preventing requests from even attempting calls to unhealthy services

A request might be rejected by a circuit breaker (service unhealthy) or by deadline checking (no time remaining). Both protect the system, but at different points in the request lifecycle.

### Load Balancing Strategies

Load balancing distributes requests across multiple service instances. The choice of algorithm affects latency, throughput, and resilience to individual instance failures.

#### Round-Robin

Round-robin distributes requests sequentially across all healthy instances. It is simple, predictable, and requires no state beyond the current position in the rotation.

The limitation: round-robin assumes all instances have equal capacity and all requests have equal cost. When instances have different resources or requests have varying complexity, round-robin can create imbalances.

#### Least Connections

Least connections routes requests to the instance with the fewest active connections. This naturally balances load based on actual instance utilization and adapts to varying request durations.

Least connections requires tracking connection counts across instances, which adds overhead. It works well when request processing times vary significantly and instances have similar capacity.

#### Weighted Distribution

Weighted distribution assigns different weights to instances based on their capacity. An instance with weight 2 receives twice the traffic of an instance with weight 1.

This strategy enables gradual rollouts (new version starts with low weight), heterogeneous deployments (larger instances get more traffic), and graceful degradation (reduce weight of struggling instances rather than removing them entirely).

#### Consistent Hashing

Consistent hashing routes requests based on a hash of some request attribute (user ID, session ID, request key). The same key always routes to the same instance, enabling effective caching and session affinity.

The "consistent" part means that when instances are added or removed, only a fraction of keys remap to new instances, rather than reshuffling everything. This stability is valuable for caching layers where remapping causes cache misses.

<!-- DIAGRAM: Load balancing strategies comparison: Round-robin (sequential distribution to 3 servers: 1,2,3,1,2,3), Least-connections (preference to server with fewer active connections), Consistent hashing (same user always routes to same server based on hash) -->

![Load Balancing Strategies](../assets/ch10-load-balancing-strategies.html)

### Service Mesh Traffic Management

Service meshes like Istio and Linkerd move traffic management from application code to infrastructure, providing sophisticated routing, load balancing, and resilience capabilities without code changes. For API optimization, service meshes offer several capabilities that complement application-level patterns.

A service mesh deploys a sidecar proxy (typically Envoy) alongside each service instance. All traffic flows through these proxies, which enforce policies defined in mesh configuration. The control plane (Istiod in Istio's case) distributes configuration to the proxies and collects telemetry [Source: Istio Documentation, 2024].

<!-- DIAGRAM: Service mesh traffic flow showing: Client -> Ingress Gateway -> VirtualService routing rules -> DestinationRule policies -> Envoy sidecar -> Service Pod. Annotate each component's role in traffic management -->

![Service Mesh Traffic Flow](../assets/ch10-service-mesh-traffic.html)

**Virtual Services** define routing rules that determine how requests reach services:

- **Traffic splitting**: Route percentages of traffic to different service versions for canary deployments. Send 5% of traffic to v2 while 95% continues to v1.
- **Header-based routing**: Route requests based on HTTP headers, enabling feature flags or A/B testing at the infrastructure level.
- **Request matching**: Route based on URI path, query parameters, or headers for fine-grained traffic control.

**Destination Rules** define policies that apply after routing decisions:

- **Load balancing algorithms**: Configure round-robin, least connections, random, or consistent hashing per destination.
- **Connection pool settings**: Limit maximum connections, pending requests, and requests per connection to prevent resource exhaustion.
- **Outlier detection**: Automatically eject unhealthy instances from the load balancing pool based on consecutive errors or latency.

Outlier detection deserves particular attention for resilience. The mesh monitors each endpoint and tracks consecutive errors (5xx responses, connection failures). When errors exceed a threshold, the endpoint is ejected from the pool for a configurable interval. After the ejection period, traffic resumes gradually. This pattern implements circuit breaking at the infrastructure level without application code changes.

**When Service Mesh Adds Value:**

- Multiple services need consistent traffic policies
- Teams use different languages/frameworks but need uniform resilience
- Canary deployments and traffic shifting are frequent
- You need mTLS between services without application changes
- Observability gaps exist in service-to-service communication

**When Service Mesh Adds Complexity Without Proportionate Benefit:**

- Few services or simple topologies
- Team already has mature resilience patterns in application code
- Latency requirements are extreme (sidecars add ~1-2ms per hop)
- Operational capacity is limited for mesh management

The mesh does not replace application-level resilience entirely. Timeout values, retry budgets, and fallback logic often require application context. The mesh provides infrastructure-level defaults; applications customize behavior where needed.

### Bulkhead Pattern

The bulkhead pattern isolates failures by partitioning resources. Named after the watertight compartments in ships, bulkheads prevent a failure in one area from flooding the entire system.

In practice, bulkheads create separate resource pools for different operations or dependencies. If a slow dependency exhausts its pool, other operations continue unaffected. Without bulkheads, a single slow dependency can consume all available threads or connections, causing complete system failure.

#### Thread Pool Bulkheads

Thread pool bulkheads assign dedicated thread pools to different dependencies or operation types. If the payment service slows down and exhausts its pool of 10 threads, the order service's separate pool of 20 threads continues functioning normally.

The trade-off is resource efficiency: dedicated pools may sit idle while other pools are exhausted. Some implementations allow stealing from idle pools while maintaining minimum guaranteed resources.

#### Semaphore Bulkheads

Semaphore bulkheads use counting semaphores to limit concurrent operations without dedicating threads. A semaphore limits how many requests to a dependency can be in flight simultaneously. When the limit is reached, new requests either wait (with timeout) or fail fast.

Semaphore bulkheads are more memory-efficient than thread pools but do not provide the same isolation guarantees. They are suitable when the goal is limiting concurrency rather than complete resource isolation.

<!-- DIAGRAM: Bulkhead pattern showing isolated resource pools: Service A pool (5 connections) at 80% capacity, Service B pool (10 connections) at 100% and blocking, Service C pool (3 connections) at 30% capacity. Annotation: "Service B exhaustion does not affect A or C" -->

![Bulkhead Pattern](../assets/ch10-bulkhead-pattern.html)

### Graceful Degradation Strategies

Circuit breakers fail fast when dependencies are unhealthy, but simply returning errors is not always the best user experience. Graceful degradation provides partial functionality when full functionality is unavailable, maintaining value for users even during failures.

The key insight is that not all features are equally important. When capacity is constrained or dependencies fail, systems can shed less critical work while protecting core functionality. A product page can display without personalized recommendations. A dashboard can show cached data rather than real-time metrics. A search can return fewer results faster rather than timing out.

<!-- DIAGRAM: Degradation hierarchy pyramid showing layers from bottom to top: Unavailable (503 error), Minimal (static fallback), Partial (cached/stale data), Full Service (real-time, complete). Each layer shows what features are available and example scenarios -->

![Graceful Degradation Hierarchy](../assets/ch10-graceful-degradation.html)

**Feature Flags for Runtime Resilience**

Feature flags are often associated with A/B testing and gradual rollouts, but they serve equally well as kill switches during incidents. When a recommendation service is overloaded, disable recommendations at the flag rather than waiting for timeouts. When a third-party API experiences latency, switch to cached results via flag.

This requires pre-planning: identify which features can be disabled safely, implement fallback behavior behind flags, and document the degradation paths. During incidents, operators can disable features without code deployments, reducing time to mitigation.

**Priority-Based Load Shedding**

Not all requests are equally important. During overload, systems can prioritize based on:

- **User tier**: Premium users get resources before free users
- **Request type**: Read operations continue while writes queue
- **Endpoint criticality**: Checkout continues while analytics pauses
- **SLA commitments**: Requests with contractual guarantees take precedence

Priority can be communicated via headers (`X-Priority: high`), extracted from authentication tokens (user tier), or inferred from the endpoint. Load shedding then rejects low-priority requests first, preserving capacity for critical operations.

**Stale Data as Fallback**

When real-time data is unavailable, stale data is often better than no data. Cache-Control headers with `stale-while-revalidate` and `stale-if-error` directives enable this at the HTTP level: serve cached responses while fetching fresh data, or serve stale data when the origin fails.

For application-level caching, implement explicit fallbacks: if the database query fails, return the last successful result (if recent enough). Include staleness indicators in responses so clients can display appropriate warnings ("Data from 5 minutes ago").

**Degradation Hierarchies**

Design degradation as a series of steps rather than binary available/unavailable:

| Level | Behavior | Example |
|-------|----------|---------|
| Full | All features, real-time data | Normal operation |
| Partial | Core features, cached data | Recommendations disabled, products from cache |
| Minimal | Essential operations only | Browse and search work, checkout uses fallback |
| Static | Static content, queued writes | Informational pages, "try again later" for actions |
| Unavailable | Error page | Maintenance page with status information |

The goal is to slide down this hierarchy smoothly as conditions worsen, rather than falling immediately from full service to error pages.

**Implementing Degradation**

Effective degradation requires:

1. **Identifying degradation triggers**: High latency, error rates, circuit breaker state, feature flag status
2. **Defining fallback behavior**: What does each feature do when degraded?
3. **Communicating degradation**: Headers or response fields indicating degraded mode
4. **Testing degradation paths**: Regular testing ensures fallbacks actually work
5. **Monitoring degradation frequency**: Frequent degradation indicates underlying issues

### Retry Strategies with Exponential Backoff

Transient failures are common in distributed systems: network blips, temporary overload, garbage collection pauses. Retrying failed requests can recover from these issues without user impact. However, naive retries can overwhelm recovering services and extend outages.

#### Exponential Backoff

Exponential backoff increases the delay between retries multiplicatively: 1 second, 2 seconds, 4 seconds, 8 seconds, and so on. This gives services progressively more time to recover and prevents a thundering herd of retry attempts.

The formula is typically: `delay = base_delay * (2 ^ attempt_number)`, capped at a maximum delay. Common configurations use a base delay of 100ms to 1 second and a maximum delay of 30-60 seconds.

#### Adding Jitter

Even with exponential backoff, if many clients start retrying at the same time, their retry attempts synchronize and create periodic load spikes. Adding jitter (randomization) to retry delays spreads retries over time.

Full jitter chooses a random delay between 0 and the calculated backoff: `delay = random(0, base_delay * 2^attempt)`. Equal jitter splits the difference: `delay = (base_delay * 2^attempt) / 2 + random(0, base_delay * 2^attempt / 2)`.

AWS recommends full jitter for most use cases, as it provides the best distribution of retry attempts over time [Source: AWS Architecture Blog, "Exponential Backoff And Jitter"].

#### Retry Budgets

A retry budget limits the total retry rate across all clients rather than per-client. If the system allows 10% retry budget, only 10% of requests can be retries; when the budget is exhausted, clients do not retry.

Retry budgets prevent retry amplification during outages. Without them, if 50% of requests fail and all failed requests retry, load increases by 50%. If those retries also fail and retry, load increases further, creating a cascading failure.

### Hedged Requests

Tail latency dominates user experience in distributed systems. Even if p50 is fast, occasional slow requests create poor perceived performance. The paper "The Tail at Scale" by Dean and Barroso established that tail latencies in distributed systems can be 10x to 100x higher than median latencies [Source: Dean & Barroso, 2013].

Hedged requests address tail latency by sending redundant requests and using the first response. We trade compute resources for latency predictability.

#### The Hedged Requests Pattern

Hedged requests send the same request to multiple backends (or retry to the same backend) after a delay. If the first request returns quickly, we cancel the hedge. If the first request is slow, the hedge often returns faster.

<!-- DIAGRAM: Hedged request timeline showing: Request 1 sent -> wait 50ms -> Request 2 (hedge) sent -> First response received (from either) -> Cancel other request -->

![Hedged Requests Timeline](../assets/ch10-hedged-requests.html)

The hedge delay is critical. Too short increases load substantially. Too long provides no benefit. A common strategy uses the p95 latency as the hedge trigger: if the first request has not returned by the time 95% of requests normally complete, we send the hedge.

#### Cost Considerations

Hedged requests increase load on backend systems. With a 50ms hedge delay and a p95 of 50ms, approximately 5% of requests will trigger hedges. This means roughly 5% additional load. For latency-sensitive paths where tail latency matters, this trade-off is often worthwhile.

To manage costs:
- Use adaptive hedge delays based on observed latency percentiles
- Implement request budgets that limit hedging under high load
- Apply hedging selectively to latency-critical paths

### Chaos Engineering

Building resilience patterns is necessary but not sufficient. Without testing these patterns under realistic failure conditions, we cannot know whether they actually work. Chaos engineering is the discipline of proactively injecting failures to discover weaknesses before they cause outages. As practitioners often say: "Chaos engineering enables us to find shortcomings before our customers find them" [Source: Principles of Chaos Engineering, 2019].

The approach is empirical: define steady-state behavior (normal system metrics), hypothesize that the system will maintain steady state during a specific failure, inject that failure, and observe whether the hypothesis holds. When it does not, we have discovered a weakness to address.

<!-- DIAGRAM: Chaos engineering workflow showing circular process: Define Steady State -> Form Hypothesis -> Design Experiment -> Inject Fault (with blast radius controls) -> Observe Behavior -> Analyze Results -> Address Weaknesses -> back to Define Steady State -->

![Chaos Engineering Workflow](../assets/ch10-chaos-engineering.html)

**Types of Fault Injection**

Chaos experiments can target multiple failure modes:

- **Network faults**: Latency injection, packet loss, network partitions. Does the circuit breaker trip when latency exceeds thresholds?
- **Pod/container failures**: Random pod deletion, node failures. Does the system maintain availability with reduced capacity?
- **Resource exhaustion**: CPU stress, memory pressure, disk I/O saturation. How does the system degrade under resource contention?
- **Dependency failures**: Blocking calls to databases or external APIs. Do fallbacks activate correctly?

**Tools and Platforms**

The chaos engineering ecosystem has matured significantly:

| Tool | Scope | Integration |
|------|-------|-------------|
| LitmusChaos | Kubernetes-native, broad fault library | CNCF graduated, CRD-based experiments |
| Chaos Mesh | Kubernetes, fine-grained attacks | CNCF incubating, rich Kubernetes integration |
| AWS Fault Injection Simulator | AWS services and infrastructure | Native AWS integration, managed service |
| Gremlin | Multi-platform, enterprise features | Commercial, comprehensive fault library |

LitmusChaos and Chaos Mesh both use Kubernetes Custom Resource Definitions (CRDs) to define experiments declaratively. This enables GitOps workflows where chaos experiments are version-controlled and reviewed like other infrastructure configuration [Source: LitmusChaos Documentation, 2024].

**Blast Radius Management**

Chaos experiments must be controlled. The blast radius (the scope of potential impact) should start small and expand as confidence grows:

1. **Development environments**: Inject any fault, no blast radius limits
2. **Staging with synthetic traffic**: Realistic faults, production-like conditions
3. **Production with narrow targeting**: Single instances or specific user cohorts
4. **Production GameDays**: Planned exercises with expanded scope, teams on standby

Start experiments during low-traffic periods with quick abort capabilities. Monitor closely and stop immediately if impact exceeds expectations. The goal is learning, not demonstrating courage.

**Steady-State Hypothesis**

Every experiment needs a clear hypothesis about expected behavior:

- "When we inject 500ms latency to the payment service, checkout latency will increase by less than 700ms due to deadline propagation, and error rate will remain below 0.1% due to circuit breaker fallbacks."
- "When we kill 2 of 5 API pods, request success rate will remain above 99.5% and p99 latency will stay below 300ms due to load balancer health checks and horizontal redundancy."

Vague hypotheses produce vague results. Specific, measurable hypotheses reveal precise weaknesses.

**Integrating Chaos into CI/CD**

Mature organizations run chaos experiments as part of their deployment pipelines:

1. Deploy new version to staging
2. Run smoke tests to verify basic functionality
3. Run chaos experiments targeting new code paths
4. If experiments pass, proceed to production
5. Run limited chaos experiments in production post-deploy

This automated approach catches resilience regressions before they reach production. It also builds confidence that patterns like retries, circuit breakers, and fallbacks actually function under the conditions they are designed for.

**When to Start**

Chaos engineering is most valuable when:
- Systems have basic resilience patterns in place (retrying without retries to test helps no one)
- Monitoring and observability allow detecting failures quickly
- Teams can respond to discovered issues
- Business context tolerates controlled risk

Start simple: kill a non-critical pod and verify traffic shifts to remaining instances. Graduate to more sophisticated experiments as the practice matures. The goal is continuous improvement, not a single dramatic test.

## Common Pitfalls

- **Rate limiting without client feedback**: Rejecting requests without communicating retry timing wastes client resources. Always include `Retry-After` headers or equivalent information so clients can back off intelligently rather than hammering the server with immediate retries.

- **Circuit breaker thresholds too sensitive**: Opening circuits on a few failures causes unnecessary outages. Require a minimum request volume before evaluating failure rates, and consider using percentage thresholds (50% failure rate) rather than absolute counts (5 failures).

- **Independent timeouts without deadline propagation**: When each service sets its own timeout independently, requests can "succeed" at each hop while exceeding the end-to-end SLO. Propagate deadlines so downstream services know the actual time remaining and can fail fast when the deadline has passed.

- **No jitter in retry delays**: Even with exponential backoff, synchronized retries create periodic load spikes. Always add jitter. Full jitter (random delay between 0 and the calculated backoff) provides the best distribution [Source: AWS Architecture Blog].

- **Bulkheads too large**: Bulkheads sized equal to total thread pool capacity provide no isolation. Size each bulkhead based on the dependency's expected concurrency, ensuring that one dependency's exhaustion leaves capacity for others.

- **Missing fallbacks for open circuits**: Circuit breakers that just throw exceptions push the problem to callers. Provide meaningful fallbacks: cached data, default values, degraded functionality. The circuit breaker's job is to fail fast, but your system's job is to keep working.

- **Retrying non-idempotent operations**: Retrying operations that are not idempotent (like payments or writes without deduplication) can cause duplicate effects. Only retry operations that are safe to repeat, or ensure idempotency through unique request IDs.

- **Ignoring retry budgets**: Individual clients retrying independently can amplify load during outages. Implement system-wide retry budgets that limit total retry rate, preventing retry storms from extending outages.

- **Load balancer health checks too aggressive**: Marking instances unhealthy on single failures causes unnecessary churn. Use multiple consecutive failures or sliding windows for health decisions, and implement separate liveness and readiness checks.

- **Hedging without budgets**: Unbounded hedging can amplify load during incidents. When a service is slow, hedging creates even more requests, potentially causing cascading failure. Implement budgets that disable hedging under high load.

- **Adaptive concurrency limits without warm-up**: Adaptive algorithms need time to discover system capacity. Starting with zero or very low limits causes immediate request rejection. Set reasonable initial limits and allow warm-up time before relying on adaptive behavior.

- **Service mesh without understanding overhead**: Service meshes add latency (typically 1-2ms per hop) and operational complexity. For simple topologies or extreme latency requirements, application-level resilience patterns may be more appropriate.

- **No graceful degradation planning**: Systems that go from full functionality to complete failure provide poor user experience. Design degradation paths in advance, identifying which features can be disabled and what fallbacks to use, so degradation is graceful rather than catastrophic.

- **Chaos engineering without observability**: Injecting failures without the ability to observe their impact teaches nothing. Ensure monitoring, logging, and alerting are in place before running chaos experiments, or you will not detect whether hypotheses hold.

- **Running chaos experiments without abort capability**: Chaos experiments must be stoppable immediately when impact exceeds expectations. Without quick abort mechanisms, experiments can cause actual outages rather than learning opportunities.

## Summary

- **Rate limiting algorithms** offer different trade-offs: token bucket allows bursts while enforcing average rates, leaky bucket smooths output at the cost of latency, and sliding window provides accurate limits without boundary issues.

- **Adaptive concurrency limits** automatically discover system capacity by measuring actual latency. Unlike static limits, they adjust to changing conditions (deployments, traffic patterns, dependency performance) without manual tuning.

- **Circuit breakers** protect against cascading failures by failing fast when dependencies are unhealthy. The three states (closed, open, half-open) enable automatic recovery testing without overwhelming recovering services.

- **Deadline propagation** ensures latency budgets flow through distributed systems. By passing an absolute deadline header, downstream services know how much time remains and can fail fast when deadlines have passed.

- **Load balancing strategies** should match your workload: round-robin for uniform requests, least connections for varying request durations, consistent hashing for cache affinity and session stickiness.

- **Service meshes** provide infrastructure-level traffic management through sidecar proxies. Virtual Services handle routing; Destination Rules enforce policies. Meshes add value for multi-service environments needing consistent resilience but add latency and complexity.

- **Bulkheads** isolate failures by partitioning resources. When one dependency exhausts its resource pool, other dependencies continue functioning. Size bulkheads to leave capacity for other operations when any single dependency fails.

- **Graceful degradation** provides partial functionality when full functionality is unavailable. Design degradation hierarchies in advance, use feature flags as kill switches, and implement priority-based load shedding to protect critical paths.

- **Retry with exponential backoff and jitter** recovers from transient failures without overwhelming recovering services. Full jitter provides the best distribution of retry attempts over time. Retry budgets prevent retry amplification.

- **Hedged requests** reduce tail latency by sending redundant requests and using the first response. Configure hedge delays based on p95 latency and implement budgets to prevent load amplification.

- **Chaos engineering** validates resilience patterns through controlled failure injection. Start with clear hypotheses about expected behavior, manage blast radius carefully, and integrate experiments into CI/CD for continuous resilience validation.

- Combine patterns thoughtfully: rate limiting at the edge prevents resource exhaustion, circuit breakers protect against dependency failures, bulkheads contain blast radius, graceful degradation maintains user value, and chaos engineering validates it all works.

## References

1. **Netflix Hystrix Wiki** (2018). "How It Works." https://github.com/Netflix/Hystrix/wiki/How-it-Works

2. **Resilience4j Documentation**. "Circuit Breaker." https://resilience4j.readme.io/docs/circuitbreaker

3. **AWS Architecture Blog**. "Exponential Backoff And Jitter." https://aws.amazon.com/blogs/architecture/exponential-backoff-and-jitter/

4. **Stripe Engineering Blog** (2017). "Designing robust and predictable APIs with idempotency." https://stripe.com/blog/idempotency

5. **Google SRE Book** (2016). "Handling Overload." https://sre.google/sre-book/handling-overload/

6. **Envoy Proxy Documentation**. "Circuit Breaking." https://www.envoyproxy.io/docs/envoy/latest/intro/arch_overview/upstream/circuit_breaking

7. **Martin Fowler** (2014). "CircuitBreaker." https://martinfowler.com/bliki/CircuitBreaker.html

8. **Michael Nygard** (2007). "Release It!: Design and Deploy Production-Ready Software." Pragmatic Bookshelf.

9. **Netflix Tech Blog** (2018). "Performance Under Load." https://netflixtechblog.medium.com/performance-under-load-3e6fa9a60581

10. **Envoy Documentation** (2024). "Adaptive Concurrency." https://www.envoyproxy.io/docs/envoy/latest/configuration/http/http_filters/adaptive_concurrency_filter

11. **Istio Documentation** (2024). "Traffic Management." https://istio.io/latest/docs/concepts/traffic-management/

12. **Principles of Chaos Engineering** (2019). https://principlesofchaos.org/

13. **LitmusChaos Documentation** (2024). https://litmuschaos.io/docs/

14. **Dean, J., & Barroso, L. A.** (2013). "The Tail at Scale." Communications of the ACM, 56(2), 74-80. https://dl.acm.org/doi/10.1145/2408776.2408794

## Next: [Chapter 11: Authentication Performance](./11-auth-performance.md)

With resilience patterns established, the next chapter examines authentication through the lens of performance. We cover token validation overhead, caching strategies, stateless vs stateful trade-offs, and maintaining performance under attack.
