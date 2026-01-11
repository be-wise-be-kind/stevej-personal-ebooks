# Chapter 7: Database and Storage Selection

![Chapter 7 Opener](../assets/ch07-opener.html)

\newpage

## Overview

When an API performs poorly, developers often reach for database optimization techniques: adding indexes, tuning queries, adjusting connection pools. These techniques matter, but they assume we have already chosen the right database. The more fundamental question, one that shapes the entire system architecture, is whether we are using the appropriate type of data store for our access patterns in the first place.

**A note on scope:** Database optimization is a deep discipline with excellent specialized resources. *High Performance MySQL*, *PostgreSQL 14 Internals*, and *MongoDB: The Definitive Guide* dedicate hundreds of pages to tuning specific database engines. This chapter takes a different approach: we focus on the strategic question of *which* database type fits *which* API interaction pattern. Optimizing your chosen database is important work, but it belongs to those specialized resources, not this book.

The modern data landscape offers remarkable variety: relational databases for transactional integrity, document stores for flexible schemas, key-value stores for sub-millisecond lookups, wide-column databases for massive write throughput, vector databases for semantic similarity, and search engines for full-text queries. Each excels at specific access patterns and struggles with others. The API developer's job is to match the right tool to the right problem.

This chapter provides a decision framework for storage selection. We will examine each major database category, understand where it shines, recognize its trade-offs, and learn when to combine multiple stores in a polyglot architecture. The goal is not to make you an expert in every database (that would require several books) but to help you ask the right questions and make informed architectural decisions.

Database selection involves three interconnected decisions:

1. **Data model**: Which database type matches your data shape and query patterns?
2. **Read/write optimization**: How do you tune for your dominant access pattern?
3. **Durability and consistency**: What guarantees does your application require?

The diagrams in this chapter address each decision independently, because real-world choices rarely follow a single linear decision tree. You might need a document database (data model) with read replicas (read-heavy optimization) and eventual consistency (consistency trade-off). These dimensions combine; they do not cascade.

![Data Model Selection Guide](../assets/ch07-data-model-selection.html)

## Key Concepts

### The Data Store Landscape

Before diving into specific database types, we need a mental model of the landscape. Data stores fall into several broad categories, each optimized for different access patterns:

| Category | Examples | Optimized For |
|----------|----------|---------------|
| **Relational (SQL)** | PostgreSQL, MySQL, SQLite | Transactions, complex queries, strong consistency |
| **Document** | MongoDB, CouchDB, Firestore | Flexible schemas, nested data, read-heavy workloads |
| **Key-Value** | Redis, Memcached, DynamoDB | Simple lookups, caching, session storage |
| **Wide-Column** | Cassandra, ScyllaDB, HBase | Write-heavy workloads, time-series, massive scale |
| **Vector** | Pinecone, Weaviate, pgvector | Semantic similarity, embeddings, AI applications |
| **Search** | Elasticsearch, OpenSearch, Typesense | Full-text search, faceted navigation, log analysis |

These categories are not mutually exclusive. PostgreSQL offers document storage via JSONB, vector search via pgvector, and full-text search capabilities. Redis provides data structures beyond simple key-value pairs. The boundaries blur, but the core strengths remain distinct.

![Data Store Comparison Matrix](../assets/ch07-data-store-comparison.html)

### Relational Databases (SQL)

Relational databases remain the default choice for most applications, and for good reason. They provide ACID transactions (Atomicity, Consistency, Isolation, Durability), support complex queries across related data, and offer decades of battle-tested reliability.

**When to choose relational databases:**

- **ACID transactions are required.** Financial operations, inventory management, and order processing typically need guarantees that a transfer either fully completes or fully fails. No partial states.

- **Data relationships are complex.** When entities relate to each other in multiple ways (users have orders, orders contain products, products belong to categories, categories form hierarchies), relational databases model these connections naturally with foreign keys and JOINs.

- **Query patterns are varied or unknown.** If you need ad-hoc reporting, complex aggregations, or the flexibility to query data in ways not anticipated at design time, SQL's expressive power helps.

