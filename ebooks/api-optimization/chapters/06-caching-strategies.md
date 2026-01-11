# Chapter 6: Caching Strategies

![Chapter 6 Opener](../assets/ch06-opener.html)

\newpage

## Overview

Caching is often described as the single most effective optimization technique available to API developers, and for good reason. A well-implemented caching strategy can reduce p95 latency from hundreds of milliseconds to single digits, cut database load by 90% or more, and transform a struggling API into one that scales effortlessly. The introduction to this book promised that caching would be among the most important techniques we cover. This chapter delivers on that promise with the depth the topic deserves.

The power of caching comes from a simple observation: many API requests ask for the same data. Product catalogs, user profiles, configuration settings, and countless other data types are read far more often than they are written. By storing the results of expensive operations (database queries, computations, or network calls) and reusing them for subsequent requests, we avoid repeating work that has already been done.

However, as Phil Karlton famously noted, "There are only two hard things in Computer Science: cache invalidation and naming things." Caching introduces complexity. Stale data can cause bugs that are maddening to reproduce. Cache stampedes can take down production systems. Memory pressure from unbounded caches can degrade performance rather than improve it. This chapter addresses these challenges head-on.

We examine caching across every layer of the stack: from the database's internal buffer pools, through application-level memoization, to distributed caches like Redis, and finally to CDN edge caches positioned globally. Each layer offers different trade-offs between latency, consistency, and complexity. Understanding these trade-offs, and knowing how to measure their effectiveness, distinguishes strategic caching from hopeful guessing.

Throughout this chapter, we maintain our empirical approach: every caching decision should be driven by measured cache hit rates, latency improvements, and consistency requirements. A cache that is not measured is a cache that is not understood.

## Key Concepts

### The Cache Hierarchy

Modern API systems employ multiple layers of caching, each with distinct characteristics. Understanding this hierarchy helps us place data at the optimal layer for our access patterns.

<!-- DIAGRAM: Cache hierarchy pyramid showing layers from top to bottom: Browser cache (0ms network latency) -> CDN edge (10-50ms from user) -> Distributed cache/Redis (1-5ms from app) -> In-process cache (microseconds) -> Database buffer pool (microseconds, but still disk-backed) -> Database disk (10-100ms), with annotations showing typical latencies and use cases for each layer -->

![Cache Hierarchy](../assets/ch06-cache-hierarchy.html)

**L0: Database Internal Caches**

Before considering application-level caching, understand that your database already caches aggressively. PostgreSQL's shared buffers, MySQL's InnoDB buffer pool, and similar mechanisms cache recently accessed data pages in memory. A query that would take 50ms to read from disk might return in microseconds if the data is already in the buffer cache.

This is often overlooked. Teams add Redis caching for data that is already effectively cached by the database itself. Measure your database cache hit ratio before adding additional caching layers. A PostgreSQL database with a 99% buffer cache hit ratio may not benefit significantly from adding Redis for the same data.

**L1: In-Process Cache**

The fastest cache is memory in the application process itself. In-process caches like Python's `functools.lru_cache`, Rust's `moka`, or Node.js's `node-cache` provide sub-millisecond access times, typically measured in microseconds. These caches are ideal for frequently accessed, computationally expensive data that does not change often: configuration values, compiled templates, parsed schemas, or database connection metadata.

The trade-off is memory consumption and the lack of sharing between application instances. Each instance maintains its own cache, which can lead to inconsistency in horizontally scaled deployments. If you have 10 application instances and update a cached value, the other 9 instances will serve stale data until their caches expire or are invalidated.

**L2: Distributed Cache**

Distributed caches like Redis or Memcached sit between the application and the database. They provide shared state across all application instances with typical latencies of 1-5ms over a local network. Redis has become the de facto standard for application caching, offering not just key-value storage but also data structures like sorted sets, hash maps, and pub/sub messaging that enable sophisticated caching patterns.

According to Redis documentation, properly configured Redis instances can handle over 100,000 operations per second on modest hardware, making them suitable for high-throughput API scenarios [Source: Redis Documentation, 2024].

**L3: Content Delivery Network (CDN)**

CDNs cache content at edge locations distributed globally. When a user in Tokyo requests data from an API hosted in Virginia, a CDN edge node in Tokyo can serve the cached response without the request ever reaching the origin server. This eliminates network latency that can add 100-300ms for intercontinental requests.

CDN caching for APIs differs from static asset caching. API responses are often personalized, authenticated, or dynamic. Effective CDN caching requires careful header configuration and cache key design, topics we cover in depth later in this chapter.

Cloudflare reports that customers with well-configured caching rules achieve cache hit ratios above 90% for cacheable content, dramatically reducing origin server load [Source: Cloudflare, 2023].

For comprehensive coverage of CDN architecture, edge workers, and advanced edge patterns, see [Chapter 12: Edge Infrastructure](./12-edge-infrastructure.md).

