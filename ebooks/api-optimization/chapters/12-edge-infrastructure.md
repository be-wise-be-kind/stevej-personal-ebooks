# Chapter 12: Edge Infrastructure

![Chapter 12 Opener](../assets/ch12-opener.html)

\newpage

## Overview

Edge infrastructure represents a fundamental shift in API architecture: rather than processing every request at a centralized origin, we distribute computation, caching, and security enforcement to nodes positioned geographically close to users. The benefits come from two distinct sources, and understanding the difference matters for setting realistic expectations.

**When physics actually helps:** If a request can be handled entirely at the edge—a cache hit, a KV lookup, authentication validation, or rate limiting—the user's request never travels to your origin. A user in Singapore hitting an edge node in Singapore gets a 30ms round-trip instead of 160ms+ to Virginia. This is a genuine physics win: the data simply travels less distance.

**When physics doesn't help:** If your origin servers are in Virginia and a request *must* reach them, a user in Singapore routing through a Singapore edge node still needs to traverse the same 15,000 kilometers to Virginia and back. The edge node doesn't teleport data. For origin-required requests with a single-region origin, the distance is fundamentally the same.

So why use edge infrastructure for origin-required requests? Because edge vendors provide infrastructure you'd never build yourself: pre-warmed connection pools to your origin, HTTP/3 and QUIC by default, optimized routing through their backbone networks, and request coalescing that combines multiple user requests into fewer origin calls. The distance is the same, but the quality of the pipe is dramatically better.

The breakdown of a typical API request reveals the opportunity: processing takes just 1-2 milliseconds, but network transit consumes the rest.

![Where Does Latency Come From?](../assets/ch12-latency-waterfall.html)

This creates a clear optimization strategy with three tiers:

1. **Handle entirely at edge**: Cache hits, KV lookups, auth validation, rate limiting. The request never reaches origin. User experiences 30ms instead of 160ms—a genuine physics win.

2. **Accept at edge, process asynchronously**: For operations that need origin processing but don't require an immediate result, edge workers can validate the request, enqueue it, and return immediately. The user experiences 30ms while origin processes the work in the background. Analytics events, webhook deliveries, and many write operations fit this pattern.

3. **Synchronous origin required**: When the response genuinely depends on origin data, edge infrastructure still helps through optimized connections—but the physics are what they are.

![Three Tiers of Edge Advantage](../assets/ch12-three-tier-advantage.html)

In practice, many common API operations fit the first two tiers. Cache lookups, authentication validation, rate limiting, session retrieval, and async writes can all be handled at edge with 80-90% latency reductions. Even synchronous origin requests see 30-40% improvement through optimized connection management. The more processing you can push to the edge—or defer asynchronously—the more latency you eliminate from user experience.

Beyond latency reduction, edge infrastructure offloads work from origin servers. CDN caching serves repeated requests without origin involvement. Edge workers handle routing decisions, authentication validation, and response transformation at the network edge. Edge data stores maintain configuration and session data globally. Together, these capabilities reduce origin load, improve resilience, and enable performance that centralized architectures cannot match.

The impact can be dramatic. One browser extension company serving millions of users saw average server connections drop from approximately 500 per server to around 20 after adopting Cloudflare's edge platform. The combination of edge caching, connection pooling, and request coalescing meant origin servers handled a fraction of the traffic they previously processed—without any application code changes.

This chapter extends concepts introduced in earlier chapters. We build on Chapter 6's caching fundamentals with CDN-specific patterns for API responses. We complement Chapter 10's traffic management with edge-native rate limiting. We expand Chapter 11's authentication coverage with edge validation patterns. The techniques here integrate with rather than replace origin-side optimizations.

## Key Concepts

### Choosing an Edge Platform

The edge computing landscape offers platforms ranging from enterprise CDN providers to developer-focused services. Understanding the options helps you choose the right platform for your requirements.

**Enterprise CDN Providers**

Enterprise CDNs offer global reach, sophisticated caching, and comprehensive support contracts:

- **Akamai**: The largest CDN by network size, with over 4,000 points of presence. Strong enterprise features, complex pricing, and deep integration capabilities. Best for organizations with dedicated CDN teams and complex requirements.
- **AWS CloudFront**: Tight integration with AWS services. Lambda@Edge provides edge compute, though with higher cold start latency than dedicated edge platforms. Natural choice for AWS-heavy architectures.
- **Fastly**: Known for real-time cache purging (typically under 200ms globally) and Compute@Edge using WebAssembly. Strong among media companies and API-first organizations.
- **Azure CDN**: Multiple CDN provider options (Microsoft, Akamai, Verizon) through a single interface. Integrates with Azure Front Door for additional edge capabilities.

**Developer-Focused Platforms**

These platforms prioritize developer experience, comprehensive free tiers, and integrated edge capabilities:

- **Cloudflare**: Offers Workers (edge compute), KV (key-value store), D1 (edge database), Durable Objects (coordination), R2 (object storage), and integrated WAF/rate limiting. Comprehensive free tier enables experimentation without commitment.
- **Vercel Edge**: Deep integration with Next.js and frontend frameworks. Edge Functions run on Cloudflare's network. Optimized for frontend-heavy applications with API routes.
- **Netlify Edge**: Deno-based edge functions with strong Jamstack integration. Simpler model focused on request transformation and routing.

**The Cloudflare Platform**

This book uses Cloudflare for examples because it offers a comprehensive free tier, extensive documentation, and covers all edge capabilities (CDN, compute, data, and security) in one platform. The principles apply regardless of which platform you choose.

Cloudflare's edge platform includes:

- **Workers**: JavaScript/TypeScript/Rust edge functions with sub-millisecond cold starts
- **KV**: Globally distributed key-value store with eventual consistency
- **D1**: SQLite database with global read replicas
- **Durable Objects**: Strongly consistent coordination primitives
- **R2**: S3-compatible object storage without egress fees
- **Rate Limiting**: Distributed rate limiting with WAF integration
- **Cache Rules**: Fine-grained caching control for API responses

### CDN Caching for APIs

CDN caching for APIs differs from static asset caching in important ways. API responses are often personalized, authenticated, or dynamic. Effective CDN caching requires careful header configuration and cache key design.

#### Cache-Control Headers for APIs

The `Cache-Control` header governs caching behavior. Key directives for API responses:

- **`max-age=N`**: Cache for N seconds in any cache (browser, CDN, proxies)
- **`s-maxage=N`**: Cache for N seconds in shared caches (CDN) only. Overrides `max-age` for CDN while allowing different browser cache duration.
- **`stale-while-revalidate=N`**: Serve stale content immediately while fetching fresh content in background. Eliminates cache miss latency for users.
- **`private`**: Response is user-specific; do not cache in shared caches (CDN). Use for authenticated, personalized responses.
- **`no-store`**: Never cache this response. Use for sensitive data.