- **Strong consistency matters.** When a write completes, all subsequent reads see that write. No eventual consistency surprises.

**Trade-offs to consider:**

Relational databases struggle with horizontal scaling for writes. Vertical scaling (bigger machines) works until it doesn't, and sharding relational data introduces significant complexity. Read scaling is more tractable via replicas (see "Read/Write Pattern Optimization" below), but write scaling often requires application-level partitioning or moving to a different database type.

Schema rigidity cuts both ways. Enforced schemas catch errors early but make evolution harder. Adding a column to a billion-row table can take hours or require careful migration strategies.

For simple key-based lookups, relational databases add overhead. If every access is "get user by ID" with no joins or complex queries, a key-value store is faster and simpler.

### Document Databases

Document databases store data as self-contained documents (typically JSON or BSON) rather than rows in tables. Each document can have a different structure, and nested data lives naturally within the document rather than requiring JOIN operations.

**When to choose document databases:**

- **Schema flexibility is valuable.** Product catalogs where each product type has different attributes, content management systems with varied content types, or any domain where the data model evolves frequently.

- **Data is naturally hierarchical.** A blog post with embedded comments and author information, a configuration object with nested settings, or an event with nested metadata. Rather than spreading this across multiple tables and reassembling with JOINs, a document stores the complete unit.

- **Read patterns are document-centric.** If most reads fetch a complete document by ID (or a handful of indexed fields), document databases excel. They avoid the JOIN overhead of reassembling data from multiple tables.

- **Scale requirements favor horizontal distribution.** MongoDB, Couchbase, and similar stores are designed for sharding across many nodes. If you anticipate massive scale, document databases often provide an easier path.

**Trade-offs to consider:**

Document databases sacrifice JOIN capabilities. When you need to combine data from multiple document types ("show me all orders for users in California"), you either denormalize (embed user state in each order), perform multiple queries and combine in application code, or use limited aggregation pipelines. None of these are as clean as a SQL JOIN.

Transaction support varies. MongoDB added multi-document transactions in version 4.0, but they carry performance overhead [Source: MongoDB Documentation, "Transactions"]. CouchDB provides document-level atomicity only. Design around the database's native capabilities rather than fighting them.

Consistency guarantees differ by product. Some document databases default to eventual consistency for reads. Understand your database's consistency model and configure appropriately for your requirements.

### Key-Value Stores

Key-value stores are the simplest database model: given a key, return the value. This simplicity enables remarkable performance (sub-millisecond reads are routine) and straightforward horizontal scaling. Every key hashes to a specific partition; no cross-partition coordination is needed.

**When to choose key-value stores:**

- **Access is by known keys.** Session tokens, shopping carts keyed by user ID, feature flags keyed by flag name, cached API responses keyed by request signature. If you always know the key when reading, key-value stores are optimal.

- **Latency requirements are aggressive.** When p99 latency targets are under 10 milliseconds, key-value stores deliver. Redis benchmarks show 50,000+ operations per second on modest hardware with sub-millisecond latency [Source: Redis Benchmarks, "How Fast is Redis?"].

- **Data is ephemeral or cacheable.** Session data that can be regenerated, cached computation results, rate limiting counters. If losing data is acceptable (or merely inconvenient), key-value stores offer simpler operations with optional persistence.

- **The data model is simple.** No relationships between keys, no need to query by value, no aggregations across keys. The data fits the model.

**Trade-offs to consider:**

Key-value stores provide no query capabilities beyond key lookup. "Find all sessions created in the last hour" is not possible without secondary indexes (which not all key-value stores support) or maintaining the query externally.

Memory costs can be significant. Redis keeps data in memory by default, providing speed but limiting dataset size to available RAM. Disk-backed key-value stores like RocksDB trade some latency for larger capacity.

Consistency models vary. Redis clustering provides eventual consistency for reads after writes to different nodes. DynamoDB offers configurable consistency per read. Know your requirements and your database's guarantees.

### Wide-Column Databases

Wide-column databases (Cassandra, ScyllaDB, HBase) optimize for a specific access pattern: massive write throughput across many nodes, with reads by known partition keys. They organize data by row key and column family, allowing different rows to have different columns without schema changes.

