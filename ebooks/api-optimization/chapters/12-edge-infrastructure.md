# Chapter 12: Edge Infrastructure

![Chapter 12 Opener](../assets/ch12-opener.html)

\newpage

## Overview

Edge infrastructure represents a fundamental shift in API architecture: rather than processing every request at a centralized origin, we distribute computation, caching, and security enforcement to nodes positioned geographically close to users. This approach addresses a constraint that no amount of code optimization can overcome—the speed of light.

When a user in Singapore makes an API request to a server in Virginia, the round trip traverses approximately 15,000 kilometers. Light through fiber travels at roughly two-thirds the speed of light in a vacuum, establishing a minimum latency floor of around 80ms for physics alone. Real-world latencies are substantially higher due to routing inefficiencies, network hops, and protocol overhead. Edge infrastructure eliminates this penalty by ensuring the nearest compute node is typically within 20ms of any user worldwide.

Beyond latency reduction, edge infrastructure offloads work from origin servers. CDN caching serves repeated requests without origin involvement. Edge workers handle routing decisions, authentication validation, and response transformation at the network edge. Edge data stores maintain configuration and session data globally. Together, these capabilities reduce origin load, improve resilience, and enable performance that centralized architectures cannot match.

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

This book uses Cloudflare for examples because it offers a comprehensive free tier, extensive documentation, and covers all edge capabilities—CDN, compute, data, and security—in one platform. The principles apply regardless of which platform you choose.

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

A typical cacheable API response:

```
Cache-Control: public, max-age=60, s-maxage=300, stale-while-revalidate=600
```

This caches in browsers for 60 seconds, in CDN for 5 minutes, and serves stale content for up to 10 minutes while revalidating.

#### Cache Keys and the Vary Header

The cache key determines when a cached response can be reused. By default, CDNs key on URL only. The `Vary` header adds request headers to the cache key:

```
Vary: Accept-Encoding, Accept-Language
```

This creates separate cache entries for different encodings and languages. Be intentional about `Vary` headers—each additional header fragments the cache, reducing hit rates. `Vary: Cookie` or `Vary: Authorization` effectively disable caching since each user gets unique responses.

For authenticated APIs, consider alternative patterns: validate authentication at the edge and forward a standardized user-id header, allowing the response to be cached per-user-id rather than per-cookie.

#### Surrogate Keys and Cache Invalidation

Surrogate keys (also called cache tags) enable targeted invalidation. Tag responses with logical identifiers:

```
Surrogate-Key: product-123 category-electronics user-456
```

When product 123's data changes, purge all responses tagged with `product-123` rather than guessing URL patterns. Cloudflare's Cache Tags, Fastly's Surrogate-Key, and Akamai's Edge-Cache-Tag provide this capability.

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

### Edge Workers and Compute

Edge workers execute code at CDN nodes worldwide, enabling computation without origin round trips. Unlike serverless functions in regional data centers, edge workers run within milliseconds of users.

#### Execution Model

Modern edge platforms use V8 isolates rather than containers. Each request runs in an isolated JavaScript context without the container startup overhead. Cloudflare Workers achieve cold starts under 5ms—effectively imperceptible—compared to 100-500ms for Lambda@Edge's container-based model [Source: Cloudflare, 2024].

Resource constraints are tighter than traditional serverless:

- **CPU time**: 10-50ms for free tiers, up to 30 seconds for paid tiers
- **Memory**: Typically 128MB
- **No persistent state**: Each request starts fresh; use external storage for state

These constraints enforce a specific design philosophy: edge workers should be thin, fast, and stateless, delegating heavy computation and state to origin servers or edge data stores.

#### Common Edge Worker Patterns

**Request Routing and A/B Testing**

Route requests based on geography, device, user segment, or experiment assignment:

```typescript
export default {
  async fetch(request: Request): Promise<Response> {
    const userId = request.headers.get('X-User-ID') ||
                   crypto.randomUUID();
    const variant = hashToVariant(userId, 'checkout-experiment');

    const origin = variant === 'A'
      ? 'https://api-v1.example.com'
      : 'https://api-v2.example.com';

    return fetch(origin + new URL(request.url).pathname, request);
  }
}
```

This runs at the edge, adding no latency to the request path while enabling experimentation infrastructure without origin changes (see Example 12.1).

**Authentication Validation**

Validate JWT tokens at the edge to reject unauthorized requests before they reach the origin:

```typescript
async function validateJWT(token: string, publicKey: CryptoKey): Promise<boolean> {
  const [headerB64, payloadB64, signatureB64] = token.split('.');
  const data = new TextEncoder().encode(`${headerB64}.${payloadB64}`);
  const signature = base64UrlDecode(signatureB64);

  return crypto.subtle.verify(
    { name: 'RSASSA-PKCS1-v1_5' },
    publicKey,
    signature,
    data
  );
}
```

Public keys can be cached in KV store. This pattern eliminates origin load from invalid tokens and reduces latency for valid requests (see Example 12.2).

**Response Transformation**

Modify responses without origin changes—adding security headers, injecting analytics, or personalizing content:

```typescript
const response = await fetch(request);
const newResponse = new Response(response.body, response);
newResponse.headers.set('Strict-Transport-Security', 'max-age=31536000');
newResponse.headers.set('X-Content-Type-Options', 'nosniff');
return newResponse;
```

#### When Not to Use Edge Compute

Edge workers are not appropriate for all workloads:

- **Complex business logic**: CPU limits prevent heavy computation. Validate and route at edge; process at origin.
- **Database transactions**: Edge workers cannot maintain transaction state across requests. Perform writes at origin.
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

**IP-based limiting** protects against single-source attacks:

```json
{
  "expression": "(http.request.uri.path contains \"/api/\")",
  "action": "block",
  "ratelimit": {
    "characteristics": ["ip.src"],
    "period": 60,
    "requests_per_period": 100
  }
}
```

**API key limiting** provides per-customer quotas:

```json
{
  "expression": "(http.request.uri.path contains \"/api/\")",
  "action": "block",
  "ratelimit": {
    "characteristics": ["http.request.headers[\"x-api-key\"]"],
    "period": 3600,
    "requests_per_period": 10000
  }
}
```

**Path-based rules** apply different limits to different endpoints:

```json
{
  "expression": "(http.request.uri.path eq \"/api/login\")",
  "action": "challenge",
  "ratelimit": {
    "characteristics": ["ip.src"],
    "period": 300,
    "requests_per_period": 5
  }
}
```

#### Edge vs Origin Rate Limiting

Edge rate limiting complements rather than replaces origin rate limiting:

| Aspect | Edge Rate Limiting | Origin Rate Limiting |
|--------|-------------------|---------------------|
| Latency | Immediate rejection | Request reaches origin before rejection |
| State | Eventually consistent | Strongly consistent |
| Granularity | IP, headers, simple fields | Full request context, user state |
| Cost | Minimal (edge rejection) | Origin compute for every request |

Use edge limiting for coarse protection (IP-based, API key quotas) and origin limiting for business-logic rules (per-user-per-resource limits, complex quotas).

### Edge Data Stores

Edge compute without edge data requires origin fetches, negating latency benefits. Edge data stores provide globally distributed state with varying consistency guarantees.

#### KV Stores

Key-value stores like Cloudflare KV optimize for read-heavy, eventually consistent workloads:

- **Read latency**: Single-digit milliseconds from any location
- **Write propagation**: Eventually consistent, typically 60 seconds globally
- **Capacity**: Megabytes to gigabytes of data
- **Use cases**: Configuration, feature flags, session data, cached API responses

```typescript
// Read configuration at edge
const config = await env.CONFIG_KV.get('feature-flags', { type: 'json' });
if (config.newCheckoutEnabled) {
  return fetch('https://checkout-v2.example.com' + url.pathname, request);
}
```

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

```typescript
const { results } = await env.DB.prepare(
  'SELECT preferences FROM users WHERE id = ?'
).bind(userId).all();
```

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

```typescript
export class Counter implements DurableObject {
  private count: number = 0;

  async fetch(request: Request): Promise<Response> {
    this.count++;
    return new Response(String(this.count));
  }
}
```

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

Edge platforms provide declarative rules for request processing, security enforcement, and response transformation without writing code.

#### WAF and Security Rules

Web Application Firewall (WAF) rules protect APIs from common attacks:

- **OWASP Core Ruleset**: SQL injection, XSS, command injection detection
- **Rate limiting rules**: Covered in previous section
- **Bot management**: Challenge suspicious traffic, block known bad bots
- **IP reputation**: Block requests from known malicious IPs

Most edge platforms provide managed rulesets that update automatically as new attack patterns emerge. Enable these as a baseline, then add custom rules for application-specific protection.

#### Request and Response Transforms

Transform rules modify requests and responses without code:

**Header injection** adds security headers to all responses:

```
Response Header: Strict-Transport-Security = max-age=31536000; includeSubDomains
Response Header: X-Content-Type-Options = nosniff
Response Header: X-Frame-Options = DENY
```

**URL rewriting** enables API versioning or migrations:

```
If: URI path starts with /v1/
Then: Rewrite to /v2/ + remaining path
```

**Bot score routing** sends suspicious traffic to different backends:

```
If: cf.bot_management.score < 30
Then: Route to /honeypot/
```

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

```typescript
const token = request.headers.get('Authorization')?.replace('Bearer ', '');
if (!token) {
  return new Response('Unauthorized', { status: 401 });
}

const payload = await validateJWT(token, env.JWT_PUBLIC_KEY);
if (!payload) {
  return new Response('Invalid token', { status: 401 });
}

// Forward validated claims to origin
const headers = new Headers(request.headers);
headers.set('X-User-ID', payload.sub);
headers.set('X-User-Roles', payload.roles.join(','));
return fetch(request.url, { ...request, headers });
```

This pattern eliminates cryptographic validation overhead at origin while enabling edge caching of responses by user ID (see Example 12.2).

#### Token Revocation at Edge

JWT validation alone cannot handle revocation—tokens remain valid until expiration. Edge revocation patterns:

**Revocation list in KV**: Store revoked token IDs (jti claims) in KV store. Check against list during validation. Eventual consistency means brief windows where revoked tokens work.

```typescript
const jti = payload.jti;
const revoked = await env.REVOKED_TOKENS.get(jti);
if (revoked) {
  return new Response('Token revoked', { status: 401 });
}
```

**Short-lived tokens with refresh**: Issue tokens valid for 5-15 minutes. Refresh tokens validate against origin. Limits revocation window without KV lookup on every request.

**Durable Object for instant revocation**: When immediate revocation is required, route validation through a Durable Object that maintains the authoritative revocation list. Adds latency but guarantees consistency.

#### Session Lookup Patterns

For session-based authentication, the session store must be accessible from edge:

**Edge KV with origin fallback**:
1. Check session in KV store
2. If found, use cached session data
3. If not found, fetch from origin, cache in KV

```typescript
let session = await env.SESSIONS.get(sessionId, { type: 'json' });
if (!session) {
  const response = await fetch(`${ORIGIN}/internal/session/${sessionId}`);
  session = await response.json();
  await env.SESSIONS.put(sessionId, JSON.stringify(session), {
    expirationTtl: 3600
  });
}
```

**Trade-offs**: Edge session lookup adds read latency (single-digit ms) but eliminates origin session validation. Suitable when session data changes infrequently. For frequently-changing session data, consider short KV TTLs or origin validation.

For comprehensive coverage of authentication performance patterns at origin, see Chapter 11.

For implementation examples related to these concepts, see the [Appendix: Code Examples](./15-appendix-code-examples.md).

## Common Pitfalls

- **Moving complex business logic to edge**: Edge workers have CPU limits (10-50ms) and limited debugging tools. Validate and route at edge; keep complex logic at origin. If your worker frequently hits CPU limits, the logic belongs at origin.

- **Ignoring cold start differences**: Lambda@Edge cold starts (100-500ms) differ dramatically from Cloudflare Workers (<5ms). Benchmark your actual platform, not theoretical limits.

- **Edge caching without invalidation strategy**: Caching API responses at edge without purge mechanisms leads to stale data. Implement surrogate keys and event-driven purging before enabling edge caching.

- **KV store for write-heavy workloads**: KV stores optimize for reads with eventual consistency. Using KV for counters, inventories, or frequently-updated data causes consistency issues. Use Durable Objects or origin storage for write-heavy patterns.

- **Over-fragmenting cache keys**: Each Vary header value multiplies cache entries. `Vary: Cookie` effectively disables caching. Be intentional about cache key components.

- **Forgetting the Vary header**: Serving different responses based on Accept-Encoding or Accept-Language without appropriate Vary headers causes incorrect cached responses. Always set Vary for headers that affect responses.

- **Rate limiting without origin fallback**: If edge rate limiting fails or is bypassed, origin receives unthrottled traffic. Implement defense in depth with both edge and origin rate limiting.

- **Durable Objects for read-heavy patterns**: Durable Objects route all requests to one location. For read-heavy workloads, this adds latency. Use Durable Objects for coordination, KV for read distribution.

- **Assuming edge solves all latency problems**: Edge reduces network latency, not computation time. If your API is slow due to database queries or processing, edge caching helps but edge compute does not.

- **Not monitoring edge performance**: Edge caching and compute add complexity. Monitor cache hit rates, worker CPU time, and edge vs origin latency to verify benefits.

## Summary

- Edge infrastructure moves computation, caching, and security to network nodes close to users, eliminating latency that physics makes irreducible from centralized origins.

- Choose an edge platform based on your requirements: enterprise CDNs (Akamai, CloudFront) for complex enterprise needs; developer platforms (Cloudflare, Vercel) for comprehensive capabilities with lower operational overhead.

- CDN caching for APIs requires intentional header configuration. Use `s-maxage` for CDN-specific TTLs, `stale-while-revalidate` for latency elimination, and surrogate keys for targeted invalidation.

- Edge workers execute lightweight logic globally with sub-millisecond cold starts. Use for routing, authentication validation, and response transformation. Keep complex logic at origin.

- Edge rate limiting provides distributed protection with eventual consistency. Combine with origin rate limiting for defense in depth. Use per-location limits for immediate protection, global synchronization for distributed attack detection.

- Edge data stores offer different consistency trade-offs: KV for read-heavy eventual consistency, D1 for SQL with global read replicas, Durable Objects for strong consistency coordination.

- WAF rules, request transforms, and bot management provide declarative security without code. Enable managed rulesets as baseline protection.

- Edge authentication validates tokens without origin round trips. Cache public keys in KV, implement revocation lists, and forward validated claims to origin. Combine with origin auth for defense in depth.

- Monitor edge infrastructure: cache hit rates, worker execution time, and edge latency. Edge adds complexity; verify it delivers expected benefits.

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

## Next: [Chapter 13: Advanced Optimization Techniques](./13-advanced-techniques.md)

With edge infrastructure established, we turn to advanced optimization techniques: GraphQL query optimization with DataLoader, gRPC and Protocol Buffers for efficient serialization, and speculative execution patterns for tail latency reduction.
