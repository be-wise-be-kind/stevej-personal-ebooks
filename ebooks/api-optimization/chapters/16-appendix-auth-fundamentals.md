# Appendix: Authentication Fundamentals

This appendix provides background on authentication and authorization concepts for readers who need a refresher before reading Chapter 11: Authentication Performance. If you are already familiar with JWT, OAuth 2.0, and session-based authentication, you can skip this appendix and proceed directly to the performance content.

\newpage

## Authentication vs Authorization

These terms are often conflated but serve distinct purposes:

**Authentication** answers "Who are you?" It establishes identity through credentials such as passwords, tokens, certificates, or biometrics. When a user logs in with username and password, they are authenticating.

**Authorization** answers "What can you do?" It determines permissions based on the authenticated identity. When an API checks whether a user can access a specific resource, it is authorizing.

The distinction matters because different mechanisms optimize for different concerns. A system might authenticate once (login) and then authorize on every request (permission checks). Performance optimization strategies differ for each.

Most modern systems use tokens that carry both authentication (proof of identity) and authorization (permissions or roles) information. Understanding this dual role helps when designing caching and validation strategies.

## Session-Based Authentication

Session-based authentication stores user state on the server. The flow:

1. User submits credentials (username/password)
2. Server validates credentials against user store
3. Server creates a session object containing user identity
4. Server stores session in session store (memory, Redis, database)
5. Server returns session ID to client (typically via cookie)
6. Client includes session ID in subsequent requests
7. Server looks up session, retrieves user identity

<!-- DIAGRAM: Session flow: Client sends login credentials -> Server validates -> Server creates session (stores in Redis) -> Server sends session ID cookie -> Client sends cookie on requests -> Server looks up session -> Server retrieves user data -->

![Session Flow](../assets/ch15-session-flow.html)

### Characteristics

**Server-side state**: The session store maintains all session data. Clients hold only an opaque identifier.

**Revocation**: Logout deletes the session from the store. Revocation is immediate: the session ID becomes invalid as soon as the session is deleted.

**Scaling considerations**: Horizontal scaling requires either session affinity (routing users to the same server) or shared session storage (all servers access the same session store).

**Cookie-based transport**: Sessions typically use HTTP cookies, which the browser manages automatically. This simplifies client implementation but introduces CSRF considerations.

### When to Use Sessions

Sessions work well when:
- Immediate revocation is required (banking, healthcare)
- The application is primarily web-based (browsers handle cookies natively)
- Session data changes frequently during a user's session
- A reliable session store is already part of the infrastructure

## Token-Based Authentication (JWT)

JSON Web Tokens (JWTs) are self-contained tokens that carry identity and claims without requiring server-side state. The flow:

1. User submits credentials
2. Server validates credentials
3. Server creates JWT containing user identity and claims
4. Server signs JWT with secret (symmetric) or private key (asymmetric)
5. Server returns JWT to client
6. Client stores JWT (localStorage, sessionStorage, or cookie)
7. Client includes JWT in request headers (`Authorization: Bearer <token>`)
8. Server validates signature and reads claims from token

### JWT Structure

A JWT consists of three Base64-encoded parts separated by dots: the header, the payload, and the signature.

<!-- DIAGRAM: JWT structure showing three parts: Header ({"alg": "RS256", "typ": "JWT"}) | Payload ({"sub": "user123", "exp": 1704067200, "roles": ["admin"]}) | Signature (RSASHA256(header + "." + payload, privateKey)), with arrows showing how each part is encoded and combined -->

![JWT Structure](../assets/ch15-jwt-structure.html)

**Header**: Specifies the token type and signing algorithm. Contains fields like `alg` (the signing algorithm, such as RS256) and `typ` (the token type, typically "JWT").

**Payload**: Contains claims about the user and token metadata, including the subject identifier (`sub`), issuer (`iss`), audience (`aud`), expiration time (`exp`), issued-at time (`iat`), and any custom claims like roles.

**Signature**: Cryptographic signature preventing tampering.

### Standard Claims

JWTs use standardized claim names:

