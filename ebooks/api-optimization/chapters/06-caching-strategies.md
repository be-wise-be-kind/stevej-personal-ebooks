# Chapter 5: Caching Strategies

![Chapter 6 Opener](../assets/ch06-opener.html)

\newpage

## Overview

Caching is often described as the single most effective optimization technique available to API developers. By storing the results of expensive operations and reusing them for subsequent requests, we can dramatically reduce latency, decrease database load, and improve overall system throughput. However, as Phil Karlton famously noted, "There are only two hard things in Computer Science: cache invalidation and naming things." This chapter explores not just how to implement caching, but how to do so correctly.

We will examine caching from multiple angles: the hierarchy of caches from browser to origin, the patterns that govern how data flows through caches, and the strategies for keeping cached data fresh. We will also tackle the thundering herd problem—a failure mode that has brought down production systems at companies of all sizes. Throughout, we maintain our empirical approach: every caching decision should be driven by measured cache hit rates, latency improvements, and consistency requirements.

The goal is not to cache everything, but to cache strategically. A well-designed caching strategy can reduce p95 latency from hundreds of milliseconds to single digits, while a poorly designed one can introduce subtle bugs, stale data, and operational nightmares.

## Key Concepts

### Cache Hierarchy

Modern API systems employ multiple layers of caching, each with distinct characteristics. Understanding this hierarchy helps us place data at the optimal layer for our access patterns.

<!-- DIAGRAM: Cache hierarchy pyramid showing layers from top to bottom: Browser cache (0ms network latency) -> CDN edge (10-50ms from user) -> Distributed cache/Redis (1-5ms from app) -> In-process cache (microseconds) -> Database (10-100ms), with annotations showing typical latencies and use cases for each layer -->

![Cache Hierarchy](../assets/ch05-cache-hierarchy.html)

**L1: In-Process Cache**

The fastest cache is memory in the application process itself. In-process caches like Python's `functools.lru_cache`, Rust's `moka`, or Node.js's `node-cache` provide sub-millisecond access times—typically measured in microseconds. These caches are ideal for frequently accessed, computationally expensive data that does not change often: configuration values, compiled templates, or parsed schemas.

The trade-off is memory consumption and the lack of sharing between application instances. Each instance maintains its own cache, which can lead to inconsistency in horizontally scaled deployments.

**L2: Distributed Cache**

Distributed caches like Redis or Memcached sit between the application and the database. They provide shared state across all application instances with typical latencies of 1-5ms over a local network. Redis, in particular, has become the de facto standard for application caching, offering not just key-value storage but also data structures like sorted sets and hash maps that enable sophisticated caching patterns.

According to Redis documentation, properly configured Redis instances can handle over 100,000 operations per second on modest hardware, making them suitable for high-throughput API scenarios [Source: Redis Documentation, 2024].

**L3: Content Delivery Network (CDN)**

CDNs cache content at edge locations distributed globally. When a user in Tokyo requests data from an API hosted in Virginia, a CDN edge node in Tokyo can serve the cached response without the request ever reaching the origin server. This eliminates network latency that can add 100-300ms for intercontinental requests.

CDN caching is controlled primarily through HTTP headers: `Cache-Control`, `Expires`, and `ETag`. The `Cache-Control: max-age=3600` header tells CDN nodes (and browsers) to cache the response for one hour. For API responses, the `Vary` header is critical—it tells the CDN which request headers affect the response and should be included in the cache key.

Cloudflare reports that customers with well-configured caching rules achieve cache hit ratios above 90% for cacheable content, dramatically reducing origin server load [Source: Cloudflare, 2023].

**L4: Browser/Client Cache**

For API clients, browser caching reduces requests entirely. When an API response includes appropriate `Cache-Control` headers, the browser may serve subsequent requests from its local cache without any network activity. This is particularly effective for mobile applications where network requests drain battery and may be slow or unreliable.

### Caching Patterns

Different access patterns require different caching strategies. The choice of pattern affects consistency guarantees, write latency, and operational complexity.

<!-- DIAGRAM: Cache-aside pattern sequence diagram showing: Client -> Application -> Check Cache -> [Hit: return cached data] or [Miss: Query Database -> Store result in Cache -> return data to client] -->

![Cache-Aside Pattern](../assets/ch05-cache-aside-pattern.html)

**Cache-Aside (Lazy Loading)**

Cache-aside is the most common caching pattern. The application is responsible for managing the cache explicitly:

