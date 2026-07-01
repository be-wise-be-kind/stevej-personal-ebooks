# Chapter 8: Database Access Patterns: Common Performance Mistakes

![Chapter 8 Opener](../assets/ch08-opener.html)

\newpage

## Overview

Chapter 7 addressed the strategic question of database selection: which storage engine fits which data model and access pattern. That choice determines what operations are available to us. This chapter addresses the subsequent question: given the right database, how do we access it in ways that perform well under production load?

The two questions are related but distinct. A team can choose PostgreSQL correctly for a transactional workload and still produce an API that grinds to a halt at scale, because the access patterns layered on top of that database create contention, excessive round trips, or lock chains that were invisible during development. These problems have a common characteristic: they are imperceptible at development scale and catastrophic at production scale.

This chapter examines eight areas where access patterns determine performance:

1. **Transaction scope and duration**: how long locks are held and what work belongs inside a transaction boundary
2. **Connection pool management**: sizing, leak detection, and the thundering herd problem
3. **The N+1 query problem**: how a single ORM call becomes thousands of queries at scale
4. **Lock contention and deadlocks**: when and how locks cascade into application errors
5. **ORM performance traps**: cartesian product explosions, SELECT *, and lazy loading defaults
6. **Bulk operations**: the difference between 10,000 round trips and 10 batched inserts
7. **Indexing mistakes**: missing FK indexes, wrong composite index column order, and the cost of over-indexing
8. **Pagination at scale**: why OFFSET becomes progressively more expensive and how keyset pagination solves it

The guidance in each section is grounded in specific, measurable results. "Use connection pooling" is not useful advice. "A pool sized to measured concurrency, with a 5-second connection leak threshold and exponential jitter on retry, reduced connection exhaustion errors from 200/hour to 0/hour during load testing" is actionable. Where benchmarks and vendor documentation provide concrete numbers, we use them.

## Key Concepts

### Transaction Scope and Duration

In an ACID-compliant data store, a transaction is a unit of atomicity: either all of its writes commit, or none do. This guarantee is not universal. It is provided by relational databases (PostgreSQL, MySQL with InnoDB, and similar) and by a growing number of distributed databases, but many data stores offer it only under specific configurations, only within a single partition, or not at all. As Chapter 7 discussed, document stores, key-value stores, and wide-column databases vary widely in their transactional guarantees, and some trade atomicity for horizontal write scalability. The discussion that follows assumes an ACID-compliant store, because that is where transaction scope is both a correctness tool and a performance concern. If your store does not provide atomicity, the scoping guidance still applies to lock duration, but the all-or-nothing semantics do not.

Within such a store, transactions hold locks on the rows they modify, and those locks block concurrent access to the same rows until the transaction commits or rolls back. The performance implication follows directly: the longer a transaction runs, the longer other operations wait.

Leapcell's 2024 analysis of production PostgreSQL workloads found that transactions exceeding 5 seconds double the risk of timeout cascades and deadlocks compared to transactions completing within 2 seconds [Source: Leapcell, 2024]. This is not because 5 seconds is some intrinsic threshold; it is because in a system under load, 5 seconds is long enough for many other operations to queue up behind the same locks, and when the long-running transaction finally commits, the queued operations all proceed simultaneously, creating a burst that can exceed connection pool capacity.

The HTTP request lifecycle is a tempting but incorrect boundary for transactions. Developers often open a transaction at the start of a request handler and commit at the end, wrapping everything the handler does. The problem is that request handlers routinely include work that has no business being inside a transaction:

- Input validation (no database writes needed)
- Business logic computation (CPU-only work)
- Calls to external APIs (introduces network latency into the lock window)
- Audit logging (often tolerable as a separate, non-atomic write)

Correct transaction scope is the smallest set of writes that must succeed or fail together as a single unit of business logic. For most operations, this is 2-4 queries. An order creation might atomically debit inventory and insert the order row. Everything else, fetching the product record, validating the customer, calling a payment gateway, sending a confirmation, happens outside that boundary.

<!-- DIAGRAM: Two-panel timeline showing transaction scope comparison. Left panel labeled "Wide Transaction (Bad)": a horizontal bar spanning the full request lifecycle, from "Validate input" through "Fetch user", "Call payment API" (marked with a lightning bolt to indicate external call), "Compute totals", "INSERT order", "UPDATE inventory" to "Send email". The lock icon appears at the start of this bar and a red zone highlights the entire duration (~800ms). Concurrent request arrows on the left are shown blocked (red X) during this window. Right panel labeled "Narrow Transaction (Good)": the same operations are shown as a sequence, but the lock icon and blue transaction bar covers only "INSERT order" + "UPDATE inventory" (~20ms). All other operations appear before or after the transaction bar. Concurrent request arrows show only a brief blocked period. Both timelines share the same x-axis scale. -->