**L4: Browser/Client Cache**

For API clients, browser caching reduces requests entirely. When an API response includes appropriate `Cache-Control` headers, the browser may serve subsequent requests from its local cache without any network activity. This is particularly effective for mobile applications where network requests drain battery and may be slow or unreliable.

**Choosing the Right Layer**

Each caching layer has its place:

| Data Characteristic | Recommended Layer |
|---------------------|-------------------|
| Rarely changes, accessed constantly | L1 (In-process) + L2 (Redis) |
| User-specific, session-bound | L2 (Redis with user-scoped keys) |
| Same for all users, changes occasionally | L2 (Redis) + L3 (CDN) |
| Static reference data | L3 (CDN) + L4 (Browser) |
| Frequently queried, rarely written | Ensure L0 (Database buffers) is sufficient first |

### Database Internal Caching

Before adding application-level caches, understand how your database caches data internally. Modern databases maintain sophisticated caching layers that can eliminate the need for additional caching in many scenarios.

<!-- DIAGRAM: PostgreSQL buffer cache architecture showing: Query -> Check shared_buffers -> [Hit: return from memory, ~0.1ms] or [Miss: Load from disk into buffers, possibly evicting LRU pages, 10-100ms] -> Return to query. Annotate with shared_buffers size and hit ratio monitoring -->

![Database Buffer Cache Architecture](../assets/ch06-database-buffer-cache.html)

**PostgreSQL Shared Buffers**

PostgreSQL uses `shared_buffers` as its primary data cache. When a query requests data, PostgreSQL first checks shared buffers. If the data is present (a cache hit), the query returns immediately without disk I/O. If the data is absent (a cache miss), PostgreSQL reads it from disk and stores it in shared buffers for future queries.

The default shared_buffers value of 128 MB is intentionally conservative. For dedicated database servers, PostgreSQL documentation recommends setting shared_buffers to approximately 25% of total system memory. A server with 64 GB RAM might use 16 GB for shared_buffers [Source: PostgreSQL Documentation, 2024].

Monitor your buffer cache hit ratio to determine if shared_buffers is sized appropriately. A hit ratio below 90% suggests either shared_buffers is too small or your working set exceeds available memory. Aim for hit ratios above 99% for frequently accessed tables.

**MySQL InnoDB Buffer Pool**

MySQL's InnoDB storage engine uses a buffer pool that serves a similar purpose. The `innodb_buffer_pool_size` parameter controls the cache size, with a common recommendation of 70-80% of available memory for dedicated database servers [Source: MySQL Documentation, 2024].

The ratio of `Innodb_buffer_pool_read_requests` to `Innodb_buffer_pool_reads` indicates cache effectiveness. A ratio of 1000:1 or higher indicates excellent caching, meaning nearly all reads are served from memory.

**Query Plan Caches**

Beyond data caching, databases cache query execution plans. Parsing and planning a complex query can take milliseconds. PostgreSQL caches plans for prepared statements, while MySQL caches plans in its query cache (deprecated in MySQL 8.0) and through prepared statements.

Use prepared statements consistently to benefit from plan caching. Parameterized queries that differ only in their bound values share the same cached plan, while dynamically constructed SQL forces replanning for each execution.

**When Database Caching Is Sufficient**

If your database buffer cache hit ratio exceeds 99% and query latencies are acceptable, adding Redis may add complexity without proportional benefit. Database caching is sufficient when:

- Your working set fits comfortably in database memory
- Queries are well-indexed and return quickly
- You do not need caching across multiple services
- Consistency requirements are strict (database caching is always consistent)

Add Redis or other distributed caches when you need to cache across service boundaries, when you need data structures beyond key-value (like sorted sets for leaderboards), or when database load needs to be reduced even for already-cached queries.

### HTTP Caching Mechanics

HTTP caching, governed by RFC 9111 (formerly RFC 7234), provides the protocol-level foundation for CDN and browser caching. Understanding these mechanics is essential for API developers, as small header changes can dramatically affect caching behavior [Source: RFC 9111, 2022].

**Cache-Control Directives**

The `Cache-Control` header is the primary mechanism for controlling caching behavior. Key directives for API responses:

| Directive | Meaning |
|-----------|---------|
| `max-age=N` | Cache for N seconds in any cache (browser, CDN, proxies) |
| `s-maxage=N` | Cache for N seconds in shared caches (CDN) only; overrides max-age for CDN while allowing different browser cache duration |
| `private` | Response is user-specific; do not cache in shared caches (CDN). Use for authenticated, personalized responses |
| `public` | Response can be cached by any cache, including shared caches |
| `no-cache` | Must revalidate with origin before serving cached copy |
| `no-store` | Never cache this response. Use for sensitive data |
| `stale-while-revalidate=N` | Serve stale content immediately while fetching fresh content in background |
| `stale-if-error=N` | Serve stale content if origin returns error |

