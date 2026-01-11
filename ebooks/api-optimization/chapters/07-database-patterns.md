# Chapter 6: Database Performance Patterns

![Chapter 7 Opener](../assets/ch07-opener.html)

\newpage

## Overview

Database operations represent one of the most common bottlenecks in API performance. When a user reports that an endpoint is slow, the root cause frequently traces back to the database layer: an unindexed query scanning millions of rows, dozens of queries executing where one would suffice, or connections exhausted by a traffic spike.

This chapter takes an empirical approach to database optimization. We will examine how to identify database bottlenecks through measurement, understand the underlying causes, and apply targeted solutions. The patterns we cover here—proper indexing, eliminating N+1 queries, connection pooling, and read scaling—can transform an API from struggling under load to handling orders of magnitude more traffic.

The key insight is that database optimization is not about applying every technique indiscriminately. Instead, we measure first, identify the specific bottleneck, and apply the minimum intervention needed. An index that eliminates a full table scan might improve query performance by several orders of magnitude. Blindly adding indexes everywhere, however, slows down writes and wastes storage. The empirical approach guides us to the right optimizations.

<!-- DIAGRAM: Database performance bottleneck identification flowchart: Slow API response -> Check query count (N+1?) -> Check query execution time (Missing index? Full table scan?) -> Check connection wait time (Pool exhausted?) -> Check replication lag (Read replica issues?) -->

![Database Performance Bottleneck Identification Flowchart](../assets/ch06-bottleneck-flowchart.html)

## Key Concepts

### The N+1 Query Problem

The N+1 query problem is one of the most common performance issues in API development, particularly when using Object-Relational Mappers (ORMs). It occurs when code executes one query to fetch a list of N items, then executes N additional queries to fetch related data for each item—resulting in N+1 total queries where a single query with a JOIN would suffice.

Consider an API endpoint that returns a list of blog posts with their authors. The naive approach triggers a separate query for each author, while the optimized approach uses eager loading to fetch everything in a single round-trip (see Example 7.1).

The performance impact of N+1 queries grows linearly with the data set size. If each database round-trip takes 1-5ms (a typical range for local database connections), fetching 100 posts with authors takes 101-505ms in the N+1 pattern. With a JOIN-based solution, the same data retrieves in a single round-trip of 2-10ms.

<!-- DIAGRAM: N+1 problem visualization showing two scenarios: Left side shows "N+1 Pattern" with 1 query returning N posts, then N individual queries for authors (total time: N * round-trip latency). Right side shows "JOIN Pattern" with 1 query returning posts with authors (total time: 1 * round-trip latency) -->

![N+1 Query Problem vs JOIN Solution](../assets/ch06-n-plus-one.html)

### Indexing Strategies

Indexes are the primary tool for accelerating database reads. Without an index, the database must scan every row in a table to find matching records—an O(n) operation. With a proper index, the database can locate records in O(log n) time for B-tree indexes or O(1) for hash indexes.

**B-tree Indexes**

B-tree (Balanced tree) indexes are the default and most versatile index type. They support equality queries, range queries, and sorted retrieval. B-tree indexes are effective for queries using operators like `=`, `<`, `>`, `<=`, `>=`, `BETWEEN`, and `LIKE` (with prefix patterns).

Index creation varies by framework and language, but the core concepts remain the same: single-column indexes for simple queries, composite indexes for multi-column filters, and covering indexes to avoid table lookups. See Example 7.2 for Python/SQLAlchemy, Example 7.3 for Rust/Diesel, and Example 7.4 for TypeScript/Prisma implementations.

**Hash Indexes**

Hash indexes provide O(1) lookup time for exact equality queries but do not support range queries or sorting. They are useful for columns that are only ever queried with exact matches.

**Composite Index Column Order**

For composite indexes, column order significantly affects query performance. The general rule: place columns used in equality conditions before columns used in range conditions. The leftmost prefix rule means a composite index on `(status, created_at)` can serve queries on `status` alone, but not queries on `created_at` alone.

<!-- DIAGRAM: B-tree index structure showing: Root node with key ranges -> Internal nodes with finer key ranges -> Leaf nodes containing actual keys and pointers to table rows. Annotate the O(log n) path from root to leaf -->

![B-Tree Index Structure](../assets/ch06-btree-index.html)

### Query Optimization Techniques

Beyond indexing, several techniques help optimize query performance:

**Using EXPLAIN to Analyze Queries**

The `EXPLAIN` command reveals how the database plans to execute a query. `EXPLAIN ANALYZE` actually executes the query and shows real timing data. When analyzing query plans, look for sequential scans on large tables (often indicating a missing index), discrepancies between estimated and actual row counts, and high buffer usage. See Example 7.5 for Python, Example 7.6 for Rust, and Example 7.7 for TypeScript implementations of query plan analysis.

**Key Query Optimization Patterns**

1. **Avoid SELECT ***: Only retrieve columns you need. This reduces I/O and enables covering indexes.
2. **Push filtering to the database**: Filter in WHERE clauses, not in application code.
3. **Use appropriate pagination**: Prefer cursor-based pagination over OFFSET for large datasets.
4. **Batch operations**: Use bulk inserts and updates instead of individual operations.

### Database Connection Pooling

Opening a database connection is expensive. It involves TCP connection establishment, authentication, TLS negotiation (if enabled), and server-side session setup. Connection pooling maintains a cache of open connections that can be reused across requests.

The HikariCP documentation provides guidance on pool sizing [Source: HikariCP Wiki, "About Pool Sizing"]. A common formula for OLTP workloads is:


```
pool_size = (core_count * 2) + effective_spindle_count
```