![Wide-Column Database Architecture](../assets/ch07-wide-column-architecture.html)

**When to choose wide-column databases:**

- **Write throughput is extreme.** IoT sensor data arriving at millions of events per second, activity streams from social platforms, application logs at scale. Wide-column databases handle write-heavy workloads that would overwhelm relational databases.

- **Data is time-series or append-mostly.** Events, metrics, logs, and other data that arrives chronologically and rarely updates. The append-optimized storage engine handles this pattern efficiently.

- **Horizontal scale is essential.** Wide-column databases scale linearly by adding nodes. Cassandra clusters routinely span hundreds of nodes and petabytes of data [Source: DataStax, "Cassandra Case Studies"].

- **Query patterns are known and limited.** Reads by partition key (user ID, sensor ID, time bucket) work well. Ad-hoc queries across all partitions are expensive or impossible. Design your partition keys around your query patterns.

**Trade-offs to consider:**

Wide-column databases offer eventual consistency by default. Cassandra's tunable consistency allows per-query tradeoffs, but strong consistency requires coordination across replicas, reducing availability and increasing latency.

Query flexibility is limited. No JOINs, no ad-hoc queries across partitions, limited aggregation. Data modeling requires deep understanding of access patterns upfront. Changing partition keys after the fact means migrating data.

Operational complexity is higher than managed relational databases. Compaction, repair, and cluster management require expertise. Consider managed offerings (Astra, Amazon Keyspaces) if operational capacity is limited.

### Read/Write Pattern Optimization

Regardless of which database type you choose, understanding your read/write ratio shapes optimization strategies. Most APIs are read-heavy: product catalog browsing, profile viewing, content consumption. Some are write-heavy: analytics collection, logging, IoT ingestion. The optimization patterns differ significantly.

![Read-Heavy vs Write-Heavy Patterns](../assets/ch07-read-write-patterns.html)

**Read-heavy optimization: Caching and replicas**

For read-heavy workloads, we reduce database load by caching (covered in Chapter 6) and distributing reads across replicas. Most relational and document databases support read replicas: a primary handles all writes, which then replicate to one or more read replicas. Read queries route to replicas, distributing the load.

A database router directs write operations to the primary and distributes reads across available replicas. The router can use random selection or round-robin to balance load, falling back to primary if no replicas are available.

Replication introduces eventual consistency. After a write to the primary, there is a delay before the data appears on replicas (typically milliseconds, but potentially seconds under heavy load) [Source: PostgreSQL Documentation, "Streaming Replication"]. For read-after-write consistency (a user creating a post and immediately viewing it), either route that specific read to the primary, or track recent writes per session and route accordingly.

```
on database query:
    if query is a write (INSERT, UPDATE, DELETE):
        route to primary
    else if user just performed a write:
        route to primary (read-after-write consistency)
    else:
        route to random healthy replica
```

### Pagination Strategies

When APIs return large datasets, pagination becomes essential for both client usability and database performance. However, not all pagination approaches perform equally. The strategy we choose determines whether fetching page 1,000 is as fast as fetching page 1, or orders of magnitude slower.

**Offset pagination** is the most intuitive approach. The client specifies `page=50&limit=20`, and the database executes `OFFSET 980 LIMIT 20`. This simplicity comes with a significant hidden cost: the database must scan and discard 980 rows before returning the 20 we want. At page 1,000, we are discarding 19,980 rows to return 20. Performance degrades linearly with depth. Offset pagination is O(n) where n is the offset value, regardless of indexes.

Offset pagination also suffers from consistency problems. If a new record is inserted while a user navigates between pages, they may see duplicate items or miss items entirely as the window shifts. For administrative interfaces with modest data sizes and infrequent updates, these trade-offs are acceptable. For user-facing product lists with millions of items, they are not.

**Cursor-based pagination** (also called keyset pagination) takes a fundamentally different approach. Instead of "skip 980 rows," we say "give me 20 rows where `created_at` is less than this timestamp." The database uses an index to jump directly to the right position, then reads forward. Whether we are fetching page 1 or page 10,000, the database reads exactly the same number of rows. Performance is O(1) with proper indexing.