![Transaction Scope: Wide vs. Narrow](../assets/ch08-transaction-scope.html)

\newpage

The pattern that causes the most severe cascades in practice is the long-running background job that holds a transaction open across hundreds of records. A nightly export job that opens a transaction, reads 50,000 rows, enriches each with external data, and commits at the end locks those rows for the full duration of the job. Moving preparatory work outside the transaction boundary and committing in small batches of 100-500 records eliminates this contention entirely.

Concretely: validate and prepare all records outside the transaction, open a transaction, write one batch, commit, open the next transaction for the next batch. The lock window per batch is milliseconds rather than minutes.

```
// Bad: transaction wraps entire export job
begin transaction
for each of 50,000 records:
    fetch record
    call external enrichment API  // network I/O inside lock window
    write enriched record
commit transaction

// Good: narrow transaction per batch
fetch and enrich all records (outside transaction)
for each batch of 500 enriched records:
    begin transaction
    write batch
    commit transaction
```

Alert on transactions exceeding 2-3 seconds. PostgreSQL exposes `pg_stat_activity` with `state = 'idle in transaction'` and elapsed time; querying this table on a schedule and alerting on outliers catches problems before they cascade.

### Connection Pool Management

Establishing a database connection is expensive. The process involves a TCP handshake (1-3 round trips at typical LAN latency), TLS negotiation if the connection is encrypted (2 additional round trips), PostgreSQL authentication (1-2 round trips), and session initialization. On a datacenter-internal connection with 0.5ms RTT, this adds up to roughly 5-15ms per new connection. At 100 requests per second, without pooling, this overhead alone accounts for 500-1,500ms of aggregate database latency per second [Source: HikariCP Documentation, 2024].

Connection pools maintain a set of pre-established connections, amortizing this overhead across many requests. The correct pool size is derived from measured concurrency, not from the database's `max_connections` limit. The sizing formula is:

```
pool_size = (concurrent_threads * 1.2) + headroom_buffer
```

A service handling 20 concurrent requests needs roughly 24-26 connections, not 100. Oversizing pools creates a different problem: when every application instance maintains a large pool, the aggregate connection count across all instances approaches the database's connection limit, reducing the capacity margin available for administrative connections and monitoring queries.

In multi-tenant architectures where each tenant's database is separate, the multiplication becomes significant. A naive implementation that creates one database engine (and therefore one connection pool) per tenant on first access produces: 50 connections per pool × 200 tenants = 10,000 potential connections. The correct approach is to scope pools to unique database hosts, not to tenants. Many tenants often share a host, and a single pool per host serves all of them.

<!-- DIAGRAM: Two-panel diagram showing thundering herd problem. Left panel labeled "Thundering Herd": show a pool with 10 connection slots, all marked red (exhausted). Below the pool, 50 request arrows are stacked up (yellow, "waiting"). When the pool recovers (green flash at top), all 50 arrows rush to the pool simultaneously, labeled "stampede". A DB cylinder on the right shows a spike in connections with a red overload zone. Right panel labeled "Jitter + Queue": same pool exhaustion scenario, but the 50 waiting requests are shown entering a queue. A timer with wavy intervals (representing jitter: 100ms, 130ms, 95ms, 120ms) releases them one at a time in staggered groups. The DB cylinder shows a smooth, steady connection rate. Both panels share the same vertical layout. Annotate the left panel with "all waiters released simultaneously" and the right with "staggered release prevents stampede". -->

![Connection Pool: Thundering Herd vs. Jittered Release](../assets/ch08-connection-pool.html)

\newpage

**Thundering herd** occurs when a pool is exhausted, multiple requests queue up waiting for a connection, and when a connection becomes available, all waiters are notified simultaneously and compete for it. The solution is to add random jitter to retry intervals and release pool waiters sequentially rather than broadcasting availability. Redis's 2024 analysis of cache stampede patterns applies equally to connection pools: staggering releases by 50-200ms of random jitter absorbs the burst without queuing theory-level analysis [Source: Redis, 2024].

**Connection leak detection** is the first diagnostic step when pool utilization grows over time without a corresponding growth in traffic. A connection leak occurs when a code path acquires a connection and fails to return it, either because of a missing `finally` block, an unhandled exception, or an early return. HikariCP's `leakDetectionThreshold` configuration logs a stack trace for any connection held longer than a configurable duration (5 seconds is a practical starting point). Enabling this before increasing pool size is important: increasing pool size masks leaks rather than fixing them. A pool that grows from 80% utilization to 95% over 48 hours is almost always leaking connections, not experiencing legitimate load growth.

