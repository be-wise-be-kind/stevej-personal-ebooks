# Chapter 8: Asynchronous Processing and Queuing

![Chapter 8 Opener](../assets/ch08-opener.html)

\newpage

## Overview

Not every operation in an API request needs to complete before we return a response to the client. Email notifications, analytics tracking, image processing, and audit logging can often happen after we have acknowledged the user's request. By moving work off the critical path, we reduce latency for the client while improving overall system throughput and resilience.

This chapter explores the patterns and technologies that enable asynchronous processing. We will examine the fundamental trade-offs between synchronous and asynchronous approaches, dive into message queue technologies like RabbitMQ, Kafka, and SQS, and learn how to build reliable systems with backpressure, retry strategies, and dead letter queues. We will also cover critical production patterns: the transactional outbox for reliable message publishing, sagas for distributed transactions, schema evolution for maintaining compatibility, and stream processing for real-time analytics. These patterns form the foundation of event-driven architecture, enabling systems that scale gracefully under load.

The empirical approach applies here as well: we measure queue depth, consumer lag, processing latency, and error rates. Asynchronous systems introduce new failure modes (messages can be lost, duplicated, or processed out of order) and our observability must account for these possibilities.

## Key Concepts

### Synchronous vs Asynchronous Trade-offs

The decision between synchronous and asynchronous processing depends on several factors: latency requirements, consistency needs, failure handling complexity, and user experience expectations.

**Synchronous processing** provides immediate feedback. When a user submits an order, they know instantly whether it succeeded or failed. The response includes all relevant data. The implementation is straightforward: errors propagate naturally, transactions maintain consistency, and debugging follows a linear request path.

**Asynchronous processing** decouples the request from the work. The API accepts the request, validates it, enqueues the work, and returns immediately. This approach excels when:

- The operation takes significant time (processing videos, generating reports, sending bulk notifications)
- The client does not need the result immediately
- The work can be retried independently of the original request
- Load spikes would otherwise overwhelm downstream systems

The trade-off is complexity. Asynchronous systems require additional infrastructure (queues, workers), introduce eventual consistency, and complicate error handling. A failed background job cannot return an error to the original HTTP request, which has already completed. For a practical implementation of this pattern, including job enqueueing and reliable consumer processing (see Example 8.1).

LinkedIn's engineering team documented their experience moving notification processing from synchronous to asynchronous paths, noting substantial reductions in API response times while maintaining delivery reliability through robust retry mechanisms [Source: LinkedIn Engineering Blog, 2019].

### Message Queue Fundamentals

Message queues provide the backbone for asynchronous communication. A **producer** sends messages to a **broker**, which stores them until a **consumer** processes them. This decoupling enables:

- **Temporal decoupling**: Producers and consumers do not need to be available simultaneously
- **Load leveling**: Queues absorb traffic spikes, allowing consumers to process at a steady rate
- **Failure isolation**: Consumer failures do not impact producers

#### Messaging Patterns: Point-to-Point vs Pub/Sub

Two fundamental messaging patterns serve different use cases:

**Point-to-point (queue)** delivers each message to exactly one consumer. Multiple consumers can compete for messages, but each message is processed once. This pattern suits task distribution where work should not be duplicated, such as order processing or job queues.

**Publish/subscribe (topic)** delivers each message to all interested subscribers. When an "OrderPlaced" event occurs, the inventory service, notification service, and analytics service each receive their own copy. This pattern enables loose coupling: publishers do not know or care who consumes their events.

Most message brokers support both patterns. Kafka topics with consumer groups provide both: messages within a partition go to one consumer in the group (point-to-point within the group), but multiple consumer groups each receive all messages (pub/sub across groups).

#### Delivery Guarantees

Message systems offer different delivery semantics:

**At-most-once**: Messages may be lost but never duplicated. The broker delivers the message and immediately marks it complete. If the consumer crashes during processing, the message is lost. This approach suits scenarios where occasional loss is acceptable (metrics, non-critical logs).