The critical requirement for cursor-based pagination is a unique, indexed sort column. If we sort by `created_at` but multiple records share the same timestamp, the cursor becomes ambiguous. The solution is a compound sort: `ORDER BY created_at DESC, id DESC` with a corresponding compound index. The cursor then encodes both values: `created_at < cursor_timestamp OR (created_at = cursor_timestamp AND id < cursor_id)`.

**Seek pagination** is a variation of cursor-based pagination that uses opaque, encoded cursors rather than exposing raw column values. The API returns a `next_cursor` like `eyJjcmVhdGVkX2F0IjoiMjAyNC0wMy0xNSIsImlkIjo0NTY3fQ==` (a Base64-encoded JSON object). Clients treat this as an opaque token and pass it back unchanged. This approach hides implementation details, allows the cursor format to evolve without breaking clients, and can include additional metadata like the sort direction or version number.

The following pseudocode illustrates the performance difference between offset and cursor approaches.

```
offset pagination (page 100, 20 items per page):
    SELECT * FROM items ORDER BY created_at DESC
    OFFSET 1980 LIMIT 20
    -- database must skip 1980 rows before returning 20

keyset pagination (after cursor):
    SELECT * FROM items
    WHERE created_at < cursor_timestamp
    ORDER BY created_at DESC
    LIMIT 20
    -- database uses index, returns 20 rows directly
```

**When to use each approach:**

Offset pagination fits scenarios with small datasets, administrative interfaces where simplicity matters more than deep-page performance, and situations where users rarely navigate past the first few pages. Most search interfaces fall into this category; users refine their query rather than browsing to page 500.

Cursor-based pagination fits user-facing lists with large datasets: activity feeds, product catalogs, message histories, and audit logs. Any scenario where users might scroll indefinitely or where the dataset grows continuously benefits from cursor-based approaches. APIs that serve mobile clients, which often implement infinite scroll, should default to cursor-based pagination.

**Caching implications differ significantly between approaches.** Offset-based pages are unstable. If we cache "page 5" and new data is inserted, the cached content no longer represents page 5. Cache invalidation becomes difficult or requires accepting stale data. Cursor-based pagination produces stable results: "20 items after this cursor" returns the same items regardless of what was inserted before the cursor position. This stability makes cursor-based responses more cacheable with longer TTLs.

For systems requiring both approaches, consider offering offset pagination for initial discovery (`GET /products?page=1`) and cursor pagination for subsequent navigation (the response includes a `next_cursor` for continuation). This hybrid preserves the simplicity of page numbers for bookmarking while delivering the performance benefits of cursors for actual traversal.

For systems that need both caching and strong consistency on writes, the write-through cache pattern ensures the cache always reflects the database state. Unlike cache-aside (where writes go directly to the database and the cache is invalidated or updated separately), write-through treats the cache as part of the write path.

```
on write operation:
    write data to database
    if database write succeeds:
        write same data to cache
        return success
    else:
        return failure (cache unchanged)
```

This pattern guarantees that successful writes are immediately visible in the cache, eliminating the window of inconsistency that exists with cache-aside patterns. The trade-off is higher write latency (two writes instead of one) and the need to handle partial failures (database succeeds but cache fails).

**Write-heavy optimization: Partitioning and batching**

For write-heavy workloads, optimization focuses on distributing writes across partitions (sharding) and batching writes to reduce per-operation overhead. Wide-column databases handle this natively. Relational databases require application-level sharding or specialized extensions (Citus for PostgreSQL, Vitess for MySQL).

Batching writes improves throughput by amortizing network and transaction overhead. Instead of 1,000 individual INSERT statements, a single bulk insert executes faster. Most databases provide bulk write APIs; use them for high-volume ingestion.

**Connection pooling fundamentals**

Regardless of read/write ratio, connection pooling matters for any database. Opening a connection involves TCP handshake, authentication, TLS negotiation, and session setup, overhead that adds tens of milliseconds per request if done repeatedly. Connection pools maintain a cache of open connections for reuse.