Timeout hierarchy for production pools:

| Timeout | Recommended Value | Purpose |
|---------|-------------------|---------|
| Connection timeout | 5 seconds | Fail fast; surface pool exhaustion immediately |
| Idle timeout | 10 minutes | Release connections unused by traffic |
| Max lifetime | 30 minutes | Recycle to avoid stale connections from database-side expiry |
| Leak detection threshold | 5 seconds | Log stack trace for abnormally held connections |

### The N+1 Query Problem

The N+1 query problem is a specific failure mode of lazy loading: the application issues 1 query to fetch a list of N records, then issues N additional queries to fetch related data for each record. At development scale with 10 records, this produces 11 queries, which is imperceptible. At production scale with 10,000 records, it produces 10,001 queries. At 1ms per query, this is 10 seconds of database time for a single request that should complete in under 100ms.

The problem is invisible in development because developers test with small datasets. The correct detection approach is query logging in staging: enable per-request query count tracking and alert when a single request exceeds a threshold (50 queries is a reasonable starting point for most APIs). Distributed tracing tools will show dense clusters of identical queries as a visual signature of N+1 patterns.

The solution hierarchy, ordered by applicability:

1. **Eager loading with a JOIN**: issue 1 query that fetches the primary records and related records together. Best for single-object relationships (many-to-one, one-to-one) where the related record is always needed.

2. **Batch loading (IN query)**: collect all foreign key IDs from the primary result set, then issue 1 query with `WHERE id IN (...)` to fetch all related records at once. Map them back by ID in application memory.

3. **DataLoader pattern**: for GraphQL APIs where the same relationship may be resolved from multiple query paths simultaneously, a DataLoader batches all resolution requests within a single tick of the event loop, then issues a single batch query.

```
// Bad: N+1
for each order in orders:
    fetch order.customer    // 1 query per order; N queries total

// Good: eager load (joined)
fetch all orders with joinedload(customer)  // 1 query total

// Good: batch load (IN query)
customer_ids = collect order.customer_id for each order
customers = fetch customers where id IN customer_ids  // 1 query total
map each order.customer = customers[order.customer_id]
```

<!-- DIAGRAM: Line chart. X-axis labeled "Number of Records" with values 10, 100, 1,000, 10,000. Y-axis labeled "Total Queries Issued" ranging from 1 to 10,001. Two lines: (1) "N+1 Loading", a straight line from (10, 11) to (10000, 10001), steep slope, colored red. (2) "Batch Loading", a nearly flat line staying at 1-2 queries regardless of record count, colored green. Annotate the N+1 line at (10000, 10001) with "10,001 queries". Annotate the batch loading line with "2 queries (always)". Add a light gray annotation band at the "imperceptible" zone (below 50 queries) and label it "Invisible in development". -->

![N+1 Query Growth: N+1 vs. Batch Loading](../assets/ch08-n-plus-one.html)

\newpage

**Selectin loading** is a specific variant of batch loading supported by SQLAlchemy and similar ORMs. Instead of joining related records (which creates a cartesian product when the relationship is a collection), selectin loading issues a separate SELECT for related records using an IN clause, then assembles the result in memory. For one-to-many relationships, this avoids the cartesian product problem: fetching 100 orders with 10 line items each via a JOIN returns 1,000 rows; selectin loading returns 100 rows for orders and 1,000 rows for line items in separate queries, using less memory and less network bandwidth [Source: SQLAlchemy Documentation, 2024].

Lazy loading is appropriate only when a relationship is genuinely optional, accessed by a small fraction of code paths, and the application explicitly opts into per-access loading with full awareness of the query cost. Leaving lazy loading as the ORM default for production hot paths is a configuration that performs well in development and degrades under production load.

### Lock Contention and Deadlocks

Database locks serialize concurrent access to shared rows. When transactions hold locks longer than necessary, or when transactions acquire locks in inconsistent order, the result is contention (operations waiting) or deadlocks (operations waiting in a cycle that cannot resolve without external intervention).

**Lock escalation with SELECT FOR UPDATE**: acquiring a write lock on a row via `SELECT FOR UPDATE` blocks concurrent reads (in databases that do not use MVCC for reads), blocks concurrent writes to the same row, and, in PostgreSQL, blocks concurrent INSERTs of rows that reference the locked row via a foreign key. Cybertec's 2024 analysis found that `SELECT FOR UPDATE` on parent rows can block child-row INSERTs in workloads with referencing relationships, reducing throughput on write-heavy endpoints [Source: Cybertec, 2024].

