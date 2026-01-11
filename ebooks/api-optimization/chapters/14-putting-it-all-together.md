# Chapter 14: Building Collab Docs: A Case Study

![Chapter 14 Opener](../assets/ch14-opener.html)

\newpage

## Overview

Throughout this book, we have explored individual optimization techniques in isolation: caching strategies, database selection, connection pooling, circuit breakers, and more. Each chapter provided specific patterns with measurable improvements and documented trade-offs. But real systems do not present problems neatly labeled "this is a caching issue" or "apply circuit breaker here." They present symptoms, constraints, and competing priorities that require coordinated decisions across multiple layers.

This chapter tells the story of a fictional team building a real-time collaborative document platform from the ground up. We follow them from the initial leadership mandate through architecture decisions, implementation challenges, production incidents, and eventually to a successful launch. Along the way, they apply techniques from every chapter in this book, not in isolation, but as part of a coherent system designed for performance from the start.

The stakes are real. As we explored in Chapter 1, performance directly impacts revenue: Amazon's research showed that every 100 milliseconds of added latency cost approximately 1% in sales [Source: Amazon, 2006]. Google found that when page load time increased from one to three seconds, bounce rates increased by 32% [Source: Google, 2017]. The team in this chapter faces similar pressures. Their company's flagship product is declining, and Collab Docs represents the strategic bet on the future. They have six months to prove the concept can scale.

The goal is not to provide a template to copy, but to demonstrate how the empirical methodology we have advocated throughout this book plays out in practice. The team measures before optimizing, forms hypotheses before implementing, and validates that changes actually improve the system. Their mistakes are as instructive as their successes.

We will follow this team through three phases: the foundational decisions that shape everything that follows, the implementation challenges that test those decisions, and the production incidents that reveal what they missed. Each phase draws on concepts from multiple chapters, showing how patterns combine in practice. By the end, you will see not just what the team built, but how they thought through the problems, and how they recovered when things went wrong.

## The Team

Before we begin, let us introduce the people who will guide us through this journey. Understanding their backgrounds helps explain why they approach problems the way they do, and why they sometimes disagree.

**Elena Park, VP of Engineering**: Elena owns the technical strategy for the company. She spent fifteen years at a major cloud provider before joining this startup, and she brings both the ambition and the scars from that experience. Elena is the one who pushed for Collab Docs when the board was skeptical, and she is personally invested in its success. She understands performance at a business level: she can translate "p95 latency increased by 50 milliseconds" into "we will lose approximately $2 million in annual revenue." When incidents happen, Elena is the one explaining impact to the CEO. She expects the team to have answers, but she also shields them from political pressure so they can focus on solutions.

**Maya Chen, Lead Architect**: Maya thinks in systems. Her background spans distributed databases and large-scale web platforms. She was an early engineer at a company that scaled from thousands to millions of users, and she learned firsthand how architectural decisions made in month one become constraints in year three. Maya asks "what are we optimizing for?" before anyone touches a keyboard, and she insists on understanding the fundamental trade-offs of every architectural decision. She keeps a whiteboard in her office covered with system diagrams, and she updates it obsessively. During incidents, Maya is the one who can trace a symptom back through multiple layers to find the root cause.

**Jordan Okafor, SRE Lead**: Jordan's mantra is "if we can't measure it, we can't improve it." They built observability platforms at two previous companies and have strong opinions about dashboards, alerts, and the difference between monitoring and observability. Jordan joined after a stint at a company that had a catastrophic outage, one that took four hours to diagnose because nobody could see what was happening inside the system. That experience made them almost religious about instrumentation. Jordan runs the load tests, maintains the on-call rotation, and is usually the first to notice when something is wrong. Their desk has three monitors: one for code, one for Grafana dashboards, and one for Slack alerts.

**Priya Sharma, Backend Lead**: Priya turns architecture into code. She owns the caching strategy, the async processing pipeline, and most of the network optimization work. Pragmatic to her core, Priya prefers solutions that are boring but reliable over clever but fragile. She has a sign above her desk that reads "Complexity is not a feature." Before joining the team, Priya worked at a fintech company where a caching bug caused incorrect account balances to display for 45 minutes,an experience that gave her deep respect for cache invalidation. When the team debates approaches, Priya is the one who asks "but how do we operate this at 3 AM when something breaks?"

**Alex Rivera, Security/Auth Engineer**: Alex bridges security and performance, a combination that often creates tension. They own authentication performance, token validation, and increasingly, the edge infrastructure. Alex came from a security consulting background where they saw the aftermath of breaches, but they also saw companies whose security measures made their products unusable. They learned that secure systems can also be fast systems,they just require more careful design. Alex is the team's skeptic: when someone proposes a caching optimization, Alex asks about the security implications. When someone suggests moving logic to the edge, Alex thinks through the attack surface. The team sometimes finds this frustrating, but Alex has prevented several near-misses.

**Sam Kim, Engineering Manager**: Sam coordinates the team, manages trade-off discussions, and represents business constraints. They joined from the product organization and understand user needs in a way the engineers sometimes miss. When technical debates reach an impasse, Sam helps frame the decision in terms of user impact and business value. Sam is also the team's historian,they keep meticulous notes on every decision and the reasoning behind it, which proves invaluable when the team needs to revisit earlier choices. During incidents, Sam handles communication with stakeholders while the engineers focus on resolution.

## Part I: Foundation

### The Leadership Mandate

The project began in a glass-walled conference room on the executive floor. Elena had called the meeting, and the tension was palpable. The company's flagship product,a traditional document management system,was losing market share to nimbler competitors. Revenue had declined for three consecutive quarters. The board was asking hard questions, and Elena needed answers.

"I am going to be direct with you," Elena began, standing at the head of the table. The team,Maya, Jordan, Priya, Alex, and Sam,sat with laptops open, waiting. "Our core product is dying. The market has moved to real-time collaboration, and we are still selling software that requires users to email documents back and forth. We have six months to launch Collab Docs or we start discussing which teams to cut."

The silence that followed was uncomfortable. Sam broke it first. "What are the actual requirements? What does success look like?"

Elena pulled up a slide. "One hundred thousand daily active users within six months of launch. p95 latency under 200 milliseconds for all core operations,creating documents, editing, and real-time sync. If two people edit the same document, they need to see each other's changes within one second. And this is not negotiable: the product needs to feel as fast as our competitors. Users will compare us directly."

"That is a lot of users for a first version," Jordan observed. "Most products launch with much smaller targets."

"Most products are not betting the company," Elena replied. "The board approved this project because I told them we could compete. If we launch something slow, they will not give us time to optimize. First impressions matter."

Maya had already started sketching on the whiteboard. "Let me break down what 'real-time collaboration' means technically. We are looking at WebSocket connections for persistent bidirectional communication. Conflict resolution for concurrent edits,probably Operational Transformation or CRDTs. A presence system so users can see who else is viewing the document, with cursor positions and selection state. And all of this synchronized across potentially thousands of concurrent users on a single document."

"And authentication on every operation," Alex added. "Users need to be authorized for each workspace and document they access. That is going to be on the critical path for every request. We cannot just authenticate once and assume,permissions can change while a user has a document open."

Priya was already thinking through the implementation. "That is a lot of state to synchronize. WebSocket connections are inherently stateful, which complicates horizontal scaling. We will need to think carefully about how sync servers communicate with each other."

Jordan pulled up their laptop. "Before we design anything, we need to define what success looks like in measurable terms. 'Fast' is not a specification. 'Under 200 milliseconds p95' is a specification. What are our Service Level Objectives?"

Elena nodded. "That is exactly the right question. And I want to add one more constraint: we need to understand the business impact of performance. If we miss our latency targets, I need to explain to the board what that costs us. Research from Akamai shows that a 100-millisecond delay in website load time can decrease conversion rates by 7% [Source: Akamai, 2017]. We should assume similar sensitivity for our users."

Sam was taking notes. "So we are not just optimizing for speed,we are optimizing for revenue. Every millisecond has a dollar value."

"Exactly," Elena said. "Which is why I want Jordan's observability in place before we write feature code. When something is slow, I need to know how slow, for how many users, and what it is costing us. That is the only way I can have an informed conversation with the board."

### Defining Success: SLOs and Budgets

The team spent the next two hours defining their SLOs. This was not bureaucratic overhead,it was the foundation for every decision that followed. As we discussed in Chapter 2, Service Level Objectives translate business requirements into measurable technical targets.

Maya led the discussion. "Our end-to-end target is p95 under 200 milliseconds. Let's allocate that budget across the request path." She drew a simple diagram on the whiteboard showing the request flow.

The team settled on the following latency budget:

- **API Gateway and routing**: 20ms
- **Authentication and authorization**: 30ms
- **Business logic and database**: 100ms
- **Serialization and response**: 20ms
- **Network transfer to client**: 30ms

"This budget gives us a target for each layer," Maya explained. "If authentication is taking 80 milliseconds, we know we have a problem even if our end-to-end numbers look acceptable. We are borrowing from other budgets, and eventually that debt comes due."

Jordan documented the full SLO framework:

- **Availability**: 99.9% (approximately 8.7 hours of downtime per year)
- **Latency**: p95 < 200ms for API operations, p95 < 1000ms for real-time sync propagation
- **Error rate**: < 0.1% of requests returning 5xx errors
- **Throughput**: Must handle 2,000 requests per second at peak