A typical cacheable API response might use `Cache-Control: public, max-age=60, s-maxage=300, stale-while-revalidate=600`, which caches in browsers for 60 seconds, in CDN for 5 minutes, and serves stale content for up to 10 minutes while revalidating.

#### Cache Keys and the Vary Header

The cache key determines when a cached response can be reused. By default, CDNs key on URL only. The `Vary` header adds request headers to the cache key. For example, `Vary: Accept-Encoding, Accept-Language` creates separate cache entries for different encodings and languages. Be intentional about `Vary` headers because each additional header fragments the cache, reducing hit rates. `Vary: Cookie` or `Vary: Authorization` effectively disable caching since each user gets unique responses.

For authenticated APIs, consider alternative patterns: validate authentication at the edge and forward a standardized user-id header, allowing the response to be cached per-user-id rather than per-cookie.

#### Surrogate Keys and Cache Invalidation

Surrogate keys (also called cache tags) enable targeted invalidation. Tag responses with logical identifiers like `product-123`, `category-electronics`, or `user-456`. When product 123's data changes, purge all responses tagged with that key rather than guessing URL patterns. Cloudflare's Cache Tags, Fastly's Surrogate-Key, and Akamai's Edge-Cache-Tag provide this capability.

Purging strategies:
- **Instant purge**: API call triggers immediate invalidation. Use for critical data changes.
- **Event-driven purge**: Database change events trigger purges. Provides consistency without application coupling.
- **TTL-based**: Let content expire naturally. Simplest approach when eventual consistency is acceptable.

#### Debugging Cache Behavior

CDNs add response headers indicating cache status:

- **`CF-Cache-Status`** (Cloudflare): `HIT`, `MISS`, `EXPIRED`, `BYPASS`, `DYNAMIC`
- **`X-Cache`** (CloudFront, Fastly): `Hit from cloudfront`, `Miss from cloudfront`
- **`Age`**: Seconds since the response was cached

Monitor cache hit ratios in your observability stack. Low hit rates indicate cache key fragmentation, aggressive TTLs, or uncacheable content being cached. Target 80%+ hit rates for cacheable API endpoints.

#### Cache Stampede Prevention

A cache stampede (also called thundering herd) occurs when many concurrent requests arrive for the same expired cache entry. All requests simultaneously find the cache empty and attempt to refresh from origin, potentially overwhelming the backend.

The impact can be severe: during a traffic spike, cache expiration at a specific moment might trigger 50,000 simultaneous origin requests, causing response times to spike to 10 seconds and generating 503 errors as the backend struggles to handle the load. With request coalescing enabled, the same expiration triggers exactly one origin request while the other 49,999 requests wait less than 50ms for the shared response.

Edge platforms provide mechanisms to prevent stampedes:

**Request coalescing (collapse forwarding)**: When multiple requests arrive for the same cache key during a cache miss, the CDN forwards only one request to origin. Subsequent requests wait for the first to complete, then all share the same response. Akamai and other enterprise CDNs provide this capability built-in [Source: Akamai, 2025].

**Stale-while-revalidate**: The `stale-while-revalidate` directive allows serving stale cached content immediately while triggering a background refresh. This eliminates the stampede entirely. Users get instant responses while only one background request fetches fresh content.

**Probabilistic early expiration**: Rather than all cache entries expiring simultaneously, introduce jitter. Some requests randomly trigger refresh before expiration, spreading refresh load over time rather than concentrating it at expiration moments.

**Lock-based refresh**: For critical resources, use Durable Objects to coordinate refresh. Only one worker acquires the refresh lock; others wait or serve stale content. This adds latency but guarantees single-flight refresh.

Each mechanism involves trade-offs:

- **Request coalescing** adds slight latency for waiting requests (typically under 50ms) but requires no configuration
- **Stale-while-revalidate** provides the best user experience (zero added latency) but serves potentially outdated data during the revalidation window
- **Probabilistic early expiration** spreads load but introduces unpredictable refresh timing; with a 5-minute TTL and 10% early expiration probability, requests in the final 30 seconds have increasing chances of triggering refresh
- **Lock-based refresh** via Durable Objects adds 20-100ms latency for distant users since all requests route to a single location, but provides the strongest consistency guarantee

![Cache Stampede Prevention Mechanisms](../assets/ch12-cache-stampede-prevention.html)

#### Event-Driven Cache Invalidation

Rather than relying solely on TTL expiration, implement event-driven invalidation:

**Webhook-triggered purges**: When data changes in the origin database, trigger a webhook to the CDN's purge API. Tag responses with surrogate keys, and purge by key when the underlying data changes.

**Message queue integration**: Subscribe to database change events (CDC) and purge corresponding cache entries. This decouples invalidation from application code.

**Tiered invalidation**: For hierarchical data, invalidate at appropriate levels. Changing a product invalidates product responses; changing a category invalidates category and all contained product responses.

The key insight: cache stampede is a coordination problem, not a caching problem. The goal is ensuring only one request performs expensive work while others wait or receive stale data [Source: Wikipedia, 2024].

### Edge Workers and Compute

Edge workers execute code at CDN nodes worldwide, enabling computation without origin round trips. Unlike serverless functions in regional data centers, edge workers run within milliseconds of users.

The latency benefits vary by scenario. For operations that can complete entirely at edge (cache hits, auth validation, rate limiting), improvements reach 80-90%. For dynamic content requiring origin involvement, edge compute still provides 30-40% improvement through connection optimization and edge-side processing.

![Edge vs Origin Latency Scenarios](../assets/ch12-edge-vs-origin-latency.html)

#### Execution Model

Modern edge platforms use V8 isolates rather than containers. Each request runs in an isolated JavaScript context without the container startup overhead. Cloudflare Workers achieve cold starts under 5ms (effectively imperceptible) compared to 100-500ms for Lambda@Edge's container-based model [Source: Cloudflare, 2024].

Resource constraints are tighter than traditional serverless:

- **CPU time**: 10-50ms for free tiers, up to 30 seconds for paid tiers
- **Memory**: Typically 128MB
- **No persistent state**: Each request starts fresh; use external storage for state

These constraints enforce a specific design philosophy: edge workers should be thin, fast, and stateless, delegating heavy computation and state to origin servers or edge data stores.

#### Common Edge Worker Patterns

**Request Routing and A/B Testing**

Route requests based on geography, device, user segment, or experiment assignment. An edge worker can hash the user ID to determine experiment variant and route to different origin servers accordingly. This runs at the edge, adding no latency to the request path while enabling experimentation infrastructure without origin changes.

**Authentication Validation**

Validate JWT tokens at the edge to reject unauthorized requests before they reach the origin. Split the token into its three parts (header, payload, signature), verify the signature using the Web Crypto API, and check claims. Public keys can be cached in KV store. This pattern eliminates origin load from invalid tokens and reduces latency for valid requests.