A typical cacheable API response might use `Cache-Control: public, max-age=60, s-maxage=300, stale-while-revalidate=600`. This configuration caches in browsers for 60 seconds, in CDN for 5 minutes, and allows serving stale content for up to 10 minutes while revalidating in the background.

**ETags and Conditional Requests**

ETags enable efficient cache revalidation. When a client has a cached response, it can ask the server if the data has changed rather than fetching the entire response again.

<!-- DIAGRAM: HTTP conditional request flow showing: Client with cached response (ETag: "abc123") -> If-None-Match: "abc123" to server -> Server checks current ETag -> [Match: 304 Not Modified, no body transferred] or [Changed: 200 OK with new ETag and full response body] -->

![HTTP Conditional Request Flow](../assets/ch06-conditional-request-flow.html)

The flow works as follows:

1. Server includes `ETag: "abc123"` in the initial response
2. Client caches the response with its ETag
3. When cache expires, client sends `If-None-Match: "abc123"` with the request
4. Server compares the ETag to the current data:
   - If unchanged: return `304 Not Modified` with no body (saves bandwidth)
   - If changed: return `200 OK` with new data and new ETag

For API responses, generate ETags from a hash of the response body or from version timestamps. The key is consistency: the same data must always produce the same ETag.

**stale-while-revalidate: The Hidden Performance Gem**

The `stale-while-revalidate` directive is one of the most underutilized caching features for APIs. It instructs caches to serve stale content immediately while fetching fresh content in the background.

Without stale-while-revalidate, when cached content expires, users wait for the full round trip to the origin. With it, users receive an immediate response while the cache refreshes asynchronously. A configuration like `Cache-Control: max-age=60, stale-while-revalidate=600` provides a 60-second "fresh" window where cached content is served directly. After 60 seconds, content is "stale but usable" for 10 minutes. Requests during this window receive the stale content immediately while the cache fetches fresh content for subsequent requests [Source: RFC 5861, 2010].

**stale-if-error: Resilience Through Caching**

The `stale-if-error` directive provides resilience when your origin is unavailable. If the origin returns an error (5xx status codes), the cache can serve stale content rather than forwarding the error to users. Using `Cache-Control: max-age=60, stale-if-error=86400` allows serving day-old content if the origin fails, often preferable to showing users an error page. Combined with stale-while-revalidate, this creates a robust caching strategy that degrades gracefully under origin failures [Source: MDN Web Docs, 2024].

**The Vary Header**

The `Vary` header tells caches which request headers affect the response. Without proper Vary configuration, caches may serve incorrect responses. For example, `Vary: Accept-Encoding, Accept-Language` creates separate cache entries for different encodings and languages. A gzip-compressed English response is cached separately from an uncompressed Spanish response.

Be intentional about Vary headers. Each additional header value fragments the cache, reducing hit rates. `Vary: Cookie` or `Vary: Authorization` effectively disable CDN caching since each user gets unique cache entries.

For authenticated APIs, consider validating authentication at the edge and forwarding a standardized user-id header, allowing the response to be cached per-user-id rather than per-cookie.

### Application-Layer Caching

Application-layer caching operates within your service code, providing fine-grained control over what is cached, for how long, and under what conditions.

**Request-Scoped Caching (Memoization)**

Request-scoped caching stores computed values for the duration of a single request. This is particularly valuable when the same data is needed multiple times during request processing. For example, checking user permissions in multiple middleware layers. Using context variables, you can create a per-request cache dictionary that automatically discards when the request completes.

Request-scoped caching is safe because the cache is automatically discarded when the request completes. There is no risk of serving stale data to other users.

**Function Memoization**

For expensive pure functions (those that always return the same output for the same input), memoization caches results indefinitely. Python's `functools.lru_cache` provides simple memoization with configurable size limits. Rust's `moka` crate provides thread-safe, bounded caching with TTL support.

**The DataLoader Pattern**

The DataLoader pattern, popularized by Facebook for GraphQL, combines batching and caching to solve the N+1 query problem. It collects all data requests during a single tick of the event loop, then executes one batched query. When multiple loads are called concurrently, DataLoader batches them into a single database query and returns results in the same order as requested.

DataLoader provides per-request caching: if user-1 is requested twice during the same request, the second call returns the cached result. This eliminates duplicate queries without risking stale data across requests [Source: DataLoader Documentation, 2024].

#### Query Complexity Analysis

Unbounded GraphQL queries represent a denial-of-service vulnerability. A malicious client can construct deeply nested queries that consume excessive server resources. Query complexity analysis assigns costs to fields and rejects queries exceeding thresholds.

Common approaches include:

- **Depth limiting**: Reject queries exceeding maximum nesting depth (typically 7-15 levels)
- **Field cost assignment**: Assign complexity points to each field, sum for total query cost
- **Multiplier fields**: List fields multiply the cost of their children by expected result count

Shopify's GraphQL API uses complexity analysis, publishing their cost calculation formula and rate limits publicly [Source: Shopify GraphQL Admin API Documentation, 2024].

### Distributed Cache Patterns

Distributed caches like Redis provide shared caching across multiple application instances. They introduce new considerations around consistency, invalidation, and failure handling.

**Cache-Aside (Lazy Loading)**

Cache-aside earns its name from the cache's position in the architecture: it sits *beside* the data path rather than in front of it. The application explicitly manages both the cache and the database, deciding when to read from each and when to populate the cache.

The logic is straightforward: check cache first, and on a miss, fetch from the database and store the result before returning. What makes cache-aside powerful is what it *does not* do. It does not require cache warming at startup. It does not cache data that is never requested. It does not maintain consistency between cache and database automatically. These are features, not bugs.

<!-- DIAGRAM: Cache-aside pattern sequence diagram showing: Client -> Application -> Check Cache -> [Hit: return cached data] or [Miss: Query Database -> Store result in Cache -> return data to client] -->

![Cache-Aside Pattern](../assets/ch06-cache-aside-pattern.html)

The cache contents emerge organically from actual access patterns. Frequently requested data stays hot; rarely requested data either never enters the cache or expires without renewal. This self-organizing property makes cache-aside well-suited for workloads where the hot set is not known in advance or shifts over time.

The trade-off is that every cache miss pays the full database round-trip cost, and the application bears responsibility for invalidation. When data changes in the database, the cache does not know. Stale data persists until TTL expiration or explicit invalidation.

```
on read request for key:
    value = check cache for key
    if cache hit:
        return value

    value = fetch from database
    store value in cache with TTL
    return value
```

**Write-Through**

In write-through caching, every write operation updates both the cache and the database synchronously. This ensures the cache is always consistent with the database but increases write latency since both operations must complete before the write is acknowledged.

Write-through is appropriate when read latency is critical and you cannot tolerate any stale reads, but write volume is moderate enough that the latency penalty is acceptable.

**Write-Behind (Write-Back)**

Write-behind inverts the write-through approach: writes go to the cache immediately and are asynchronously persisted to the database. This minimizes write latency since the application only waits for the cache write, but introduces the risk of data loss if the cache fails before the write is persisted.

This pattern is suitable for high-write-volume scenarios where some data loss is acceptable, such as analytics events or activity logs where losing a few records is not catastrophic.

<!-- DIAGRAM: Write-through vs Write-behind comparison showing: Write-through with synchronous paths to both cache and database (higher latency, strong consistency) vs Write-behind with async database write (lower latency, eventual consistency, data loss risk) -->

![Write-Through vs Write-Behind Patterns](../assets/ch06-write-patterns.html)

**Redis Pub/Sub for Distributed Invalidation**

When an API service is scaled horizontally across multiple instances, each instance may maintain its own in-memory cache. If one instance updates data, others continue serving stale content.

Redis Pub/Sub provides a lightweight solution. When data changes, publish an invalidation message. All service instances subscribe to the channel and invalidate their local caches accordingly.

<!-- DIAGRAM: Redis Pub/Sub cache invalidation across instances: Service Instance A writes to DB -> Publishes "invalidate:user:123" to Redis -> Service Instances B, C, D receive message -> Each invalidates local cache entry -->

![Redis Pub/Sub Cache Invalidation](../assets/ch06-redis-pubsub-invalidation.html)

When data changes, the publisher broadcasts an invalidation message to a Redis channel. Each service instance subscribes to the channel and invalidates its local cache entry when a message arrives.

Note that Pub/Sub is best-effort and non-persistent. If a service is restarted during a publish, it may miss the message. Combine Pub/Sub invalidation with TTL-based expiration as a fallback.

**Redis 6+ Client-Side Caching**

Redis 6 introduced server-assisted client-side caching. The server tracks which keys each client has accessed and sends invalidation messages when those keys change. When client tracking is enabled and you access a key, Redis remembers the access. If another client modifies that key, Redis automatically sends an invalidation to all clients that accessed it.

This provides the benefits of local caching with automatic, server-driven invalidation. The trade-off is increased memory usage on the Redis server to track client access patterns [Source: Redis Documentation, 2024].

### Edge and CDN Caching for APIs

CDN caching for APIs differs from static asset caching in important ways. API responses are often personalized, authenticated, or dynamic. Effective CDN caching requires intentional configuration.

**Why APIs Need Different CDN Strategies**

Static assets like images and JavaScript files are identical for all users and change infrequently. API responses may vary by:

- User identity (personalized content)
- Request parameters (pagination, filters)
- Request headers (Accept-Language, Accept-Encoding)
- Time of day (real-time data)