"These numbers are not arbitrary," Jordan noted. "Research by Nielsen Norman Group shows that users perceive delays under 100 milliseconds as instantaneous, while delays over 1 second break their flow of thought [Source: Nielsen Norman Group, Response Time Limits]. Our 200ms target keeps us well within the 'feels responsive' range."

### Database Selection: The First Architecture Decision

With SLOs defined, the team turned to their first major architectural decision: database selection. As we explored in Chapter 7, this choice would shape the system's capabilities and constraints for years to come.

Priya outlined the data requirements. "We have structured metadata,users, workspaces, documents, permissions. We have the document content itself, which is semi-structured and varies in size from a few kilobytes to several megabytes. And we have real-time presence data,who is viewing what, cursor positions, selection state."

Maya framed the decision. "I see three options. First, a document database like MongoDB that can handle the flexible schema of document content. Second, PostgreSQL with JSONB columns for the document content. Third, a polyglot approach with different stores for different data types."

The team debated for an hour. MongoDB offered schema flexibility and built-in support for large documents. PostgreSQL provided ACID guarantees, mature tooling, and the ability to join metadata with content in a single query.

"What about consistency requirements?" Alex asked. "If a user changes document permissions, how quickly does that need to take effect?"

This question crystallized the decision. Permission changes needed to be immediately consistent,a user removed from a document should lose access on their very next request. Document content could tolerate brief inconsistency during collaboration, but security boundaries could not.

The team chose a polyglot approach:

- **PostgreSQL** for structured data: users, workspaces, documents metadata, permissions
- **Redis** for ephemeral real-time data: presence information, active cursor positions, session state
- **PostgreSQL JSONB** for document content, with the option to migrate to a dedicated store if needed

"This gives us ACID where we need it for permissions and strong tooling for complex queries," Maya summarized. "Redis handles the high-frequency, ephemeral data that would overwhelm PostgreSQL. We are accepting the operational complexity of multiple data stores in exchange for using each tool for its strengths."

The trade-offs were documented: two systems to operate, potential consistency gaps between stores, and the need for careful cache invalidation when permissions changed.

### Building Observability Before Features

Jordan made an unusual request at the next team meeting,unusual enough that it sparked a debate that would shape the entire project.

"Before we write a single line of feature code, I want us to spend two weeks implementing observability infrastructure. Traces, metrics, structured logging, and continuous profiling,everything described in Chapters 3 and 4."

Sam raised an eyebrow. "Two weeks? We have six months total. That is a significant portion of our timeline for infrastructure that users will never see."

"That is exactly the point," Jordan replied. "Users will never see the plumbing, but they will feel the difference when something goes wrong. A study by Honeycomb found that teams with mature observability practices resolved incidents 90% faster than teams without proper instrumentation [Source: Honeycomb, Observability Maturity Report]. More importantly, we will be flying blind during development without it. How will we know if our database query is taking 50 milliseconds or 500 milliseconds without traces?"

Elena, who had been listening from the doorway, stepped in. "I support this. I have seen too many teams launch fast, hit performance problems, and then spend months trying to understand their own system. The two weeks we invest now will save us months later."

The team agreed. Over the following two weeks, Jordan led the implementation of what they called the "Four Pillars",the observability infrastructure that would prove invaluable in every incident to come.

#### Pillar One: Distributed Tracing

"Every request tells a story," Jordan explained during the first design session. "The question is whether we can read that story when we need to."

The team implemented distributed tracing with OpenTelemetry, following the patterns from Chapter 3. Every service was instrumented to propagate trace context using the W3C Trace Context standard. The API Gateway created a trace ID on each incoming request, and every downstream call,database queries, Redis operations, internal service calls,became a span in that trace.

But Jordan pushed for more than basic instrumentation. "We need to think about sampling strategy. At 2,000 requests per second, we cannot store every trace forever. But we also cannot afford to miss the traces that matter."

The team debated the options. Head-based sampling,deciding at the start of a request whether to trace it,was simple but risked missing interesting slow requests. Tail-based sampling,deciding after the request completed,captured all interesting cases but required more infrastructure.

"We will use a hybrid approach," Jordan decided. "One percent head-based sampling for normal requests, but 100% capture for any request that errors or exceeds 500 milliseconds. The interesting requests are the slow ones and the failures,we cannot afford to miss those."

Priya raised a practical concern. "How do we handle sampling across service boundaries? If the API Gateway decides not to sample a request, but the downstream service has an interesting failure, we lose that trace."

"The sampling decision propagates with the trace context," Jordan explained. "Once a request is selected for sampling, every downstream service honors that decision. And if any service in the chain hits our 'always sample' criteria,error or slow,we upgrade the entire trace to full capture."

#### Pillar Two: Metrics and the Golden Signals

For metrics, Jordan insisted on implementing the four golden signals from the Google SRE book: latency, traffic, errors, and saturation. Every service exported these via Prometheus.

"Most teams focus on latency and errors," Jordan noted. "But saturation is where the early warnings live. By the time latency spikes, you are already in trouble. Saturation tells you when you are approaching trouble."

The team implemented saturation metrics at every layer:

- **Database connection pool**: Connections in use versus pool size, wait time for connection acquisition
- **Redis connection pool**: Same metrics, plus command queue depth
- **Application thread pool**: Active threads versus pool size, task queue length
- **WebSocket connections**: Current connections versus configured maximum per instance

"Wait time is the key metric," Jordan emphasized. "If pool utilization is 80% but wait time is zero, you are fine. If utilization is 60% but wait time is 50 milliseconds, something is wrong,probably pool contention or slow queries holding connections."

The team also added business-specific metrics: documents created per minute, active WebSocket connections, permission cache hit rate, export jobs queued versus completed. These would prove essential for understanding user impact during incidents.

#### Pillar Three: Structured Logging with Correlation

Every log line needed to include the trace ID, enabling developers to jump from a log entry to the full distributed trace. But Jordan pushed further.

"Logs are only useful if you can find them," they explained. "We need structured logging, not string formatting. Every log entry should be JSON with consistent field names: `trace_id`, `span_id`, `service`, `level`, `message`, and any relevant context fields."

Priya implemented a logging library wrapper that automatically injected trace context into every log statement. The wrapper also enforced sampling alignment,if a request was being traced, its logs were retained; if not, logs were sampled at the same rate.

"This seems like overkill," Sam observed. "Do we really need this much infrastructure for logging?"

"You will thank me at 3 AM," Jordan replied. "When an alert fires and you have 60 seconds to understand what is happening, being able to search for a trace ID and see every log from every service involved in that request,that is the difference between resolution and escalation."

#### Pillar Four: Continuous Profiling

The final pillar was the most controversial. Jordan wanted to run continuous profiling in production using Pyroscope, generating flame graphs for every service.

"Profiling in production?" Alex raised concerns immediately. "What is the overhead? And what about sensitive data in the call stacks?"

"Pyroscope uses sampling profilers," Jordan explained. "Overhead is typically 1-2% CPU, which is acceptable. As for sensitive data,we are capturing function names and call stacks, not variable values. There is nothing PII-visible in a flame graph."

Maya saw the value immediately. "This could have saved us weeks at my last company. We had a memory leak that only appeared under production load. We spent two months adding targeted profiling, reproducing the issue, analyzing, repeating. Continuous profiling would have caught it in days."

The team agreed to implement Pyroscope with a 90-day retention policy. Flame graphs would be generated every 10 seconds and aggregated by service and endpoint. When the authentication incident hit weeks later, these flame graphs would be the key to rapid diagnosis.

#### Traffic Baselines and Alert Design

With the four pillars in place, Jordan turned to dashboards and alerting. But before creating a single alert, they needed baselines.

"We cannot alert on 'high latency' if we do not know what normal latency looks like," Jordan explained. "And 'normal' changes throughout the day. What is acceptable at 3 AM is concerning at 2 PM."

The team ran the system under synthetic load for a week, establishing baseline patterns. Jordan documented the expected diurnal shape: low traffic from midnight to 6 AM, ramp starting at 8 AM, peak between 1 PM and 3 PM, gradual decline through the evening. Latency followed an inverse pattern: lower during off-peak when resources were abundant, slightly higher during peak.

"Now we can create meaningful alerts," Jordan said. "Instead of 'p95 latency above 200ms,' we alert on 'p95 latency more than 50% above baseline for this time of day.' That catches real problems while ignoring the natural variation between peak and off-peak."

The alerting design followed principles from Chapter 4:

**Symptom-based, not cause-based**: Alerts fired on user-impacting symptoms (high latency, elevated errors) rather than underlying causes (high CPU, full disk). The causes were investigated during incident response, but the triggers focused on what users experienced.

**Multi-burn-rate SLO alerts**: Instead of binary threshold alerts, Jordan implemented error budget consumption tracking. A slow burn,consuming error budget faster than sustainable,triggered a warning. A fast burn,consuming budget at 10x the sustainable rate,triggered immediate pages.

**Alert fatigue prevention**: Every alert required a runbook link explaining what the alert meant, how to investigate, and when to escalate. Alerts that fired frequently without action were candidates for tuning or removal. "A noisy alert is worse than no alert," Jordan insisted. "It trains people to ignore pages."

"This seems like a lot of infrastructure for a product that does not exist yet," Priya observed as Jordan demonstrated the dashboards.