| Claim | Name | Description |
|-------|------|-------------|
| `sub` | Subject | The user identifier |
| `iss` | Issuer | Who created the token |
| `aud` | Audience | Intended recipient(s) |
| `exp` | Expiration | When the token expires (Unix timestamp) |
| `iat` | Issued At | When the token was created |
| `nbf` | Not Before | Token not valid before this time |
| `jti` | JWT ID | Unique token identifier |

### Signing Algorithms

**Symmetric (HS256, HS384, HS512)**: Use HMAC with a shared secret. The same key signs and verifies. Fast but requires secure key distribution.

**Asymmetric (RS256, RS512, ES256, ES512)**: Use public/private key pairs. Private key signs; public key verifies. Slower but enables verification without exposing signing keys.

### When to Use JWTs

JWTs work well when:
- Stateless architecture is required
- Services need to validate tokens without central authority
- Token claims eliminate downstream lookups
- Short token lifetimes are acceptable (or refresh is implemented)
- Cross-origin or cross-service authentication is needed

## OAuth 2.0 Overview

OAuth 2.0 is an authorization framework that enables third-party applications to access resources on behalf of users without exposing credentials. It is the foundation for "Login with Google/GitHub/Facebook" flows.

### Key Roles

**Resource Owner**: The user who owns the data (you, when logging into an app with Google)

**Client**: The application requesting access (the app you are logging into)

