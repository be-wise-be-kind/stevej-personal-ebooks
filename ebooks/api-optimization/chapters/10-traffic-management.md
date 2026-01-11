# Chapter 10: Traffic Management and Resilience

![Chapter 10 Opener](../assets/ch10-opener.html)

\newpage

## Overview

Even the most optimized API will eventually face conditions that exceed its capacity. Traffic spikes, dependency failures, network partitions, and resource exhaustion are not edge cases but inevitabilities in distributed systems. The difference between a system that gracefully handles these conditions and one that cascades into complete failure lies in deliberate traffic management and resilience engineering.

This chapter explores the patterns that protect our APIs when things go wrong. We will examine rate limiting algorithms that prevent resource exhaustion, circuit breakers that fail fast when dependencies are unhealthy, load balancing strategies that distribute work effectively, bulkhead patterns that isolate failures, and retry strategies that recover from transient errors without overwhelming recovering services. These patterns, pioneered by companies like Netflix and Amazon and now codified in libraries like Resilience4j, form the foundation of reliable distributed systems.

The philosophy here is pragmatic: we assume failures will happen and design our systems to contain their blast radius. Every pattern we discuss involves trade-offs between throughput, latency, resource utilization, and complexity. Our goal is to equip you with the knowledge to make informed decisions about which patterns to apply and how to configure them for your specific requirements.

<!-- DIAGRAM: High-level resilience architecture showing: Client requests -> Rate Limiter -> Load Balancer -> Circuit Breaker -> Bulkhead -> Service, with arrows showing where each pattern intervenes -->

![Resilience Architecture](../assets/ch09-resilience-architecture.html)

## Key Concepts

### Rate Limiting Algorithms

Rate limiting controls the number of requests a client or system can make within a time window. Without rate limiting, a single misbehaving client or sudden traffic spike can exhaust resources and deny service to everyone. The choice of algorithm affects how strictly we enforce limits and how we handle burst traffic.

#### Token Bucket Algorithm

The token bucket is the most widely deployed rate limiting algorithm due to its flexibility with burst traffic. Conceptually, tokens are added to a bucket at a fixed rate (the refill rate), and each request consumes one token. When the bucket is empty, requests are rejected. The bucket has a maximum capacity that determines the burst size allowed.

The token bucket provides two key parameters: the sustained rate (how fast tokens refill) and the burst capacity (maximum tokens in the bucket). This allows legitimate burst traffic while preventing sustained overload. For example, a bucket configured with 100 tokens per second refill rate and 500 token capacity allows a burst of 500 requests followed by a sustained 100 requests per second.

The algorithm's strength is its simplicity and predictability. Clients can reason about their rate limits: if they have been quiet, they accumulate tokens for a burst; if they have been active, they are constrained to the refill rate. This makes token bucket ideal for user-facing API rate limits where occasional bursts are acceptable (see Example 10.1).

#### Leaky Bucket Algorithm

The leaky bucket processes requests at a constant rate, regardless of input burstiness. Incoming requests enter a queue (the bucket), and requests leave the queue (leak out) at a fixed rate. If the queue fills up, new requests are rejected.

Unlike the token bucket, the leaky bucket smooths output rather than allowing bursts. This is valuable when downstream services require steady traffic or when we need to shape traffic to match a specific throughput limit. However, it introduces latency as requests wait in the queue.

The leaky bucket is commonly used in network traffic shaping and quality-of-service implementations where consistent throughput matters more than minimizing individual request latency.

#### Sliding Window Algorithm

Fixed window rate limiting divides time into discrete intervals (e.g., one-minute windows) and counts requests per window. The problem: a client could make their entire quota at the end of one window and the beginning of the next, effectively doubling their allowed rate across the boundary.

The sliding window algorithm addresses this by weighting requests from the previous window. A common approach calculates: `requests in current window + (requests in previous window * overlap percentage)`. This provides smoother rate limiting without the boundary spike problem.

Sliding window requires tracking requests across two windows, which increases memory usage slightly. However, the improved accuracy usually justifies the cost. Redis and similar systems provide efficient primitives for implementing sliding window rate limiting in distributed environments.

<!-- DIAGRAM: Comparison of fixed window vs sliding window rate limiting showing: Fixed window with boundary spike (requests clustered at window boundaries), Sliding window with smooth enforcement (consistent rate across boundaries) -->

![Rate Limiting Comparison](../assets/ch09-rate-limiting-comparison.html)

For rate limiting at the CDN edge—including distributed state challenges and edge-specific configuration patterns—see [Chapter 12: Edge Infrastructure](./12-edge-infrastructure.md).

### Circuit Breaker Pattern

The circuit breaker pattern prevents an application from repeatedly trying to execute an operation that is likely to fail. Like an electrical circuit breaker, it "trips" when failures exceed a threshold, failing fast instead of waiting for timeouts.

The pattern originated at Netflix, documented in their Hystrix library. While Hystrix is now in maintenance mode, the patterns it established have been adopted by libraries like Resilience4j, Sentinel, and Polly, and are built into service meshes like Istio and Envoy [Source: Netflix Hystrix Wiki, 2018].