"That is exactly the point," Jordan replied. "We will iterate faster because we can see what is happening. Every optimization we make, we will see the impact immediately. Every bug we introduce, we will catch it in development instead of production. And when something breaks in production,not if, when,we will be able to diagnose it in minutes instead of hours."

The two-week investment would pay dividends repeatedly. During the authentication incident, Jordan would diagnose the root cause in under five minutes using flame graphs. During the export cascade, traces would reveal the connection pool contention within the first ten minutes. The observability infrastructure was not overhead,it was the foundation that made everything else possible.

<!-- DIAGRAM: Collab Docs architecture showing API Gateway, Document Service, Auth Service, Sync Service, PostgreSQL, Redis, with OpenTelemetry instrumentation and Prometheus metrics flowing to Grafana -->

![Collab Docs Architecture](../assets/ch14-architecture.html)

## Part II: Implementation

### Real-Time Sync: WebSocket Architecture

The real-time collaboration feature required persistent connections between clients and servers. Priya led the design of the WebSocket architecture, drawing heavily on the concepts from Chapter 5.

"HTTP request-response is not going to work for real-time sync," Priya explained. "We need server-push capability to broadcast changes to all users viewing a document. WebSockets give us bidirectional communication over a single long-lived connection."

The design challenges were significant:

**Connection management**: Each active user maintains a WebSocket connection. With 100,000 daily active users, peak concurrent connections could reach 20,000 or more. Each connection consumes server memory and file descriptors.

**Horizontal scaling**: WebSocket connections are stateful,a client connects to a specific server. If that server needs to notify users about a document change, it may not have connections to all relevant users.

**Connection establishment overhead**: As we covered in Chapter 5, establishing a connection involves TCP handshake (one round trip), TLS handshake (one to two round trips with TLS 1.2, one round trip with TLS 1.3), and WebSocket upgrade. We needed to minimize connection churn.

Priya's design addressed each challenge:

**Dedicated sync service**: A separate service handles WebSocket connections, keeping the stateless API service simple. The sync service runs on larger instances optimized for many concurrent connections.

**Redis pub/sub for fan-out**: When a document changes, the API service publishes to a Redis channel keyed by document ID. All sync service instances subscribe to channels for documents their connected users are viewing. This decouples the API from specific sync service instances.

**HTTP/2 for internal communication**: Communication between the API Gateway and backend services uses HTTP/2, multiplexing many requests over a single connection to each service instance. This reduces connection overhead within the cluster.

**Connection pooling**: Database and Redis connections are pooled aggressively. Priya sized the pools based on expected concurrency and the formula from Chapter 5: `pool_size = (throughput × average_latency) + buffer`.

For the PostgreSQL connection pool, with a target of 500 queries per second and average query latency of 20 milliseconds: `pool_size = (500 × 0.020) + 5 = 15` connections per application instance, with a buffer for variance.

### The Permission Caching Debate

Three weeks into implementation, Jordan flagged a concerning pattern in the traces. "Every document operation is spending 15 milliseconds in permission checks. That is almost our entire auth budget."

Alex investigated. The permission system was correct but slow. Each request required:

1. Look up the user's workspace memberships (database query)
2. Look up the document's workspace (database query)
3. Check if the user has permission for the operation (in-memory logic)

Two database queries on the critical path of every request added up.

"We need to cache permissions," Priya proposed. "We can store user-workspace memberships in Redis with a reasonable TTL."

Alex raised the concern the team expected. "Permission changes need to take effect immediately. If we remove someone from a workspace, they should not be able to access documents for the next 5 minutes while the cache expires."

This tension,between cache performance and permission consistency,is fundamental to caching systems, as we discussed in Chapter 6. The team debated several approaches:

**Short TTL (30 seconds)**: Simple but only reduces load by 30x, not enough given query frequency.

**Event-driven invalidation**: When permissions change, publish an event that invalidates relevant cache entries. Complex but precise.

**Hybrid approach**: Short TTL (5 minutes) with event-driven invalidation for explicit permission changes.

They chose the hybrid approach. Permissions would cache for 5 minutes, long enough to handle the vast majority of requests from cache. When a user was removed from a workspace,a relatively rare event,the permission service would publish an invalidation event to Redis pub/sub. All application instances subscribed to these events and cleared the relevant cache entries immediately.

"This gives us 95% or better cache hit rate for permission checks while maintaining immediate consistency for permission changes," Priya summarized. "The trade-off is additional complexity in the permission service and the need to ensure our invalidation events are reliable."

The implementation reduced permission check latency from 15 milliseconds to under 1 millisecond for cached lookups.

### Moving Work Off the Critical Path

As features accumulated, the team noticed response times creeping upward. Jordan's traces revealed the culprit: document export functionality.

Users could export documents to PDF and Word formats. The initial implementation was synchronous,the API waited for export to complete before responding. Small documents exported in hundreds of milliseconds, acceptable if not ideal. But large documents with embedded images could take 10 seconds or more, pushing API latency through the roof.

"We are violating our SLO every time someone exports a large document," Jordan reported.

Priya proposed the asynchronous pattern from Chapter 8. "Export does not need to be synchronous. The user requests an export, we return immediately with a job ID, and the client polls for completion or subscribes to a webhook."

The async export architecture worked as follows:

1. User requests export via POST `/documents/{id}/export`
2. API validates the request and publishes a job to the export queue
3. API returns immediately with HTTP 202 Accepted and a job ID
4. Export workers consume jobs from the queue and generate files
5. Completed exports are stored in object storage (S3)
6. Client polls GET `/exports/{job_id}` or receives webhook notification

The team implemented the transactional outbox pattern to ensure reliability. Export requests were written to an outbox table in the same transaction as any associated document metadata changes. A background process published outbox entries to the message queue, guaranteeing that every export request eventually reached a worker.

"What about export failures?" Alex asked. "The third-party PDF service we are using is not always reliable."

Priya configured the queue with retry logic: failed exports would be retried three times with exponential backoff. If all retries failed, the job moved to a dead-letter queue for manual investigation, and the user received a notification that their export failed.

The impact was dramatic. API p95 latency dropped by 200 milliseconds,the overhead of slow exports was no longer on the critical path.

### Load Testing: Finding Limits Before Users Do

With the core features implemented, Jordan called a meeting to discuss the final validation phase before launch. The team gathered in the war room,a conference room that had been converted into a permanent home for dashboards and whiteboards.

"We are not launching until we understand our limits," Jordan announced. "Chapter 13 lays out the methodology: load tests to find breaking points, stress tests to understand failure modes, and soak tests to catch resource leaks. We are doing all three."

Maya nodded. "What is our target?"

"Elena said 100,000 daily active users. Based on our usage projections, that translates to roughly 10,000 concurrent users at peak, generating about 2,000 requests per second. We need to handle that with headroom,I want to see 12,000 concurrent users before we hit stress."

#### The First Load Test

Jordan had spent weeks building the test harness using k6, chosen for its modern approach to load testing and its ability to handle both HTTP and WebSocket connections. The test script simulated realistic user behavior: login, navigate to workspace, open a document, make edits, see presence updates, and occasionally export.

"One critical detail," Jordan explained as they walked through the test configuration. "We are using think time,pauses between user actions that simulate real human behavior. A real user does not submit requests as fast as possible. They read, they think, they type. Without think time, 1,000 virtual users could generate 50,000 requests per second. With realistic think time, those same 1,000 users generate perhaps 500 requests per second."

The team ran the first load test at 2 PM on a Wednesday. Jordan watched the dashboards as virtual users ramped up: 1,000... 2,000... 3,000... 4,000...

At 5,000 concurrent users, the metrics went red.

WebSocket connection failures started appearing,about 2% at first, then climbing to 10%. API latency spiked from 120 milliseconds to over 2 seconds. The sync service instances showed 98% CPU, but more concerning was the Redis connection pool wait time: it had climbed from 0 milliseconds to 500 milliseconds.

"Stop the test," Jordan said. "We found our first bottleneck."

#### Diagnosing Connection Pool Exhaustion

Priya examined the pool configuration while Jordan pulled up the saturation metrics. The problem was clear: Redis connection pool exhaustion.

"We sized the pool at 20 connections per instance," Priya explained. "That seemed generous during development when we had dozens of concurrent users. But each WebSocket connection triggers multiple Redis operations,presence updates, pub/sub subscriptions, session state checks. At 5,000 users, we are far exceeding what 20 connections can handle."

Jordan calculated the required pool size using the formula from Chapter 5. "Our peak Redis operations per second is about 10,000. Average operation latency is 2 milliseconds. So we need at least `10,000 × 0.002 = 20` connections just for steady state, with no buffer for variance. Under load, variance increases. We need at least 100 connections per instance."

The team increased the Redis connection pool from 20 to 100 connections and reran the test.

This time, the system handled 12,000 concurrent users before showing stress. Latency remained under 200 milliseconds until 11,000 users, then climbed gradually. At 12,000 users, p95 latency hit 250 milliseconds,above the SLO but still functional.

"We have our ceiling," Jordan documented. "12,000 concurrent users with acceptable performance, degradation starting around 11,000. That gives us a 20% buffer above our 10,000 target."

#### Establishing Baselines

Jordan meticulously documented the baseline metrics:

- **p50 latency**: 45ms
- **p95 latency**: 120ms
- **p99 latency**: 185ms
- **Maximum throughput**: 2,400 RPS before degradation
- **WebSocket connection capacity**: 12,000 concurrent per sync service instance
- **Redis pool utilization at peak**: 65%
- **Database connection wait time at peak**: 3ms