1. Check the cache for the requested data
2. If found (cache hit), return the cached value
3. If not found (cache miss), fetch from the database
4. Store the result in the cache for future requests
5. Return the data

This pattern works well for read-heavy workloads where data is read far more often than written. The cache naturally fills with frequently accessed data, and rarely accessed data expires without consuming cache memory (see Example 6.1).

**Write-Through**

In write-through caching, every write operation updates both the cache and the database synchronously. This ensures the cache is always consistent with the database but increases write latency since both operations must complete before the write is acknowledged.

Write-through is appropriate when read latency is critical and you cannot tolerate any stale reads, but write volume is moderate enough that the latency penalty is acceptable.

**Write-Behind (Write-Back)**

Write-behind inverts the write-through approach: writes go to the cache immediately and are asynchronously persisted to the database. This minimizes write latency since the application only waits for the cache write, but introduces the risk of data loss if the cache fails before the write is persisted.

This pattern is suitable for high-write-volume scenarios where some data loss is acceptable—such as analytics events or activity logs where losing a few records is not catastrophic.

<!-- DIAGRAM: Write-through vs Write-behind comparison showing: Write-through with synchronous paths to both cache and database (higher latency, strong consistency) vs Write-behind with async database write (lower latency, eventual consistency, data loss risk) -->

![Write-Through vs Write-Behind Patterns](../assets/ch05-write-patterns.html)

### Cache Invalidation Strategies

Cache invalidation determines how stale data is removed or updated. The choice of strategy depends on your consistency requirements and the nature of your data.

**TTL-Based Expiration**

Time-to-live (TTL) is the simplest invalidation strategy: cached data automatically expires after a fixed duration. A TTL of 300 seconds means data may be up to 5 minutes stale, which is acceptable for many use cases.

The challenge is choosing the right TTL. Too short, and the cache provides little benefit. Too long, and users see stale data. For most API data, TTLs between 60 seconds and 1 hour strike a reasonable balance, but the optimal value depends on your specific data's update frequency and staleness tolerance.

**Event-Based Invalidation**

Event-based invalidation removes cached data when the underlying data changes. When a user updates their profile, the application explicitly deletes the cached profile data. This provides strong consistency at the cost of additional invalidation logic.

The Facebook paper "Scaling Memcache at Facebook" describes their invalidation pipeline where database writes trigger cache invalidations across their globally distributed Memcached clusters. They found that event-based invalidation was essential for maintaining consistency at scale [Source: Nishtala et al., "Scaling Memcache at Facebook," NSDI 2013].

**Version-Based Invalidation**

Version-based caching embeds a version identifier in the cache key. When data changes, the version increments, effectively creating a new cache key. Old versions naturally expire via TTL while new requests use the new version.

This pattern is particularly useful for configuration data or feature flags where you want an immediate switch across all instances. Changing the version causes all instances to fetch fresh data, achieving coordinated invalidation without explicit communication.

### The Thundering Herd Problem

The thundering herd (also called cache stampede) occurs when a popular cache entry expires and many concurrent requests simultaneously attempt to regenerate it. If 1000 requests arrive in the moment after a cache entry expires, all 1000 may attempt to fetch from the database simultaneously, potentially overwhelming it.

<!-- DIAGRAM: Thundering herd problem visualization: Single cache entry expires -> 100 simultaneous requests arrive -> All 100 hit database simultaneously (database overload). Solution: Single-flight pattern where first request acquires lock, other 99 wait, only 1 database query executes, all 100 receive result -->

![Thundering Herd Problem and Solution](../assets/ch05-thundering-herd.html)

**Single-Flight Pattern**

The single-flight pattern ensures only one request regenerates a cache entry while others wait for its result. The first request to find an expired entry acquires a lock, fetches the data, and populates the cache. Concurrent requests that arrive during this window wait for the first request to complete rather than independently fetching the data (see Example 6.3).

This pattern is implemented in Go's `golang.org/x/sync/singleflight` package and similar libraries in other languages. It is essential for any cache key that experiences high concurrent access.

**Probabilistic Early Expiration**

An alternative approach is probabilistic early expiration: instead of all requests treating the TTL as a hard deadline, each request has a small probability of refreshing the cache before expiration. This spreads cache regeneration over time, reducing the likelihood of simultaneous expirations.

The probability increases as the TTL approaches expiration. With a TTL of 300 seconds, a request at 290 seconds might have a 5% chance of proactively refreshing, while a request at 299 seconds might have a 20% chance.