**At-least-once**: Messages are never lost but may be duplicated. The consumer must acknowledge processing before the broker removes the message. If acknowledgment fails, the broker redelivers. This is the most common guarantee and requires idempotent consumers.

**Exactly-once**: Each message is processed exactly once. This requires coordination between the broker and consumer, often through transactional processing. Kafka provides exactly-once semantics through its transactional API, though with additional complexity and latency [Source: Apache Kafka Documentation].

#### Consumer Groups and Partitioning

Kafka and similar systems use **consumer groups** to enable parallel processing with ordering guarantees:

- Each partition is assigned to exactly one consumer within a group
- Multiple consumer groups receive all messages independently
- Adding consumers to a group increases parallelism (up to the partition count)
- Consumers track their **offset** (position) in each partition

**Partition assignment strategies** affect load distribution:

- **Range**: Assigns contiguous partitions to consumers; can create imbalance
- **Round-robin**: Distributes partitions evenly; better load distribution
- **Sticky**: Maintains assignments during rebalances when possible; reduces disruption

When a consumer joins or leaves, **rebalancing** redistributes partitions. During eager rebalancing, all consumers stop briefly. Cooperative rebalancing incrementally moves partitions, maintaining higher availability [Source: Confluent Kafka Consumer Documentation].

### Message Queue Technologies

Different queue technologies optimize for different use cases:

**Apache Kafka** excels at high-throughput, ordered event streaming. Kafka stores messages in partitioned, replicated logs. Consumers track their position (offset) and can replay messages. Kafka's design enables throughput measured in millions of messages per second per cluster for well-tuned deployments [Source: Apache Kafka Documentation]. The trade-off is operational complexity: Kafka requires ZooKeeper (or the newer KRaft mode), careful partition planning, and tuning for your workload.

**RabbitMQ** provides flexible routing with traditional message queue semantics. Messages flow through exchanges to queues based on routing rules. RabbitMQ supports multiple protocols (AMQP, MQTT, STOMP), offers sophisticated routing patterns, and provides per-message acknowledgments. It handles tens of thousands of messages per second per node, scaling through clustering and federation [Source: RabbitMQ Documentation].

**Amazon SQS** offers a managed queue service with minimal operational overhead. SQS provides at-least-once delivery, automatic scaling, and integration with AWS services. Standard queues offer high throughput with best-effort ordering; FIFO queues guarantee order with lower throughput limits. SQS abstracts infrastructure concerns but provides less control over performance tuning [Source: AWS SQS Documentation].

**Redis Streams** provides lightweight streaming with Redis's operational simplicity. For teams already running Redis, Streams offers consumer groups and persistence without additional infrastructure. Throughput is lower than Kafka but sufficient for many workloads.

### Reliable Message Publishing

A critical challenge in distributed systems is ensuring that database updates and message publications happen together or not at all. This is the **dual-write problem**.

![Transactional Outbox Pattern](../assets/ch08-transactional-outbox.html)

#### The Dual-Write Problem

Consider an order service that saves an order to the database and publishes an "OrderCreated" event. If the database write succeeds but the message publish fails, downstream services never learn about the order. If the message publishes but the database write fails, downstream services act on an order that does not exist.

You cannot solve this with a traditional distributed transaction across the database and message broker. The two-phase commit protocol is slow, reduces availability, and most message brokers do not support it.

#### Transactional Outbox Pattern

The solution is the **transactional outbox**: write events to an outbox table in the same database transaction as your business data.

1. Business logic updates the `orders` table
2. Same transaction inserts a row into the `outbox` table with the event payload
3. Transaction commits atomically—both writes succeed or both fail
4. A separate process reads the outbox and publishes to the message broker
5. After successful publish, the outbox row is marked as processed or deleted

This guarantees consistency: if the business data is committed, the event is in the outbox. If the transaction rolls back, no event exists to publish.

#### Change Data Capture (CDC)

**Change Data Capture** tools like Debezium read the database transaction log and stream changes to Kafka. This approach has advantages over polling the outbox table:

- Lower latency: events stream as they commit
- No polling overhead or missed events
- Works with any database that exposes its transaction log