"These numbers become our benchmark," Jordan explained to the team. "Any code change that makes them worse needs justification. We will run a subset of these tests on every deploy to catch performance regressions before they reach production."

#### The Soak Test: Finding the Memory Leak

With load testing complete, Jordan proposed something the team had not anticipated: an 8-hour soak test.

"What is the point of running for 8 hours?" Sam asked. "If the system handles load for an hour, why would it fail at hour six?"

"Resource leaks," Jordan replied. "Memory leaks, connection leaks, file descriptor leaks,they accumulate slowly. A system can look healthy for hours and then suddenly fall over. The only way to find these issues is to run for extended periods under production-like load."

Following the methodology from Chapter 13, Jordan configured the soak test to run at 70% of peak load,about 7,000 concurrent users,for 8 hours overnight. The test started at 10 PM and would complete at 6 AM.

At 6:30 AM, Jordan checked the results and immediately called an emergency meeting.

"We have a problem," Jordan said, pulling up a graph. "Look at the memory usage for the sync service over the 8 hours."

The graph told a clear story. Memory usage started at 1.2 GB per instance. It climbed steadily throughout the test,not spiking, not fluctuating, just a steady upward march. By hour 8, each instance was using 2.4 GB, approaching the 3 GB container limit.

"We are leaking about 150 megabytes per hour," Jordan calculated. "At production load, an instance would hit memory limits in about 12 hours. If we launched on Monday, we would crash on Tuesday."

Priya dove into the code. The leak took three hours to find. WebSocket disconnection handlers were supposed to clean up presence state and pub/sub subscriptions, but a race condition meant that about 0.1% of disconnections left orphaned objects in memory. Under the churn of a soak test,thousands of connections opening and closing over 8 hours,these orphans accumulated.

"This never appeared in our unit tests or integration tests," Priya observed. "The leak is so slow that short tests cannot detect it."

Maya summarized the lesson. "Soak testing found what unit tests and load tests never could. If we had skipped this step and launched, our first production weekend would have been a disaster."

The team fixed the race condition, reran the 8-hour soak test, and watched the memory graph stay flat. The system was ready.

<!-- DIAGRAM: Soak test memory trend showing the before (steadily climbing memory over 8 hours) and after (flat line) graphs -->

"These numbers become our baseline for production," Jordan said. "Any change that degrades them needs justification."

## Part III: Launch and Incidents

### Soft Launch: First Production Traffic

The team deployed to production with a soft launch strategy,5% of traffic routed to the new system while monitoring closely for issues.

Initial metrics were encouraging:

- **p95 latency**: 85ms (well under the 200ms SLO)
- **Error rate**: 0.02% (under the 0.1% SLO)
- **Cache hit rates**: Permission cache at 97%, document metadata cache at 78%

Alex had configured edge caching for static assets using Cloudflare, applying the CDN strategies from Chapter 12. Static JavaScript, CSS, and images were cached at the edge with long TTLs and cache-busting via content hashing.

"Origin traffic for static assets dropped 70%," Alex reported. "Our servers are handling only dynamic API requests."

The team gradually increased traffic over two weeks, watching metrics at each stage. At 50% traffic, the system remained healthy. At 100%, they declared the soft launch complete.

Then marketing launched their campaign.

### Incident Report: The Authentication Storm

The incident that would teach the team the most about authentication performance began with good news. Marketing had been waiting for weeks to launch their email campaign, and the soft launch had proven the system was stable. On a Tuesday afternoon, they hit send.

#### The Alert

Jordan was at their desk reviewing the weekly metrics report when the first anomaly appeared. The traffic dashboard, usually a predictable wave, suddenly showed a vertical line. Requests per second jumped from 50 to 200 to 400 to 800 in under five minutes.

"The marketing email went out," Sam announced in Slack. "We might see increased traffic."

Jordan smiled,increased traffic was good news. Then the latency graph updated.

p95 login latency, which had been holding steady at 85 milliseconds, started climbing. 200 milliseconds. 400 milliseconds. 800 milliseconds. At T+8 minutes, it crossed 2,000 milliseconds, and the error rate started ticking up. Users were timing out before they could even log in.

At T+12 minutes, Jordan's pager fired: "SLO violation - auth latency. p95 at 2,100ms (target: 200ms). Error rate: 15%."

Jordan opened the incident channel in Slack and pinged the team. "Auth latency incident. Investigating. Please join the war room."

Within three minutes, Maya, Priya, and Alex were gathered around Jordan's desk, staring at the dashboards. Sam started a video call for Elena, who was in a meeting with the board.

#### Wrong Hypothesis #1: Database Overload

"It has to be the database," Priya said, pulling up the PostgreSQL metrics. "Every login hits the user table for authentication. At 800 logins per second, we could be overwhelming it."

Jordan pulled up the database dashboard. Connection pool utilization was at 45%,elevated but healthy. Query latency was 3 milliseconds average, right in line with baseline. No slow queries in the log.

"Database looks fine," Jordan reported. "Connections are healthy, queries are fast. Whatever is slow, it is not PostgreSQL."

"What about Redis?" Maya suggested. "Session management hits Redis."

Jordan checked. Redis operations were completing in under a millisecond. The Redis cluster showed 20% CPU utilization,nowhere near stressed.

"It is not Redis either," Jordan confirmed. "Both data stores are healthy."

#### Wrong Hypothesis #2: CDN Cache Miss

Alex had an idea. "Marketing just sent a lot of emails. What if they all have tracking pixels or links that are hitting our CDN? A cache miss storm could be overwhelming the origin."

Jordan pulled up the Cloudflare dashboard. Cache hit rate was actually higher than usual,92%, up from the typical 85%. The CDN was doing its job.

"Cache is fine," Jordan reported. "Actually better than usual. Origin traffic for static assets is down."

Maya was studying the distributed traces. "Look at this," she said, pointing to her screen. "I pulled a slow login request. The trace shows 2.3 seconds total, and look where the time is going."

The trace breakdown showed:
- API Gateway routing: 15ms
- Auth middleware: 2,100ms
- Database query: 4ms
- Response serialization: 3ms

"Auth middleware is the bottleneck," Maya observed. "But what is auth middleware doing for 2.1 seconds?"

#### The Flame Graph Moment

Jordan remembered the continuous profiling they had set up during the observability build-out. "Let me check Pyroscope. If auth middleware is consuming time, the flame graph will show us exactly where."

They pulled up the flame graph for the auth service, filtered to the last 15 minutes. The visualization was stark: a wide, flat bar dominated the graph, consuming 40% of total CPU time. The label read `jwt.RS256.Verify`.

"JWT verification," Alex said, leaning in. "That should not take 2 milliseconds per request, let alone dominating the CPU."

Jordan drilled into the flame graph. Below the RS256 verification, there was another wide bar: `jwks.FetchKeySet`.

"We are fetching the JWKS on every request," Alex realized, their face falling. "Every single JWT validation is making an HTTP call to fetch the public keys. At 800 requests per second, that is 800 HTTP requests per second just for key fetching."

The diagnosis was now clear. As covered in Chapter 11, RS256 uses asymmetric cryptography. Verifying a signature requires the public key, which is distributed via the JSON Web Key Set (JWKS) endpoint. The auth middleware was fetching this key set on every request instead of caching it.

But there was a second problem. Even if JWKS had been cached, RS256 verification itself is computationally expensive,roughly 2 milliseconds per verification on their hardware. At 800 requests per second, that added up to 1.6 CPU seconds per second just for JWT verification. The auth service instances were saturating.

"We have two problems," Alex summarized. "First, we are not caching JWKS. Second, even with caching, RS256 at this volume is going to crush us."

#### Resolution

Elena joined the video call. "What is the user impact?"

Sam had been monitoring social media. "Complaints are starting to appear. 'Collab Docs is slow' and 'Can't log in' are trending on our forums. Customer support is getting tickets."

"What is our path to resolution?" Elena asked.

Alex had already started coding. "I can fix the JWKS caching in about 20 minutes. That addresses the immediate crisis,eliminates the HTTP call on every request."

"What about the RS256 computation overhead?" Maya asked. "Even with caching, we are going to hit CPU limits as we scale."

"That is a bigger fix," Alex replied. "The right answer is edge validation,verify tokens at Cloudflare Workers before requests even reach origin. But that is a multi-day project. For today, we cache JWKS and monitor."

The team agreed on the plan. Alex deployed the JWKS caching fix at T+35 minutes. The cache used a 5-minute TTL with background refresh starting at 4 minutes,ensuring that key rotation would be picked up within one refresh interval while avoiding thundering herd on cache expiration.

Jordan watched the dashboards as the fix rolled out. Login latency dropped from 2,100 milliseconds to 180 milliseconds within 2 minutes of deployment. Error rate fell to 0.3%. The crisis was over.

But the team was not done. Over the following two weeks, Alex implemented edge validation. JWT verification moved to Cloudflare Workers, where tokens were validated at edge locations before requests reached origin. The origin now received only pre-authenticated requests, reducing CPU load dramatically.

#### Business Impact

Elena scheduled a post-incident review for the following morning. The first question was about user impact.

"Total incident duration was 35 minutes," Jordan reported. "During that time, approximately 12,000 login attempts were affected. Of those, about 1,800 timed out or errored,roughly 15%. The remaining 10,200 experienced elevated latency but eventually succeeded."

