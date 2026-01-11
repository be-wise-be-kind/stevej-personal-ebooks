# API Performance Optimization: Style Guide

This document establishes the writing standards, terminology, and formatting conventions for all chapters in this ebook. All author agents must follow these guidelines to ensure consistency across the book.

---

## 1. Voice and Tone

### Philosophy
This ebook takes an **empirical, measurement-driven approach** to API optimization. We do not guess at performance problems—we measure, analyze, and verify. Every optimization recommendation should be grounded in observable metrics.

### Writing Style
- **Professional but accessible**: Write for a mixed audience. Content should be approachable for intermediate developers while remaining valuable for senior engineers.
- **Use "we" to include the reader**: "We can improve latency by..." rather than "You can improve latency by..." This creates a collaborative learning experience.
- **Explain WHY, not just WHAT**: Every recommendation needs justification. Do not just say "use connection pooling"—explain the overhead of connection establishment, TCP handshake costs, and measurable impact.
- **Be concrete**: Prefer specific examples over abstract descriptions. Instead of "caching can significantly improve performance," write "caching reduced p95 latency from 450ms to 12ms in this scenario."
- **Acknowledge trade-offs**: Performance optimization involves trade-offs. Always discuss the costs (complexity, memory, consistency) alongside the benefits.

### Tone Guidelines
- Avoid hyperbole ("blazingly fast," "incredibly powerful")
- Do not use superlatives without data to back them up
- Be direct and concise—respect the reader's time
- Use technical terms precisely (see Terminology Dictionary below)
- Maintain an encouraging but realistic tone about optimization challenges

---

## 2. Terminology Dictionary

Use these terms consistently throughout the book. Do not use synonyms or alternate definitions.

### Core Performance Terms

| Term | Definition | Usage Notes |
|------|------------|-------------|
| **API** | Application Programming Interface; in this book, specifically refers to HTTP/REST, GraphQL, or gRPC interfaces | Always clarify the protocol when relevant |
| **Endpoint** | A specific URL path that accepts requests and returns responses | Use "endpoint" not "route" or "path" |
| **Latency** | The time elapsed from when a request is sent to when the response is received | Always specify the percentile when citing numbers |
| **p50 / p95 / p99** | Percentile latencies—the latency at or below which 50%, 95%, or 99% of requests complete | Write as "p50" not "50th percentile" for brevity |
| **Throughput** | The number of requests processed per unit of time, typically requests per second (RPS) | Specify the unit: "1,200 RPS" not just "1,200" |
| **Response Time** | Synonymous with latency in this book | Prefer "latency" for consistency |

### Observability Terms

| Term | Definition | Usage Notes |
|------|------------|-------------|
| **Golden Signals** | The four key metrics: latency, traffic, errors, saturation (from Google SRE) | Always cite Google SRE when introducing |
| **SLO** | Service Level Objective—a target value for a service metric | Example: "99.9% of requests under 200ms" |
| **SLA** | Service Level Agreement—a contract with consequences for missing SLOs | Distinguish from SLO: SLAs have penalties |
| **SLI** | Service Level Indicator—the actual measured metric | "The SLI showed 99.7% availability" |
| **Trace** | A record of a request's path through distributed services | Use "trace" not "distributed trace" |
| **Span** | A single unit of work within a trace | Always explain in context of traces |

### Caching Terms

| Term | Definition | Usage Notes |
|------|------------|-------------|
| **Cache Hit** | A request served from cached data | Express as ratio: "85% cache hit rate" |
| **Cache Miss** | A request requiring origin fetch | The complement of cache hit |
| **Cache Invalidation** | Removing or updating stale cached data | Always discuss invalidation strategies |
| **TTL** | Time To Live—how long cached data remains valid | Specify units: "TTL of 300 seconds" |
| **Cache-Aside** | Application manages cache reads/writes explicitly | Also called "lazy loading" |
| **Write-Through** | Writes go to cache and database simultaneously | Contrast with write-behind |
| **Write-Behind** | Writes go to cache, async to database | Also called "write-back" |
| **CDN** | Content Delivery Network—geographically distributed cache | Spell out on first use |

### Infrastructure Terms

| Term | Definition | Usage Notes |
|------|------------|-------------|
| **Connection Pool** | A cache of database/service connections for reuse | Specify pool size when relevant |
| **Circuit Breaker** | A pattern that fails fast when a dependency is unhealthy | Reference the state machine: closed/open/half-open |
| **Backpressure** | A mechanism to slow producers when consumers are overwhelmed | Critical for queue discussions |
| **Rate Limiting** | Restricting the number of requests per time window | Specify the algorithm when relevant |
| **Load Balancer** | Distributes requests across multiple server instances | Specify the algorithm: round-robin, least-connections, etc. |
| **Bulkhead** | Isolating failures to prevent cascade | Named after ship compartments |

