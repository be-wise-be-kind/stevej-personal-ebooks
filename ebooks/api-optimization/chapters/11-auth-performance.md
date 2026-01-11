# Chapter 11: Authentication Performance

![Chapter 11 Opener](../assets/ch11-opener.html)

\newpage

## Overview

Authentication touches every protected API request. A single millisecond of overhead in token validation compounds across millions of daily requests. What seems negligible at the unit level becomes significant at scale. Yet authentication performance is often overlooked during optimization efforts because security concerns rightfully dominate the conversation. This chapter addresses that gap: we examine authentication not through the lens of security (though we note security trade-offs where relevant) but through the lens of latency, throughput, and scalability.

If you need a refresher on authentication fundamentals (the difference between sessions and tokens, OAuth 2.0 flows, or when to use API keys), see [Appendix: Auth Fundamentals](./15-appendix-auth-fundamentals.md) before proceeding. This chapter assumes familiarity with these concepts and focuses on their performance characteristics.

The patterns here connect directly to earlier chapters: token caching applies the strategies from Chapter 6, connection pooling to identity providers follows Chapter 5's network optimization principles, and protecting authentication under attack uses the circuit breakers and rate limiting from Chapter 10. Authentication is where these patterns converge on a critical path that affects every request.

For edge-based authentication patterns (validating tokens at the CDN edge before requests reach your origin servers), see [Chapter 12: Edge Infrastructure](./12-edge-infrastructure.md). Edge auth can eliminate origin load from invalid tokens and reduce latency for valid requests.

<!-- DIAGRAM: Request timeline showing: TLS handshake complete -> Extract token -> Validate signature -> Check claims -> Authorization check -> Business logic, with typical latency annotations at each step -->

![Request Auth Timeline](../assets/ch11-request-auth-timeline.html)

## Key Concepts

### Measuring Authentication Overhead

Before optimizing, we must measure. Authentication overhead hides inside total request latency unless we instrument it specifically. The first step is isolating auth time from application time.

#### What to Measure

The critical metrics for authentication performance are:

**Validation Latency**: Time from receiving a token to completing validation. This includes parsing, signature verification, and claims checking. Track percentiles (p50, p95, p99) since validation time can vary based on token size and algorithm.

**Cache Hit Rate**: If you are caching validation results, track hit rates. A healthy cache should achieve 80-95% hit rate for repeated tokens. Low hit rates indicate either misconfigured TTLs or high token churn.

**Auth Error Rates**: Track 401 (Unauthorized) and 403 (Forbidden) responses separately. High 401 rates may indicate expired tokens or misconfigured clients. High 403 rates suggest authorization issues unrelated to performance, though they still consume validation resources.

**Token Refresh Rate**: How often clients request new tokens. Excessive refresh rates indicate short token lifetimes or clients not caching tokens properly. Each refresh adds latency to user-perceived performance.

#### Instrumenting Auth Middleware

Wrap your authentication middleware to capture timing. The key is measuring the auth portion separately from request handling. Record the start time before validation, measure elapsed time after, and emit metrics for both successful validations (as a histogram) and errors (as a counter with error type tags). This pattern captures validation time for every request, enabling dashboard visualization and alerting on regressions.

### Token Validation Performance

JWT validation is CPU-bound work: parsing JSON, decoding Base64, and verifying cryptographic signatures. The choice of algorithm and validation approach significantly affects throughput.

#### Symmetric vs Asymmetric Algorithms

JWT signing algorithms fall into two categories with different performance characteristics:

**Symmetric (HS256, HS384, HS512)**: Use a shared secret for both signing and verification. Verification is fast because HMAC operations complete in microseconds. The trade-off is key distribution: every service that validates tokens needs the secret, increasing the blast radius of key compromise.

**Asymmetric (RS256, RS512, ES256, ES512)**: Use public/private key pairs. The issuer signs with a private key; validators verify with the public key. Verification is slower because RSA operations take single-digit milliseconds, ECDSA slightly less. The advantage is key distribution: public keys can be shared freely.

Benchmark data from the `jsonwebtoken` library (Node.js) and `pyjwt` (Python) shows typical verification times [Source: Library benchmarks, 2024]:

| Algorithm | Verification Time (us) | Notes |
|-----------|----------------------|-------|
| HS256 | 5-15 | Fastest, shared secret required |
| HS512 | 8-20 | Slightly slower, stronger hash |
| RS256 | 200-800 | RSA 2048-bit, widely supported |
| RS512 | 300-1000 | RSA with SHA-512 |
| ES256 | 100-400 | ECDSA P-256, good balance |
| ES512 | 150-500 | ECDSA P-521, strongest |