**Response Transformation**

Modify responses without origin changes by adding security headers, injecting analytics, or personalizing content. Fetch from origin, clone the response, add or modify headers as needed, and return the modified response.

**Async Accept and Queue**

This pattern deserves special attention because it delivers edge-like latency for operations that ultimately require origin processing. The edge worker validates the request, enqueues it for background processing, and returns immediately. The user experiences 30ms latency while origin handles the work asynchronously.

Operations well-suited for async edge handling:

- **Analytics and telemetry**: Validate event structure, enqueue, return 202 Accepted. Origin processes in batches.
- **Webhook delivery**: Accept the webhook, validate signature, enqueue for reliable delivery with retries. The sender sees fast acknowledgment.
- **Write operations**: For creates and updates that don't need immediate confirmation, validate at edge, queue the write, return optimistically. Origin processes and handles conflicts.
- **Email and notifications**: Enqueue send requests immediately. Background workers handle actual delivery.
- **Data exports**: Accept export request, enqueue job, return job ID. User polls or receives webhook when complete.

Cloudflare Queues provides native queue infrastructure at the edge. A typical pattern:

```javascript
export default {
  async fetch(request, env) {
    // Validate request at edge
    const data = await request.json();
    if (!isValid(data)) {
      return new Response('Invalid payload', { status: 400 });
    }

    // Enqueue for background processing
    await env.MY_QUEUE.send({
      type: 'analytics_event',
      payload: data,
      timestamp: Date.now()
    });

    // Return immediately - user sees ~30ms
    return new Response(JSON.stringify({ status: 'accepted' }), {
      status: 202,
      headers: { 'Content-Type': 'application/json' }
    });
  }
};
```

The queue consumer runs separately, processing batches at origin or in workers with higher CPU limits. This decouples user-facing latency from processing time.

For operations without native queue support, edge workers can POST to origin endpoints designed for async ingestion, or write to edge KV as a temporary buffer that origin polls.

The key insight: **user-perceived latency is what matters for experience**. If the user doesn't need to wait for processing to complete, don't make them wait. Accept fast, process later.

#### When Not to Use Edge Compute

Edge workers are not appropriate for all workloads:

- **Complex business logic**: CPU limits prevent heavy computation. Validate and route at edge; process at origin.
- **Complex database transactions**: Edge databases (D1, Durable Objects) support transactions for scoped workloads like session management or per-user state, but lack the capacity and features of origin databases. Route complex multi-table transactions or heavy write volumes to origin.
- **Large response generation**: Memory constraints limit response body size. Stream from origin for large payloads.
- **Debugging-intensive development**: Edge debugging tools are less mature than origin debugging. Start at origin, move to edge after stabilization.

### Edge Rate Limiting

Rate limiting at the edge stops abusive traffic before it consumes origin resources. However, distributed rate limiting across hundreds of edge locations presents unique challenges.

#### The Distributed State Challenge

A client hitting your API from Tokyo generates requests through one edge location, while requests from London route through another. If rate limits are enforced per-location, a distributed attacker can exceed global limits by spreading requests across locations.

Edge platforms address this through tiered enforcement:

1. **Per-location limits**: Immediate enforcement with local state. Catches obvious abuse instantly.
2. **Global synchronization**: Periodic aggregation across locations. Catches distributed attacks with slight delay.
3. **Eventual consistency**: Limits may briefly exceed during synchronization windows. Design limits with headroom.

Cloudflare's rate limiting synchronizes state globally within seconds, making eventual consistency acceptable for most API protection scenarios.

#### Configuration Patterns

**IP-based limiting** protects against single-source attacks by limiting requests per source IP (e.g., 100 requests per minute per IP for API paths).

**API key limiting** provides per-customer quotas by keying on the API key header (e.g., 10,000 requests per hour per API key).

**Path-based rules** apply different limits to different endpoints: stricter limits on authentication endpoints (e.g., 5 requests per 5 minutes to `/api/login`), more generous limits on read-only endpoints.

#### Edge vs Origin Rate Limiting

Edge rate limiting complements rather than replaces origin rate limiting:

| Aspect | Edge Rate Limiting | Origin Rate Limiting |
|--------|-------------------|---------------------|
| Latency | Immediate rejection | Request reaches origin before rejection |
| State | Eventually consistent | Strongly consistent |
| Granularity | IP, headers, simple fields | Full request context, user state |
| Cost | Minimal (edge rejection) | Origin compute for every request |

Use edge limiting for coarse protection (IP-based, API key quotas) and origin limiting for business-logic rules (per-user-per-resource limits, complex quotas).

#### Advanced Rate Limiting Patterns

**Sliding window vs fixed window**: Fixed window rate limits (100 requests per minute) have a boundary problem: a client can make 100 requests at 0:59 and 100 more at 1:01, effectively 200 requests in two seconds. Sliding window algorithms track requests over a rolling time period, providing smoother enforcement. Edge platforms increasingly support sliding window limits, though with higher state synchronization overhead.

**Token bucket for burst handling**: Token buckets allow controlled bursts while maintaining average rate limits. The bucket fills at a steady rate (e.g., 10 tokens/second) and drains when requests consume tokens. A bucket with 50 token capacity allows bursts of 50 requests while limiting sustained rate to 10 RPS. This pattern is more forgiving for legitimate traffic spikes while still protecting against sustained abuse.

**Priority tiers**: Not all requests deserve equal rate limit treatment. Implement tiered limits:
- Premium API keys: Higher limits, priority queue during congestion
- Standard keys: Normal limits
- Anonymous/unauthenticated: Lowest limits, aggressive throttling

Edge workers can examine request metadata (API key tier, user subscription level) and apply appropriate limits.

**Quota carryover**: For API billing and fairness, consider whether unused quota carries forward. Strict per-period limits may unfairly penalize clients with variable traffic patterns. Carryover policies (unused quota rolls forward for N periods) improve fairness but complicate state management at edge.

### Edge Data Stores

Edge compute without edge data requires origin fetches, negating latency benefits. Edge data stores provide globally distributed state with varying consistency guarantees.

#### KV Stores

Key-value stores like Cloudflare KV optimize for read-heavy, eventually consistent workloads:

- **Read latency**: Single-digit milliseconds from any location
- **Write propagation**: Eventually consistent, typically 60 seconds globally
- **Capacity**: Megabytes to gigabytes of data
- **Use cases**: Configuration, feature flags, session data, cached API responses

Edge workers read configuration from KV and use it to make routing decisions. For example, checking a feature flag to route to a new checkout service version.

KV limitations:
- Write conflicts resolve via last-write-wins; not suitable for counters or inventories
- No query capability; key-based access only
- Large values (>25MB) may have higher latency

#### Edge Databases

Edge databases like Cloudflare D1 provide SQL semantics with global read replicas:

- **Read latency**: Low-millisecond from nearest replica
- **Write latency**: Higher, as writes route to primary location
- **Consistency**: Strong consistency for writes; read-your-writes semantics
- **Use cases**: User preferences, metadata, lightweight transactional data

Edge workers can execute prepared SQL statements against D1 with bound parameters, retrieving user preferences or metadata with low-latency reads from the nearest replica.

D1 is not a replacement for your primary database. Use it for edge-specific data that benefits from global distribution and low-latency reads.

#### Durable Objects

Durable Objects solve the coordination problem: how do you maintain consistent state across a distributed system without a central database?

Each Durable Object instance runs in exactly one location, providing:
- **Strong consistency**: Single-threaded execution guarantees
- **Persistent state**: SQLite storage survives restarts
- **WebSocket support**: Real-time connections to a single coordinator

Use cases:
- **Rate limiting with exact counts**: When eventual consistency is insufficient
- **Collaborative editing**: Single source of truth for document state
- **Game servers**: Authoritative game state with global player connections

A Durable Object class maintains its own state (such as a counter) and handles requests with single-threaded execution guarantees, ensuring consistent updates without race conditions.

Trade-off: Durable Objects route all requests for an object to one location, adding latency for distant users. Use when consistency matters more than latency.

#### Choosing Edge vs Origin Data

| Data Characteristic | Edge Storage | Origin Storage |
|--------------------|--------------|----------------|
| Read-heavy, rarely written | KV Store | - |
| Global reads, occasional writes | D1 (edge database) | - |
| Needs strong consistency for coordination | Durable Objects | - |
| Complex queries, joins, transactions | - | Origin database |
| Source of truth, audit requirements | - | Origin database |
| Large datasets (>1GB) | - | Origin database |

The pattern: cache and replicate at edge for reads; write to origin for durability and consistency; sync to edge as needed.

### Rules, Transforms, and Security

Edge platforms provide declarative rules for request processing, security enforcement, and response transformation without writing code. From an optimization perspective, this matters because these checks execute before requests reach origin servers. Malicious traffic, bot floods, and invalid requests get rejected at the edge, meaning your expensive origin infrastructure isn't wasting compute cycles, memory, and database connections processing requests that will ultimately be denied. During an attack or traffic spike, edge rejection keeps origin servers healthy and responsive for legitimate users.

#### WAF and Security Rules

Web Application Firewall (WAF) rules protect APIs from common attacks at the edge, before traffic reaches your infrastructure:

- **OWASP Core Ruleset**: SQL injection, XSS, command injection detection
- **Rate limiting rules**: Covered in previous section
- **Bot management**: Challenge suspicious traffic, block known bad bots
- **IP reputation**: Block requests from known malicious IPs

Most edge platforms provide managed rulesets that update automatically as new attack patterns emerge. Enable these as a baseline, then add custom rules for application-specific protection.

#### Request and Response Transforms

Transform rules modify requests and responses without code:

**Header injection** adds security headers (like `Strict-Transport-Security`, `X-Content-Type-Options`, `X-Frame-Options`) to all responses through declarative rules.

**URL rewriting** enables API versioning or migrations. For example, rewriting requests from `/v1/` to `/v2/` paths during a migration.

**Bot score routing** sends suspicious traffic (low bot management scores) to different backends like honeypots for analysis.

#### Image Optimization

For APIs serving images, edge image optimization reduces bandwidth and improves performance:

- **Automatic format conversion**: Serve WebP or AVIF to supporting browsers
- **Responsive sizing**: Generate appropriate sizes based on client hints
- **Quality adjustment**: Balance quality and file size based on network conditions

This offloads image processing from origin servers while serving optimized images from cache.

### Authentication at the Edge

Edge authentication validates credentials before requests reach origin servers, reducing latency for valid requests and protecting origins from authentication floods.

#### JWT Validation at Edge

JWT tokens are self-contained and can be validated without origin contact:

1. **Retrieve public key**: Cache JWKS (JSON Web Key Set) in KV store, refresh periodically
2. **Validate signature**: Use Web Crypto API for RS256/ES256 verification
3. **Check claims**: Verify `exp`, `iat`, `iss`, `aud` claims
4. **Forward or reject**: Pass validated claims to origin in headers; reject invalid tokens immediately

The edge worker extracts the token from the Authorization header, validates it, and either rejects with 401 or forwards the request with validated claims (user ID, roles) in custom headers. This pattern eliminates cryptographic validation overhead at origin while enabling edge caching of responses by user ID.

```
on request at edge:
    token = extract from Authorization header
    if no token:
        return 401 Unauthorized

    claims = verify signature using cached public key
    if signature invalid or token expired:
        return 401 Unauthorized

    add claims to request headers
    forward to origin
```

#### Token Revocation at Edge

JWT validation alone cannot handle revocation. Tokens remain valid until expiration. Edge revocation patterns:

**Revocation list in KV**: Store revoked token IDs (jti claims) in KV store. Check against list during validation. If the token's jti exists in the revocation list, reject immediately. Eventual consistency means brief windows where revoked tokens work.

**Short-lived tokens with refresh**: Issue tokens valid for 5-15 minutes. Refresh tokens validate against origin. Limits revocation window without KV lookup on every request.

**Durable Object for instant revocation**: When immediate revocation is required, route validation through a Durable Object that maintains the authoritative revocation list. Adds latency but guarantees consistency.

#### Session Lookup Patterns

For session-based authentication, the session store must be accessible from edge:

**Edge KV with origin fallback**:
1. Check session in KV store
2. If found, use cached session data
3. If not found, fetch from origin, cache in KV with TTL

This pattern checks KV first for the session. On cache miss, it fetches from origin, caches the result with an expiration TTL (e.g., one hour), and proceeds with the request.

**Trade-offs**: Edge session lookup adds read latency (single-digit ms) but eliminates origin session validation. Suitable when session data changes infrequently. For frequently-changing session data, consider short KV TTLs or origin validation.

For comprehensive coverage of authentication performance patterns at origin, see Chapter 11.

### Edge Aggregation and Composition

One of the most powerful edge optimization patterns is aggregating responses from multiple origin services into a single response. Rather than having clients make multiple API calls (each incurring network latency), an edge worker can fetch from multiple backends in parallel and return a composed response.

#### Multi-Origin Response Assembly

The fundamental pattern uses `Promise.all` to fetch from multiple origins concurrently. An edge worker receives a client request, fans out to multiple backend services simultaneously, awaits all responses, and assembles the combined data before returning to the client. This approach transforms multiple sequential round trips into a single client request with parallel backend fetches.

```
on aggregation request:
    start all backend requests in parallel:
        user_data = fetch from user service
        orders = fetch from order service
        recommendations = fetch from rec service

    wait for all to complete
    combine responses into single payload
    return to client
```