The HikariCP documentation provides a useful formula for OLTP workloads: pool size equals core count times two, plus effective spindle count [Source: HikariCP Wiki, "About Pool Sizing"]. For modern SSDs, treat spindle count as 1. A 4-core server might use a pool of 9-10 connections. However, optimal sizing depends on query patterns and should be determined through measurement.

Connection pool configuration follows similar patterns across languages and databases: set minimum and maximum counts, configure idle timeouts, and establish query timeouts.

### Durability and Consistency Tradeoffs

Beyond data model and read/write patterns, database selection involves durability and consistency decisions. These concepts are related but distinct:

**Durability** answers "will my data survive failures?" It ranges from synchronous multi-region replication (zero data loss even if an entire datacenter fails) to memory-only storage (data lost on process restart). Higher durability costs more in latency and infrastructure.

**Consistency** answers "will all readers see the same data?" Strong consistency guarantees that every read sees the most recent write. Eventual consistency allows stale reads temporarily, trading correctness for availability and latency.

![Durability and Consistency Tradeoffs](../assets/ch07-durability-consistency.html)

Every application has different requirements. Financial transactions need the strongest durability and consistency guarantees. Social media feeds tolerate eventual consistency and brief data loss. The sections that follow explore specific patterns along these spectrums.

### Fire-and-Forget Patterns

Not all data requires immediate durability. Analytics events, telemetry, and activity logs often tolerate potential data loss in exchange for lower latency and higher throughput. Fire-and-forget patterns acknowledge this trade-off explicitly.

![Fire-and-Forget Data Flow](../assets/ch07-fire-forget-flow.html)

**When fire-and-forget makes sense:**

- **The data is statistical, not transactional.** Missing 0.1% of analytics events doesn't change aggregate conclusions. Missing 0.1% of order transactions is unacceptable. Know the difference.

- **Latency requirements are aggressive.** Waiting for a durable write adds 10-50ms to request latency. If the API should respond in under 20ms, synchronous durability may not fit.

- **The system can regenerate or tolerate loss.** Cached data can be recalculated. Analytics can be reprocessed from logs. If loss is merely inconvenient rather than catastrophic, fire-and-forget is an option.

**Implementation patterns:**

The simplest pattern uses an in-memory buffer with periodic flushing. Events accumulate in memory and flush to durable storage every N seconds or when the buffer reaches M items. If the process crashes between flushes, buffered events are lost. Redis with `appendfsync everysec` (flush every second) provides a middle ground between pure memory and synchronous durability [Source: Redis Documentation, "Persistence"].

For higher guarantees without synchronous writes, use an asynchronous queue. The API writes to a local queue or memory-mapped buffer, and a separate process drains the queue to durable storage. This decouples API latency from storage latency while providing durability if the drain process runs continuously.

**Trade-offs:**

Fire-and-forget trades durability for latency. Measure the actual loss rate and ensure stakeholders understand the trade-off. An explicit 0.1% loss rate by design is better than an implicit loss rate nobody measured.

### WORM (Write Once Read Many) Patterns

Some data should never change after creation: audit logs, financial records, compliance data, event sourcing event streams. Write Once Read Many (WORM) patterns enforce immutability, providing guarantees that data was not modified after the fact.

![WORM Storage Pattern](../assets/ch07-worm-pattern.html)

**When WORM patterns apply:**

- **Regulatory compliance requires audit trails.** Financial transactions, healthcare records, and legal documents often require provable immutability. WORM storage provides evidence that records have not been altered.

- **Event sourcing architectures.** Rather than storing current state (which overwrites previous state), event sourcing stores the sequence of events that produced the current state. These events are immutable by design [Source: Fowler, "Event Sourcing"].

- **Debugging and forensics.** Append-only logs of API requests, system events, and state changes enable post-incident investigation without worrying about evidence tampering.

**Implementation patterns:**

Time-series databases (InfluxDB, TimescaleDB, QuestDB) are designed for append-heavy workloads and support retention policies that age out old data. They optimize for time-range queries and down-sampling.