### Scaling Terms

| Term | Definition | Usage Notes |
|------|------------|-------------|
| **Horizontal Scaling** | Adding more instances of a service | Also called "scaling out" |
| **Vertical Scaling** | Adding more resources to an existing instance | Also called "scaling up" |
| **Auto-scaling** | Automatically adjusting capacity based on demand | Hyphenate consistently |
| **Cold Start** | The delay when a new instance initializes | Especially relevant for serverless |

### Authentication Terms

| Term | Definition | Usage Notes |
|------|------------|-------------|
| **JWT** | JSON Web Token | Spell out on first use: "JSON Web Token (JWT)" |
| **OAuth 2.0** | Authorization framework for delegated access | Always include version: "OAuth 2.0" not "OAuth" |
| **OIDC** | OpenID Connect—identity layer on OAuth 2.0 | Spell out on first use |
| **Access Token** | Short-lived credential for API access | Distinguished from ID token and refresh token |
| **Refresh Token** | Long-lived credential for obtaining new access tokens | Store securely; used only with authorization server |
| **ID Token** | JWT containing identity claims (OIDC) | Distinguished from access token |
| **Token Validation** | Verifying a token's signature and claims | Prefer over "token verification" |
| **Token Introspection** | Remote validation via OAuth 2.0 introspection endpoint | RFC 7662; adds network latency |
| **Session** | Server-side user state identified by session ID | Contrast with stateless JWT approach |
| **JWKS** | JSON Web Key Set—public keys for JWT validation | Cache aggressively; refresh on key rotation |

---

## 3. Code Example Standards

### Language Requirements
**Each code example uses ONE language only.** Distribute languages across chapters for variety:
- Python, Rust, and TypeScript should each appear roughly equally across the book
- Choose the language that best fits the example (e.g., Rust for performance-critical code, Python for data processing)

### Placement: All Code in Appendix

**All code examples are placed in the Code Examples appendix.** There are no inline fenced code blocks in chapter text.

- Reference examples by number in prose: "(see Example N.M in the Code Examples appendix)"
- Use prose descriptions to explain concepts without embedded code
- Keep chapters focused on concepts while the appendix provides implementation

Example of reference in text:

> The cache-aside pattern checks the cache first, falling back to the database
> on miss (see Example 5.1). The key insight is that the application—not the
> cache—owns the invalidation logic.

**Note:** Single inline commands may use backtick code spans (e.g., `redis-cli INFO`) but fenced code blocks are reserved for the Code Examples appendix.

### Code Quality Standards