"How many of those 1,800 were lost conversions?" Elena asked.

Sam had cross-referenced with analytics. "Based on our typical conversion funnel, those 1,800 failed logins likely cost us 50-100 new signups. At our current LTV, that is roughly $5,000 to $10,000 in lost revenue."

"The fix cost us about 4 hours of engineering time," Alex noted. "The edge validation project was another 40 hours. So call it 50 hours total to fully resolve."

Elena did the math. "If we had not fixed this, and it happened every time marketing sent an email, we would lose $10,000 each time. Over a year of monthly campaigns, that is $120,000. The 50-hour investment paid for itself immediately."

The incident reinforced a principle from Chapter 11: authentication performance deserves early attention. Token validation happens on every request,it is always on the critical path. The team added "auth performance review" to their launch checklist for future projects.

**Results (before/after)**:

- **p95 auth latency**: 180ms → 12ms
- **JWKS fetch rate**: 800/second → 1/5 minutes (cached)
- **Origin auth CPU**: 40% of request processing → 5%

<!-- DIAGRAM: Authentication flow before and after optimization: Before shows client -> origin -> JWKS fetch -> validate (showing latency at each step). After shows client -> edge validation -> origin (pre-authenticated) with much lower latency -->

![Authentication Optimization](../assets/ch14-auth-optimization.html)

### Incident Report: The Export Cascade

Two weeks after the authentication incident, Jordan was asleep when their phone started vibrating at 3:17 AM. The alert summary made their stomach drop: "Document service error rate exceeded. 5.2% of requests failing."

Document saves were the core functionality,the reason the product existed. An error rate above 5% meant users were losing work.

Jordan rolled out of bed, grabbed their laptop, and joined the incident channel while still half-asleep. The war room Zoom was already active; Maya had been awake working late and had seen the alerts.

#### Initial Confusion

"I do not understand what I am looking at," Maya said as Jordan joined. "Document service errors are through the roof, but the document service itself looks healthy. CPU is fine, memory is fine, no recent deployments."

Jordan pulled up the document service dashboard on their laptop, squinting at the screen in the dark bedroom. Maya was right,all the service's internal metrics looked normal. CPU at 35%, memory at 60%, no garbage collection pressure, no thread pool saturation.

But the error graph was undeniable. At T+0 (about 15 minutes ago), errors had started climbing. Now they were at 5.2% and still rising.

"What are the errors?" Jordan asked, still trying to wake up fully.

Maya pulled up the error logs. "Database connection timeout. 'Failed to acquire connection within 30000ms.'"

Jordan's mind was clearing now. "The database is fine,I can see the metrics. It is not overloaded. So why are we timing out on connection acquisition?"

#### Wrong Hypothesis #1: Document Service Bug

"Did anyone deploy anything to document service recently?" Jordan asked.

Sam, who had just joined the call, checked the deployment log. "Nothing. Last deploy was four days ago, and we have been running clean since then."

"What about database schema changes? Index modifications?"

"Nothing. Database has been untouched."

Maya was digging through the traces. "Look at this. I found a failing document save. The trace shows the document service waiting 30 seconds for a database connection, then timing out. But there is no actual database query,it never gets the connection in the first place."

"Where are all the connections going?" Jordan wondered aloud.

#### Wrong Hypothesis #2: Database Failure

Priya had joined the call, looking bleary-eyed through her camera. "Maybe the database is dropping connections? Some kind of connection limit issue?"

Jordan checked the PostgreSQL metrics. The database showed 95 active connections,elevated, but well below the 200 connection limit. More importantly, query latency was normal. The database itself was fine.

"PostgreSQL is healthy," Jordan confirmed. "It is accepting connections and running queries at normal speed. The bottleneck is before the query,we are exhausting our connection pool somewhere."

Maya had an idea. "What if something else is holding the connections? We share that connection pool across multiple services."

Jordan felt a cold realization forming. "What services share the document service's connection pool?"

"Document service, obviously," Maya listed. "And... the export workers. They read document content for PDF generation."

#### The Cascade Discovery

Jordan pulled up the export service metrics. And there it was.

The export worker threads were all blocked. Every single one,50 threads,was in "waiting" state. The queue of pending export jobs had grown to 200, far above the normal 5-10.

"When did this start?" Jordan asked.

"About 20 minutes ago," Maya replied, checking the timeline. "Right before document service errors started appearing."

Jordan traced an individual export request. The worker had made an HTTP call to the third-party PDF generation service at 2:57 AM. That call was still waiting,it had been waiting for 20 minutes.

"The PDF service is down," Jordan realized. "Our export workers are hung waiting for a response that is never coming."

Priya made the connection. "And while they are hung, they are holding database connections. For reading the document content before sending it to the PDF service. Those connections are never released."

The full cascade was now clear:

1. Third-party PDF service goes down at approximately 2:55 AM
2. Export workers make HTTP calls to PDF service and hang waiting for response
3. Each hung worker holds a database connection (acquired for reading document content)
4. With 50 workers hung and each holding a connection, 50 connections are unavailable
5. The document service's connection pool (sized at 100) is now 50% consumed by hung export workers
6. Under normal document save load, the remaining 50 connections are not enough
7. Document saves start timing out waiting for connections

"Export is supposed to be async," Sam said. "How did an async service failure take down document saves?"

"Shared resources," Maya explained. "The export workers share a database connection pool with the document service. We never isolated them. A problem in export cascaded to document saves through the shared pool."

#### Emergency Mitigation

"What is the fastest way to stop the bleeding?" Elena asked. She had joined the call silently five minutes earlier.

"Restart the export workers," Priya said. "That will release the held connections immediately. Document saves will recover."

Jordan hesitated. "But then users' export jobs will be lost. They will have to re-request."

"How many users versus how many export jobs?" Elena asked.

Jordan checked. "We have about 800 active users right now. There are 200 pending exports. The 800 users cannot save their work; the 200 exports can be re-requested."

"Restart the workers," Elena decided. "Saving user work takes priority."

Jordan triggered a rolling restart of the export workers. Within 60 seconds, document save errors dropped to zero. The crisis was over, but the work was just beginning.

#### Root Cause Analysis

At 5 AM, with the immediate crisis resolved, the team gathered for a real-time post-mortem. Priya had whiteboarded the cascade on her screen.

"We made a classic mistake," Priya said. "We assumed that making export asynchronous meant it was isolated. But isolation is not automatic,we have to explicitly design for it."

Maya identified the contributing factors:

1. **Shared connection pool**: Export workers and document service both used the same database connection pool. Any resource contention in export could starve document service.

2. **Long timeout on external service**: The PDF service HTTP call had a 30-second timeout. That is reasonable for a single request, but when 50 workers all hit a 30-second timeout simultaneously, connections are held for 30 seconds each.

3. **No circuit breaker**: There was no mechanism to detect that the PDF service was failing and stop sending requests. The workers kept trying, kept hanging, kept holding connections.

4. **Hidden coupling**: The relationship between export and document save was not obvious from the architecture diagram. The shared resource created invisible coupling.

#### The Fix: Bulkhead Isolation and Circuit Breakers

Over the following week, the team implemented multiple resilience patterns from Chapter 10:

**Bulkhead isolation**: Export workers received their own dedicated database connection pool, completely separate from the document service pool. Priya sized it at 30 connections,enough for normal export load, but even if every connection was exhausted, document saves would be unaffected.

"This is like the bulkheads in a ship," Maya explained to the team. "If one compartment floods, the water does not spread to other compartments. Export failure no longer spreads to document saves."

**Circuit breaker on PDF service**: When the PDF service fails 50% of requests over a 10-second window, the circuit opens. Subsequent export attempts fail immediately with a clear error message rather than waiting 30 seconds to timeout. The circuit attempts recovery every 60 seconds by letting a single request through.

**Timeout reduction**: Export timeouts were reduced from 30 seconds to 5 seconds. If a PDF service call does not complete in 5 seconds, something is wrong,hanging longer does not help.

**Async retry with backoff**: Failed exports were automatically retried with exponential backoff: first retry after 1 second, then 2, then 4, up to three attempts. Users received a notification if all retries failed, explaining that export would be available once the service recovered.

**Dead letter queue monitoring**: Failed exports moved to a dead letter queue for investigation. Jordan added an alert if the DLQ depth exceeded 100 items,a sign that something systematic was wrong.

#### Business Impact and Learning

At the post-incident review, Elena asked the hard questions.

"How many users were affected?"

Jordan had the numbers. "Incident duration was 47 minutes from first impact to resolution. During that time, approximately 2,400 document save attempts were made. About 140 failed,a 5.8% failure rate. Those 140 represent actual user work that may have been lost if they closed the browser."

"What was the business cost?"

Sam had contacted customer support. "We received 23 support tickets related to the incident. Three customers mentioned it on social media. No enterprise customers were affected,most of them were not active at 3 AM."

"And the cost of the fix?"

"About 40 engineering hours for the resilience improvements," Priya estimated. "Connection pool separation, circuit breaker, monitoring,call it a week of focused work."

Elena nodded. "The lesson here is one we should have learned during design: non-critical does not mean non-impactful. Export is a nice-to-have feature, but its failure took down our core functionality. Every external dependency, every shared resource, needs to be evaluated for cascade potential."

The team added three items to their architectural review checklist:

1. **Identify all shared resources** (connection pools, thread pools, queues) and evaluate coupling
2. **Add circuit breakers to all external service calls** with appropriate timeouts
3. **Design bulkheads** around any non-critical functionality that could affect critical paths

**Results**:

- Export service failures no longer impact document saves
- Circuit opens within 10 seconds of PDF service degradation
- Mean time to user notification of export failure: 45 seconds (previously: 90+ seconds waiting for timeout)
- Dead letter queue provides visibility into systematic failures

The incident reinforced a principle from Chapter 10: assume failures will happen and design systems to contain their blast radius.

### Incident Report: The Viral Document

One month after launch, Collab Docs experienced an incident unlike the others,not a failure, but unexpected success. This was the incident that would force the team to fundamentally rethink how stateful services scale.

#### The Anomaly

Jordan noticed it first,not from an alert, but from an unusual pattern on their dashboard. It was a Wednesday afternoon, and they were checking metrics between meetings when something caught their eye.

"That is strange," Jordan muttered, leaning closer to the screen. The document connections graph, which typically showed a smooth curve across thousands of documents, had a single anomalous spike. One document had 200 concurrent connections and climbing. The next highest document had 12.

Jordan opened Slack. "Anyone know what's going on with document ID 847291? It's getting unusual traffic."

Sam responded within minutes. "Let me check... Oh. Oh wow. Someone's live-tweeting writing a product announcement using our platform. The tweet has 10,000 retweets."

Jordan pulled up Twitter. The tweet from a startup founder read: "Watch us write our Series A announcement in real-time. No edits hidden, no drafts,just raw startup chaos. Link in replies."

The link led directly to a Collab Docs document.

#### The Slow Deterioration

Jordan shifted to monitoring mode, watching the dashboards as the situation developed. The document's connection count climbed steadily: 200... 500... 800. Each new viewer added another WebSocket connection, another presence subscription, another set of cursor position updates.

At 500 concurrent viewers, the system was handling the load. p95 latency was at 120 milliseconds,elevated but acceptable.

At 1,500 viewers, Jordan noticed the first warning signs. Sync latency for that specific document had climbed to 800 milliseconds. Users started commenting on Twitter: "Anyone else seeing lag?"

"Priya, Maya," Jordan pinged. "I need you to look at the sync service. We have a document with 1,500 concurrent viewers and latency is degrading."

Priya pulled up the metrics. "Sync service looks... actually, it looks mostly fine. CPU is at 40%, memory is at 60%. But wait,that is the average across instances. Let me check individual instances."

The individual instance view told a different story. Sync service instance sync-3 showed 85% memory utilization and climbing. The other instances were at 30%.

"Why is all the load on one instance?" Maya asked.

Jordan knew immediately. "Sticky sessions. Our load balancer uses connection affinity based on document ID to ensure all users on the same document hit the same instance for coordinated updates. It is supposed to improve consistency. But it means all 1,500 viewers of this one document are landing on sync-3."

At 3,000 viewers, the situation was critical. Sync latency for the document exceeded 5 seconds. Users reported "ghost cursors",seeing cursor positions from minutes ago. The presence system was so backed up that it showed users who had already left.

Twitter was filled with screenshots. "Is Collab Docs broken?" "The cursors are not moving." "I see 3,000 people typing but nothing is updating."

#### Wrong Hypothesis #1: Network Saturation

"It has to be network," Priya suggested. "3,000 users receiving presence updates every 100 milliseconds,that is 30,000 messages per second for one document. We must be saturating the network."

Jordan checked the network metrics for sync-3. Inbound: 50 Mbps. Outbound: 200 Mbps. The instance had a 1 Gbps connection.

"Network is fine," Jordan reported. "We are nowhere near saturation. The bytes are getting through,it is the processing that cannot keep up."

#### Wrong Hypothesis #2: Redis Overload

Maya looked at the Redis metrics. "Every presence update publishes to Redis and fans out to subscribers. At 30,000 updates per second, maybe Redis is the bottleneck?"

Jordan checked. Redis cluster was at 15% CPU. Pub/sub message throughput was elevated but well within capacity.

"Redis is handling it fine," Jordan confirmed. "The problem is on the receiving end. Sync-3 is subscribed to the document's channel and receiving 30,000 messages per second, but it cannot process them fast enough."

#### The Memory Discovery

At 4,500 concurrent viewers, sync-3's memory utilization hit 98%. The instance was allocating memory faster than garbage collection could reclaim it.

"We are about to lose this instance," Jordan warned. "Memory is at 98% and climbing. When it hits the limit, Kubernetes will OOM-kill the pod."

Elena had been watching silently. "What happens when we lose the instance?"

"4,500 WebSocket connections drop simultaneously," Maya said grimly. "Every user gets disconnected and immediately tries to reconnect. They will land on the remaining sync instances,which are not prepared for a sudden influx of 4,500 connections."

At T+60 minutes, sync-3 hit the memory limit. The Kubernetes kubelet killed the process. 4,500 users saw their browsers show "Connection lost. Reconnecting..."

And then they all reconnected.

#### The Reconnection Storm

The remaining sync instances,sync-1, sync-2, sync-4, and sync-5,suddenly received a flood of connection requests. Within 10 seconds, they were all at 70% memory utilization and climbing.

"They are going to cascade," Priya said. "If we lose another instance, the remaining three take the load. Then we lose another. This is a cascade in progress."

Jordan acted fast. "I am manually scaling the sync service to 10 instances. That will dilute the load."

But the scale-up took 45 seconds,time for Kubernetes to schedule new pods, for containers to start, for health checks to pass. During those 45 seconds, sync-2 hit 95% memory utilization.

The new instances came online just in time. Load rebalanced across 10 instances. Memory utilization dropped to 50% across the fleet. The document was back online,but the damage was visible on Twitter.

"Collab Docs crashed while 4,500 people were watching," one user posted. "Not a great look for a 'real-time collaboration' platform."

#### Understanding the Root Cause

That evening, the team gathered for an extended post-mortem. Maya had prepared diagrams showing exactly what had happened.

"Our architecture made several implicit assumptions," Maya explained. "First, we assumed connections would be distributed across many documents. A typical user has 1-3 documents open. We designed for that,not for 4,500 users all opening the same document."

"Second, we assumed sticky sessions would improve performance by keeping document state local. And it does,for normal usage. But it also means all the load for a hot document concentrates on a single instance."

Priya added the technical details. "Each WebSocket connection consumes memory: the connection buffer, the presence state, the pub/sub subscription. At 4,500 connections, that is roughly 2GB of memory for connection state alone. Add the presence update processing,every 100 milliseconds per user, times 4,500 users,and the instance cannot keep up."

"The presence system was never designed for this scale," Jordan admitted. "At 100ms update intervals with 4,500 users, we were trying to broadcast 45,000 position updates per second for a single document. That is an order of magnitude beyond what we tested."

Alex raised a security concern. "There is also a potential attack vector here. A malicious actor could create a document, share it widely, and intentionally crash our sync service. We have no limits."

#### The Architectural Redesign

The fix required fundamental changes to how the sync service worked. The team designed a layered solution over the following two weeks.

**Document-based connection sharding**: Instead of sticky sessions routing all connections for a document to a single instance, the sync service now distributes connections across a "shard group" of 3 instances per document. The instances in a shard group coordinate directly using a lightweight gossip protocol rather than all publishing/subscribing through Redis. This bounds the fan-out: each instance receives one-third of the connections and presence updates.

"The key insight," Maya explained, "is that we do not need every instance to see every update. We just need the instances serving a particular document to coordinate among themselves."

**Presence throttling**: For documents with more than 100 concurrent viewers, presence updates switch from real-time to sampled mode. Instead of broadcasting 4,500 cursor positions 10 times per second, the system samples 50 representative positions and updates every 500 milliseconds.

"Users do not need to see 4,500 individual cursors," Priya reasoned. "At that scale, it is visual noise. A heatmap of activity areas plus a viewer count serves the same purpose."

**Connection limits with graceful degradation**: Documents now have tiered connection modes:
- 1-100 viewers: Full real-time mode (everyone can edit, all cursors visible)
- 101-500 viewers: Reduced presence mode (editing allowed, sampled cursors)
- 501+ viewers: View-only mode for new connections (existing editors keep full access)

The UI explains the mode to users: "This document has 4,500+ viewers. You're in view-only mode with periodic updates. Join the wait list to edit."

**Predictive scaling**: When a document's connection count crosses 100, 500, or 1,000, the system proactively scales the shard group handling that document. By the time a document hits 1,000 viewers, its shard group has already expanded from 3 to 9 instances.

#### The Positive Outcome

When the team presented the post-mortem to Elena, they expected criticism. Instead, she smiled.

"You know what the irony is?" Elena said. "This incident was the best marketing we could have asked for. The startup's tweet reached 2 million people. Half of them now know Collab Docs exists. TechCrunch wrote about it,'Startup launches product with 4,500 people watching live.' They mentioned that we crashed for 2 minutes, but they also mentioned that we recovered."

Sam pulled up the signup numbers. "New user registrations spiked 400% in the 48 hours after the incident. Some of that attention converted."

"So we turned a near-disaster into publicity," Jordan observed.

"Only because you recovered quickly," Elena clarified. "If we had been down for an hour, the narrative would have been 'Collab Docs cannot handle load.' Two minutes of disconnection followed by recovery reads as 'Collab Docs handled an unexpected viral moment.' The difference is in how fast you responded."