#### Circuit Breaker States

The circuit breaker operates as a state machine with three states:

**Closed (Normal Operation)**: Requests pass through normally. The breaker monitors failures and tracks the failure rate or count. When failures exceed a configured threshold (e.g., 50% failure rate over 10 requests), the circuit "opens."

**Open (Fail Fast)**: All requests fail immediately without attempting the operation. This prevents cascading failures and gives the downstream service time to recover. After a configured timeout (e.g., 30 seconds), the circuit transitions to half-open.

**Half-Open (Testing Recovery)**: A limited number of test requests are allowed through. If they succeed, the circuit closes and normal operation resumes. If they fail, the circuit opens again with a reset timeout. This gradual recovery prevents a flood of requests from overwhelming a service that is just coming back online (see Example 10.2).

<!-- DIAGRAM: Circuit breaker state machine: Closed (normal) -[failures exceed threshold]-> Open (fail fast) -[timeout expires]-> Half-Open (test) -[success]-> Closed OR -[failure]-> Open, with annotations for each transition condition -->

![Circuit Breaker State Machine](../assets/ch09-circuit-breaker-states.html)

#### Configuring Circuit Breakers

Effective circuit breaker configuration requires understanding your service's failure modes:

**Failure Rate Threshold**: The percentage of failures that trips the circuit. A threshold of 50% is common, but latency-sensitive services may use lower values (25-30%) to fail fast before users notice degradation.

**Minimum Request Volume**: The minimum number of requests before the failure rate is evaluated. This prevents the circuit from tripping on the first few requests. A value of 10-20 requests is typical for services with moderate traffic.

**Wait Duration in Open State**: How long to wait before testing recovery. Too short risks hammering a recovering service; too long delays recovery unnecessarily. Starting with 30-60 seconds and adjusting based on observed recovery times works well.

**Permitted Calls in Half-Open**: How many test requests to allow. One is safest but delays recovery confirmation. Three to five requests provide faster confirmation while limiting exposure.

### Deadline Propagation

Deadline propagation ensures that latency budgets flow through a distributed system. When a user-facing service has a 500ms SLO, downstream services need to know how much time remains—not just their individual timeout, but the overall deadline for the entire request chain.

#### The Problem with Independent Timeouts

Consider a request that passes through three services sequentially, each with a 200ms timeout:


```
Gateway (200ms timeout) -> Auth (200ms timeout) -> Database (200ms timeout)
```

If Auth takes 150ms and Database takes 180ms, the total is 330ms. Each service "succeeded" within its individual timeout, but the gateway's 200ms timeout already fired. The user sees a timeout error even though every downstream call "worked."

Independent timeouts don't compose. Deadline propagation solves this by sharing a single end-to-end deadline across all services.

#### How Deadline Propagation Works

The originating service calculates an absolute deadline (current time plus SLO budget) and passes it to downstream services via a header:


```
X-Request-Deadline: 1704067200500  (Unix timestamp in milliseconds)
```

Each downstream service:

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

**Fail fast on expired deadlines**: When a request arrives with an already-passed deadline, return immediately. There is no point in doing work that the caller has already abandoned:


```python
def check_deadline(request):
    deadline = request.headers.get('X-Request-Deadline')
    if deadline and int(deadline) < current_time_ms():
        raise DeadlineExceeded("Request deadline already passed")
```

**Reserve buffer time**: Don't use 100% of remaining time. If 50ms remains, set a 40ms timeout to allow for response transmission and processing:


```python
remaining = deadline_ms - current_time_ms()
timeout = max(remaining - 10, 1)  # Reserve 10ms buffer, minimum 1ms
```

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

![Load Balancing Strategies](../assets/ch09-load-balancing-strategies.html)

### Bulkhead Pattern

The bulkhead pattern isolates failures by partitioning resources. Named after the watertight compartments in ships, bulkheads prevent a failure in one area from flooding the entire system.

In practice, bulkheads create separate resource pools for different operations or dependencies. If a slow dependency exhausts its pool, other operations continue unaffected. Without bulkheads, a single slow dependency can consume all available threads or connections, causing complete system failure.

#### Thread Pool Bulkheads

Thread pool bulkheads assign dedicated thread pools to different dependencies or operation types. If the payment service slows down and exhausts its pool of 10 threads, the order service's separate pool of 20 threads continues functioning normally.

The trade-off is resource efficiency: dedicated pools may sit idle while other pools are exhausted. Some implementations allow stealing from idle pools while maintaining minimum guaranteed resources.

#### Semaphore Bulkheads

Semaphore bulkheads use counting semaphores to limit concurrent operations without dedicating threads. A semaphore limits how many requests to a dependency can be in flight simultaneously. When the limit is reached, new requests either wait (with timeout) or fail fast.

Semaphore bulkheads are more memory-efficient than thread pools but do not provide the same isolation guarantees. They are suitable when the goal is limiting concurrency rather than complete resource isolation (see Example 10.4).