Naive CDN caching of API responses can serve incorrect data to users. Intentional cache key design and header configuration are essential.

**Cache Keys for API Responses**

The cache key determines when a cached response can be reused. By default, CDNs key on URL only. This is insufficient for APIs where the same URL may return different responses based on headers or authentication.

Configure cache keys to include relevant request characteristics. For example, a CDN cache rule might match API product endpoints and include the URL, Accept-Language header, and query string in the cache key while setting a 5-minute shared cache duration.

Be intentional about what is included. Each additional cache key component fragments the cache. Including `Cookie` in the cache key effectively disables caching.

**Surrogate Keys for Targeted Invalidation**

Surrogate keys (also called cache tags) enable invalidation by logical entity rather than URL pattern. Tag responses with the entities they contain using a header like `Surrogate-Key: product-123 category-electronics user-456`. When product 123's data changes, purge all responses tagged with `product-123` across all edge locations. This is far more precise than attempting to guess all URL patterns that might include product 123.

Cloudflare's Cache Tags, Fastly's Surrogate-Key, and Akamai's Edge-Cache-Tag provide this capability.

**When to Use Edge Caching**

Edge caching is most effective for:

- **Read-heavy, public data**: Product catalogs, content feeds, reference data
- **Geographically distributed users**: Edge cache eliminates cross-continent latency
- **High-volume endpoints**: Offloading popular endpoints reduces origin load

Edge caching is less suitable for:

- **User-specific data**: Per-user cache entries fragment the cache
- **Rapidly changing data**: High invalidation frequency negates caching benefits
- **Strong consistency requirements**: Edge eventual consistency may be unacceptable

For comprehensive coverage of CDN architecture, edge workers, edge data stores, and edge authentication, see [Chapter 12: Edge Infrastructure](./12-edge-infrastructure.md).

### Cache Invalidation Strategies

Cache invalidation determines how stale data is removed or updated. The choice of strategy depends on your consistency requirements and the nature of your data.

**TTL-Based Expiration**

Time-to-live (TTL) is the simplest invalidation strategy: cached data automatically expires after a fixed duration. A TTL of 300 seconds means data may be up to 5 minutes stale, which is acceptable for many use cases.

The challenge is choosing the right TTL:

- **Too short**: Cache provides little benefit; requests still hit the database
- **Too long**: Users see stale data; changes take too long to propagate

For most API data, TTLs between 60 seconds and 1 hour strike a reasonable balance. The optimal value depends on your specific data's update frequency and staleness tolerance.

**Event-Based Invalidation**

Event-based invalidation removes cached data when the underlying data changes. When a user updates their profile, the application explicitly deletes the cached profile data.

The Facebook paper "Scaling Memcache at Facebook" describes their invalidation pipeline where database writes trigger cache invalidations across their globally distributed Memcached clusters. They found that event-based invalidation was essential for maintaining consistency at scale [Source: Nishtala et al., "Scaling Memcache at Facebook," NSDI 2013].

Implement event-based invalidation using:

1. **Direct invalidation**: Application code deletes cache entries after writes
2. **Change Data Capture (CDC)**: Database change events trigger cache invalidation
3. **Pub/Sub messaging**: Publish invalidation events; all services subscribe

**Version-Based Invalidation**

Version-based caching embeds a version identifier in the cache key. When data changes, the version increments, effectively creating a new cache key (e.g., `user:123:v1` becomes `user:123:v2`). Old cache entries naturally expire via TTL.

This pattern is particularly useful for configuration data or feature flags where you want an immediate switch across all instances. Changing the version causes all instances to fetch fresh data, achieving coordinated invalidation without explicit communication.

**Surrogate Key Purging**

For CDN caches, surrogate keys enable targeted invalidation. When product data changes, purge by tag using the CDN provider's API.

This invalidates all cached responses that contain product 123, regardless of URL structure. Surrogate key purging is typically fast (sub-second) across global CDN networks [Source: Cloudflare Documentation, 2024].

### The Thundering Herd Problem

The thundering herd (also called cache stampede) occurs when a popular cache entry expires and many concurrent requests simultaneously attempt to regenerate it. If 1000 requests arrive in the moment after a cache entry expires, all 1000 may attempt to fetch from the database simultaneously, potentially overwhelming it.

This is not a theoretical concern. Cache stampedes have caused outages at companies of all sizes. The mitigation strategies below should be considered essential for any production caching system.

<!-- DIAGRAM: Thundering herd mitigation strategies comparison showing four solutions side-by-side: 1) Single-flight: Lock acquired by first request, others wait, single DB query 2) Probabilistic early expiration: Requests have increasing probability of refresh as TTL approaches, spreads load over time 3) TTL with jitter: Entries expire at random times within range (e.g., 270-330s), prevents synchronized expiration 4) stale-while-revalidate: Serve stale immediately, refresh in background, no user-facing delay -->