Maya summarized the technical learning. "The fundamental lesson is that stateful services require different scaling strategies than stateless APIs. Horizontal scaling works when load can be distributed,but when load concentrates on a single entity, you need entity-aware sharding, graceful degradation, and predictive scaling. We designed for the average case and got hit by the extreme case."

"Every system has an extreme case," Jordan added. "The question is whether you design for it proactively or learn about it reactively. We learned reactively. Next time, we will ask earlier: what happens when all the load lands on one entity?"

**Results**:

- Single document can now support 10,000+ concurrent viewers without degradation
- Sync latency remains under 200ms even for viral documents
- Memory usage per instance stays bounded regardless of document popularity
- Graceful degradation preserves core functionality under extreme load
- Connection limits prevent intentional or accidental overload

<!-- DIAGRAM: Viral document scaling showing: Before (single instance overwhelmed, all 4500 connections) vs After (document sharding across instance group with connection limits and presence throttling) -->

![Viral Document Scaling](../assets/ch14-viral-document.html)

## Part IV: Scaling to Success

### Growing Pains: Auto-Scaling Strategies

Three months post-launch, Collab Docs reached 50,000 daily active users. Traffic patterns had stabilized into a predictable diurnal shape: low overnight, ramping up at 9 AM local time, peak around 2 PM, and gradual decline through the evening.

The fixed infrastructure provisioned for launch was no longer optimal. Overnight, servers sat idle. During peaks, CPU utilization approached 80%.

Maya proposed implementing auto-scaling, following the principles from Chapter 9. "Our services are stateless,they store no local state that would be lost on termination. We can scale horizontally based on demand."

The team configured Kubernetes Horizontal Pod Autoscaler (HPA) with the following triggers:

- **Scale up**: Average CPU > 60% for 2 minutes
- **Scale down**: Average CPU < 30% for 5 minutes
- **Minimum replicas**: 3 (for availability)
- **Maximum replicas**: 20 (budget constraint)

For the WebSocket-based sync service, CPU was not the right metric,connections consumed memory, not CPU. The team configured custom metrics scaling:

- **Scale up**: Average connections per pod > 8,000
- **Scale down**: Average connections per pod < 4,000

The asymmetric timing (fast scale-up, slow scale-down) prevented thrashing during traffic fluctuations.

Jordan also implemented predictive scaling for known traffic spikes. When marketing scheduled campaigns, the team pre-scaled infrastructure 30 minutes before the expected traffic, avoiding the latency penalty of reactive scaling.

**Results**:

- **Infrastructure cost**: 35% reduction through off-peak scaling
- **p95 latency during peaks**: Remained under 150ms (previously approached 200ms before manual intervention)
- **Zero manual scaling interventions** in the three months following implementation

### Enterprise Features: Per-Tenant Rate Limiting

Success brought a new challenge: enterprise customers. A Fortune 500 company wanted to deploy Collab Docs for 5,000 employees in a dedicated workspace. This was exciting for the business but concerning for engineering.

"What happens when their entire company logs in at 9 AM?" Jordan asked. "5,000 users hitting us simultaneously could impact other customers."

Alex proposed per-tenant rate limiting, a pattern from Chapter 10 implemented at the edge. Each workspace would have its own rate limit, preventing any single customer from monopolizing system capacity.

The implementation used sliding window rate limiting at Cloudflare Workers:

- **Default limit**: 100 requests per second per workspace
- **Enterprise limit**: 500 requests per second (configurable per contract)
- **Burst allowance**: 2x the limit for 10-second windows
- **Response**: HTTP 429 with Retry-After header when limits exceeded

"Rate limiting is not just about protection," Alex explained. "It is also about fairness. Without limits, one customer's traffic spike degrades experience for everyone else."

The team also implemented API quotas for expensive operations like document export:

- **Free tier**: 100 exports per month
- **Business tier**: 1,000 exports per month
- **Enterprise tier**: Unlimited (but rate-limited)

These limits were enforced at the application layer, with usage tracked in PostgreSQL and cached in Redis for fast lookup.

### 90-Day Review: Measuring Success

Three months after full launch, Elena called a formal review meeting. The entire team gathered in the same glass-walled conference room where the project had begun,the one where Elena had told them the company was betting its future on Collab Docs.

The mood was different now. Where there had been anxiety, there was cautious confidence. Where there had been uncertainty, there was data.

"Let us start with the numbers," Elena said. "Jordan, walk us through where we are."

#### The Dashboard Walkthrough

Jordan connected their laptop to the conference room display. The Grafana dashboard showed three months of production data, annotated with incident markers and optimization deployments.

"Our original target was 100,000 daily active users within six months," Jordan began. "We are at 85,000 after three months. On track, potentially ahead of schedule."

The traffic graph showed a healthy diurnal pattern,low overnight, peak in the afternoon, gradual decline. But more importantly, it showed growth. Week over week, the peak was climbing.

"Now let us talk about SLOs," Jordan continued. They switched to the SLO dashboard, which showed four green indicators.

**Performance Against SLOs**:

| Metric | Target | Actual | Status |
|--------|--------|--------|--------|
| Availability | 99.9% | 99.95% | Exceeded |
| p95 Latency | < 200ms | 78ms | Exceeded |
| Error Rate | < 0.1% | 0.03% | Exceeded |
| Sync Propagation | < 1000ms | 450ms | Exceeded |

"We are exceeding every SLO," Jordan noted. "Availability at 99.95%,that is about 4.5 hours of downtime budget per year, and we have used less than an hour across three incidents. p95 latency at 78 milliseconds is well under our 200 millisecond target. Error rate at 0.03% is three times better than target."

Elena leaned forward. "What about the business metrics? What does this performance mean for the company?"

Sam had the numbers. "User conversion from signup to active use is 34%,significantly above the industry benchmark of 20-25%. More importantly, our churn rate is 2.1% monthly, compared to 5-8% for competitors. Users are not leaving because of performance issues."

"We ran a user survey last week," Sam continued. "When asked 'How would you rate the responsiveness of Collab Docs?', 78% said 'Excellent' and 19% said 'Good'. Only 3% had any performance complaints."

#### The Cost Story

Maya presented the infrastructure analysis. "Elena, you asked us six months ago to build something fast. But you also need it to be efficient. Let me show you where we are on costs."

She pulled up the infrastructure spending dashboard. "Our original projection was $0.15 per user per month based on industry benchmarks. We are actually at $0.09 per user per month,40% lower than projected."

"How?" Elena asked.

"Several factors," Maya explained. "First, the auto-scaling implementation. We are not paying for peak capacity 24/7,we scale down during off-peak hours. That alone saves 35%."

"Second, the edge validation work Alex did after the authentication incident. By moving JWT verification to the edge, we reduced origin compute requirements significantly. Origin CPU dropped 40%."

"Third, the observability investment. Every optimization we made was targeted because we could see exactly where time was being spent. We never wasted cycles optimizing the wrong thing."

#### The Incident Retrospective

Elena pulled up a chart she had prepared,a timeline of the three major incidents annotated with resolution times and business impact.

"Let us talk about what went wrong," she said. "Three incidents in three months. What did we learn?"

Jordan walked through each one.

"The authentication storm: 35 minutes total duration, approximately $5,000-10,000 in lost conversions, root cause identified in under 5 minutes via flame graphs. We shipped a fix the same day and a permanent solution within two weeks."

"The export cascade: 47 minutes total duration, approximately 140 failed document saves affecting active users. Root cause identified in 20 minutes via trace analysis. We implemented circuit breakers and bulkhead isolation within a week."

"The viral document: 2 minutes of hard disconnection, widespread degradation before that. Positive media coverage despite the incident. Led to a fundamental redesign of how we handle hot documents."

Elena nodded. "What is the common thread?"

Maya answered. "In every case, our observability infrastructure was the difference between a minor incident and a major outage. Without flame graphs, the auth incident could have taken hours to diagnose. Without traces, the cascade would have been a mystery. We invested two weeks in observability before writing features, and that investment has paid dividends in every incident."

#### The Soak Testing Retrospective

Jordan raised a point that had been on their mind. "I want to highlight something that did not become an incident,because we caught it in testing."

They pulled up the memory graph from the pre-launch soak test. "Remember this? The memory leak in the WebSocket disconnection handler. We were leaking 150 megabytes per hour."

The graph showed the steady climb over 8 hours, approaching the container memory limit.

"If we had not run that soak test, we would have launched with a time bomb," Jordan continued. "At production load, instances would have crashed every 12-18 hours. We would have woken up Tuesday morning,two days after launch,to find half our sync service instances dead."

"Instead," Maya added, "we spent three hours finding and fixing the leak before a single user was affected. The soak test caught what unit tests and load tests never could."

Elena made a note. "Soak testing before every major release. That is going in our launch checklist."

#### The Next Bottleneck

With the review of past performance complete, the team turned to the future.

"Where is our next problem?" Elena asked.

Priya pulled up a specific metric. "Document search. p95 search latency has crept up to 350 milliseconds,above our general 200 millisecond SLO. It was fine at thousands of documents, but we now have 800,000 documents in the system."

The search implementation used PostgreSQL LIKE queries, which performed a sequential scan on the document content. As the corpus grew, search slowed linearly.

"What are our options?" Elena asked.