<!-- DIAGRAM: Bulkhead pattern showing isolated resource pools: Service A pool (5 connections) at 80% capacity, Service B pool (10 connections) at 100% and blocking, Service C pool (3 connections) at 30% capacity. Annotation: "Service B exhaustion does not affect A or C" -->

![Bulkhead Pattern](../assets/ch09-bulkhead-pattern.html)

### Retry Strategies with Exponential Backoff

Transient failures are common in distributed systems: network blips, temporary overload, garbage collection pauses. Retrying failed requests can recover from these issues without user impact. However, naive retries can overwhelm recovering services and extend outages.

#### Exponential Backoff

Exponential backoff increases the delay between retries multiplicatively: 1 second, 2 seconds, 4 seconds, 8 seconds, and so on. This gives services progressively more time to recover and prevents a thundering herd of retry attempts.

The formula is typically: `delay = base_delay * (2 ^ attempt_number)`, capped at a maximum delay. Common configurations use a base delay of 100ms to 1 second and a maximum delay of 30-60 seconds.

#### Adding Jitter

Even with exponential backoff, if many clients start retrying at the same time, their retry attempts synchronize and create periodic load spikes. Adding jitter (randomization) to retry delays spreads retries over time.

Full jitter chooses a random delay between 0 and the calculated backoff: `delay = random(0, base_delay * 2^attempt)`. Equal jitter splits the difference: `delay = (base_delay * 2^attempt) / 2 + random(0, base_delay * 2^attempt / 2)`.

AWS recommends full jitter for most use cases, as it provides the best distribution of retry attempts over time [Source: AWS Architecture Blog, "Exponential Backoff And Jitter"]. A complete implementation demonstrating configurable retry strategies with exponential backoff and jitter is provided in Example 10.3.

#### Retry Budgets

A retry budget limits the total retry rate across all clients rather than per-client. If the system allows 10% retry budget, only 10% of requests can be retries; when the budget is exhausted, clients do not retry.

Retry budgets prevent retry amplification during outages. Without them, if 50% of requests fail and all failed requests retry, load increases by 50%. If those retries also fail and retry, load increases further, creating a cascading failure.

For implementation examples related to these concepts, see the [Appendix: Code Examples](./13-appendix-code-examples.md).

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

## Summary

- Rate limiting algorithms offer different trade-offs: token bucket allows bursts while enforcing average rates, leaky bucket smooths output at the cost of latency, and sliding window provides accurate limits without boundary issues.

- Circuit breakers protect against cascading failures by failing fast when dependencies are unhealthy. The three states (closed, open, half-open) enable automatic recovery testing without overwhelming recovering services.

- Deadline propagation ensures latency budgets flow through distributed systems. By passing an absolute deadline header, downstream services know how much time remains and can fail fast when deadlines have passed rather than doing work that callers have abandoned.

- Load balancing strategies should match your workload: round-robin for uniform requests, least connections for varying request durations, consistent hashing for cache affinity and session stickiness.

- Bulkheads isolate failures by partitioning resources. When one dependency exhausts its resource pool, other dependencies continue functioning. Size bulkheads to leave capacity for other operations when any single dependency fails.

- Retry with exponential backoff and jitter recovers from transient failures without overwhelming recovering services. Full jitter provides the best distribution of retry attempts over time.

- Retry budgets prevent retry amplification during outages. Without budgets, retries can multiply load and extend outages rather than helping recovery.

- All traffic management patterns require monitoring: track rejection rates, circuit state transitions, bulkhead utilization, and retry success rates to tune configurations and detect issues early.

- Combine patterns thoughtfully: rate limiting at the edge prevents resource exhaustion, circuit breakers protect against dependency failures, bulkheads contain blast radius, and retries recover from transient errors.

## References

1. **Netflix Hystrix Wiki** (2018). "How It Works." https://github.com/Netflix/Hystrix/wiki/How-it-Works

2. **Resilience4j Documentation**. "Circuit Breaker." https://resilience4j.readme.io/docs/circuitbreaker

3. **AWS Architecture Blog**. "Exponential Backoff And Jitter." https://aws.amazon.com/blogs/architecture/exponential-backoff-and-jitter/

4. **Stripe Engineering Blog** (2017). "Designing robust and predictable APIs with idempotency." https://stripe.com/blog/idempotency

5. **Google SRE Book** (2016). "Handling Overload." https://sre.google/sre-book/handling-overload/

6. **Envoy Proxy Documentation**. "Circuit Breaking." https://www.envoyproxy.io/docs/envoy/latest/intro/arch_overview/upstream/circuit_breaking

7. **Martin Fowler** (2014). "CircuitBreaker." https://martinfowler.com/bliki/CircuitBreaker.html

8. **Michael Nygard** (2007). "Release It!: Design and Deploy Production-Ready Software." Pragmatic Bookshelf.

## Next: [Chapter 11: Authentication Performance](./11-auth-performance.md)

With resilience patterns established, the next chapter examines authentication through the lens of performance. We cover token validation overhead, caching strategies, stateless vs stateful trade-offs, and maintaining performance under attack.