`SELECT FOR NO KEY UPDATE` is a less restrictive alternative introduced in PostgreSQL 9.3. It acquires a write lock on the row's non-key columns, allowing concurrent INSERTs of child rows whose foreign key references the locked row's primary key. For update operations that do not modify the primary key, this is almost always the correct choice over `SELECT FOR UPDATE` [Source: Cybertec, 2024].

For work queue patterns where multiple workers compete to claim tasks, `SELECT FOR UPDATE SKIP LOCKED` allows each worker to acquire the next available unlocked row without waiting for rows locked by other workers. Without `SKIP LOCKED`, workers block each other; with it, they fan out across available work without contention.

**Deadlock formation and prevention**: a deadlock occurs when transaction A holds lock X and waits for lock Y, while transaction B holds lock Y and waits for lock X. Neither can proceed. The database detects the cycle and terminates one transaction with an error (SQLSTATE 40P01 in PostgreSQL, error 1213 in MySQL).

Prevention requires consistent lock ordering across all transactions: if every transaction that touches rows in table_x and table_y always acquires the lock on table_x first, no deadlock can form between those transactions. This is a code-level convention that must be applied consistently; the database cannot enforce it automatically.

<!-- DIAGRAM: Two-panel diagram. Left panel labeled "Deadlock Formation": Transaction A (blue rectangle) holds a lock icon on "Row 1" and has an arrow pointing toward "Row 2" labeled "waiting". Transaction B (orange rectangle) holds a lock icon on "Row 2" and has an arrow pointing toward "Row 1" labeled "waiting". A red circular arrow connects A→B→A labeled "deadlock: neither can proceed". Right panel labeled "Consistent Lock Order (Prevention)": Transaction A (blue) acquires "Row 1" first (green lock), then "Row 2" (green lock). Transaction B (orange) also acquires "Row 1" first (shown with a wait indicator, a yellow hourglass), then "Row 2" after A releases. An arrow shows B queued behind A for Row 1, with text "B waits; no cycle forms". Both panels should share the same row layout for visual comparison. -->

![Lock Strategies: Deadlock Formation vs. Prevention](../assets/ch08-lock-strategies.html)

\newpage

Application-level handling for deadlocks: catch the database error, roll back, apply exponential backoff with jitter, and retry. The default retry count of 1 in most frameworks provides no meaningful recovery. A retry configuration of 3-5 attempts with 50-500ms jittered backoff handles the vast majority of transient deadlocks.

```
// Deadlock retry logic
attempts = 0
max_attempts = 5
while attempts < max_attempts:
    begin transaction
    result = try:
        execute operations
        commit transaction
        return result
    catch deadlock_error:
        rollback transaction
        wait for (50ms * 2^attempts) + random(0, 50ms)
        attempts = attempts + 1
raise error "max deadlock retries exceeded"
```

**Optimistic vs. pessimistic locking** represent two strategies for managing concurrent access to the same record:

| Strategy | When to Use | Trade-off |
|----------|-------------|-----------|
| Optimistic (version column) | Low contention, high read load | More application-level retries on conflict; no blocking while reading |
| Pessimistic (SELECT FOR UPDATE) | High contention, financial transfers, inventory reservation | Serializes access; reduces throughput; eliminates retry overhead |

The default for most APIs should be optimistic locking. Reserve pessimistic locking for code paths where contention is measured (not assumed) and where the cost of retries exceeds the cost of serialization.

### ORM Performance Traps

Object-relational mappers reduce boilerplate and provide a type-safe interface to the database, but they introduce performance failure modes that are not visible in the ORM's API surface. Understanding these patterns is necessary for any team using an ORM in production.

**Cartesian product explosion** occurs when an ORM fetches a complex entity graph using a single JOIN query. If a `Product` entity has 3 categories, 4 images, and 5 tags, and we fetch 10 products with all their relationships via a single JOIN, the database returns 10 × 3 × 4 × 5 = 600 rows for 10 logical entities. Adding reviews (say, 10 per product) pushes this to 6,000 rows. The ORM deduplicates these rows in memory, but the network transfer, memory allocation, and database processing costs scale with the row count, not the entity count [Source: Tideways, n.d.].

The correct approach for collection relationships is selectin loading: issue a separate query for each relationship type using an IN clause on the parent IDs. This produces a predictable number of rows (parent count + total child count) rather than an exponential product.

```
// Bad: cartesian product via joined loading
fetch 10 products with joined(categories, images, tags, reviews)
// 10 × 3 × 4 × 5 × 10 = 6,000 rows transferred

// Good: selectin loading per relationship
fetch 10 products                                         // 10 rows
fetch categories where product_id IN [product_ids]        // ~30 rows
fetch images where product_id IN [product_ids]            // ~40 rows
fetch tags where product_id IN [product_ids]              // ~50 rows
fetch reviews where product_id IN [product_ids]           // ~100 rows
// Total: ~230 rows, assembled in memory
```