Append-only tables in relational databases work for moderate scale. Create tables with no UPDATE or DELETE triggers, and enforce INSERT-only access at the application layer. PostgreSQL's append-only table storage option provides additional guarantees.

Object storage with immutability (S3 Object Lock, GCS retention policies) provides WORM guarantees at the storage layer. Write complete log segments as immutable objects. This pattern scales to arbitrary volumes at low cost but limits real-time query capabilities.

**Trade-offs:**

WORM storage grows indefinitely unless you implement retention policies. Storage costs accumulate. Plan for data lifecycle from the start.

Queries over large WORM datasets can be expensive. Consider materialized views, pre-aggregation, or indexing layers on top of raw WORM storage for common query patterns.

### Vector Databases

The rise of machine learning, particularly large language models, has driven adoption of vector databases. These stores optimize for similarity search over high-dimensional vectors, the numerical representations (embeddings) that ML models produce.

![Vector Similarity Search](../assets/ch07-vector-similarity.html)

**When to choose vector databases:**

- **Semantic search is required.** Traditional keyword search finds exact or fuzzy matches. Semantic search finds conceptually similar items. "Comfortable running shoes" should match "cushioned jogging sneakers" even without keyword overlap. Vector similarity enables this.

- **Recommendation systems need similar-item lookup.** "Users who liked this also liked..." often uses embedding similarity. Vector databases make this lookup fast even with millions of items.

- **RAG (Retrieval Augmented Generation) architectures.** Modern LLM applications often retrieve relevant context from a knowledge base before generating responses. Vector databases provide the retrieval layer [Source: Lewis et al., "Retrieval-Augmented Generation for Knowledge-Intensive NLP Tasks"].

- **Image, audio, or video similarity.** Content-based retrieval (finding similar images, songs, or video clips) uses embeddings and vector similarity.

**Product landscape:**

Purpose-built vector databases include Pinecone (fully managed), Weaviate (open source), Qdrant (open source, Rust-based), and Milvus (open source, designed for scale). These offer optimized indexing (HNSW, IVF) and high query throughput.

Hybrid options add vector search to existing databases. PostgreSQL with pgvector provides vector similarity within a relational database, useful when vectors are one part of a larger data model. Redis with RediSearch, Elasticsearch with dense vector fields, and MongoDB Atlas Search all offer vector capabilities.

**Trade-offs:**

Vector databases require embeddings, which require embedding models. You need an ML pipeline to convert text/images/audio to vectors before storage and at query time. This adds complexity and latency.

Index building for vector similarity involves trade-offs between recall (finding the true nearest neighbors), query speed, and memory usage. HNSW indexes are fast but memory-intensive. IVF indexes are more compact but may miss some results. Understand your recall requirements.

Vector similarity is one piece of retrieval. Hybrid approaches that combine vector similarity with keyword matching often outperform either alone [Source: Karpukhin et al., "Dense Passage Retrieval for Open-Domain Question Answering"].

### Search Databases

Search databases (Elasticsearch, OpenSearch, Typesense, Meilisearch) are optimized for full-text search, faceted navigation, and log analysis. They invert the traditional database model: rather than storing rows and querying by column, they build inverted indexes that map terms to documents containing those terms.

![Search Engine: The Inverted Index](../assets/ch07-inverted-index.html)

**When to choose search databases:**

- **Full-text search is a primary access pattern.** Product search, article search, documentation search. When users type queries and expect relevant results ranked by relevance, search databases excel.

- **Faceted navigation is needed.** E-commerce filtering by category, price range, brand, and ratings. Search databases efficiently compute facet counts across large result sets.

- **Log and event analysis.** The "ELK stack" (Elasticsearch, Logstash, Kibana) became a standard for log aggregation because Elasticsearch handles high write volumes and flexible queries over semi-structured log data.

- **Autocomplete and suggestions.** Search databases provide prefix matching, fuzzy matching, and phrase suggestions that enable responsive search-as-you-type interfaces.

**Product landscape:**

Elasticsearch remains the dominant option, with OpenSearch as the open-source fork after licensing changes. Both handle large-scale deployments and complex query DSLs. Typesense and Meilisearch offer simpler APIs and faster indexing for smaller-scale use cases, with less operational complexity.