The latency improvement is substantial. Consider a mobile client that needs user profile, recent orders, and recommendations. Without edge aggregation, three sequential API calls from Singapore to Virginia:

- Request 1: 80ms RTT + 10ms processing = 90ms
- Request 2 (waits for 1): 80ms RTT + 15ms processing = 95ms
- Request 3 (waits for 2): 80ms RTT + 12ms processing = 92ms
- Client-side assembly: 5ms
- **Total: 282ms**

With edge aggregation at a Singapore edge node:

- Client to edge: 15ms
- Edge to 3 origins in parallel: max(90ms, 95ms, 92ms) = 95ms
- Edge assembly: 3ms
- Edge to client: 15ms
- **Total: 128ms (55% reduction)**

The improvement comes from two sources: eliminating two sequential RTTs (160ms saved) and reducing client-edge distance (65ms saved per trip compared to client-origin).

![Edge Aggregation Latency Comparison](../assets/ch12-edge-aggregation-latency.html)

Edge aggregation also reduces bandwidth consumption on mobile networks. Instead of three HTTP request/response cycles with headers, clients receive one response. For API responses averaging 5KB each, this reduces header overhead from approximately 1.5KB (3 × 500B) to 500B.

Edge aggregation introduces a failure decision: what happens when one of three backend calls fails? Options include returning partial data (common for optional fields), returning an error immediately (for required fields), or using cached fallback (for stale-tolerant data). The edge worker determines this policy per-request based on which fields are critical.

#### Backend-for-Frontend at Edge

The Backend-for-Frontend (BFF) pattern tailors API responses to specific client types. Mobile clients need compact payloads optimized for bandwidth; web clients can handle richer data structures. Rather than implementing BFF logic at origin (which still requires origin round trips), implement it at the edge.

An edge BFF examines the User-Agent or client hints, transforms responses appropriately, and serves optimized payloads. Mobile requests might receive only essential fields; web requests receive full responses. This reduces bandwidth for mobile users while avoiding origin changes.

#### Response Reshaping

Edge workers can filter, transform, and enrich responses without origin modifications:

- **Field filtering**: Remove unnecessary fields from verbose API responses before sending to clients
- **Data transformation**: Convert between formats (XML to JSON) or reshape nested structures
- **Enrichment**: Add computed fields, inject CDN metadata, or append geographic information from edge context

The key constraint is CPU time. Complex transformations that approach edge CPU limits (10-50ms) belong at origin. Simple filtering and reshaping work well at edge.

#### GraphQL at Edge

GraphQL workloads benefit from edge processing in several ways:

- **Query parsing and validation**: Reject malformed queries before they reach origin
- **Complexity analysis**: Enforce query complexity limits at edge, protecting origins from expensive queries
- **Field-level caching**: Cache individual resolved fields, composing responses from cached fragments
- **Persisted queries**: Store approved query documents at edge, rejecting unknown queries

For read-heavy GraphQL APIs, edge caching of query results (keyed by query hash and variables) can dramatically reduce origin load. Cloudflare's edge cache can store GraphQL responses with surrogate keys based on the data types involved, enabling targeted invalidation when underlying data changes.

### Streaming and Real-Time at Edge

Edge infrastructure handles streaming and real-time connections, enabling low-latency data delivery without buffering entire responses.

#### Server-Sent Events from Edge

Server-Sent Events (SSE) provide a simple, HTTP-based mechanism for streaming data to clients. Edge workers can generate SSE streams, aggregating updates from multiple sources or transforming origin streams.

The Streams API in edge workers enables memory-efficient streaming without buffering entire responses. Using `ReadableStream` and `TransformStream`, an edge worker can process multi-gigabyte payloads within its 128MB memory limit by processing chunks incrementally rather than loading everything into memory.

SSE from edge is particularly effective for:
- **AI response streaming**: Stream LLM outputs token-by-token, reducing perceived latency
- **Live data feeds**: Stock prices, sports scores, or social feeds
- **Progress updates**: Long-running operation status without polling

For AI response streaming, the perceived latency improvement is dramatic. Consider a typical LLM response of 500 tokens generated over 5 seconds. With traditional request-response, users see a loading spinner for 5 seconds before any content appears. With SSE streaming, the first token appears in approximately 100ms (model warmup plus first token generation), and subsequent tokens flow every 10ms. Users perceive immediate responsiveness despite identical total generation time.

The Streams API also enables processing payloads that would otherwise exceed memory limits. Without streaming, a 500MB file download would fail at edge due to the 128MB memory constraint. With TransformStream, the worker processes 64KB chunks sequentially, never holding more than one chunk in memory. This enables use cases like log streaming, large JSON transformations, and video transcoding previews.

When using SSE on edge platforms, there is typically no effective time limit on streaming duration. Responses can stream for minutes without termination [Source: Cloudflare, 2025].

#### WebSocket Proxying

WebSockets require persistent connections, which edge platforms handle through connection pooling and intelligent routing.

Edge workers accept WebSocket upgrades from clients and establish corresponding connections to origins. The edge layer provides:
- **Connection pooling**: Multiplex many client connections over fewer origin connections
- **Protocol handling**: Ping/pong keepalives, graceful closure
- **Message transformation**: Filter, enrich, or route messages at edge

For applications requiring coordination among multiple WebSocket connections (chat rooms, multiplayer games, collaborative editors), Durable Objects provide the single-point-of-coordination. Each Durable Object instance maintains WebSocket connections to multiple clients while ensuring consistent state [Source: Cloudflare, 2025].

For a collaborative editing application, a Durable Object maintains the document state and active cursor positions. Each client's WebSocket connects to the edge, which routes document-related messages to the single Durable Object instance. The Durable Object broadcasts changes to all connected clients. While this adds latency for users distant from the Durable Object's location (up to 100-200ms for cross-continental users), it guarantees consistency that eventually-consistent approaches cannot provide.

Edge WebSocket limits are generous: free and pro tiers support up to 100,000 concurrent connections per domain [Source: Cloudflare, 2025]. However, occasional bursts beyond these limits may trigger rate limiting.

#### Choosing SSE vs WebSocket at Edge

Both protocols have their place:

| Characteristic | SSE | WebSocket |
|---------------|-----|-----------|
| Direction | Server to client only | Bidirectional |
| Reconnection | Automatic with Last-Event-ID | Manual implementation |
| Binary data | Text only (base64 for binary) | Native binary support |
| Browser support | Excellent | Excellent |
| Edge overhead | Lower | Higher (connection state) |
| Long connections | Good for minutes | Better for hours |

For simple streaming scenarios (AI responses, event feeds), SSE is simpler and lower overhead. For bidirectional communication or connections lasting hours, WebSockets are more robust [Source: Cloudflare, 2025].

![Edge Streaming Architecture](../assets/ch12-edge-streaming-architecture.html)