**SELECT * on read-heavy paths**: ORMs default to selecting all columns. On tables with wide schemas (text blobs, JSON columns, binary data), this transfers significantly more data than necessary. Column projection to the 2-5 fields actually used by an endpoint reduces network transfer, reduces memory allocation in both the database and application, and can allow the database to satisfy the query from an index alone (index-only scan) without touching the heap.

**Conditional eager loading** creates an inconsistency between callers. A pattern like `if kwargs.get('eagerload'): apply_joinedload()` means most callers receive lazy-loaded relationships and will generate N+1 queries at scale. Make eager loading explicit and consistent for known hot paths; do not rely on opt-in flags that callers may not know to pass.

**Raw SQL for complex operations**: ORMs are optimized for single-entity CRUD. For complex aggregations, multi-table updates, bulk operations, and analytical queries, the ORM abstraction adds overhead without benefit. Using raw SQL or native bulk-load protocols for these operations is not a failure of abstraction; it is the correct tool selection.

### Bulk Operations

Single-row INSERT operations are expensive at scale because each round trip includes query parsing, planning, execution, and a commit flush to disk (for durable writes). The cost per row is dominated by round-trip latency and per-transaction overhead rather than by the work of writing the row itself.

Microsoft's 2024 benchmark of SQL Server INSERT performance measured 1,000 single-row INSERTs over a datacenter-external connection at 129 seconds. The same 1,000 rows inserted as a batch using table-valued parameters completed in 2.6 seconds: a 50x improvement [Source: Microsoft, 2024]. The ratio narrows for same-datacenter connections (where round-trip latency is lower), but the fundamental advantage of batching remains.

For PostgreSQL specifically, tigerdata.com's analysis found that the optimal INSERT batch size is approximately 1,000 rows per statement, balancing parse overhead against memory pressure from large value lists [Source: tigerdata.com, 2024]. Beyond 10,000 rows, the COPY protocol (PostgreSQL) or LOAD DATA INFILE (MySQL) bypasses the SQL parser entirely and achieves substantially higher throughput by streaming row data in a compact binary or CSV format.

<!-- DIAGRAM: Grouped bar chart. X-axis has four groups: "100 rows", "1,000 rows", "10,000 rows", "100,000 rows". Y-axis is "Time to Insert (seconds)" on a log scale from 0.01 to 1000. Each group has two bars side by side: (1) "Single-row INSERT" in red, (2) "Batched INSERT (1000 rows/batch)" in green. Example values (approximate, consistent with the 50x ratio): 100 rows: red=1.3s, green=0.05s; 1,000 rows: red=13s, green=0.26s; 10,000 rows: red=130s, green=2.6s; 100,000 rows: red=1300s, green=26s. Annotate each pair with the speedup ratio ("50x faster"). Add a note below the 10,000 and 100,000 groups: "Consider COPY protocol for >10k rows". -->

![Bulk Insert Performance: Single-Row vs. Batched](../assets/ch08-bulk-insert.html)

\newpage

Batch size guidance depends on the operational context:

| Context | Batch Size | Rationale |
|---------|------------|-----------|
| Real-time path (latency-sensitive) | 100-1,000 rows | Balances throughput with response time; smaller batches reduce tail latency |
| Background job (throughput-optimized) | 5,000-10,000 rows | Maximizes throughput; response time not a constraint |
| Very large imports (>100k rows) | COPY / LOAD DATA | Bypasses parser; highest throughput |

```
// Bad: 10,000 round trips
for each record in records:
    INSERT INTO events (type, data, created_at) VALUES (record)

// Good: 10 round trips (batches of 1,000)
for each batch of 1000 records from records:
    INSERT INTO events (type, data, created_at)
    VALUES (batch_row_1), (batch_row_2), ..., (batch_row_1000)
```

One operational consideration: large batches hold their transaction open longer, which reintroduces the lock contention problem from the transaction scope section. For write-heavy workloads with concurrent readers, batches of 500-1,000 rows balance throughput against lock duration better than batches of 10,000 rows.

### Indexing Mistakes

Indexes accelerate reads by maintaining a sorted data structure (typically a B-tree) that allows the database to locate rows without scanning the full table. The trade-off is write overhead: every INSERT, UPDATE, and DELETE must also update each index on the affected table. Adding indexes indiscriminately increases write latency and storage consumption. Omitting necessary indexes forces full table scans that grow linearly with table size.