**Authorization Server**: Issues tokens after authenticating the user (Google's auth server)

**Resource Server**: Hosts the protected resources (Google's API)

### Grant Types

OAuth 2.0 defines several flows for different scenarios:

**Authorization Code**: Most common for web applications. User is redirected to authorization server, approves access, and is redirected back with a code. The backend exchanges this code for tokens.

<!-- DIAGRAM: OAuth 2.0 Authorization Code flow: User clicks "Login with Google" -> Client redirects to Google -> User logs in and approves -> Google redirects to client with auth code -> Client backend exchanges code for tokens with Google -> Google returns access_token and refresh_token -> Client stores tokens and creates session -->

![OAuth 2.0 Authorization Code Flow](../assets/ch15-oauth2-authcode-flow.html)

**Client Credentials**: For service-to-service authentication where no user is involved. The client authenticates directly with client ID and secret to obtain an access token.

**Refresh Token**: Not a grant type itself, but a mechanism to obtain new access tokens without user interaction. Refresh tokens are long-lived; access tokens are short-lived.

### Token Types

**Access Token**: Short-lived credential for API access (minutes to hours). Included in API requests to access protected resources.

**Refresh Token**: Long-lived credential for obtaining new access tokens (days to months). Stored securely; used only with the authorization server.

**ID Token**: Part of OpenID Connect (below). Contains identity claims about the authenticated user.

## OpenID Connect (OIDC)

OpenID Connect is an identity layer built on top of OAuth 2.0. While OAuth 2.0 handles authorization (what can I access), OIDC adds authentication (who am I).

### What OIDC Adds

**ID Tokens**: JWTs containing identity claims (name, email, profile picture). These prove who the user is, not just what they can access.

**UserInfo Endpoint**: A standard endpoint for fetching additional user information beyond what is in the ID token.

**Standard Scopes**: `openid` (required), `profile`, `email`, `address`, `phone` define what identity information is requested.

**Discovery**: A `.well-known/openid-configuration` endpoint provides metadata about the identity provider, including endpoints and supported features.

### Standard Claims

OIDC defines standard claims for user identity:

| Claim | Description |
|-------|-------------|
| `sub` | Subject identifier (unique user ID) |
| `name` | Full name |
| `email` | Email address |
| `email_verified` | Whether email is verified |
| `picture` | Profile picture URL |
| `locale` | User's locale |

## API Key Authentication

API keys are the simplest authentication mechanism: a secret string that identifies the caller.

### How It Works

1. Administrator generates API key for client
2. Client stores key securely
3. Client includes key in requests (header or query parameter)
4. Server looks up key, retrieves associated identity/permissions
5. Server authorizes request based on key's permissions

### Common Patterns

**Header-based** (recommended): Pass the API key in an `Authorization` header (such as `Authorization: Api-Key sk_live_abc123`) or a custom header like `X-API-Key`.

**Query parameter** (discouraged because keys appear in logs): Passing the API key as a query parameter like `?api_key=sk_live_abc123` exposes the key in server logs, browser history, and referrer headers.

### Characteristics

**Simple**: No cryptographic validation, just a lookup.

**No expiration**: Keys typically do not expire unless explicitly rotated.

**Coarse permissions**: Keys usually have static permissions, not per-request scopes.

**Rotation complexity**: Changing keys requires coordinating with all clients.

### When to Use API Keys

API keys are appropriate for:
- Internal service-to-service communication in trusted networks
- Third-party developer access with rate limiting
- Simple integrations where OAuth complexity is unjustified
- Public APIs where key leakage is acceptable (with rate limits)

API keys are not appropriate for:
- End-user authentication (no session concept)
- Scenarios requiring token expiration
- Fine-grained, dynamic authorization

## WebSocket Authentication

WebSocket connections present unique authentication challenges. Unlike HTTP where each request is independent and can carry authentication headers, WebSocket establishes a long-lived connection that must be authenticated once at connection time.

### Connection-Level vs Per-Message Authentication

Two fundamental approaches exist:

**Connection-level authentication** validates credentials during the WebSocket handshake. Once connected, all messages on that connection are considered authenticated. The user identity is associated with the connection object server-side.

**Per-message authentication** includes credentials with each message sent over the WebSocket. The server validates authentication with every message, similar to HTTP's stateless model.

| Approach | Performance | Flexibility | Security |
|----------|-------------|-------------|----------|
| Connection-level | Lower overhead (validate once) | Less flexible (no mid-stream changes) | Token expiration harder to enforce |
| Per-message | Higher overhead (validate each message) | More flexible (can change auth mid-stream) | Easier to enforce expiration |

Most applications use connection-level authentication for performance. Per-message is reserved for scenarios requiring dynamic permission changes during a session.

### Authentication During Upgrade

The WebSocket protocol starts with an HTTP upgrade handshake. Authentication can happen during this handshake:

**Cookie-based**: If the client has an authenticated session cookie, the browser automatically includes it in the upgrade request. The server validates the session before accepting the upgrade.

**Token in protocol header**: Pass a token in the `Sec-WebSocket-Protocol` header. The server validates before upgrade completion. A common pattern is using a custom subprotocol like `auth-{token}`.

**Query parameter** (less secure): Pass a token in the WebSocket URL. The token appears in server logs and may be cached. Avoid this approach for sensitive tokens, but it can work for short-lived, single-use connection tokens.

**Separate auth step**: Complete the handshake without authentication, then require the first message to contain credentials. Reject the connection if the first message is not valid authentication. This approach works well when the initial token must be refreshed or exchanged.

### Token Validation on Connection Upgrade

When using JWT or OAuth tokens for WebSocket authentication:

1. **Validate the token** during upgrade handshake (signature, expiration, claims)
2. **Extract identity** from token and associate with connection object
3. **Store token expiry** with the connection for later enforcement
4. **Handle expiration**: Either disconnect when token expires or allow token refresh

A key consideration: JWT access tokens typically expire in minutes, but WebSocket connections may last hours. Options for handling this mismatch:

- **Disconnect on expiry**: Force reconnection when the original token expires. Simple but disruptive.
- **Token refresh messages**: Allow clients to send refresh tokens over the WebSocket. Server validates and extends the session.
- **Long-lived connection tokens**: Issue a special token with extended lifetime specifically for WebSocket connections, accepting the security tradeoff.
- **Hybrid approach**: Use short-lived tokens for initial auth; server issues a connection-specific token valid for the connection duration.

### Performance Implications

Connection-level authentication has significant performance advantages:

- **Single validation**: Token validation (signature verification, claim checks) happens once per connection, not per message
- **No header overhead**: Messages do not carry authentication headers, reducing payload size
- **Simplified server logic**: The connection object carries identity; handlers do not need to parse auth from each message

For high-frequency messaging (100+ messages/second per client), per-message authentication adds noticeable overhead. For infrequent messaging, the overhead may be acceptable for the security benefits.

### Example: Token-Based WebSocket Auth

A common pattern for browser clients:

1. Client authenticates via HTTP, receives access token
2. Client initiates WebSocket connection with token in URL or first message
3. Server validates token during handshake or upon first message
4. Server associates user identity with connection
5. Subsequent messages use connection context for identity
6. Server monitors token expiration; client refreshes or reconnects as needed

For server-to-server WebSocket connections, mTLS provides strong connection-level authentication without token management complexity.

## When to Use Which Approach

| Scenario | Recommended Approach | Reasoning |
|----------|---------------------|-----------|
| Traditional web app | Sessions or OAuth 2.0 | Cookie handling built-in, CSRF protection available |
| Single-page app + API | OAuth 2.0 with tokens | Cross-origin needs, refresh flow handles expiration |
| Mobile application | OAuth 2.0 with tokens | Secure storage available, refresh flow handles expiration |
| Service-to-service (internal) | JWTs or mTLS | No user context, low latency requirements |
| Service-to-service (external) | OAuth 2.0 client credentials | Standard, revocable, auditable |
| Third-party API access | API keys or OAuth 2.0 | Depends on integration complexity |
| Microservices within mesh | mTLS or JWT | Service identity, no user context |

## Security Considerations

This section covers security briefly, providing enough context for performance decisions. For comprehensive security guidance, consult OWASP and specialized security resources.

### Token Storage

**Browser applications**: Store access tokens in memory or sessionStorage. Avoid localStorage for sensitive tokens (XSS vulnerability). Consider HttpOnly cookies for refresh tokens.

**Mobile applications**: Use platform secure storage (iOS Keychain, Android Keystore).

**Server applications**: Use environment variables or secrets management (Vault, AWS Secrets Manager).

### Token Transmission

Always transmit tokens over TLS (HTTPS). Tokens in URLs appear in logs, browser history, and referer headers. Use headers instead.

### Token Lifetimes

**Access tokens**: Short-lived (5-60 minutes). Limits damage from token theft.

**Refresh tokens**: Longer-lived (days to months). Store more securely, rotate on use.

**Session tokens**: Typically longer than access tokens. Immediate revocation mitigates risk.

### Revocation

**Sessions**: Delete from session store. Immediate effect.

**JWTs**: Cannot revoke before expiration without additional infrastructure. Options:
- Short token lifetimes (minutes)
- Revocation list checked on each request
- Token versioning (user's "token generation" must match)

### Common Vulnerabilities

**Timing attacks**: Use constant-time comparison for secrets.

**Token leakage**: Avoid tokens in URLs, logs, or error messages.

**Insufficient validation**: Always validate signatures, expiration, issuer, and audience claims.

**Session fixation**: Generate new session ID after authentication.

## Summary

- **Authentication** proves identity; **authorization** determines permissions. Most tokens serve both purposes.

- **Session-based authentication** stores state server-side, enabling immediate revocation but requiring shared storage for horizontal scaling.

- **JWTs** are self-contained tokens with cryptographic signatures. They enable stateless architecture but cannot be revoked before expiration without additional mechanisms.

- **OAuth 2.0** is an authorization framework for delegated access. The Authorization Code flow is standard for web applications; Client Credentials is used for service-to-service.

- **OpenID Connect** adds identity (authentication) to OAuth 2.0's authorization capabilities, providing standardized user information claims.

- **API keys** are simple but lack features like expiration and fine-grained scopes. Use them for appropriate scenarios only.

- Security and performance often trade off. Shorter token lifetimes improve security but increase refresh overhead. Immediate revocation requires additional infrastructure. Make informed decisions based on your requirements.

---

For performance optimization of these mechanisms, return to [Chapter 11: Authentication Performance](./11-auth-performance.md).