Debezium's outbox pattern support extracts events from the outbox table automatically, routing them to appropriate Kafka topics [Source: Debezium Documentation, "Outbox Event Router"].

#### Implementing Idempotent Consumers

Because the outbox relay might publish a message more than once (crash after publish, before marking processed), consumers must be idempotent. Strategies include:

**Idempotency keys**: Each message includes a unique ID. Consumers store processed IDs and skip duplicates. The check and processing must happen atomically (same database transaction).

**Natural idempotency**: Some operations are naturally idempotent. Setting `user.email = 'new@example.com'` produces the same result regardless of repetition.

**Deduplication windows**: SQS FIFO queues deduplicate messages with the same deduplication ID within a 5-minute window. Kafka's idempotent producer prevents duplicates from producer retries.

For a complete transactional outbox implementation (see Example 8.5). For an idempotent consumer with deduplication (see Example 8.6).

### Backpressure and Flow Control

When producers generate messages faster than consumers can process them, queues grow unboundedly, eventually exhausting memory or disk. **Backpressure** mechanisms signal producers to slow down, maintaining system stability.

Queue depth is the primary indicator. Monitoring queue depth over time reveals whether your system is keeping pace with load. Rising queue depth indicates consumers are falling behind; falling depth suggests excess capacity.

Backpressure strategies include:

**Blocking producers**: When the queue reaches a threshold, producers block until space is available. This propagates pressure back to the source but can cause request timeouts.

**Rejecting messages**: Producers receive errors when the queue is full. This fails fast, allowing the client to retry later or take alternative action.

**Dynamic rate limiting**: Producers adjust their send rate based on queue depth signals. This smooth approach prevents sudden failures but requires coordination.

**Consumer scaling**: Auto-scaling consumers based on queue depth addresses backpressure by increasing processing capacity rather than limiting production.

Effective flow control requires visibility. Monitor these metrics:

- Queue depth (current and historical)
- Consumer lag (difference between latest message and consumer position)
- Age of oldest unprocessed message
- Producer throttling events
- Consumer processing rate

For a complete implementation of rate-limited consumers with backpressure controls (see Example 8.2).

### Dead Letter Queues and Retry Strategies

Messages fail for various reasons: malformed data, transient downstream failures, bugs in consumer code, or resource constraints. A robust system distinguishes between transient and permanent failures, retries appropriately, and isolates problematic messages.

**Retry strategies** should use exponential backoff with jitter:

1. First retry after a base delay (e.g., 1 second)
2. Subsequent retries double the delay (2s, 4s, 8s...)
3. Add random jitter to prevent synchronized retry storms
4. Cap the maximum delay and total retry count

The jitter is essential. Without it, all failed messages retry simultaneously, potentially overwhelming a recovering downstream service (the "thundering herd" problem). A production-ready implementation of exponential backoff with jitter is shown in (see Example 8.3).

**Dead letter queues (DLQ)** capture messages that exceed retry limits. Rather than losing the message or blocking the queue, we move it to a separate queue for inspection. DLQs enable:

- Preserving failed messages for debugging
- Alerting on accumulating failures
- Manual replay after fixing issues
- Analysis of failure patterns

Configure DLQ handling carefully. Set appropriate retry limits: enough to handle transient failures, not so many that a poison message blocks processing for hours. Monitor DLQ depth and alert on growth.

### Priority Queues and Scheduled Messages

Not all messages are equally urgent. **Priority queues** ensure critical work processes before routine tasks.

**Implementation approaches**:

- **Broker-native priorities**: RabbitMQ supports message priorities (0-255). Higher-priority messages are delivered first. Use sparingly—more than a few priority levels adds complexity [Source: RabbitMQ Documentation, "Priority Queue Support"].

- **Separate queues by priority**: Route high-priority messages to a dedicated queue with more consumers or faster processing. This approach is simpler to reason about and monitor.

- **Priority-based consumer allocation**: Assign more workers to high-priority queues. A common ratio: 70% of workers on high-priority, 30% on normal, with overflow handling.