**Missing foreign key indexes**: PostgreSQL does not automatically create indexes on foreign key columns. When a DELETE or UPDATE is performed on a parent row, PostgreSQL must verify that no child rows reference it. Without an index on the child table's foreign key column, this check requires a sequential scan of the entire child table. Cybertec's 2024 analysis found that missing FK indexes on large child tables cause table-level lock escalation during parent-row modifications, blocking all concurrent reads and writes to the child table [Source: Cybertec, 2024].

A practical audit: query `pg_constraint` for foreign key constraints, then cross-reference against `pg_index` to identify FK columns with no corresponding index. This should be part of every schema review process.

PostgreSQL 16 benchmarks showed 15% faster SELECT performance on join-heavy queries when FK columns were indexed, due to improved join path selection by the query planner [Source: PostgreSQL Global Development Group, 2024].

**Composite index column order**: a composite index on `(a, b, c)` can satisfy queries that filter on `a`, on `a AND b`, or on `a AND b AND c`. It cannot satisfy a query that filters only on `b` or only on `c`. The leftmost column in the index must match the most selective filter in the query. "Selective" means the column that narrows the result set most aggressively.

```sql
-- Table: orders (user_id, status, created_at)

-- Correct: most selective column first (user_id is highly selective; status has few distinct values)
CREATE INDEX idx_orders_user_status ON orders (user_id, status);

-- Query that uses this index efficiently:
SELECT * FROM orders WHERE user_id = 123 AND status = 'pending';

-- Query that cannot use the index (no leading user_id filter):
SELECT * FROM orders WHERE status = 'pending';  -- full scan or separate index needed
```

**Leading wildcard LIKE**: a query with `LIKE '%term'` cannot use a B-tree index because the match pattern does not have a known prefix. The database must scan every row and evaluate the pattern against each value. Full-text search indexes (PostgreSQL `tsvector`, Elasticsearch, Typesense) are the correct mechanism for substring and fuzzy matching.

**OR conditions across columns**: a query with `WHERE col_a = 1 OR col_b = 2` often cannot use a single index efficiently and forces a full table scan. The alternatives are: create separate indexes on `col_a` and `col_b` (the query planner may merge them with a bitmap scan), rewrite as `UNION` of two targeted queries, or rethink the data model if this query pattern is common.

**Index bloat from frequent deletes**: deleted rows leave dead entries in B-tree indexes. PostgreSQL's autovacuum process reclaims these entries, but high-delete workloads can outpace autovacuum's default schedule, causing indexes to grow without bound and scan performance to degrade. Scheduling regular VACUUM ANALYZE on high-delete tables and tuning autovacuum's `autovacuum_vacuum_scale_factor` for these tables is necessary maintenance.

Every index added slows INSERT, UPDATE, and DELETE operations on that table. Audit unused indexes quarterly using `pg_stat_user_indexes` (the `idx_scan` column shows how many times each index has been used since the last statistics reset). Indexes with zero scans over a 30-day measurement window are candidates for removal.

### Pagination at Scale

Pagination allows an API to return large result sets in manageable chunks. The two dominant implementations are OFFSET pagination and keyset (cursor-based) pagination, and they have dramatically different performance characteristics at scale.

**OFFSET pagination** works by instructing the database to skip a specified number of rows before returning results:

```sql
-- Page 1: return rows 1-20
SELECT * FROM events ORDER BY created_at LIMIT 20 OFFSET 0

-- Page 100: skip 1,980 rows, return 20
SELECT * FROM events ORDER BY created_at LIMIT 20 OFFSET 1980

-- Page 1,000: skip 19,980 rows, return 20
SELECT * FROM events ORDER BY created_at LIMIT 20 OFFSET 19980
```

The cost model of OFFSET is linear: the database must read and discard all `OFFSET` rows before it can return the requested `LIMIT` rows. CedarDB's 2024 analysis of OFFSET performance on PostgreSQL measured: page 1 (OFFSET 0) at approximately 10ms; page 100 (OFFSET 1,980) at approximately 500ms; page 1,000 (OFFSET 19,980) at over 5 seconds on a million-row table [Source: CedarDB, 2024].

OFFSET pagination also has a correctness problem: if rows are inserted or deleted between page requests, the offset shifts. A row inserted at position 5 while a client is reading page 3 causes page 4 to contain a duplicate of the last row from page 3. A row deleted from position 15 causes a row to be skipped entirely. These are not edge cases; they are routine in any actively written table.

**Keyset (cursor-based) pagination** uses a predicate on an indexed column rather than a row count:

```sql
-- Page 1: return first 20 rows
SELECT * FROM events ORDER BY created_at DESC LIMIT 20

-- Next page: rows older than the oldest row from the previous page
SELECT * FROM events
WHERE created_at < :last_cursor
ORDER BY created_at DESC LIMIT 20
```