**Trade-offs:**

Search databases are not primary data stores. They lack ACID transactions, and data loss scenarios (while uncommon) require re-indexing from the source of truth. Use search databases as secondary indexes, not as the authoritative record.

Indexing has latency. New or updated documents are not immediately searchable; there is a refresh interval (typically 1 second in Elasticsearch) before changes appear. Near-real-time, not real-time.

Relevance tuning is an art. Default relevance scoring works for many cases, but optimizing for your specific domain requires experimentation with analyzers, boosting, and custom scoring. Budget time for relevance engineering.

### Polyglot Persistence

Real-world systems often use multiple database types together. An e-commerce API might use PostgreSQL for orders and inventory (ACID transactions), Redis for shopping carts and sessions (low latency), Elasticsearch for product search (full-text), and a vector database for recommendations (similarity). This is polyglot persistence.

![Polyglot Persistence Architecture](../assets/ch07-polyglot-architecture.html)

**When polyglot persistence makes sense:**

- **Access patterns are genuinely different.** If 80% of requests are key-value lookups but 20% need complex joins, a single database optimized for one pattern will underperform for the other. Splitting workloads lets each database do what it does best.

- **Scale requirements differ by data type.** Session data needs sub-millisecond access but modest total volume. Analytics data needs high write throughput but tolerates higher read latency. Different databases fit different scaling profiles.

- **Specialized capabilities are required.** No single database is best at transactions, full-text search, vector similarity, and time-series ingestion. When you need multiple specialized capabilities, multiple specialized databases may be the honest answer.

**Implementation considerations:**

**Source of truth:** Designate one database as authoritative for each piece of data. Other databases hold derived views. When data diverges (and it will), the source of truth wins.

**Synchronization patterns:** Data flows from the source of truth to secondary databases. This can be synchronous (within the same transaction, which adds latency and coupling), asynchronous via change data capture (CDC) or event streams (adds eventual consistency), or periodic batch jobs (adds latency, simpler implementation).

Change data capture reads the database's transaction log rather than querying tables directly, capturing every committed change without impacting query performance. A CDC processor transforms these log entries into events that downstream systems consume.

```
CDC processor:
    read database transaction log
    for each committed change:
        transform to event format
        publish to message stream

downstream consumers:
    subscribe to stream
    apply changes to secondary databases
```

This pattern decouples the primary database from secondary systems. The primary does not need to know which systems consume its changes, and downstream systems can be added or removed without modifying the primary. Tools like Debezium (for relational databases) and MongoDB Change Streams provide CDC capabilities out of the box.

**Failure handling:** When a secondary database is unavailable, should writes fail, succeed with degraded functionality, or queue for retry? Design explicit failure modes rather than discovering them in production.

**Trade-offs:**

Operational complexity multiplies. Each database requires monitoring, backup, scaling, and expertise. Two databases are not twice as complex as one; they are more than twice as complex due to interaction effects.

Consistency is harder. Data in Redis may be stale relative to PostgreSQL. Search results may not reflect recent writes. Document these consistency windows and design around them.

Debugging spans systems. A bug might involve the interaction between PostgreSQL state, Redis cache, and Elasticsearch index. Observability needs to span all systems.

## Common Pitfalls

- **Using relational databases for everything by default.** PostgreSQL can do many things, but that doesn't mean it should. If 90% of your access is simple key-value lookups, the overhead of SQL parsing, query planning, and connection management adds unnecessary latency. Match the database to the access pattern.

- **Choosing databases based on hype rather than requirements.** Vector databases are not always the answer for AI applications; many ML features work fine with traditional databases. NoSQL was not always the answer for scale; many "web scale" applications run on well-tuned PostgreSQL. Start with requirements, then choose tools.

- **Ignoring operational complexity.** A three-database polyglot architecture requires three times the monitoring, three times the backup procedures, three times the on-call expertise. Managed services reduce but do not eliminate this burden. Simpler architectures fail less.

- **Underestimating migration costs.** Changing database types mid-project is expensive. Data migration, code changes, and testing take months. Choose thoughtfully upfront; "we can always change it later" is more expensive than it sounds.