**Scheduled/delayed messages** defer processing until a specified time:

- **SQS delay queues**: Messages are invisible for up to 15 minutes after send. Useful for rate-limiting retries or scheduling near-term work [Source: AWS SQS Documentation, "Delay Queues"].

- **Scheduled message brokers**: ActiveMQ and others support CRON-style scheduling for message delivery.

- **External schedulers**: For delays beyond broker limits, use EventBridge Scheduler (AWS) or a dedicated job scheduler to enqueue messages at the right time.

Use cases include: delayed email reminders, scheduled report generation, rate-limited API calls to external services, and time-based retry policies.

### Distributed Transactions with Sagas

When a business operation spans multiple services, we need a way to maintain consistency without distributed transactions. The **saga pattern** coordinates a sequence of local transactions, with compensating transactions to undo work if a step fails.

![Saga Patterns: Choreography vs Orchestration](../assets/ch08-saga-patterns.html)

#### Choreography vs Orchestration

**Choreography**: Services react to events without a central coordinator. The Order Service publishes "OrderCreated." The Payment Service consumes it, processes payment, and publishes "PaymentProcessed." The Inventory Service reacts to that event, and so on.

Advantages: loose coupling, no single point of failure, simple services. Disadvantages: hard to track the overall flow, risk of cyclic dependencies, complex failure handling.

**Orchestration**: A central saga orchestrator directs each step. It sends commands ("ProcessPayment," "ReserveInventory") and waits for replies before proceeding. The orchestrator maintains state and knows the complete workflow.

Advantages: clear visibility into saga state, simpler rollback logic, easier to add steps. Disadvantages: orchestrator is a single point of failure, tighter coupling to the orchestrator.

#### Compensating Transactions

When a saga step fails, earlier steps must be undone through **compensating transactions**:

- Step 1: Create Order → Compensate: Cancel Order
- Step 2: Reserve Inventory → Compensate: Release Inventory
- Step 3: Charge Payment → Compensate: Refund Payment

Compensations execute in reverse order. If Step 3 fails, we compensate Step 2 then Step 1.

Key requirements for compensating transactions:

- **Idempotent**: Safe to execute multiple times (retries after failures)
- **Retryable**: Must eventually succeed; use infinite retries with backoff

#### When to Use Sagas

Use sagas when:

- Operations span multiple services with separate databases
- Strong consistency is not required (eventual consistency is acceptable)
- Operations are long-running (seconds to days)
- You need visibility into multi-step business processes

Avoid sagas for:

- Operations that can use a single database transaction
- Scenarios requiring immediate consistency
- Simple two-service interactions (consider simpler patterns first)

For frameworks that simplify saga implementation, see Temporal, Axon Saga, or Eventuate Tram [Source: Microsoft Azure Architecture Center, "Saga Pattern"].

For a saga orchestrator implementation pattern (see Example 8.7).

### Schema Evolution and Versioning

Messages are contracts between services. As systems evolve, message schemas change. Without careful management, schema changes break consumers.

![Schema Compatibility Types](../assets/ch08-schema-evolution.html)

#### Compatibility Types

**Backward compatible**: New consumers can read old messages. Achieved by adding optional fields with defaults. Deploy consumers first, then producers.

**Forward compatible**: Old consumers can read new messages. Achieved by ignoring unknown fields. Deploy producers first, then consumers.

**Full compatible**: Both backward and forward compatible. Any version can communicate with any other version. Most flexible for deployment.

#### Schema Registry

A **schema registry** (Confluent Schema Registry, AWS Glue Schema Registry) stores schemas and enforces compatibility rules:

- Producers register schemas before publishing
- Consumers fetch schemas to deserialize messages
- The registry rejects incompatible schema changes

Serialization formats like Avro and Protobuf support schema evolution natively. JSON Schema provides similar capabilities for JSON messages [Source: Confluent Documentation, "Schema Evolution and Compatibility"].

#### Safe Schema Changes

**Safe changes** (preserve compatibility):