The database executes this as an index seek: it finds the position of `last_cursor` in the `created_at` index and reads forward 20 entries. The cost is O(1) with respect to pagination depth: page 1,000 costs the same as page 1 [Source: CedarDB, 2024]. Keyset pagination is also correct under concurrent writes: because it is anchored to a column value rather than a row count, insertions and deletions elsewhere in the table do not affect the current page's results.

<!-- DIAGRAM: Line chart. X-axis labeled "Page Number" ranging from 1 to 1,000 with major ticks at 1, 100, 200, 500, 1000. Y-axis labeled "Query Time (ms)" ranging from 0 to 6000ms. Two lines: (1) "OFFSET Pagination" in red: starts at 10ms at page 1, rises to 500ms at page 100, and reaches 5,000ms at page 1,000 (concave-up curve). (2) "Keyset Pagination" in green: flat line at approximately 10ms across all page depths. Mark data points with dots at pages 1, 100, and 1000. Add dashed horizontal reference lines at 100ms (labeled "acceptable") and 1,000ms (labeled "user-visible degradation"). Annotate the OFFSET line at page 1000 with "5,000ms (5s)". -->

![Pagination Strategy: OFFSET vs. Keyset Performance](../assets/ch08-pagination.html)

\newpage

OFFSET pagination remains appropriate in limited contexts:

- Datasets under approximately 10,000 rows where the depth-related cost is small in absolute terms
- Infrequently updated data where offset drift is not a correctness concern
- Interfaces where users navigate by explicit page number (search results where "jump to page 47" is a supported interaction, and keyset would require iterating through 46 pages to get there)

For all other contexts, keyset pagination is the correct default. The implementation requires that the cursor column (or combination of columns) be indexed and that the sort order be stable and deterministic. If using a non-unique column as the cursor (e.g., `created_at`), add a tiebreaker column (e.g., `id`) to ensure stable ordering when multiple rows share the same cursor value.

```sql
-- Keyset with tiebreaker for non-unique cursor column
SELECT * FROM events
WHERE (created_at, id) < (:last_created_at, :last_id)
ORDER BY created_at DESC, id DESC
LIMIT 20
```

APIs that expose OFFSET pagination without a maximum depth limit allow clients to issue arbitrarily expensive queries. Enforce a maximum OFFSET or maximum page number at the API layer as a defensive measure, and include migration guidance in API documentation when transitioning to keyset pagination.

## Common Pitfalls

**Wrapping background jobs in a single transaction.** Jobs processing hundreds or thousands of entities should commit in small batches, not at the end of the full job. Holding a transaction open for the duration of a job lasting several minutes locks rows for that entire period and blocks all concurrent access to those rows. Commit every 100-500 records and treat each batch as an independent unit of work.

**Using default ORM lazy loading in production.** Lazy loading is a development convenience that defers queries until a relationship is accessed. Under production load with real record counts, it produces N+1 query patterns that are orders of magnitude more expensive than the equivalent eager or batch load. Audit every relationship's loading strategy and assign an explicit strategy based on the access pattern of each code path.

**Ignoring query count in code review.** A method that appears to perform a simple database operation may trigger N additional queries through lazy-loaded relationships. Review query logs during development using slow query logging or ORM debug output, and set per-request query count alerts in staging environments. A request that issues more than 50 queries is almost always doing something that should be rewritten.