These microseconds matter when multiplied across thousands of requests per second. A service handling 10,000 RPS spends 2-8 seconds per second on RS256 verification versus 50-150 milliseconds on HS256, a 15-50x difference in CPU time dedicated to auth.

<!-- DIAGRAM: JWT validation flow showing: Parse header -> Decode payload (base64) -> Extract algorithm -> Fetch signing key (if asymmetric) -> Verify signature -> Validate claims (exp, iss, aud) -> Decision, with typical latency for each step -->

![JWT Validation Flow](../assets/ch11-jwt-validation-flow.html)

#### Local vs Remote Validation

**Local validation** verifies tokens using keys available to the service. For JWTs, this means the signing key (symmetric) or public key (asymmetric) is present locally. Validation completes without network calls.

**Remote validation (introspection)** sends the token to an authorization server that responds with token metadata and validity. This adds a network round-trip but enables features local validation cannot: real-time revocation checking and opaque token support.

The latency difference is substantial:

| Approach | Typical Latency | Notes |
|----------|----------------|-------|
| Local (HS256) | 10-50 us | Fastest, no network |
| Local (RS256) | 200-800 us | CPU-bound crypto |
| Remote (same region) | 5-20 ms | Network + processing |
| Remote (cross-region) | 50-150 ms | Geographic latency |

Remote validation becomes a critical dependency. If the authorization server is slow or unavailable, every protected request is affected. Apply circuit breakers and timeouts to introspection endpoints, and consider caching introspection responses with short TTLs.

### Session Management Performance

Session-based authentication stores user state server-side, with clients sending a session identifier (typically in a cookie). Performance depends entirely on the session storage backend.

#### Storage Backend Comparison

| Storage | Read Latency | Write Latency | Scaling | Notes |
|---------|--------------|---------------|---------|-------|
| In-memory | < 1 us | < 1 us | None | Lost on restart, no horizontal scaling |
| Redis | 0.5-2 ms | 0.5-2 ms | Excellent | Most common choice |
| Memcached | 0.5-2 ms | 0.5-2 ms | Excellent | Simpler, less features |
| PostgreSQL | 2-10 ms | 5-20 ms | Good | Persistent, ACID guarantees |
| DynamoDB | 5-15 ms | 5-15 ms | Excellent | Managed, predictable |

For most applications, Redis provides the best balance of performance and features. Its sub-millisecond latency adds minimal overhead to request processing, and built-in TTL support handles session expiration automatically.

#### Session Size Impact

Session data is serialized on every write and deserialized on every read. Bloated sessions (storing shopping carts, preferences, or entire user profiles) multiply this overhead:

- 100-byte session: negligible serialization cost
- 10 KB session: 0.5-2 ms serialization overhead
- 100 KB session: 5-20 ms serialization overhead

Keep sessions lean. Store references (user ID, cart ID) rather than full objects. Move large data to dedicated storage with its own caching strategy.

#### Connection Pooling for Session Stores

Session lookups happen on every request. Without connection pooling, each request opens a new connection to Redis or your session store, adding 1-5 ms of connection overhead.

Apply the connection pooling principles from Chapter 5: maintain a pool of warm connections, size the pool based on concurrent request volume, and implement health checks to remove stale connections.

### Token Caching Strategies

Token validation, whether local or remote, can be cached. The insight: the same token submitted repeatedly produces the same validation result (until expiration). Caching validation results eliminates redundant cryptographic operations and network calls.

#### Cache Validation Results, Not Tokens

Cache the output of validation (the user claims and validity status) keyed by a hash of the token. Never cache the raw token itself, as this creates a credential store that becomes an attack target. The caching pattern checks for a cached result first, records cache hit/miss metrics, validates on miss, and caches the result with a TTL shorter than token expiration.

```
on request with token:
    cache_key = hash(token)
    cached_result = check cache for cache_key
    if cache hit:
        return cached_result

    claims = validate token cryptographically
    store claims in cache with TTL
    return claims
```

<!-- DIAGRAM: Token cache-aside pattern: Request with token -> Hash token -> Check validation cache -> [hit: return cached user claims] or [miss: validate token, cache result with TTL, return claims] -->

![Token Cache Pattern](../assets/ch11-token-cache-pattern.html)

#### TTL Considerations