For modern SSDs, the spindle count is typically treated as 1. So a 4-core server might use a pool size of 9-10 connections. However, the optimal size depends on your specific workload and should be determined through measurement.

Connection pool configuration follows similar patterns across languages: set minimum and maximum connection counts, configure idle timeouts to recycle unused connections, and establish query timeouts to prevent runaway queries. See Example 7.8 for Python/asyncpg, Example 7.9 for Rust/SQLx, and Example 7.10 for TypeScript/pg implementations.

**Pool Sizing Considerations**

- **Too small**: Requests wait for connections, increasing latency. Monitor connection wait time.
- **Too large**: Wastes database server resources, may hit database connection limits.
- **Monitor pool utilization**: If consistently above 80%, consider increasing pool size or optimizing query patterns.

<!-- DIAGRAM: Connection pool architecture showing: Application threads (many) -> Pool manager with queue -> Pool of reusable connections (sized) -> Database. Annotate the flow: request waits if pool exhausted, connection returns to pool after use -->

![Database Connection Pool Architecture](../assets/ch06-connection-pool.html)

### Read Replicas and Write Optimization

When read traffic exceeds what a single database can handle, read replicas provide horizontal read scaling. A primary database handles all writes, which then replicate to one or more read replicas. Read queries route to replicas, distributing the load.

**Read/Write Splitting**

A database router directs write operations to the primary database and distributes read operations across available replicas. The router can use random selection or round-robin to balance load across replicas, falling back to primary if no replicas are available (see Example 7.11).

**Replication Lag Considerations**

Read replicas introduce eventual consistency. After a write to the primary, there is a delay (replication lag) before the data appears on replicas. This lag is typically milliseconds to seconds under normal conditions but can grow during high write loads.

For read-after-write consistency requirements (e.g., a user creating a post and immediately viewing it), either:
1. Route that specific read to the primary
2. Use session-based routing that directs a user's reads to primary for a short period after their writes
3. Include a version token in responses that clients send back, routing to primary if the replica is behind

<!-- DIAGRAM: Read replica architecture showing: Write queries -> Primary database -> Replication stream -> Read Replica 1 and Read Replica 2. Read queries distributed across replicas. Annotate replication lag between primary and replicas -->

![Read Replica Architecture](../assets/ch06-read-replica.html)

For implementation examples related to these concepts, see the [Appendix: Code Examples](./13-appendix-code-examples.md).

## Common Pitfalls

- **Premature optimization without measurement**: Adding indexes, read replicas, or connection pool tuning without first measuring to confirm the bottleneck wastes effort and may introduce new problems. Always profile queries with EXPLAIN ANALYZE before optimizing.

- **Over-indexing**: Every index speeds up reads but slows down writes, since the database must update all relevant indexes on INSERT, UPDATE, and DELETE operations. Only create indexes that serve actual query patterns shown in your slow query logs.

- **Ignoring connection pool metrics**: A pool that is too small causes requests to wait; one that is too large wastes database resources. Monitor pool utilization, wait time, and connection errors. Tune pool size based on actual load testing.

- **Using OFFSET for deep pagination**: OFFSET-based pagination becomes progressively slower as the offset increases, since the database must scan and discard all preceding rows. For large datasets, use cursor-based (keyset) pagination instead.

- **Assuming replica consistency**: Code that writes to primary and immediately reads from a replica may see stale data due to replication lag. Design for eventual consistency or implement read-after-write consistency patterns.

- **Returning large result sets**: Queries without LIMIT can return millions of rows, consuming memory and network bandwidth. Always paginate large result sets and set reasonable default limits.

- **Not using prepared statements**: Beyond SQL injection protection, prepared statements allow the database to cache query plans, reducing parsing overhead for repeated queries.

## Summary

- **The N+1 problem** multiplies database round-trips linearly with data size. Solve it with eager loading (JOINs or batch fetching), reducing N+1 queries to 1-2 queries.

- **Proper indexing** transforms O(n) table scans into O(log n) lookups. Use B-tree indexes for most cases; consider composite indexes for multi-column filters with equality columns first.

- **EXPLAIN ANALYZE** is your primary diagnostic tool. Look for sequential scans on large tables, large row estimates, and high buffer usage as indicators of optimization opportunities.

- **Connection pooling** amortizes the cost of connection establishment across many requests. Size pools based on workload characteristics and monitor utilization.

- **Read replicas** provide horizontal read scaling but introduce eventual consistency. Implement appropriate read/write routing and handle replication lag for read-after-write scenarios.

- **Measure before and after** every optimization. Database performance tuning is empirical—what works in one scenario may not help in another.

## References

1. **Use The Index, Luke** - A comprehensive guide to database indexing. https://use-the-index-luke.com/

2. **HikariCP Wiki** - "About Pool Sizing" provides guidance on connection pool configuration. https://github.com/brettwooldridge/HikariCP/wiki/About-Pool-Sizing

3. **PostgreSQL Documentation** - "EXPLAIN" chapter covers query plan analysis. https://www.postgresql.org/docs/current/using-explain.html

4. **PostgreSQL Documentation** - "Indexes" chapter covers index types and usage. https://www.postgresql.org/docs/current/indexes.html

5. **Martin Fowler** - "OrmHate" discusses N+1 and other ORM performance patterns. https://martinfowler.com/bliki/OrmHate.html

6. **Percona Blog** - MySQL and PostgreSQL optimization best practices. https://www.percona.com/blog/

## Next: [Chapter 8: Asynchronous Processing and Queuing](./08-async-queuing.md)

Having optimized our database layer, we turn to patterns that remove database operations from the critical request path entirely. The next chapter covers asynchronous processing, message queues, and event-driven architectures that improve responsiveness by deferring non-essential work.