**TTL with Jitter**

Adding randomized jitter to TTL values prevents synchronized expiration across cache entries. Instead of all entries expiring at exactly 300 seconds, they expire between 270 and 330 seconds (see Example 6.2). This simple technique significantly reduces the severity of thundering herd events.

### Monitoring Cache Effectiveness

Regardless of which caching pattern or invalidation strategy we choose, measuring cache performance is essential for data-driven optimization. Key metrics include cache hit rate, miss rate, and operation latency. Without instrumentation, we cannot know whether our cache is providing value or simply adding complexity (see Example 6.4).

For implementation examples related to these concepts, see the [Appendix: Code Examples](./13-appendix-code-examples.md).

## Common Pitfalls

- **Caching without measuring hit rate**: A cache with a low hit rate wastes memory and adds latency for cache checks. Always instrument your cache and monitor hit rates. A hit rate below 80% often indicates poor cache key design or inappropriate TTLs.

- **Ignoring cache key collisions**: Poor cache key design can cause different data to share the same key, leading to incorrect responses. Always include all parameters that affect the response in the cache key, and consider including a version prefix.

- **Unbounded cache growth**: Caches without memory limits or eviction policies can exhaust available memory. Always configure maximum memory limits and an eviction policy (LRU is a safe default).

- **Caching personalized data with shared keys**: User-specific data cached under generic keys can leak to other users—a serious security vulnerability. Always include user identifiers in cache keys for personalized data.

- **Synchronous cache invalidation across distributed systems**: Attempting to synchronously invalidate caches across multiple services or regions introduces coupling and latency. Prefer eventual consistency with reasonable TTLs.

- **Not accounting for cache stampede**: Popular cache entries expiring under high load can overwhelm databases. Implement single-flight, probabilistic early expiration, or TTL jitter to mitigate thundering herd.

- **Caching errors**: Caching error responses at long TTLs can make temporary failures permanent from the user's perspective. Either do not cache errors, or use very short TTLs (seconds, not minutes).

- **Over-relying on cache for availability**: If your application cannot function during a cache outage, the cache has become a single point of failure. Design for graceful degradation when the cache is unavailable.

## Summary

- The cache hierarchy—browser, CDN, distributed cache, in-process cache—provides multiple opportunities to serve requests without hitting the origin database. Place data at the layer that best matches its access patterns and consistency requirements.

- Cache-aside (lazy loading) is the most common pattern, suitable for read-heavy workloads. Write-through provides stronger consistency at the cost of write latency. Write-behind minimizes write latency but risks data loss.

- TTL-based expiration is simple and effective for most use cases. Event-based invalidation provides stronger consistency when needed. Version-based invalidation enables coordinated cache refresh across instances.

- The thundering herd problem can overwhelm databases when popular cache entries expire. Mitigation strategies include the single-flight pattern, probabilistic early expiration, and TTL with jitter.

- Always measure cache effectiveness. Key metrics include hit rate, miss rate, latency, and eviction rate. A cache hit rate target of 90% or higher is reasonable for most API workloads.

- Cache invalidation is genuinely difficult. When in doubt, prefer shorter TTLs over complex invalidation logic—the simplicity often outweighs the slight efficiency cost.

- Caching introduces trade-offs between consistency, latency, and complexity. Make these trade-offs explicitly, document your cache's consistency guarantees, and ensure your team understands the implications.

## References

1. **Nishtala, R., et al.** (2013). "Scaling Memcache at Facebook." NSDI 2013. https://www.usenix.org/conference/nsdi13/technical-sessions/presentation/nishtala

2. **Redis Documentation** (2024). "Redis Best Practices." https://redis.io/docs/management/optimization/

3. **Cloudflare** (2023). "Caching Static and Dynamic Content." https://developers.cloudflare.com/cache/

4. **RFC 7234** (2014). "Hypertext Transfer Protocol (HTTP/1.1): Caching." https://tools.ietf.org/html/rfc7234

5. **Veeraraghavan, K., et al.** (2016). "Kraken: Leveraging Live Traffic Tests to Identify and Resolve Resource Utilization Bottlenecks in Large Scale Web Services." OSDI 2016.

6. **Fitzpatrick, B.** (2004). "Distributed Caching with Memcached." Linux Journal.

## Next: [Chapter 7: Database Performance Patterns](./07-database-patterns.md)

With caching strategies in place to reduce load on our data stores, the next chapter examines how to optimize the database layer itself through query optimization, indexing strategies, and connection management.