Cache TTL must be shorter than token lifetime to avoid serving stale validation results for expired tokens. A common formula calculates cache TTL as the minimum of a maximum cache duration (e.g., 5 minutes) and the remaining token lifetime minus a buffer. The buffer (e.g., 60 seconds) accounts for clock skew and provides safety margin.

#### Handling Revocation

Cached validation results create a revocation gap: a revoked token continues working until cache entries expire. Strategies to minimize this gap:

**Short TTLs**: 1-5 minute cache TTLs limit revocation lag but reduce cache hit rates.

**Revocation list check**: Check a revocation list (stored in Redis or similar) on every request. This adds one cache lookup but enables immediate revocation.

**Versioned cache keys**: Include a "token generation" in cache keys. Increment the generation to invalidate all cached validations.

The right choice depends on your revocation requirements. Most APIs tolerate 1-5 minute revocation lag; high-security applications may require the revocation list approach.

#### Thundering Herd Prevention

When a popular token's cache entry expires, multiple concurrent requests may all attempt validation simultaneously. This is the thundering herd problem. Apply the single-flight pattern from Chapter 6: track in-progress validations by token hash, and if a validation is already running, wait for its result rather than starting a duplicate. This ensures only one validation occurs per unique token, with other requests waiting on the result.

### Stateless vs Stateful: Performance Trade-offs

The choice between stateless (JWT) and stateful (session) authentication has significant performance implications beyond raw validation speed.

<!-- DIAGRAM: Side-by-side comparison showing stateless (JWT) vs stateful (session) request flows. JWT: Extract token -> Verify signature -> Read claims -> Proceed. Session: Extract session ID -> Lookup session in Redis -> Deserialize session -> Proceed. Annotate typical latencies and trade-offs. -->

![Stateless vs Stateful Comparison](../assets/ch11-stateless-vs-stateful.html)

#### Stateless (JWT) Performance Profile

**Advantages**:
- No database/cache lookup per request
- Scales horizontally without shared state
- Works across services without session affinity
- Self-contained claims reduce downstream lookups

**Disadvantages**:
- Larger request headers (1-3 KB typical vs 32-byte session ID)
- CPU cost for cryptographic verification
- Cannot revoke before expiration without additional infrastructure
- Token refresh adds latency when tokens expire

#### Stateful (Session) Performance Profile

**Advantages**:
- Immediate revocation by deleting session
- Small request headers (32-byte session ID)
- Session data can be updated without new token
- No cryptographic overhead per request

**Disadvantages**:
- Network round-trip to session store per request
- Session store becomes critical dependency
- Requires session affinity or shared storage for horizontal scaling
- Session store capacity planning required

#### Decision Framework

Choose **stateless (JWT)** when:
- Services are distributed across regions
- Horizontal scaling without shared state is required
- Token validation is cacheable (repeated tokens)
- Revocation latency of minutes is acceptable

Choose **stateful (sessions)** when:
- Immediate revocation is required (banking, healthcare)
- Request payload size is critical (mobile, IoT)
- Session data changes frequently during a session
- A reliable session store is already available

Many systems use both: JWTs for service-to-service communication where revocation is less critical, and sessions for user-facing applications where immediate logout matters.

### OAuth 2.0 and OIDC Performance

OAuth 2.0 authorization flows add latency through token exchanges and identity provider interactions. Understanding these flows helps minimize their performance impact.

#### Token Exchange Latency

The Authorization Code flow requires multiple round-trips:

1. User redirects to authorization server (user-facing, not API latency)
2. Authorization server redirects back with code
3. **Backend exchanges code for tokens** (adds latency)
4. Backend validates ID token
5. Backend creates session or issues application token

Step 3 (the token exchange) adds 50-200 ms depending on identity provider location and performance. This is acceptable for login flows but should not occur on every request.

#### Proactive vs Reactive Token Refresh

Access tokens expire. The refresh strategy affects user experience:

**Reactive refresh**: Wait for token expiration (or 401 response), then refresh. Users experience latency during refresh.

**Proactive refresh**: Refresh tokens before expiration. Background refresh when tokens are within a threshold of expiring (e.g., 5 minutes before expiration) eliminates user-visible latency.

```
on token use:
    time_remaining = token.expiry - now
    if time_remaining < refresh_threshold:
        start background refresh

    return current token (still valid)

background refresh:
    new_token = call identity provider
    replace stored token with new_token
```

Proactive refresh requires tracking token expiration and scheduling refresh. The complexity is justified for user-facing applications where perceived latency matters.