- **Over-engineering early.** A single PostgreSQL instance handles more than most applications need. Start simple, measure actual bottlenecks, and add complexity only when measurements justify it. Premature optimization applies to architecture too.

- **Neglecting consistency requirements.** "Eventual consistency is fine" is true until it isn't. A user creating an account and immediately being told "account not found" destroys trust. Map consistency requirements to each operation; don't accept eventual consistency as a blanket default.

- **Forgetting that databases fail.** Replicas lag. Leaders fail over. Network partitions happen. Design for database unavailability: retries, circuit breakers, graceful degradation. The database is a dependency, not a guarantee.

## Summary

- **Match the database to the access pattern.** Relational databases for transactions and complex queries, document stores for flexible schemas, key-value stores for simple lookups, wide-column databases for write-heavy workloads, vector databases for similarity search, search databases for full-text queries.

- **Relational databases remain the default for good reason.** ACID transactions, flexible queries, and decades of reliability. Start here unless specific requirements point elsewhere.

- **Key-value stores excel at simple lookups with aggressive latency requirements.** Sessions, caching, feature flags: when access is by known key and latency matters, key-value stores deliver sub-millisecond performance.

- **Write-heavy workloads need specialized solutions.** Wide-column databases (Cassandra, ScyllaDB) and time-series databases handle write volumes that would overwhelm traditional databases.

- **Read-heavy workloads benefit from caching and replicas.** Distribute reads across replicas, but design for replication lag and eventual consistency.

- **Fire-and-forget trades durability for latency.** Acceptable for analytics and telemetry where statistical accuracy matters more than perfect completeness.

- **WORM patterns provide immutability for audit logs and event sourcing.** Plan for storage growth and query patterns over large historical datasets.

- **Vector databases enable semantic search and ML-powered features.** But they require embedding pipelines and add complexity; use when similarity search is genuinely required.

- **Polyglot persistence uses the right database for each access pattern.** Powerful but operationally complex. Justify the complexity with clear requirements.

- **Start simple, measure, and add complexity only when needed.** A well-tuned PostgreSQL handles more than most applications require.

## References

1. **MongoDB Documentation** - "Transactions" covers multi-document ACID guarantees and performance considerations. https://www.mongodb.com/docs/manual/core/transactions/

2. **Redis Documentation** - "How Fast is Redis?" provides benchmark methodology and typical performance numbers. https://redis.io/docs/management/optimization/benchmarks/

3. **Redis Documentation** - "Persistence" covers RDB snapshots and AOF durability options. https://redis.io/docs/management/persistence/

4. **DataStax** - "Cassandra Case Studies" documents large-scale Cassandra deployments. https://www.datastax.com/resources/case-studies

5. **PostgreSQL Documentation** - "Streaming Replication" covers replica setup and lag monitoring. https://www.postgresql.org/docs/current/warm-standby.html

6. **HikariCP Wiki** - "About Pool Sizing" provides guidance on connection pool configuration. https://github.com/brettwooldridge/HikariCP/wiki/About-Pool-Sizing

7. **Fowler, Martin** - "Event Sourcing" pattern description. https://martinfowler.com/eaaDev/EventSourcing.html

8. **Lewis, Patrick et al.** (2020) - "Retrieval-Augmented Generation for Knowledge-Intensive NLP Tasks." Introduces RAG architecture. https://arxiv.org/abs/2005.11401

9. **Karpukhin, Vladimir et al.** (2020) - "Dense Passage Retrieval for Open-Domain Question Answering." Dense retrieval foundations. https://arxiv.org/abs/2004.04906

10. **Kleppmann, Martin** (2017) - *Designing Data-Intensive Applications*. O'Reilly Media. Comprehensive coverage of database internals and distributed systems.

## Next: [Chapter 8: Asynchronous Processing and Queuing](./08-async-queuing.md)

Having selected appropriate data stores, we now examine patterns that remove database operations from the critical request path entirely. The next chapter covers message queues, event-driven architectures, and asynchronous processing patterns that improve responsiveness by deferring non-essential work.