- Add optional fields with default values
- Remove optional fields (consumers ignore them)
- Add new enum values at the end

**Breaking changes** (require migration):

- Remove or rename required fields
- Change field types
- Reorder enum values

For breaking changes, use the **expand-contract pattern**:

1. **Expand**: Add the new field alongside the old
2. **Migrate**: Update all consumers to use the new field
3. **Contract**: Remove the old field after all consumers have migrated

This allows breaking changes over multiple deployments without downtime.

### Stream Processing

Beyond message queues for task distribution, **stream processing** enables continuous computation over unbounded event streams. While queues focus on work distribution, stream processors analyze, transform, and aggregate data in real-time.

![Stream Processing Architecture](../assets/ch08-stream-processing.html)

#### Streams vs Queues

Message queues typically deliver each message once (to one consumer or one consumer per group). Stream processors treat the event log as the source of truth:

- Messages are retained (for replay, reprocessing)
- Multiple processors can read the same stream independently
- State is maintained across events (aggregations, joins)
- Time-based operations (windowing) are first-class

#### Stream Processing Frameworks

**Apache Flink** is a distributed stream processor designed for stateful computations. Flink handles millions of events per second with millisecond latency, provides exactly-once processing guarantees, and supports complex event processing. The trade-off is operational complexity—Flink requires a cluster [Source: Apache Flink Documentation].

**Kafka Streams** is a library (not a cluster) for stream processing within your application. It leverages Kafka for storage and coordination, making it simpler to operate for teams already using Kafka. Throughput is lower than Flink but sufficient for many use cases [Source: Confluent Documentation, "Kafka Streams"].

**Comparison considerations**:

- **Flink**: Best for high-throughput analytics, complex event processing, large-scale deployments
- **Kafka Streams**: Best for microservices, simpler operational model, Kafka-native workflows
- **Spark Streaming**: Best for batch/stream hybrid workloads, existing Spark infrastructure

#### Windowing Patterns

Windowing groups events for aggregation:

**Tumbling windows**: Fixed-size, non-overlapping intervals. "Count orders per hour" uses 1-hour tumbling windows. Each event belongs to exactly one window.

**Sliding windows**: Fixed-size, overlapping intervals. "Average latency over the last 5 minutes, updated every minute" slides a 5-minute window forward each minute.

**Session windows**: Dynamic windows based on activity gaps. Events within the gap threshold belong to the same session. Useful for user behavior analysis.

**Global windows**: All events in one window, with custom triggers (count-based, time-based) to emit results.

#### When to Use Stream Processing for API Optimization

Stream processing shines for:

- **Real-time dashboards**: Aggregate metrics as they arrive
- **Anomaly detection**: Identify unusual patterns in request rates or error rates
- **Dynamic rate limiting**: Adjust limits based on recent traffic patterns
- **Live recommendations**: Update suggestions based on recent user behavior
- **Log aggregation**: Process and route logs in real-time

The trade-off is complexity. Stream processing introduces eventual consistency, requires understanding of time semantics (event time vs processing time), and adds operational overhead. Use it when sub-second latency on continuous data justifies the complexity.

### Async API Patterns

When an API initiates asynchronous work, clients need a way to learn the outcome. Two primary patterns exist: polling and webhooks.

![Async Results: Webhooks vs Polling](../assets/ch08-webhook-vs-polling.html)

#### Polling

The API returns a job ID; clients periodically check status:

1. `POST /jobs` returns `202 Accepted` with `{job_id: "123"}`
2. Client polls `GET /jobs/123` until status is "complete" or "failed"
3. Final response includes the result or error details

**Advantages**: Simple for clients (no public endpoint needed), works with browsers, client controls timing.

**Disadvantages**: Wastes API calls on "still pending" responses, delayed notification (depends on poll interval), increased server load.

**Optimization**: Use long polling (server holds the request until completion or timeout) to reduce wasted calls.

#### Webhooks

The client provides a callback URL; the server pushes the result:

1. `POST /jobs` with `{callback_url: "https://client.com/webhook"}` returns `202 Accepted`
2. Worker completes the job
3. Server `POST`s result to the callback URL
4. Client acknowledges with `200 OK`

**Advantages**: Real-time notification, no wasted requests, efficient for servers.

**Disadvantages**: Client needs a publicly accessible endpoint, must handle retries if webhook delivery fails, security considerations (validating webhook authenticity).

**Best practice**: Support both patterns. Clients without public endpoints use polling; server-to-server integrations use webhooks.

#### Worker Pool Architecture

For processing queued work, a **worker pool** provides controlled concurrency:

- Fixed number of workers prevents resource exhaustion
- Work queue buffers incoming tasks
- Each worker pulls tasks, processes, and acknowledges

**Graceful shutdown** is critical:

1. Stop accepting new work
2. Wait for in-progress work to complete (with timeout)
3. Re-queue incomplete work for other consumers
4. Exit cleanly

Monitor worker utilization to tune pool size. Too few workers: queue depth grows. Too many: resources wasted on idle workers.

### Event-Driven Architecture

Beyond simple task queuing, message systems enable event-driven architectures where services communicate through events rather than direct calls.

**Event sourcing** stores state changes as a sequence of events. Instead of updating a database row, we append an "OrderPlaced" event. The current state is reconstructed by replaying events. This pattern provides a complete audit trail, enables temporal queries ("what was the state at time X?"), and simplifies some consistency challenges.

**CQRS (Command Query Responsibility Segregation)** separates read and write models. Commands modify state through the event log; queries read from optimized view models. This enables independent scaling and optimization of reads and writes.

These patterns introduce complexity and eventual consistency. Use them when their benefits (audit trails, replay capability, independent scaling) outweigh the costs. Martin Fowler provides extensive guidance on when event sourcing and CQRS are appropriate [Source: Martin Fowler, "Event Sourcing," martinfowler.com].

For a complete async API endpoint pattern with job status polling (see Example 8.4).

For implementation examples related to these concepts, see the [Appendix: Code Examples](./15-appendix-code-examples.md).

## Common Pitfalls

- **Ignoring idempotency**: At-least-once delivery means consumers may process the same message multiple times. Design handlers to be idempotent, meaning processing the same message twice should have the same effect as processing it once. Use idempotency keys or check for duplicate work before processing.

- **Missing dead letter queue monitoring**: Configuring a DLQ is not enough. Without alerts on DLQ growth, poison messages accumulate unnoticed. Monitor DLQ depth and set alerts for any growth, as DLQs should remain empty in healthy systems.

- **Retry without backoff**: Immediate retry storms can overwhelm recovering services. Always implement exponential backoff with jitter to spread retry load over time.

- **Unbounded queues**: Queues that grow without limit eventually exhaust resources. Set maximum queue depths and implement backpressure. A queue that rejects messages at capacity is healthier than one that crashes from memory exhaustion.

- **Synchronous patterns in async code**: Using blocking calls inside async workers defeats the purpose. Ensure all I/O operations use async libraries. A single blocking call in a worker can stall the entire event loop.

- **Ignoring message ordering requirements**: Some operations must process in order (e.g., deposit before withdrawal). Understand your ordering requirements and use partitioning or sequence numbers to maintain order where needed.

- **Over-engineering for exactly-once**: Exactly-once delivery is complex and costly. Often, at-least-once with idempotent consumers achieves the same practical result with far less complexity.

- **Fire-and-forget for critical operations**: While async processing improves latency, some operations need confirmation. Do not use fire-and-forget for payment processing or other critical flows where failure must be reported to the user.

- **Ignoring the dual-write problem**: Publishing messages outside the database transaction creates inconsistency windows. Use the transactional outbox pattern to ensure atomicity between data and event publishing.

- **Schema coupling without versioning**: Changing message formats without compatibility planning breaks consumers. Use a schema registry and follow expand-contract migration patterns.

- **Treating streams like queues**: Stream processing and message queuing serve different purposes. Do not use Kafka Streams when a simple consumer would suffice, and do not use basic consumers when you need windowed aggregations.