1. **Include comments on key lines**: Explain what non-obvious code does
2. **Keep examples focused**: Even end-of-chapter examples should be 15-40 lines maximum
3. **Use realistic variable names**: `connection_pool` not `cp`, `request_timeout` not `rt`
4. **Show complete, runnable examples when possible**: Include imports and setup
5. **Handle errors appropriately**: Show proper error handling, not just the happy path
6. **Use modern idioms**: async/await, type hints (Python), proper typing (TypeScript)
7. **Blank line before code blocks**: Always include a blank line before opening code fences (```) to ensure proper spacing in rendered output. Enforced by `just lint md`.
8. **Space before inline code**: Always include a space before opening backticks for inline code. Write `the `Cache-Control` header` not `the`Cache-Control` header`. Exceptions: possessives (`Python's `lru_cache``), opening brackets/parentheses, markdown emphasis (`**`bold code`**`), and start of line. Enforced by `just lint md`.

---

## 4. Citation Format

### Why Citations Matter
This is a technical ebook that makes specific claims about performance. All data-driven claims must be verifiable. **No made-up statistics.**

### Inline Citation Format

Use bracketed citations immediately after the claim:

- For published sources: `[Source: Author/Organization, Year]`
- For web sources: `[Source: URL]`
- For research papers: `[Source: Author et al., Year]`

**Examples:**
- "Connection establishment adds 1-3 round trips for TCP and TLS handshake [Source: Cloudflare, 2023]."
- "The 99th percentile latency is often 10x higher than the median [Source: https://www.brendangregg.com/usemethod.html]."
- "Tail latencies dominate user-perceived performance in distributed systems [Source: Dean & Barroso, 2013]."

### References Section

Every chapter ends with a References section containing full citation details:

```markdown
## References

1. **Dean, J., & Barroso, L. A.** (2013). "The Tail at Scale." Communications of the ACM, 56(2), 74-80. https://dl.acm.org/doi/10.1145/2408776.2408794

2. **Google SRE Book** (2016). "Monitoring Distributed Systems." https://sre.google/sre-book/monitoring-distributed-systems/

3. **Cloudflare Blog** (2023). "A primer on connection pooling." https://blog.cloudflare.com/...
```

### What Requires Citations

**Citations REQUIRED for:**
- All statistics and percentages
- Performance benchmark results
- Specific latency or throughput numbers
- Claims about industry practices ("most companies do X")
- Quotes from other sources
- Research findings
- Tool-specific performance characteristics

**Citations NOT required for:**
- General programming concepts ("a loop iterates over elements")
- Mathematical definitions ("p99 means 99th percentile")
- Obvious facts ("databases store data on disk")
- Your own code examples
- Logical reasoning and analysis

---

## 5. Diagram Placeholder Format

Authors write the content; diagrams are created separately. Use HTML comments to indicate where diagrams should be placed and what they should show.

### Format

```markdown
<!-- DIAGRAM: Brief but complete description of what the diagram should show -->
```

### Good Diagram Descriptions

```markdown
<!-- DIAGRAM: Request flow showing client -> load balancer -> API server -> cache check -> database, with latency annotations at each hop -->

<!-- DIAGRAM: Circuit breaker state machine with three states (Closed, Open, Half-Open) and transition conditions -->

<!-- DIAGRAM: Cache hierarchy showing L1 (in-process) -> L2 (Redis) -> Origin (PostgreSQL) with typical latencies: 1ms, 5ms, 50ms -->

<!-- DIAGRAM: Comparison of horizontal vs vertical scaling, showing multiple small instances vs one large instance -->
```

### Poor Diagram Descriptions (Avoid These)

```markdown
<!-- DIAGRAM: Architecture diagram -->  // Too vague
<!-- DIAGRAM: Show caching -->  // Not specific enough
<!-- DIAGRAM: The thing we just discussed -->  // Not self-contained
```

### Diagram Naming Convention

When referencing future diagrams, use: `See diagram: [description]`

Example: "The request flows through multiple layers (see diagram: cache hierarchy with latencies)."

---

## 6. Chapter Structure Template

Every chapter must follow this structure:

```markdown
# Chapter N: Chapter Title

## Overview

[2-3 paragraphs introducing the chapter topic. Explain what problem this chapter solves, why it matters, and what the reader will learn. Connect to the book's empirical philosophy.]

## Key Concepts

### Concept Name

[Detailed explanation with examples]

### Another Concept

[Continue as needed with ### subsections]

## Common Pitfalls

[Bulleted list of mistakes to avoid, with brief explanations]

- **Pitfall name**: Explanation of why it's a problem and how to avoid it.
- **Another pitfall**: Explanation.

## Summary

[Bullet points summarizing key takeaways—aim for 5-8 points]

- Key point one
- Key point two
- ...

## References

[Numbered list of all sources cited in the chapter]

## Next: [Chapter N+1 Title](./0N+1-filename.md)

[One sentence preview of the next chapter and how it builds on this one.]
```

### Section Guidelines

- **Overview**: Set context. Why does this topic matter? What problem does it solve?
- **Key Concepts**: The meat of the chapter. Use ### subsections liberally. Reference examples in the Code Examples appendix by number: "(see Example N.M)". No inline fenced code blocks.
- **Common Pitfalls**: Real mistakes developers make. Be specific and actionable.
- **Summary**: Scannable recap. Readers often review just this section.
- **References**: Complete, clickable where possible.
- **Next**: Creates continuity between chapters.

**Note on Code Examples**: All code examples are collected in the Code Examples appendix, not inline in chapters. This keeps chapters focused on concepts while providing complete, runnable implementations in one reference location.

---

## Final Checklist for Authors

Before submitting a chapter, verify:

- [ ] All three languages (Python, Rust, TypeScript) are represented in code examples
- [ ] All statistics and claims have citations
- [ ] Terminology matches this style guide exactly
- [ ] Chapter follows the required structure
- [ ] Diagram placeholders are descriptive and specific
- [ ] Word count is within 3000-8000 words (narrative case study chapters like "Putting It All Together" may exceed this limit; complex/technical chapters may also require more space)
- [ ] Common pitfalls section is included
- [ ] References section is complete
- [ ] "Next" link points to the correct chapter