Maya outlined the choices. "We can add Elasticsearch for full-text search,it is purpose-built for this use case. Or we can explore pgvector for semantic search, which would let users search by meaning rather than just keywords. Or we can do both: Elasticsearch for keyword search, pgvector for 'find documents similar to this one.'"

"What is the recommendation?"

"Start with Elasticsearch," Maya said. "It solves the immediate problem. pgvector is compelling for the future, but keyword search is table stakes,we need to fix that first."

"How long?"

"Two weeks to implement, one week to load test and tune. We can have it in production in a month."

Elena nodded. "Approved. Same process as before: measure first, optimize with data, validate the improvement."

#### The Closing Observations

As the meeting wound down, Elena asked each team member for their key takeaway.

"Observability is not optional," Jordan said. "Every minute we spent on tracing and metrics saved us hours in incident response. If you can only afford one thing, afford observability."

"Isolation matters more than you think," Priya added. "We assumed async was isolated. It was not. Every shared resource is a potential cascade vector."

"Performance and security can coexist," Alex said. "The authentication work proved it. RS256 at the edge is both secure and fast. You do not have to choose."

"User research complements metrics," Sam observed. "Our numbers showed 78ms latency. User surveys showed 78% 'Excellent' ratings. Both mattered for the business case."

Maya went last. "The empirical approach works. We set SLOs before writing code. We measured before optimizing. We formed hypotheses and tested them. Every decision had data behind it. That discipline,not any single optimization,is why we succeeded."

Elena closed the meeting. "Six months ago, I told you the company was betting on this project. You delivered. Not perfectly,we had incidents,but you responded to those incidents with systemic fixes rather than patches. The system is faster, more reliable, and cheaper than we projected."

She paused. "And most importantly, we can prove it. Because we measured everything."

#### Key Metrics at 90 Days

- **Daily active users**: 85,000 (approaching 100,000 target)
- **Peak concurrent WebSocket connections**: 18,000
- **Average API throughput**: 1,200 RPS, peak 2,800 RPS
- **Permission cache hit rate**: 98%
- **Infrastructure cost per user**: 40% lower than initial projections
- **Mean time to incident resolution**: 35 minutes
- **SLO compliance**: 100% (all targets exceeded)

## Common Pitfalls

The Collab Docs team made mistakes along the way. Here are the lessons they learned,and a few they avoided by investing in testing and observability:

- **Skipping observability to move faster**: The team almost delayed tracing implementation. Had they done so, the authentication and cascade incidents would have taken hours to diagnose instead of minutes. Observability is not overhead,it is infrastructure. The two-week investment saved weeks of debugging time across three incidents.

- **Skipping soak testing to meet deadlines**: The memory leak in the WebSocket disconnection handler would have crashed production instances every 12-18 hours. No load test would have caught it,only the 8-hour soak test revealed the slow leak. Soak testing is not optional for stateful services.

- **Assuming async means isolated**: Moving export to async processing did not automatically isolate it from critical paths. Shared resources (connection pools, thread pools, queues) can still create coupling. Explicit bulkhead isolation is required. The word "async" is not a magic incantation for isolation.

- **Underestimating authentication overhead**: Token validation seems simple but executes on every request. At scale, "2 milliseconds per request" becomes significant. Auth performance deserves dedicated attention early, not as an afterthought. The authentication storm taught the team that RS256 without JWKS caching is a ticking time bomb.

- **Sizing pools for average, not peak**: Connection pools sized for average load will be exhausted during traffic spikes,exactly when you need them most. Size for peak, with headroom. The first load test failure at 5,000 users was a direct result of sizing for development-time concurrency.

- **Treating rate limiting as purely defensive**: Rate limiting protects systems from overload, but it also provides fairness guarantees to customers. Design limits that users can understand and plan around. Rate limits should be part of the API contract, not a hidden safety valve.

- **Optimizing without baselines**: The team's load testing before launch established baselines that made post-launch optimization tractable. Without baselines, "is this faster?" becomes guesswork. More importantly, without baselines, "is this normal?" becomes unanswerable during incidents.

- **Ignoring the cascade potential of non-critical services**: The PDF export service was "non-critical," but its failures cascaded to critical document saves. Every dependency, critical or not, needs failure isolation. The question is not "is this critical?" but "can this affect something critical?"

- **Assuming stateless scaling patterns apply to stateful services**: The team's stateless API services scaled beautifully with random load balancing. The stateful WebSocket sync service did not. When the viral document hit, load concentrated on a single instance. Stateful services need entity-based sharding, connection limits, and graceful degradation,patterns fundamentally different from stateless horizontal scaling.

- **Treating incidents as failures rather than learning opportunities**: Each incident revealed a gap in the architecture. The authentication storm exposed missing JWKS caching. The export cascade exposed missing bulkheads. The viral document exposed missing entity-aware scaling. The team responded with systemic fixes, not patches,and the system improved each time.

- **Setting alert thresholds without understanding traffic patterns**: Alerts based on absolute thresholds fire during normal diurnal variation. The team established baselines first, then set thresholds relative to expected patterns for each time of day. An alert that fires every night at 3 AM when traffic is naturally low is worse than useless,it trains on-call engineers to ignore pages.

## Summary

- **Define SLOs before writing code**: The team's latency budgets and availability targets guided every architectural decision. Without clear targets, optimization is aimless. SLOs also enabled meaningful alerting,alerts based on error budget consumption rather than arbitrary thresholds.

- **Build observability as foundation, not afterthought**: Distributed tracing, metrics, structured logging, and continuous profiling enabled rapid diagnosis of every incident. The two-week investment paid dividends throughout the project. Flame graphs were the key to diagnosing the authentication storm in under five minutes.

- **Establish baselines before production**: Load testing and soak testing established baseline metrics that made "is this normal?" answerable during incidents. Without baselines, anomaly detection is impossible and optimization is guesswork.

- **Soak testing catches what other testing misses**: The memory leak discovered during the 8-hour soak test would have crashed production instances within two days of launch. Resource leaks accumulate slowly,only extended testing reveals them.

- **Make database decisions based on access patterns**: The polyglot approach (PostgreSQL for ACID, Redis for ephemeral data) matched each data type to the right storage engine, accepting operational complexity as a trade-off.

- **Cache strategically with explicit invalidation**: Permission caching with event-driven invalidation achieved high hit rates while maintaining security consistency. Caching without an invalidation strategy is a time bomb.

- **Move non-critical work off the critical path**: Async export processing kept slow operations from impacting API latency. The transactional outbox pattern ensured reliability. But remember: async does not mean isolated,bulkheads are still required.

- **Implement resilience patterns proactively**: Circuit breakers and bulkhead isolation prevented cascade failures. These patterns are not premature optimization,they are essential infrastructure for production systems. The export cascade proved that failures in "non-critical" services can take down critical functionality.

- **Test at scale before users do**: Load testing revealed connection pool limits and established baselines. Problems found in load tests are cheaper than problems found in production. The cost of the test infrastructure was trivial compared to the cost of the incidents it prevented.

- **Push work to the edge when possible**: Edge caching for static assets and edge authentication validation reduced origin load and improved latency for users worldwide. Edge validation turned the authentication storm from a potential recurring problem into a solved problem.

- **Design for hot spots in stateful systems**: Stateless services distribute load randomly; stateful services concentrate it. The viral document incident showed that entity-based sharding, connection limits, and graceful degradation are essential when load can concentrate on a single entity.

- **Business impact framing improves stakeholder trust**: Elena could explain every incident in terms of users affected and revenue impact. This transparency built trust with the board rather than eroding it. Performance is a business metric, not just a technical one.

- **Treat incidents as learning opportunities**: Each incident revealed architectural gaps that systemic fixes addressed. The team emerged from three incidents with a more resilient system than they could have designed proactively. Incidents are expensive lessons,extract maximum value from them.

## References

1. **Nielsen Norman Group**. "Response Time Limits: Article by Jakob Nielsen." https://www.nngroup.com/articles/response-times-3-important-limits/

2. **Honeycomb**. "Observability Maturity Community Research." https://www.honeycomb.io/observability-maturity-community-research

3. **Google SRE Book** (2016). "Monitoring Distributed Systems." https://sre.google/sre-book/monitoring-distributed-systems/

4. **Dean, J., & Barroso, L. A.** (2013). "The Tail at Scale." Communications of the ACM, 56(2), 74-80. https://dl.acm.org/doi/10.1145/2408776.2408794

5. **Nygard, M.** (2018). "Release It! Design and Deploy Production-Ready Software, 2nd Edition." Pragmatic Bookshelf.

6. **Kleppmann, M.** (2017). "Designing Data-Intensive Applications." O'Reilly Media.

7. **Amazon** (2006). Internal research on latency impact on sales, widely cited in industry. Approximately 1% sales reduction per 100ms additional latency.

8. **Google** (2017). "The Need for Mobile Speed." https://www.thinkwithgoogle.com/marketing-strategies/app-and-mobile/mobile-page-speed-new-industry-benchmarks/

9. **Akamai** (2017). "The State of Online Retail Performance." Research showing 100ms delay reduces conversion rates by 7%.

10. **Google SRE Workbook** (2018). "Alerting on SLOs." https://sre.google/workbook/alerting-on-slos/

## Next: [Appendix: Code Examples](./15-appendix-code-examples.md)

The next chapter provides complete, runnable implementations of the patterns referenced throughout this book, including the permission caching and circuit breaker implementations used in the Collab Docs case study.