### Smart Routing and Traffic Steering

Edge infrastructure excels at intelligent request routing based on real-time conditions, enabling deployment patterns that would be complex or impossible with DNS-based routing alone.

#### Performance-Based Routing

Rather than routing to the geographically nearest origin, route to the fastest origin based on real-time latency measurements. Edge workers can:

- Track origin response times using edge analytics or KV-stored metrics
- Route requests to origins with lowest recent latency
- Fall back to geographic routing when latency data is unavailable

This approach is particularly valuable when geographic proximity doesn't correlate with performance. For example, when an origin in a different region has lower load or better network paths.

#### Canary Deployments at Edge

Edge workers enable fine-grained canary deployments without infrastructure changes. The pattern:

1. Hash user ID or session to assign users to deployment cohorts
2. Route a small percentage (1-5%) to the canary version
3. Monitor error rates and latency for the canary cohort
4. Gradually increase canary percentage if metrics are healthy
5. Roll back instantly by updating edge routing, no DNS propagation delay

Edge canary deployment offers sub-second rollback, critical when the alternative is waiting for DNS TTLs. Compare the rollback scenarios:

- **Edge-based rollback**: Configuration update propagates globally in under 1 second. Users immediately route to stable version.
- **DNS-based rollback**: TTL propagation delay of 5 minutes (aggressive TTL) to 24 hours (conservative TTL). During propagation, users continue hitting the problematic deployment.

The October 2025 Azure Front Door outage resulted from a configuration change that propagated to 100% of traffic before monitoring detected the problem. Edge-based staged rollout with automated health gates would have limited the blast radius to the 1-5% canary cohort, triggering automatic rollback before wider impact [Source: Azure Post-Incident Analysis, 2025].

Best practices for edge canary deployment:
- Start with 1-5% of traffic
- Use sticky sessions to ensure consistent user experience by hashing the session ID rather than randomly selecting per-request, so users stay on their assigned deployment throughout a session
- Set automated rollback triggers on anomalous metrics (e.g., canary error rate exceeding 2× stable error rate)
- Employ per-region gating before global propagation

Sticky sessions are particularly important when deployments involve state assumptions. Without stickiness, a user might see the stable version's checkout flow, then the canary version's confirmation page, potentially encountering bugs when state structures differ between versions.

![Smart Routing and Canary Deployment](../assets/ch12-smart-routing-canary.html)

#### Failover and Circuit Breaking

Edge workers implement circuit breaking patterns to protect origins and improve resilience:

**Health checking**: Periodically probe origins and track health status in KV or Durable Objects. Route away from unhealthy origins immediately.

**Circuit breaker state**: Maintain closed/open/half-open states per origin. When errors exceed thresholds, open the circuit and fail fast rather than queuing requests to a failing origin.

**Graceful degradation**: When primary origins fail, serve cached responses (even stale), return degraded responses, or route to backup origins.

Edge circuit breaking provides three advantages over origin-side implementation:

1. **Earlier failure detection**: Edge sees connection failures immediately; the origin might not know about network issues between edge and origin.
2. **Lower failure cost**: Rejecting at edge costs less than 1ms of compute; routing to a failing origin wastes 30+ seconds on timeout.
3. **Global view**: Edge aggregates health across all locations; origin sees only local state and cannot detect issues affecting specific geographic regions.

The edge is the ideal location for circuit breaking because it can fail fast without consuming origin resources and can implement fallback logic close to users.

#### Geographic and Cost-Aware Routing

Not all routing decisions are purely performance-based. Edge routing can consider:

- **Regulatory compliance**: Route EU users to EU-based origins for data residency
- **Cost optimization**: Route to cheaper origins during low-priority requests
- **Load balancing**: Distribute traffic across origins based on current capacity
- **A/B testing**: Route cohorts to different feature variants

The edge worker has access to request geography (country, city, ASN), enabling routing decisions impossible at DNS resolution time.

### Protocol Optimizations at Edge

Edge infrastructure can optimize protocol-level performance, taking advantage of its position between clients and origins.

#### HTTP Early Hints (103)

HTTP 103 Early Hints allows the edge to send a preliminary response before the final response is ready. When a client requests a page, the edge immediately sends hints about critical resources (stylesheets, scripts) while the origin computes the full response. Browsers begin fetching these resources during the origin's "think time" [Source: Chrome, 2024].

Cloudflare automatically caches and sends Early Hints based on Link headers observed in previous responses. This works without origin changes because the edge learns which resources to hint from response patterns.

Performance impact varies by scenario:
- Shopify measured improvements on desktop, particularly for 1-3 preloaded resources [Source: Shopify, 2025]
- Mobile devices showed mixed results; aggressive preloading can hurt performance
- Early Hints is only effective over HTTP/2 and HTTP/3

Best practices:
- Preload only critical above-the-fold resources
- Limit to 1-3 resources on mobile
- Monitor actual performance impact through RUM data
- Focus on resources blocking First Contentful Paint

#### Link Header Prefetching

Beyond Early Hints, edge workers can inject Link headers for resource hints:

- **preload**: Fetch resource for current navigation
- **prefetch**: Fetch resource for likely future navigation
- **preconnect**: Establish connection to origin before requests

Edge workers can dynamically determine appropriate hints based on request context (user behavior patterns, page type, or device capabilities) rather than static hints configured at origin.

#### Protocol Transformation

Edge workers bridge protocol differences between clients and origins:

**gRPC-to-REST transformation**: Expose REST APIs to browser clients while communicating with gRPC backends. The edge worker handles protocol translation, content-type negotiation, and error mapping.

**Compression selection**: Choose optimal compression based on client capabilities. Serve Brotli to supporting browsers (smaller than gzip, ~15-20% better compression), fall back to gzip for older clients.

**HTTP version bridging**: Accept HTTP/3 from clients while communicating with HTTP/1.1 origins. The edge terminates modern protocols and maintains optimized connections to origins.

### Edge Observability

Operating edge infrastructure requires observability into edge-specific metrics and behaviors.

#### Edge-Specific Metrics

Beyond standard API metrics, monitor edge-specific indicators:

- **Cache hit rate by type**: Distinguish hits, misses, expired, and bypassed requests
- **Worker CPU time**: Track p50/p95/p99 execution time; approaching limits indicates origin migration needed
- **Cold start frequency**: On container-based platforms (Lambda@Edge), track cold start impact
- **Edge vs origin latency**: Decompose total latency into edge processing and origin fetch time
- **Geographic distribution**: Understand where requests originate and how edge proximity affects latency

Cloudflare Workers expose these metrics through the dashboard and GraphQL Analytics API, enabling integration with existing observability stacks.

#### Distributed Tracing at Edge

Extend distributed tracing through the edge layer:

1. Extract or generate trace context from incoming requests
2. Propagate trace headers to origin requests
3. Add edge-specific spans for cache lookup, worker execution, and origin fetch
4. Include edge metadata (cache status, worker timing, geographic context)

The edge span provides visibility into time spent before requests reach origin, which is critical for understanding total latency.

#### Cost Monitoring

Edge infrastructure costs differ from origin compute:

- **Request-based pricing**: Workers typically charge per request, not per compute time
- **Bandwidth costs**: Egress from edge to clients; some platforms (Cloudflare R2, Cloudflare itself) have zero egress fees
- **Storage costs**: KV, D1, Durable Objects have their own pricing models

Monitor cost efficiency: requests served from edge cache cost far less than origin fetches. High cache hit rates directly reduce origin load and cost.

#### Debugging Edge Issues

Common edge debugging challenges:

- **Cache behavior**: Use cache status headers to understand why requests are HITs, MISSes, or BYPASS
- **Worker errors**: Edge worker logs are available but less accessible than origin logs; use structured logging and error tracking services
- **Geographic variation**: Issues may appear in specific regions; test from multiple geographic locations
- **Race conditions**: Edge workers are stateless; unexpected behavior often stems from race conditions in external state access

Develop locally using platform-specific tools (wrangler for Cloudflare Workers) before deploying to edge.

### Edge ML Inference

Running machine learning models at the edge enables intelligent request processing without origin round trips. This capability is rapidly maturing, with significant platform updates in 2024-2025.

#### Lightweight Inference at Edge

Edge ML works best for lightweight models that execute within CPU and memory constraints:

- **Text embeddings**: Generate vector representations for search, recommendations, or similarity
- **Classification**: Categorize content, detect sentiment, identify language
- **Content moderation**: Flag potentially harmful content before origin processing
- **Bot detection**: Classify requests as human or automated based on request patterns

Cloudflare Workers AI provides access to embedding models (BGE series with 2x improved inference times in 2025), classification models (Llama Guard for content safety), and small language models, all running on edge infrastructure [Source: Cloudflare, 2025].

#### Edge ML Use Cases

**Smart caching decisions**: Use embeddings to identify semantically similar requests that can share cached responses, even with different query strings.

**Request prioritization**: Classify requests by importance or complexity, routing high-priority requests to dedicated origin capacity.

**Personalization without PII**: Generate user embeddings from behavior patterns, enabling personalization at edge without sending personal data to origin.

**Anomaly detection**: Identify unusual request patterns that might indicate attacks or abuse, taking protective action at edge.

#### Constraints and Trade-offs

Edge ML has meaningful constraints:

- **Model size**: Edge platforms support small to medium models; large models (70B+ parameters) route to regional GPU clusters
- **Inference time**: Model execution counts against worker CPU limits
- **Cold start**: First inference may be slower; subsequent inferences are faster
- **Accuracy vs latency**: Smaller edge models may be less accurate than larger origin-hosted models

The decision framework: use edge ML when latency matters more than maximum accuracy, when models are small enough to execute within constraints, and when the use case benefits from global distribution.

#### Platform Capabilities

As of 2025, edge ML capabilities include:

- **Cloudflare Workers AI**: Embeddings (BGE, EmbeddingGemma), classification (Llama Guard), text generation (Llama 3.3), image generation
- **AWS Lambda@Edge**: Limited ML, primarily through Lambda layers
- **Fastly Compute@Edge**: Custom models via WebAssembly

Workers AI provides the most integrated experience, with models accessible through a simple API call from edge workers. The 2025 updates include 2-4x inference speed improvements and batch processing for large workloads [Source: Cloudflare, 2025].

## Common Pitfalls

- **Moving complex business logic to edge**: Edge workers have CPU limits (10-50ms) and limited debugging tools. Validate and route at edge; keep complex logic at origin. If your worker frequently hits CPU limits, the logic belongs at origin.

- **Ignoring cold start differences**: Lambda@Edge cold starts (100-500ms) differ dramatically from Cloudflare Workers (<5ms). Benchmark your actual platform, not theoretical limits.

- **Edge caching without invalidation strategy**: Caching API responses at edge without purge mechanisms leads to stale data. Implement surrogate keys and event-driven purging before enabling edge caching.

- **KV store for write-heavy workloads**: KV stores optimize for reads with eventual consistency. Using KV for counters, inventories, or frequently-updated data causes consistency issues. Use Durable Objects or origin storage for write-heavy patterns.

- **Over-fragmenting cache keys**: Each Vary header value multiplies cache entries. `Vary: Cookie` effectively disables caching. Be intentional about cache key components.

- **Forgetting the Vary header**: Serving different responses based on Accept-Encoding or Accept-Language without appropriate Vary headers causes incorrect cached responses. Always set Vary for headers that affect responses.

- **Rate limiting without origin fallback**: If edge rate limiting fails or is bypassed, origin receives unthrottled traffic. Implement defense in depth with both edge and origin rate limiting.

- **Durable Objects for read-heavy patterns**: Durable Objects route all requests to one location. For read-heavy workloads, this adds latency. Use Durable Objects for coordination, KV for read distribution.

- **Assuming edge solves all latency problems**: Edge only provides physics benefits when requests don't need origin (cache hits, KV lookups, auth validation). For origin-required requests with a single-region origin, the distance is the same—edge provides infrastructure benefits (better connections), not distance reduction.

- **Synchronous patterns where async works**: Many operations don't require immediate results—analytics, webhooks, notifications, non-critical writes. Making users wait for origin processing when you could accept-and-queue wastes the edge latency advantage. Default to async; require sync only when the user genuinely needs the result immediately.

- **Not monitoring edge performance**: Edge caching and compute add complexity. Monitor cache hit rates, worker CPU time, and edge vs origin latency to verify benefits.

- **Over-aggregating at edge**: Combining too many origin calls in a single edge worker can hit CPU time limits. If aggregation involves complex transformation or many origins, consider whether origin-side aggregation is more appropriate.

- **Ignoring cache stampede during traffic spikes**: Without request coalescing or stale-while-revalidate, cache expiration during high traffic can cascade into origin overload. Implement stampede prevention before enabling edge caching for high-traffic endpoints.

- **WebSocket connection limits**: While edge platforms support many concurrent WebSocket connections, hitting limits causes dropped connections. Monitor connection counts and implement graceful degradation.

- **Aggressive Early Hints preloading**: Preloading more than 1-3 resources, especially on mobile, can hurt rather than help performance. Limit Early Hints to critical above-the-fold resources and monitor actual impact.

- **Edge ML cold starts in latency-sensitive paths**: First ML inference after worker startup is slower. For latency-critical paths, consider warming strategies or accepting occasional slower responses.

- **Canary deployments without automated rollback**: Edge canary provides instant rollback capability, but only if automated triggers are configured. Manual monitoring of canary metrics delays response to problems.

## Summary