#### JWKS Caching

JSON Web Key Sets (JWKS) contain the public keys for validating JWTs from identity providers. Fetching JWKS on every request is unnecessary and slow. Implement a JWKS cache that stores keys locally and refreshes periodically (every 1-24 hours). When a key ID (kid) is not found, refresh once to handle key rotation, then fail if still not found. This pattern eliminates network calls for the vast majority of validations while still handling key rotation gracefully.

#### Connection Pooling to Identity Providers

Token exchanges and introspection requests to identity providers benefit from connection pooling. Reusing connections eliminates TLS handshake overhead (50-150 ms) on each request.

Apply the connection pooling patterns from Chapter 5 to identity provider clients. Most HTTP client libraries support this natively; ensure it is configured.

### API Key Authentication

API keys are the simplest authentication mechanism: a secret string that identifies the caller. Their simplicity translates to performance advantages when appropriate.

#### Lookup Performance

API key validation is a lookup: given a key, return the associated permissions and identity. Performance depends on the lookup mechanism:

| Approach | Lookup Time | Notes |
|----------|-------------|-------|
| In-memory hash map | < 1 us | Fast, but requires restart to update |
| Redis | 0.5-2 ms | Good balance, supports revocation |
| Database | 2-10 ms | Persistent, ACID, slower |

For high-throughput services with stable key sets, consider loading keys into memory at startup with periodic refresh. For dynamic key management, Redis provides sub-millisecond lookups with real-time updates.

#### When API Keys Outperform Tokens

API keys win on performance when:
- Keys change infrequently (can be cached aggressively)
- No cryptographic validation required
- Simple identity lookup is sufficient (no rich claims)
- Service-to-service communication within trusted networks

The trade-off is security and functionality: API keys lack expiration, scoping, and the security properties of signed tokens. Use them for appropriate scenarios, not as a general-purpose authentication mechanism.

### Performance Under Attack

Authentication systems face unique threats that affect performance. Understanding attack patterns helps design systems that degrade gracefully.

#### Brute-Force and Credential Stuffing

Attackers submitting thousands of authentication attempts create load even when all attempts fail. Each attempt consumes:
- Network resources (connections, bandwidth)
- CPU for password hashing or token validation
- Database/cache resources for lookups

Rate limiting (Chapter 10) is the primary defense. Apply aggressive limits to authentication endpoints: 5-10 attempts per minute per IP or account is typical. Return 429 (Too Many Requests) with `Retry-After` headers.

#### Token Validation Under Load

When attackers submit many invalid tokens, validation failures still consume resources. With JWT validation, each invalid token still requires:
- Base64 decoding
- JSON parsing
- Signature verification (which fails, but still runs)

Consider short-circuiting obvious invalid tokens before full validation:
- Reject tokens with invalid format (not three dot-separated parts)
- Reject tokens with unsupported algorithms
- Reject tokens with unrecognized issuers

This fails fast on malformed input without cryptographic overhead.

<!-- DIAGRAM: Auth system under attack showing: Normal load (100 RPS) -> Attack begins (10,000 RPS) -> Rate limiting activates (rejects 9,900 RPS) -> Auth service latency increases -> Circuit breaker trips on elevated error rate -> Fallback to cached sessions, with annotations showing metrics at each stage -->

![Auth Under Attack](../assets/ch11-auth-under-attack.html)

#### Circuit Breakers for Auth Services

When identity providers or auth services degrade, circuit breakers prevent cascading failures. Configure auth service calls with:
- Aggressive timeouts (500ms-1s for auth calls)
- Failure rate thresholds (open circuit at 50% failure rate)
- Fallback behavior (cached authentication results, degraded access)

The fallback strategy depends on your security requirements. Some systems can operate in degraded mode (cached auth, reduced permissions) for minutes. Others must fail closed immediately.

#### Constant-Time Comparison