![Thundering Herd Mitigation Strategies](../assets/ch06-thundering-herd-strategies.html)

**Single-Flight Pattern**

The single-flight pattern ensures only one request regenerates a cache entry while others wait for its result. The first request to find an expired entry acquires a lock, fetches the data, and populates the cache. Concurrent requests that arrive during this window wait for the first request to complete rather than independently fetching the data.

This pattern is implemented in Go's `golang.org/x/sync/singleflight` package and similar libraries in other languages.

```
on cache miss for key:
    if another request is already fetching key:
        wait for that request to complete
        return its result

    mark this request as the fetcher for key
    value = fetch from database
    notify all waiting requests
    return value
```

**Implementation considerations:**

- **Lock timeout**: Prevent deadlocks if the first request fails. Set a maximum wait time after which waiting requests proceed independently.
- **Lock scope**: Use distributed locks (Redis-based) for multi-instance deployments. Process-local locks only prevent stampedes within a single instance.
- **Error handling**: If the first request fails, the lock should be released immediately so another request can retry.

**Probabilistic Early Expiration (XFetch)**

Probabilistic early expiration, formalized as the XFetch algorithm, spreads cache regeneration over time by having requests probabilistically refresh the cache before TTL expiration. The probability increases as the TTL approaches.

The algorithm works as follows: when a request accesses a cache entry, it calculates the probability of early refresh based on remaining TTL and a configurable "beta" parameter. A random value determines whether this request should refresh the cache. The probability increases as expiry approaches, using an exponential distribution scaled by the recomputation time (delta) and the beta parameter.

With beta = 1 and a delta of 1 second (time to recompute), the probability of early refresh begins to increase significantly about 2-3 seconds before expiration. This spreads load over time rather than concentrating it at the expiration moment [Source: Vattani et al., "Optimal Probabilistic Cache Stampede Prevention," VLDB 2015].

**TTL with Jitter**

Adding randomized jitter to TTL values prevents synchronized expiration across cache entries. Instead of all entries expiring at exactly 300 seconds, they expire between 270 and 330 seconds. A typical implementation adds or subtracts a random percentage (e.g., ±10%) from the base TTL.

This technique is particularly effective when populating caches in bulk (such as during startup or cache warming) to prevent all entries from expiring simultaneously.

**stale-while-revalidate**

At the HTTP layer, `stale-while-revalidate` provides thundering herd protection at CDNs and reverse proxies. When a cache entry expires, the CDN serves the stale content immediately while fetching fresh content in the background. Only one background fetch occurs regardless of concurrent requests. Using `Cache-Control: max-age=60, stale-while-revalidate=600` enables this behavior.

This approach is powerful because it eliminates user-visible latency during cache refresh. Users always receive an immediate response, even when the cache is refreshing.

**Background Refresh / Cache Warming**

Proactive background refresh eliminates cache misses entirely by refreshing entries before they expire. A background process periodically identifies entries approaching expiration (e.g., using a Redis sorted set to track expiry times) and refreshes them before users experience cache misses.

This pattern is appropriate for high-value, predictable access patterns where cache misses are particularly costly.

### Advanced Patterns

Beyond the fundamental patterns, several advanced techniques address specific caching challenges.

**Negative Caching**

Negative caching stores the absence of data. When a query returns no results (a 404 or empty set), cache that fact to prevent repeated database queries for nonexistent data. The implementation stores a sentinel value (like "NOT_FOUND") in the cache for missing entries, with a shorter TTL than positive results.

Use shorter TTLs for negative results. If data is created later, you do not want to cache "not found" for hours.

**Request Coalescing**

Request coalescing combines multiple identical concurrent requests into a single backend call. Unlike single-flight (which operates on cache population), coalescing operates on the request itself.

CDNs like Cloudflare and Fastly implement request coalescing automatically. When multiple requests for the same resource arrive simultaneously, only one request goes to origin. Other requests wait and receive the same response.

At the application level, implement coalescing using the same single-flight pattern. Multiple concurrent calls for the same key are coalesced into a single backend fetch, with all callers receiving the same result.

**Multi-Tier Cache Coordination**

When using multiple cache layers (L1 in-process + L2 Redis), coordinate invalidation across tiers.

<!-- DIAGRAM: Multi-tier caching showing: Request -> L1 In-Process Cache (microseconds) -> L2 Redis (1-5ms) -> Database (10-100ms), with invalidation arrows flowing back through layers. When data changes: invalidate L2, then broadcast to invalidate all L1 instances -->

![Multi-Tier Cache Coordination](../assets/ch06-multi-tier-cache.html)

The pattern:

1. **Read path**: Check L1 first, then L2, then database
2. **Write path**: Write to database, invalidate L2, broadcast L1 invalidation
3. **L1 TTL**: Keep short (seconds to minutes) to limit stale data exposure
4. **L2 TTL**: Can be longer since invalidation is explicit

The read path cascades through cache tiers: check the in-process cache first (fastest), then the distributed cache like Redis, and finally the database if both miss. On write, invalidate the distributed cache and broadcast the invalidation to all instances for their local caches.

**Proxy Caching**

Reverse proxies like Varnish and nginx can cache API responses before they reach your application, providing an additional caching layer with sophisticated configuration options.

Varnish, in particular, excels at API caching with features like:

- **Grace mode**: Serve stale content while fetching fresh (similar to stale-while-revalidate)
- **Saint mode**: Temporarily mark backends as unhealthy and serve stale content
- **Request coalescing**: Collapse identical concurrent requests

For most deployments, CDN caching (L3) provides similar benefits with less operational overhead. Consider proxy caching when you need caching logic more sophisticated than CDN rules allow or when operating in environments where CDN is not feasible.

### Monitoring Cache Effectiveness

Regardless of which caching pattern or invalidation strategy we choose, measuring cache performance is essential for data-driven optimization. Without instrumentation, we cannot know whether our cache is providing value or simply adding complexity.

**Key Metrics**

| Metric | What It Measures | Target |
|--------|------------------|--------|
| **Hit rate** | Percentage of requests served from cache | >90% for most workloads |
| **Miss rate** | Percentage of requests requiring origin fetch | <10% |
| **Eviction rate** | How often entries are evicted (memory pressure) | Low and stable |
| **Latency (hit)** | Latency for cache hits | <5ms for Redis, <1ms for in-process |
| **Latency (miss)** | Latency for cache misses | Baseline without cache |
| **Memory usage** | Cache memory consumption | Below configured limit |
| **Key count** | Number of entries in cache | Understand working set size |

**Database Cache Monitoring**

Monitor your database buffer cache hit ratio. For PostgreSQL, query `pg_stat_database` for overall hit ratios and `pg_statio_user_tables` for per-table hit ratios to identify hot tables.

**Redis Cache Monitoring**

Redis provides built-in metrics via the INFO command. The `keyspace_hits` and `keyspace_misses` values let you calculate hit rate (hits divided by total requests).

Also monitor:

- `used_memory` vs `maxmemory`: Are you approaching memory limits?
- `evicted_keys`: High eviction rate indicates memory pressure
- `connected_clients`: Connection pool sizing
- `instantaneous_ops_per_sec`: Throughput capacity

**CDN Cache Monitoring**

CDN providers expose cache metrics through dashboards and APIs:

- **Cache hit ratio by endpoint**: Identify which endpoints benefit from caching
- **Origin request reduction**: How much load is offloaded from origin
- **Geographic hit distribution**: Cache performance by edge location
- **Bandwidth savings**: Data transferred from cache vs origin

Cloudflare's `cf-cache-status` header in responses indicates cache behavior: `HIT`, `MISS`, `EXPIRED`, `BYPASS`, `DYNAMIC`. Log and aggregate these values to understand caching effectiveness.

**Alerting on Cache Degradation**

Set alerts for cache performance degradation:

- **Hit rate drops below 80%**: Investigate cache key fragmentation or invalidation storms
- **Eviction rate spikes**: Memory pressure; consider increasing cache size
- **Latency increases**: Network issues, hot keys, or cache overload
- **Connection errors**: Redis availability problems

## Common Pitfalls

- **Caching without measuring hit rate**: A cache with a low hit rate wastes memory and adds latency for cache checks. Always instrument your cache and monitor hit rates. A hit rate below 80% often indicates poor cache key design or inappropriate TTLs.

- **Ignoring database buffer cache**: Adding Redis for data that is already well-cached by the database adds complexity without proportional benefit. Measure database buffer cache hit ratio before adding application-level caching.

- **Ignoring cache key collisions**: Poor cache key design can cause different data to share the same key, leading to incorrect responses. Always include all parameters that affect the response in the cache key, and consider including a version prefix.

- **Unbounded cache growth**: Caches without memory limits or eviction policies can exhaust available memory. Always configure maximum memory limits and an eviction policy (LRU is a safe default).

- **Caching personalized data with shared keys**: User-specific data cached under generic keys can leak to other users, a serious security vulnerability. Always include user identifiers in cache keys for personalized data.

- **Synchronous cache invalidation across distributed systems**: Attempting to synchronously invalidate caches across multiple services or regions introduces coupling and latency. Prefer eventual consistency with reasonable TTLs, or use async invalidation via Pub/Sub.

- **Not accounting for cache stampede**: Popular cache entries expiring under high load can overwhelm databases. Implement single-flight, probabilistic early expiration, stale-while-revalidate, or TTL jitter to mitigate thundering herd.