**Increasing pool size without investigating connection leaks.** A steadily growing pool utilization metric, without a corresponding growth in traffic, indicates that connections are being acquired but not returned. Enabling connection leak detection (e.g., HikariCP's `leakDetectionThreshold`) before increasing pool size is essential; a larger pool only delays the exhaustion rather than fixing the leak.

**SELECT FOR UPDATE as the default concurrency mechanism.** `SELECT FOR UPDATE` serializes access to the locked row and blocks concurrent INSERTs of referencing child rows. Most concurrent access patterns are better served by optimistic locking using a version column. Reserve pessimistic locking for paths where contention is measured and high, and where the cost of application-level retries (from optimistic lock conflicts) exceeds the throughput cost of serialization.

**No deadlock retry logic.** Deadlocks are expected behavior under concurrent load and are not programming errors; they are a signal that two transactions tried to acquire the same locks in different order at the same time. Applications that do not catch SQLSTATE 40P01 (PostgreSQL) or error 1213 (MySQL), roll back, and retry surface these as user-visible errors. Implement retry logic with exponential backoff and jitter for any transaction that modifies multiple rows.

**Missing foreign key indexes.** Schema migration tools (Alembic, Flyway, Liquibase) create foreign key constraints but do not always create corresponding indexes on the referencing column. Without these indexes, DELETE and UPDATE operations on parent rows trigger full sequential scans of child tables. Audit every FK column in the schema during code review and add the indexes if they are missing.

**OFFSET pagination without a depth limit.** An API endpoint that accepts arbitrary page numbers allows clients to request page 10,000 of a million-row table, which translates to OFFSET 199,980: a query that takes seconds on most hardware. Without a maximum page depth enforced at the API layer, deep pagination becomes a denial-of-service vector. Enforce a maximum OFFSET at the application layer and migrate to keyset pagination for any dataset that grows without bound.

## Summary

- Scope transactions to the smallest cohesive business operation, typically 2-4 atomic writes. Alert on transactions exceeding 2-3 seconds using `pg_stat_activity` queries on a schedule.
- Size connection pools to measured concurrency using `(concurrent_threads × 1.2) + headroom_buffer`. Enable connection leak detection before increasing pool size; growing pool utilization without traffic growth almost always indicates a leak.
- N+1 query patterns are undetectable at development scale (10 records = 11 queries) and severe at production scale (10,000 records = 10,001 queries). Set per-request query count alerts in staging environments and review query logs during code review.
- Default to optimistic locking with version columns. Reserve `SELECT FOR UPDATE` for code paths where contention is measured and serialization is required. Use `SELECT FOR NO KEY UPDATE` when the primary key is not being modified.
- Selectin loading avoids cartesian product explosions for collection relationships; use it instead of joined loading for one-to-many relationships. Joined loading is appropriate for single-object (many-to-one) relationships where no product expansion occurs.
- Bulk-insert in batches of 100-1,000 rows for real-time paths; use 5,000-10,000 rows for background jobs. For imports exceeding 10,000 rows, use COPY (PostgreSQL) or LOAD DATA INFILE (MySQL) to bypass the SQL parser.
- Index every foreign key column explicitly; they are not created automatically by PostgreSQL. Composite index column order must place the most selective (most filtered) column first; a query filtering only on the second column cannot use the index.
- Replace OFFSET pagination with keyset pagination when datasets exceed approximately 10,000 rows or pagination depth is unbounded. Enforce a maximum OFFSET at the API layer as a defensive measure for any OFFSET-based endpoint that remains.

## References

1. **Leapcell** (2024). "Optimal Database Transaction Scope in Web Requests." leapcell.io/blog. https://leapcell.io/blog/optimal-database-transaction-scope-in-web-requests

2. **Cybertec PostgreSQL International GmbH** (2024). "SELECT FOR UPDATE Considered Harmful in PostgreSQL." cybertec-postgresql.com. https://www.cybertec-postgresql.com/en/select-for-update-in-postgresql/

3. **Cybertec PostgreSQL International GmbH** (2024). "Index Your Foreign Key." cybertec-postgresql.com. https://www.cybertec-postgresql.com/en/index-your-foreign-key/

4. **Redis** (2024). "How to Tame the Thundering Herd Problem." redis.io/blog. https://redis.io/blog/thundering-herd-problem/

5. **CedarDB** (2024). "Offset Considered Harmful: The Surprising Complexity of Pagination in SQL." cedardb.com/blog. https://cedardb.com/blog/sql_pagination/

6. **Microsoft** (2024). "Optimize Large SQL Server Insert, Update, and Delete Processes by Using Batches." mssqltips.com. https://www.mssqltips.com/sqlservertip/1180/optimize-large-sql-server-insert-update-and-delete-processes-using-batches/

7. **Tideways** (n.d.). "5 Doctrine ORM Performance Traps You Should Avoid." tideways.com/profiler/blog. https://tideways.com/profiler/blog/5-doctrine-orm-performance-traps-you-should-avoid

8. **SQLAlchemy** (2024). "Relationship Loading Techniques." SQLAlchemy Documentation. docs.sqlalchemy.org. https://docs.sqlalchemy.org/en/20/orm/loading_relationships.html

9. **PostgreSQL Global Development Group** (2024). "Transaction Isolation." PostgreSQL Documentation. postgresql.org. https://www.postgresql.org/docs/current/transaction-iso.html

10. **HikariCP** (2024). "HikariCP Configuration." GitHub. https://github.com/brettwooldridge/HikariCP#gear-configuration-knobs-baby

11. **tigerdata.com** (2024). "PostgreSQL Bulk Insert Performance." tigerdata.com. https://tigerdata.com/blog/postgresql-bulk-insert-performance

---

## Next: [Chapter 9: Asynchronous Processing and Queuing](./09-async-queuing.md)

Where database access patterns determine how individual requests perform, asynchronous processing determines how systems behave under sustained load and at scale.