When comparing secrets (API keys, password hashes), use constant-time comparison to prevent timing attacks. A timing attack measures response time differences to infer correct characters. Most languages provide constant-time comparison functions (such as Python's `hmac.compare_digest`). This security measure has negligible performance impact (comparison takes constant time regardless of input) but is critical for authentication endpoints.

### Measuring and Monitoring Authentication

Authentication deserves dedicated dashboard space. Key panels include:

**Validation Latency**: P50, P95, P99 latency for token/session validation. Alert on sustained increases.

**Cache Hit Rate**: For token validation caching. Dropping hit rates may indicate configuration issues or attack patterns.

**Error Rate by Type**: Break down auth failures: expired tokens, invalid signatures, missing tokens, revoked tokens. Each category has different implications.

**Token Refresh Rate**: Spikes may indicate token lifetime misconfiguration or client issues.

**Identity Provider Latency**: If using OAuth/OIDC, track latency to identity providers separately. Degradation here affects all authentication.


## Common Pitfalls

- **Validating tokens synchronously without caching**: Token validation, especially with remote introspection, adds latency to every request. Cache validation results with appropriate TTLs. Even local JWT validation benefits from caching when the same tokens appear repeatedly.

- **Using asymmetric algorithms unnecessarily**: RS256 is 10-50x slower than HS256. If tokens are only validated by services you control, symmetric algorithms may be appropriate. Evaluate your key distribution requirements before defaulting to RSA.

- **Bloated JWT payloads**: Every claim increases token size and parsing time. Only include claims needed for authorization decisions. Move user preferences, permissions lists, and other data to server-side storage fetched after authentication.

- **No timeout on identity provider calls**: External OAuth providers can slow down or fail. Apply timeouts (500ms-1s) and circuit breakers to all identity provider interactions. Have fallback behavior defined.

- **Session stores without connection pooling**: Each request opening a new Redis connection adds 1-5ms overhead. Pool connections as with any database. This is especially critical for session stores accessed on every request.

- **Ignoring clock skew in token validation**: JWT expiration checks require synchronized clocks. Allow 30-60 seconds of leeway for clock drift, or validation will fail on valid tokens when server clocks drift.

- **Cache invalidation gaps on logout**: Users expect logout to be immediate. If you cache validation results, implement a revocation mechanism (revocation list, versioned cache keys, or very short TTLs) to ensure logged-out tokens stop working promptly.

- **Not measuring auth overhead separately**: Authentication latency hidden in total request time makes optimization impossible. Instrument auth middleware specifically. Track validation time, cache hit rates, and error types as distinct metrics.

## Summary

- Authentication overhead compounds across every protected request. A 1ms savings at 10,000 RPS saves 10 seconds of CPU time per second. Measure and optimize accordingly.

- JWT algorithm choice matters: HS256 validates in microseconds, RS256 in hundreds of microseconds to milliseconds. Choose based on your actual security requirements, not defaults.

- Token validation results are cacheable. Cache validation results (not tokens) with TTLs shorter than token expiration. Implement single-flight pattern to prevent thundering herd on cache expiration.

- Session storage choice determines authentication latency. Redis provides sub-millisecond lookups; database-backed sessions add 5-20ms per request. Size connection pools appropriately.

- Stateless (JWT) and stateful (session) authentication have different performance profiles. Neither is universally faster. Choose based on revocation requirements, scaling needs, and existing infrastructure.

- OAuth 2.0 token exchanges add latency to login flows. Proactive token refresh eliminates user-visible refresh latency. Cache JWKS for hours, not seconds.

- Authentication under attack behaves differently than normal operation. Rate limit auth endpoints aggressively, short-circuit obviously invalid tokens, and apply circuit breakers to auth service dependencies.

- Dedicated auth monitoring surfaces problems invisible in aggregate metrics. Track validation latency, cache hit rates, error breakdowns, and identity provider health separately.

## References

1. **Auth0** (2023). "JWT Best Practices." https://auth0.com/docs/secure/tokens/json-web-tokens

2. **RFC 7519** (2015). "JSON Web Token (JWT)." https://datatracker.ietf.org/doc/html/rfc7519

3. **RFC 7662** (2015). "OAuth 2.0 Token Introspection." https://datatracker.ietf.org/doc/html/rfc7662

4. **NIST SP 800-63B** (2017). "Digital Identity Guidelines: Authentication and Lifecycle Management." https://pages.nist.gov/800-63-3/sp800-63b.html

5. **Redis Documentation**. "Session Management." https://redis.io/docs/manual/patterns/session/

6. **OWASP** (2023). "Authentication Cheat Sheet." https://cheatsheetseries.owasp.org/cheatsheets/Authentication_Cheat_Sheet.html

7. **Curity** (2023). "JWT Performance." https://curity.io/resources/learn/jwt-performance/

## Next: [Chapter 12: Edge Infrastructure](./12-edge-infrastructure.md)

With authentication performance optimized, the next chapter explores edge infrastructure including CDN strategies, edge computing patterns, and how to push optimization closer to your users.