- **Caching errors indefinitely**: Caching error responses at long TTLs can make temporary failures permanent from the user's perspective. Either do not cache errors, or use very short TTLs (seconds, not minutes). Consider using `stale-if-error` to serve stale content during origin failures.

- **Over-relying on cache for availability**: If your application cannot function during a cache outage, the cache has become a single point of failure. Design for graceful degradation when the cache is unavailable.

- **Over-fragmenting CDN cache with Vary headers**: Each Vary header value multiplies cache entries. `Vary: Cookie` effectively disables CDN caching. Be intentional about cache key components.

- **Missing stale-while-revalidate for API resilience**: Not using `stale-while-revalidate` and `stale-if-error` means users experience latency spikes during revalidation and errors during origin failures.

- **Not using prepared statements**: Beyond preventing SQL injection, prepared statements enable query plan caching. Dynamic SQL forces replanning for each query.

## Summary

- **The cache hierarchy** (database buffers, in-process cache, distributed cache, CDN, browser) provides multiple opportunities to serve requests without hitting the origin database. Understand and monitor your database's internal caching before adding application-level caches.

- **Database internal caching** is often overlooked. PostgreSQL shared_buffers and MySQL InnoDB buffer pool cache data pages in memory. Monitor buffer cache hit ratios; a 99% hit rate may obviate the need for Redis for the same data.

- **HTTP caching mechanics** (Cache-Control, ETags, stale-while-revalidate) control CDN and browser behavior. Use `stale-while-revalidate` for latency-free cache refresh and `stale-if-error` for resilience during origin failures.

- **Application-layer caching** includes request-scoped memoization (safe, per-request), function memoization (for pure functions), and the DataLoader pattern (batching + caching for N+1 elimination).

- **Distributed cache patterns** like cache-aside are foundational. Use Redis Pub/Sub for cross-instance invalidation. Redis 6+ client-side caching provides automatic, server-driven invalidation.

- **Edge caching for APIs** requires intentional configuration. Use surrogate keys for targeted invalidation. Avoid Vary: Cookie which fragments the cache per-user.

- **Cache invalidation strategies** include TTL-based (simple), event-based (consistent), and version-based (coordinated). Match the strategy to your consistency requirements.

- **The thundering herd problem** is real and dangerous. Mitigation strategies include single-flight (one request regenerates, others wait), probabilistic early expiration (spread load over time), TTL jitter (prevent synchronized expiration), and stale-while-revalidate (serve stale while refreshing).

- **Advanced patterns** include negative caching (cache "not found"), request coalescing (combine identical requests), multi-tier coordination (L1 + L2), and background refresh (proactive cache warming).

- **Monitor cache effectiveness** across all layers. Key metrics: hit rate (>90%), miss rate (<10%), eviction rate (low and stable), latency (sub-5ms for Redis). Alert on degradation.

## References

1. **Nishtala, R., et al.** (2013). "Scaling Memcache at Facebook." NSDI 2013. https://www.usenix.org/conference/nsdi13/technical-sessions/presentation/nishtala

2. **Redis Documentation** (2024). "Redis Best Practices." https://redis.io/docs/management/optimization/

3. **Cloudflare** (2023). "Caching Static and Dynamic Content." https://developers.cloudflare.com/cache/

4. **RFC 9111** (2022). "HTTP Caching." https://httpwg.org/specs/rfc9111.html

5. **RFC 5861** (2010). "HTTP Cache-Control Extensions for Stale Content." https://tools.ietf.org/html/rfc5861

6. **Vattani, A., et al.** (2015). "Optimal Probabilistic Cache Stampede Prevention." VLDB Endowment.

7. **PostgreSQL Documentation** (2024). "Resource Consumption - shared_buffers." https://www.postgresql.org/docs/current/runtime-config-resource.html

8. **MySQL Documentation** (2024). "InnoDB Buffer Pool." https://dev.mysql.com/doc/refman/8.0/en/innodb-buffer-pool.html

9. **MDN Web Docs** (2024). "HTTP Caching." https://developer.mozilla.org/en-US/docs/Web/HTTP/Caching

10. **DataLoader Documentation** (2024). "DataLoader for GraphQL." https://github.com/graphql/dataloader

11. **Fitzpatrick, B.** (2004). "Distributed Caching with Memcached." Linux Journal.

12. **Veeraraghavan, K., et al.** (2016). "Kraken: Leveraging Live Traffic Tests to Identify and Resolve Resource Utilization Bottlenecks in Large Scale Web Services." OSDI 2016.

## Next: [Chapter 7: Database and Storage Selection](./07-database-patterns.md)

With caching strategies in place, the next chapter addresses a more fundamental question: which database type fits which access pattern? We examine when to use relational databases, document stores, key-value stores, wide-column databases, vector databases, and search engines.