- Edge infrastructure provides latency benefits through two mechanisms: eliminating origin round-trips entirely (a genuine physics win), and providing optimized infrastructure when origin is required (better pipes, not shorter distance). Understand which applies to your workload.

- Three optimization strategies at edge: (1) handle entirely at edge for 80-90% latency reduction, (2) accept at edge and process asynchronously for fast user experience with deferred processing, (3) synchronous origin when necessary with infrastructure benefits.

- Async patterns are critical: validate requests at edge, enqueue for background processing, return immediately. User experiences 30ms while origin processes later. Applies to analytics, webhooks, writes, notifications, and exports.

- Choose an edge platform based on your requirements: enterprise CDNs (Akamai, CloudFront) for complex enterprise needs; developer platforms (Cloudflare, Vercel) for comprehensive capabilities with lower operational overhead.

- CDN caching for APIs requires intentional header configuration. Use `s-maxage` for CDN-specific TTLs, `stale-while-revalidate` for latency elimination, and surrogate keys for targeted invalidation.

- Cache stampede prevention mechanisms (request coalescing, stale-while-revalidate, probabilistic early expiration, and lock-based refresh) prevent origin overload during cache expiration and traffic spikes. Without these protections, a single cache expiration can trigger 50,000 simultaneous origin requests; with request coalescing, the same event triggers exactly one.

- Edge workers execute lightweight logic globally with sub-millisecond cold starts. Use for routing, authentication validation, and response transformation. Keep complex logic at origin.

- Edge aggregation combines multiple origin calls into single client requests, reducing round trips by 55-70% through parallelization and edge proximity. The pattern uses `Promise.all` to fetch from multiple backends in parallel, returning composed responses in under 130ms compared to 280ms+ for sequential client-side calls.

- Streaming at edge enables memory-efficient handling of large payloads and real-time data. SSE works well for AI response streaming and event feeds; WebSockets are better for bidirectional communication and long-lived connections.

- Smart routing at edge enables canary deployments with sub-second rollback, performance-based origin selection, and circuit breaking, all without DNS propagation delays. Edge configuration updates propagate globally in under 1 second; DNS-based rollback requires 5 minutes to 24 hours of TTL propagation during which users continue hitting problematic deployments.

- Protocol optimizations include HTTP Early Hints for preloading critical resources, Link header prefetching, and gRPC-to-REST transformation. Early Hints show best results with 1-3 preloaded resources on desktop.

- Edge rate limiting provides distributed protection with eventual consistency. Combine with origin rate limiting for defense in depth. Advanced patterns include sliding window, token bucket for bursts, and priority tiers.

- Edge data stores offer different consistency trade-offs: KV for read-heavy eventual consistency, D1 for SQL with global read replicas, Durable Objects for strong consistency coordination.

- Edge observability requires tracking edge-specific metrics: cache hit rate by type, worker CPU time, geographic distribution, and edge vs origin latency decomposition.

- Edge ML inference enables smart caching, request classification, and personalization without origin round trips. Use when latency matters more than maximum accuracy and models fit within edge constraints.

- WAF rules, request transforms, and bot management provide declarative security without code. Enable managed rulesets as baseline protection.

- Edge authentication validates tokens without origin round trips. Cache public keys in KV, implement revocation lists, and forward validated claims to origin. Combine with origin auth for defense in depth.

## References

1. **Cloudflare** (2024). "How Workers Works." https://developers.cloudflare.com/workers/learning/how-workers-works/

2. **Cloudflare** (2024). "Workers KV." https://developers.cloudflare.com/kv/

3. **Cloudflare** (2024). "Durable Objects." https://developers.cloudflare.com/durable-objects/

4. **Cloudflare** (2024). "D1 Database." https://developers.cloudflare.com/d1/

5. **Cloudflare** (2024). "Rate Limiting Rules." https://developers.cloudflare.com/waf/rate-limiting-rules/

6. **AWS** (2024). "Lambda@Edge." https://docs.aws.amazon.com/lambda/latest/dg/lambda-edge.html

7. **Fastly** (2024). "Compute@Edge." https://docs.fastly.com/products/compute-at-edge

8. **Akamai** (2024). "EdgeWorkers." https://techdocs.akamai.com/edgeworkers/docs

9. **RFC 7234** (2014). "Hypertext Transfer Protocol (HTTP/1.1): Caching." https://tools.ietf.org/html/rfc7234

10. **IETF** (2022). "Cache-Status Header Field." RFC 9211. https://datatracker.ietf.org/doc/html/rfc9211

11. **Nygren, E., Sitaraman, R. K., & Sun, J.** (2010). "The Akamai Network: A Platform for High-Performance Internet Applications." ACM SIGOPS Operating Systems Review.

12. **Cloudflare Blog** (2023). "The Speed of Light and the Speed of the Internet." https://blog.cloudflare.com/

13. **Cloudflare** (2025). "Aggregate requests." https://developers.cloudflare.com/workers/examples/aggregate-requests/

14. **Cloudflare** (2025). "Streams - Runtime APIs." https://developers.cloudflare.com/workers/runtime-apis/streams/

15. **Cloudflare** (2025). "HTTP and Server-Sent Events." https://developers.cloudflare.com/agents/api-reference/http-sse/

16. **Cloudflare** (2025). "Using the WebSockets API." https://developers.cloudflare.com/workers/examples/websockets/

17. **Chrome for Developers** (2024). "Faster page loads using server think-time with Early Hints." https://developer.chrome.com/docs/web-platform/early-hints

18. **Shopify Performance** (2025). "Early Hints at Shopify." https://performance.shopify.com/blogs/blog/early-hints-at-shopify

19. **Cloudflare** (2025). "Early Hints." https://developers.cloudflare.com/cache/advanced-configuration/early-hints/

20. **Cloudflare** (2025). "Workers AI." https://developers.cloudflare.com/workers-ai/

21. **Cloudflare** (2025). "Workers AI for Developer Week - faster inference, new models, async batch API, expanded LoRA support." https://developers.cloudflare.com/changelog/2025-04-11-new-models-faster-inference/

22. **Hackenberger, P.** (2025). "From Herd to Harmony: Implementing Request Coalescing and Entitlement-Based Caching on Akamai Edge." Medium.

23. **Wikipedia** (2024). "Cache stampede." https://en.wikipedia.org/wiki/Cache_stampede

24. **Vercel** (2023). "Preventing the stampede: Request collapsing in the Vercel CDN." https://vercel.com/blog/cdn-request-collapsing

25. **Azure** (2025). "Azure Front Door Post-Incident Analysis." Microsoft Azure Status History.

## Next: [Chapter 13: Testing Performance](./13-testing-performance.md)

With edge infrastructure established, we turn to testing performance: load testing, benchmarking, and performance regression testing - the practices that validate our optimization work and prevent regressions.