- **Priority inversion**: When low-priority work consumes all workers, high-priority work waits. Use separate queues with dedicated worker pools for different priority levels.

## Summary

- Asynchronous processing moves work off the critical request path, reducing client-perceived latency while enabling better system throughput and resilience

- Message queues provide temporal decoupling between producers and consumers, enabling load leveling during traffic spikes and failure isolation between components

- Delivery guarantees (at-most-once, at-least-once, exactly-once) involve trade-offs between reliability, performance, and complexity; at-least-once with idempotent consumers is often the practical choice

- The transactional outbox pattern solves the dual-write problem by writing events to a database table in the same transaction as business data, ensuring consistency between state and events

- Consumer groups enable parallel processing while maintaining ordering within partitions; partition assignment strategies affect load distribution and rebalancing behavior

- Backpressure mechanisms prevent queue overflow by signaling producers to slow down when consumers cannot keep pace; monitor queue depth as the primary indicator

- Exponential backoff with jitter prevents retry storms that could overwhelm recovering services; cap both maximum delay and total retry attempts

- Dead letter queues isolate failing messages for debugging without blocking the main processing flow; monitor DLQ depth and alert on growth

- The saga pattern coordinates distributed transactions through a sequence of local transactions with compensating actions for rollback; choose choreography for loose coupling or orchestration for visibility

- Schema evolution requires planning for compatibility; use a schema registry and follow expand-contract patterns for breaking changes

- Stream processing enables real-time analytics on continuous data through windowing and stateful computation; use it when sub-second latency justifies the complexity

- For async results, support both polling (simple for clients) and webhooks (efficient for servers) to accommodate different integration patterns

- Consumer idempotency is essential in at-least-once systems; design handlers to produce the same result regardless of how many times they process a message

## References

1. **Apache Kafka Documentation**. "Design: Persistence" and "Design: Efficiency." https://kafka.apache.org/documentation/#design

2. **RabbitMQ Documentation**. "Reliability Guide" and "Consumer Acknowledgements." https://www.rabbitmq.com/documentation.html

3. **AWS SQS Documentation**. "Amazon SQS Developer Guide." https://docs.aws.amazon.com/AWSSimpleQueueService/latest/SQSDeveloperGuide/

4. **Fowler, M.** "Event Sourcing." martinfowler.com. https://martinfowler.com/eaaDev/EventSourcing.html

5. **Hohpe, G., & Woolf, B.** (2003). "Enterprise Integration Patterns." Addison-Wesley.

6. **LinkedIn Engineering Blog** (2019). "Building Scalable Real-time Messaging at LinkedIn." https://engineering.linkedin.com/blog/

7. **Kleppmann, M.** (2017). "Designing Data-Intensive Applications." O'Reilly Media. Chapter 11: Stream Processing.

8. **Debezium Documentation**. "Outbox Event Router." https://debezium.io/documentation/reference/transformations/outbox-event-router.html

9. **Microsoft Azure Architecture Center**. "Saga distributed transactions pattern." https://learn.microsoft.com/en-us/azure/architecture/reference-architectures/saga/saga

10. **Confluent Documentation**. "Schema Evolution and Compatibility." https://docs.confluent.io/platform/current/schema-registry/fundamentals/schema-evolution.html

11. **Apache Flink Documentation**. "What is Apache Flink?" https://flink.apache.org/what-is-flink/

12. **Confluent Documentation**. "Kafka Streams." https://docs.confluent.io/platform/current/streams/

13. **Morling, G.** "On Idempotency Keys." https://www.morling.dev/blog/on-idempotency-keys/

14. **microservices.io**. "Pattern: Transactional outbox." https://microservices.io/patterns/data/transactional-outbox.html

## Next: [Chapter 9: Compute and Scaling](./09-compute-scaling.md)

With asynchronous patterns in place, we need to scale our compute resources to handle the workload. The next chapter covers horizontal and vertical scaling strategies, stateless service design, auto-scaling policies, and container orchestration to ensure our async consumers and API servers can grow with demand.
