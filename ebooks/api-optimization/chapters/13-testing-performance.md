# Chapter 13: Testing Performance

![Chapter 13 Opener](../assets/ch13-opener.html)

\newpage

## Overview

Every optimization we have discussed in this book requires validation. We can implement connection pooling, configure caching layers, and tune database queries, but without rigorous testing, we are guessing at their effectiveness. Performance testing provides the empirical foundation that separates measured improvement from hopeful assumption.

Performance testing serves two purposes: validation and prevention. Validation confirms that our optimizations actually improve the metrics we care about. Prevention catches regressions before they reach production, ensuring that new features or refactoring do not degrade the performance we have worked to achieve. The observability infrastructure we built in Chapters 3 and 4 gives us the ability to measure; performance testing gives us controlled conditions under which to measure.

This chapter covers the full spectrum of performance testing: the types of tests we run, the tools available, the methodology for designing realistic tests, and the integration of testing into CI/CD pipelines. We also address the limitations of synthetic testing honestly. No test environment perfectly replicates production, and understanding these limitations helps us interpret results appropriately. The goal is not perfection but confidence: enough data to make informed decisions about production readiness.

## Key Concepts

### Types of Performance Tests

Performance testing is not a single activity but a family of related testing types, each answering different questions about system behavior. Understanding when to use each type helps focus testing efforts where they provide the most value.

<!-- DIAGRAM: Four load profile shapes side by side: (1) Load test showing gradual ramp-up to plateau then ramp-down, (2) Stress test showing continuous increase until failure point marked with X, (3) Spike test showing sudden vertical jump then return to baseline, (4) Soak test showing flat sustained load over 8+ hours. Each with time on X-axis and concurrent users on Y-axis -->

![Performance Test Load Profiles](../assets/ch13-load-profiles.html)

#### Load Testing

Load testing evaluates system behavior under expected user volumes. The question it answers is: "Can we handle our anticipated traffic while maintaining acceptable performance?" Load tests simulate realistic user patterns, including typical request mixes, session durations, and think times between actions [Source: BlazeMeter, 2025].

A well-designed load test follows a three-phase pattern:

1. **Ramp-up phase**: Gradually increase load from zero to target over 5-15 minutes. This reveals how the system behaves as traffic builds and allows caches to warm, connection pools to fill, and JIT compilation to complete.

2. **Steady-state phase**: Maintain target load for a sustained period, typically 15-60 minutes. This is where we collect the metrics that matter: latency distributions, throughput, error rates, and resource utilization.

3. **Ramp-down phase**: Gradually decrease load back to zero over 2-5 minutes. This reveals whether the system recovers gracefully or exhibits lingering issues like connection leaks or memory that is not released.

**Interpreting Load Test Results**

<!-- DIAGRAM: Load test time-series dashboard showing three stacked panels: RPS (with failures), Response Time (p50/p95 with initial cache-cold spike), and Concurrent Users (ramp-up/steady-state/ramp-down phases). Shows the relationship between user count, throughput, and latency over a 5-minute test -->

![Load Test Results Dashboard](../assets/ch13-load-test-dashboard.html)

The primary metrics to observe during load testing:

| Metric | What It Tells Us | Warning Signs |
|--------|------------------|---------------|
| p50 latency | Typical user experience | Increasing during steady state |
| p95 latency | Experience for 1-in-20 users | More than 3x p50 |
| p99 latency | Tail latency, often SLO target | Exceeds SLO threshold |
| Error rate | System reliability under load | Any increase from baseline |
| Throughput (RPS) | Actual capacity achieved | Lower than expected |
| CPU utilization | Compute headroom | Sustained above 70% |
| Memory utilization | Memory pressure | Continuous growth |

A successful load test shows stable metrics throughout the steady-state phase. If p95 latency drifts upward during steady state, something is degrading, perhaps a memory leak, connection pool exhaustion, or garbage collection pressure.

<!-- DIAGRAM: Per-endpoint statistics table from a load test showing Method, Endpoint, Requests, Failures, p50/p95/p99 latencies, Average, and RPS for 8 realistic API endpoints with color-coded p95 latency values -->

![Load Test Per-Endpoint Statistics](../assets/ch13-load-test-stats.html)

**Example Load Test Scenario**

Consider an e-commerce API expecting 500 concurrent users during peak hours. A load test might:

- Ramp from 0 to 500 users over 10 minutes (50 users/minute)
- Maintain 500 users for 30 minutes
- Ramp down to 0 over 5 minutes
- Total duration: 45 minutes

During the test, we verify that p95 latency stays under 200ms (our SLO), error rate remains below 0.1%, and throughput exceeds 2,000 RPS.

#### Stress Testing

Stress testing pushes the system beyond expected limits to find breaking points. The question it answers is: "At what load does the system degrade unacceptably, and how does it fail?" Understanding failure modes is critical for capacity planning and resilience engineering [Source: Abstracta, 2025].

Unlike load testing, stress testing deliberately exceeds normal capacity. We increase load continuously until latencies become unacceptable, error rates spike, or the system becomes unresponsive. The value is not in proving the system fails (all systems fail eventually) but in understanding how it fails and at what threshold.

**Failure Mode Categories**

Systems fail in different ways under stress, and the failure mode reveals architectural weaknesses:

| Failure Mode | Symptoms | Typical Cause |
|--------------|----------|---------------|
| Graceful degradation | Latency increases, no errors | Good backpressure, proper queuing |
| Error avalanche | Sudden error spike at threshold | Missing circuit breakers, cascading failures |
| Complete collapse | System becomes unresponsive | Thread exhaustion, deadlock, OOM |
| Partial failure | Some endpoints fail, others work | Bulkhead isolation working (or failing) |

A system that degrades gracefully under stress (serving slower responses rather than crashing) is more resilient than one that collapses suddenly. Stress testing reveals whether our circuit breakers, rate limiters, and bulkheads from Chapter 10 actually protect the system under duress.

**Finding the Breaking Point**

A structured stress test increases load in steps, holding each step long enough to observe system behavior:

1. Start at 100% of expected load (baseline)
2. Increase to 150% for 5 minutes, observe metrics
3. Increase to 200% for 5 minutes, observe metrics
4. Continue in 50% increments until failure
5. Document the threshold where SLOs were violated
6. Document the threshold where the system became unresponsive

The breaking point is not a single number but a range. The system might maintain SLOs at 180% load, violate p99 SLO at 200%, and become unresponsive at 250%. All three thresholds are valuable for capacity planning.

#### Spike Testing

Spike testing evaluates how the system handles sudden, dramatic increases in traffic. The question it answers is: "Can we survive a traffic surge, and how quickly do we recover?" This simulates scenarios like viral content, marketing campaign launches, flash sales, or coordinated events [Source: BlazeMeter, 2025].

Spike tests differ from stress tests in their shape: rather than gradually increasing load, they jump from normal to extreme load almost instantly. This tests not just capacity but the system's ability to adapt quickly.

**What Spikes Reveal**

Spikes stress different system components than gradual load increases:

- **Connection pools**: Can they expand quickly enough? Do they have headroom?
- **Auto-scaling**: How long before new instances are available? (Often 2-5 minutes for containers, longer for VMs)
- **Caches**: Do they absorb the spike, or does cache miss rate increase?
- **Rate limiters**: Do they protect the system, or does legitimate traffic get rejected?
- **Circuit breakers**: Do they trip appropriately, or do they oscillate?

**Spike Test Pattern**

A typical spike test:

1. Establish baseline at normal load (100 users) for 5 minutes
2. Instantly jump to spike load (1000 users)
3. Maintain spike for 5-10 minutes
4. Instantly drop back to baseline
5. Maintain baseline for 10 minutes to verify recovery

Recovery behavior matters as much as survival. After a spike subsides, how quickly does the system return to normal operation? Lingering effects like backed-up queues, exhausted connection pools, or elevated error rates indicate recovery issues.

**Measuring Recovery Time**

Recovery time is the duration from when the spike ends until metrics return to baseline levels. Track these recovery indicators:

- Time until p95 latency returns to pre-spike levels
- Time until error rate returns to zero
- Time until queue depths drain
- Time until CPU/memory utilization normalizes

A well-designed system should recover within 1-2 minutes of a spike ending. Longer recovery times indicate resource exhaustion or backlog issues that need architectural attention.

#### Soak Testing (Endurance Testing)

Soak testing maintains moderate load over extended periods, typically 8-24 hours. The question it answers is: "Does the system remain stable over time, or do issues accumulate?" This catches problems that only manifest after prolonged operation [Source: Abstracta, 2025].

**Problems Soak Testing Reveals**

| Issue | How It Manifests | Typical Root Cause |
|-------|------------------|-------------------|
| Memory leaks | Gradual memory growth until OOM | Objects not garbage collected, growing caches |
| Connection leaks | Connection pool exhaustion | Connections not returned to pool |
| File descriptor exhaustion | "Too many open files" errors | Sockets or files not closed |
| Log rotation issues | Disk fills up | Logs not rotated or archived |
| Database connection aging | Intermittent connection errors | Stale connections, firewall timeouts |
| Thread leaks | Thread count grows continuously | Threads not terminated properly |
| Cache fragmentation | Gradual latency increase | Inefficient cache eviction |

Memory leaks are the classic soak test discovery. A small leak might not matter during a 10-minute test but becomes critical after 8 hours of production traffic. If your service leaks 1MB per hour, that is 24MB per day, invisible in short tests but eventually fatal.

**Soak Test Configuration**

Soak tests require patience and dedicated resources:

- **Load level**: 70-80% of normal peak load (not maximum, but sustained realistic load)
- **Duration**: Minimum 8 hours, ideally 24 hours or matching production duty cycle
- **Metrics sampling**: Every 30-60 seconds for trend analysis
- **Resource monitoring**: Memory, connections, file descriptors, thread count

The key metric in soak testing is not the absolute value but the trend. A system using 2GB of memory is fine; a system that started at 1GB and is now at 2GB after 4 hours will hit 4GB after 12 hours.

**Analyzing Soak Test Results**

Plot resource metrics over time and look for:

- **Linear growth**: Indicates a constant leak rate
- **Step functions**: Indicates periodic events causing resource accumulation
- **Logarithmic growth**: Indicates a bounded leak (less severe but still a problem)
- **Flat lines**: Indicates proper resource management

Any upward trend in resource consumption that does not plateau is a problem that will eventually cause production failure.

#### Benchmark Testing

Benchmark testing establishes performance baselines and measures changes against them. The question it answers is: "Is this change faster or slower than what we had before?" Benchmarks provide the comparative data that validates optimization work.

Benchmarks differ from other test types in their focus on comparison rather than absolute thresholds. A benchmark might show that the new caching strategy reduces p95 latency from 45ms to 12ms. Whether 12ms is "good enough" depends on our SLOs; the benchmark tells us the improvement magnitude.

**Microbenchmarks vs Macrobenchmarks**

Performance benchmarks exist on a spectrum from micro to macro:

| Level | What It Tests | Duration | Example |
|-------|--------------|----------|---------|
| Microbenchmark | Single function or operation | Milliseconds | JSON parsing speed |
| Component benchmark | One service in isolation | Seconds | API endpoint latency |
| Integration benchmark | Multiple services together | Minutes | End-to-end request flow |
| System benchmark | Full production-like environment | Hours | Complete load test |

Microbenchmarks are useful for comparing algorithm implementations or library choices. They run quickly and provide precise measurements but do not reflect real-world performance where network latency, database access, and concurrent requests dominate.

Macrobenchmarks test realistic scenarios but are slower and have more variance. They better predict production behavior but require more infrastructure and time.

**Benchmark Requirements**

For benchmarks to produce meaningful results:

1. **Isolation**: No other workloads on the test infrastructure
2. **Consistency**: Same environment configuration across runs
3. **Warmup**: Allow JIT compilation, cache warming before measuring
4. **Repetition**: Run multiple times to account for variance
5. **Statistical analysis**: Report percentiles and confidence intervals, not just averages

### Performance Testing Tools

The performance testing ecosystem offers tools ranging from simple HTTP benchmarkers to comprehensive load testing platforms. Each tool makes different trade-offs between ease of use, scalability, and feature depth.

<!-- DIAGRAM: Architecture comparison showing three tool types: (1) Thread-based (JMeter) with one thread icon per virtual user, showing high memory usage, (2) Event-driven (Locust, k6) with single event loop handling many connections, showing low memory usage, (3) Constant-throughput (wrk2) showing fixed request rate regardless of response time -->

![Load Testing Tool Architectures](../assets/ch13-tool-architectures.html)

#### Tool Architecture Matters

The architecture of a load testing tool determines how efficiently it generates load and how accurately it measures latency:

**Thread-per-user model (JMeter, older tools)**

Each virtual user runs in a dedicated thread. This model is intuitive (the thread represents the user) but resource-intensive. Simulating 10,000 concurrent users requires 10,000 threads, each consuming memory for its stack (typically 512KB-1MB per thread). A machine with 8GB of RAM might only support 4,000-8,000 virtual users before exhausting memory.

**Event-driven model (Locust, k6, Gatling)**

A small number of threads (often matching CPU cores) handle many concurrent connections using asynchronous I/O. This is far more efficient, as a single machine can simulate tens of thousands of virtual users. k6 written in Go and Gatling using Scala's async capabilities can generate 50,000+ RPS from a modest machine.

**Constant-throughput model (wrk2)**

Rather than simulating users, wrk2 generates a fixed request rate regardless of response time. This approach avoids coordinated omission (discussed later) and provides more accurate latency measurements under variable server performance.

#### Tool Comparison

| Tool | Language | Architecture | Best For | Limitations |
|------|----------|--------------|----------|-------------|
| **JMeter** | Java | Thread-per-user | Protocol diversity, GUI workflows | Resource-heavy, complex for code |
| **k6** | JavaScript/Go | Event-driven | CI/CD integration, developer workflows | HTTP-focused, no GUI |
| **Gatling** | Scala/Java | Event-driven | High concurrency, detailed reports | JVM learning curve |
| **Locust** | Python | Event-driven | Python teams, flexible scripting | HTTP-focused |
| **wrk2** | C/Lua | Constant-throughput | Accurate latency benchmarks | Limited scripting |
| **hey** | Go | Simple | Quick ad-hoc tests | Basic features |

#### Apache JMeter

JMeter is the established standard, an open-source Java application with broad protocol support and extensive plugin ecosystem. Its GUI makes test creation accessible to non-programmers, and its protocol coverage extends beyond HTTP to JDBC, JMS, LDAP, FTP, and more [Source: TestLeaf, 2025].

**When to choose JMeter:**
- Need to test non-HTTP protocols (databases, message queues)
- Team prefers GUI-based test design
- Existing JMeter expertise in the organization
- Complex correlation and parameterization requirements

**JMeter considerations:**
- Resource consumption limits single-machine concurrency
- Requires distributed setup for high-load tests
- CLI mode more efficient than GUI mode for actual testing
- Extensive plugin ecosystem (100+ plugins available)

For high-concurrency scenarios, JMeter requires distributed deployment. A controller coordinates multiple injector machines, each running a portion of the load. This adds operational complexity but enables tests with hundreds of thousands of virtual users.

#### Grafana k6

k6 represents the modern, developer-centric approach to load testing. Tests are written in JavaScript, stored in version control alongside application code, and executed from the command line. The Go-based engine is highly efficient, simulating thousands of virtual users with minimal resources [Source: Grafana, 2025].

**When to choose k6:**
- CI/CD integration is a priority
- Team is comfortable with JavaScript
- Need SLO-based pass/fail thresholds
- Grafana ecosystem for visualization

**k6's killer feature: Thresholds**

k6 tests define thresholds that map directly to SLOs:

```javascript
export const options = {
  thresholds: {
    http_req_duration: ['p(95)<200', 'p(99)<500'],
    http_req_failed: ['rate<0.01'],
  },
};
```

If any threshold is violated, k6 exits with a non-zero code, failing the CI/CD pipeline. This enables automated quality gates without custom scripting.

**k6 metrics and output:**

k6 produces detailed metrics including:
- `http_req_duration`: Response time histogram
- `http_req_waiting`: Time to first byte (TTFB)
- `http_req_connecting`: Connection establishment time
- `http_reqs`: Request count and rate
- `iterations`: Complete scenario iterations

Results can stream to Prometheus, Grafana Cloud, InfluxDB, or JSON files for analysis.

#### Gatling

Gatling uses an asynchronous, non-blocking architecture built on Scala and Akka, efficiently simulating massive user loads from a single machine. Tests are written in a Scala DSL (or Java/Kotlin), providing powerful scripting capabilities [Source: TestLeaf, 2025].

**When to choose Gatling:**
- Need extreme concurrency from minimal infrastructure
- Want detailed HTML reports for stakeholders
- Team has JVM experience
- Complex scenario logic with conditional flows

**Gatling's reporting:**

Gatling produces comprehensive HTML reports including:
- Response time distribution histograms
- Percentile charts over time
- Active users over time
- Request/response timeline
- Detailed error analysis

These reports are self-contained HTML files, shareable without additional infrastructure.

#### Locust

Locust is a Python-based load testing framework using an event-driven architecture for efficient resource utilization. Tests are written as Python classes defining user behavior, making it accessible to teams already using Python [Source: Locust Documentation, 2025].

**When to choose Locust:**
- Team expertise is in Python
- Need full programming language flexibility
- Want distributed testing with simple master/worker model
- Prefer web UI for real-time monitoring

**Locust's distributed mode:**

Locust scales horizontally by running a master process that coordinates worker processes. Workers can run on the same machine or distributed across many machines. The master aggregates statistics and provides a unified view through its web UI.

#### wrk and wrk2

wrk and wrk2 are lightweight HTTP benchmarking tools focused on generating maximum load with minimal resources. They excel at quick benchmarks and baseline measurements rather than complex scenario testing.

**wrk2 and coordinated omission:**

wrk2 specifically addresses coordinated omission, a critical measurement issue that we discuss in detail later. For accurate latency measurement under variable load, wrk2 provides more reliable results than most other tools [Source: wrk2 GitHub, 2025].

Basic wrk2 usage:

```bash
# Generate 10,000 RPS for 60 seconds with 100 connections
wrk2 -t4 -c100 -d60s -R10000 --latency http://api.example.com/endpoint
```

The `-R` flag sets constant throughput, the key to avoiding coordinated omission.

#### hey

hey (formerly boom) is a simple Go-based HTTP load generator useful for quick, ad-hoc testing. It provides basic metrics like mean response time, percentiles, and throughput.

```bash
# Send 10,000 requests with 50 concurrent workers
hey -n 10000 -c 50 http://api.example.com/endpoint
```

hey is not designed for complex scenarios but serves well for quick sanity checks when you need an answer in seconds rather than minutes.

#### Tool Selection Decision Tree

<!-- DIAGRAM: Decision tree for tool selection: Start -> "Need non-HTTP protocols?" -> Yes: JMeter -> No: "CI/CD integration priority?" -> Yes: k6 -> No: "Team knows Python?" -> Yes: Locust -> No: "Need extreme concurrency?" -> Yes: Gatling -> No: "Quick benchmark only?" -> Yes: wrk2/hey -->

![Tool Selection Decision Tree](../assets/ch13-tool-selection.html)

### Test Design and Methodology

The quality of performance test results depends on test design. Poorly designed tests produce misleading data; well-designed tests provide actionable insights.

#### Virtual Users and Concurrency

Virtual users (VUs) simulate real users interacting with the system. Each VU executes a defined behavior: making requests, processing responses, and pausing between actions. The number of concurrent VUs determines the load level [Source: LoadFocus, 2025].

**Calculating Virtual User Counts**

Calculating appropriate VU counts requires understanding actual usage patterns. Several approaches:

**From production analytics:**

```
Peak Concurrent Users = Peak Hourly Sessions × Average Session Duration (hours)
```

If peak hour sees 10,000 sessions and average session is 6 minutes (0.1 hours):

```
Peak Concurrent Users = 10,000 × 0.1 = 1,000 users
```

**From daily active users (DAU):**

A common heuristic is that peak concurrent users approximate 10-15% of daily active users. An application with 10,000 DAU might see 1,000-1,500 concurrent users during peak hours [Source: LoadFocus, 2025]. This varies by application type:

| Application Type | Concurrent/DAU Ratio | Reasoning |
|-----------------|---------------------|-----------|
| Real-time apps (chat, gaming) | 15-25% | Users online continuously |
| E-commerce | 10-15% | Concentrated shopping hours |
| Content sites | 5-10% | Brief visits throughout day |
| B2B SaaS | 8-12% | Business hours concentration |

**From throughput requirements:**

If you know the required RPS, work backwards:

```
Virtual Users = RPS × Average Response Time (seconds) / (1 + Think Time (seconds))
```

For 1,000 RPS with 100ms average response time and 2 seconds think time:

```
Virtual Users = 1000 × 0.1 / (1 + 2) = 33 users
```

This formula shows why think time dramatically affects VU requirements.

#### Think Time

Think time represents the pauses between user actions, simulating the time real users spend reading, thinking, or entering data. Omitting think time creates artificially aggressive load patterns that do not reflect actual usage [Source: LoadFocus, 2025].

<!-- DIAGRAM: Timeline comparison showing two scenarios: (1) Without think time: request-response-request-response in rapid succession, generating 10 RPS per user, (2) With 2-second think time: request-response-[2 second pause]-request-response, generating 0.5 RPS per user. Both showing same 100 VUs but dramatically different server load -->

![Think Time Impact](../assets/ch13-think-time.html)

**Impact of Think Time**

Consider 100 virtual users with 100ms average response time:

| Think Time | Requests/User/Second | Total RPS |
|------------|---------------------|-----------|
| 0 seconds | 10 | 1,000 |
| 1 second | 0.91 | 91 |
| 2 seconds | 0.48 | 48 |
| 5 seconds | 0.20 | 20 |

Without think time, 100 users generate 1,000 RPS. With realistic 5-second think time, the same 100 users generate only 20 RPS. Tests without think time dramatically overstate the load that real users would generate.

**Realistic Think Time Values**

Derive think times from production analytics (request timing patterns, session analysis) when possible. Typical values by action type:

| Action | Typical Think Time | Reasoning |
|--------|-------------------|-----------|
| Page view | 5-30 seconds | Reading content |
| Search results | 3-10 seconds | Scanning options |
| Form submission | 30-120 seconds | Data entry |
| Login | 5-15 seconds | Credential entry |
| Checkout step | 20-60 seconds | Review and confirm |

**Implementing Think Time**

Think time should have variance to avoid synchronized request patterns:

- Fixed think time (bad): All users request simultaneously after each pause
- Random range (good): `random(3, 8)` seconds creates realistic distribution
- Statistical distribution (better): Normal or Poisson distribution matches real behavior

```
simulated user behavior:
    perform action (click, submit, navigate)
    wait random duration between min and max think time
        (e.g., 1-5 seconds, matching real user patterns)
    perform next action

this prevents artificial load spikes
and matches production traffic patterns
```

#### Ramp-Up Patterns

Ramp-up defines how load increases from zero to target levels. The pattern affects what the test reveals about system behavior.

**Gradual Ramp-Up (Load Testing)**

Increase by 5-10% of target load per minute:

- Reveals when performance begins to degrade
- Allows caches to warm gradually
- Shows connection pool behavior under increasing load
- Identifies the knee point where latency starts increasing

**Step Ramp-Up (Stress Testing)**

Hold each load level for several minutes before increasing:

- Allows system to stabilize at each level
- Clearly identifies which load level caused problems
- Easier to correlate issues with specific capacity thresholds

**Instant Jump (Spike Testing)**

Jump from baseline to target immediately:

- Tests auto-scaling response time
- Reveals connection pool expansion behavior
- Exposes cold-start issues

**Gradual Then Spike (Combined)**

Ramp to baseline, hold, then spike:

- Tests normal operation before spike
- Reveals whether baseline load affects spike handling

```
load test stages:
    stage 1: ramp from 0 to 100 users over 5 minutes
    stage 2: hold at 100 users for 10 minutes
    stage 3: ramp to 500 users over 5 minutes
    stage 4: hold at 500 users for 10 minutes
    stage 5: ramp down to 0 over 2 minutes
```

#### Realistic Scenarios

Test scenarios should reflect actual usage patterns. This means realistic request mixes, representative data sizes, and authentic user journeys.

**Request Mix Distribution**

Analyze production traffic to understand request distribution:

```
Production Traffic Analysis:
- GET /api/products: 45% of requests
- GET /api/products/{id}: 25% of requests
- GET /api/users/{id}: 15% of requests
- POST /api/cart: 10% of requests
- POST /api/orders: 5% of requests
```

Test scenarios should reflect this ratio. Testing with equal distribution across all endpoints produces results that do not predict production behavior.

**Data Variation**

A test hitting the user lookup endpoint with the same user ID repeatedly exercises cache behavior, not database performance. Realistic testing requires data variation:

- **User IDs**: Sample from realistic distribution (not uniform random)
- **Product IDs**: Weight toward popular items (Zipf distribution)
- **Search terms**: Use actual search logs
- **Geographic distribution**: Vary client locations if testing CDN

**User Journeys**

Real users follow journeys, not random endpoint access:

1. Landing page → Product list → Product detail → Add to cart → Checkout
2. Login → Dashboard → Report generation → Export

Model these journeys in test scenarios with appropriate transition probabilities. Not every user who views a product adds it to cart; your test should reflect actual conversion rates.

### Benchmarking Best Practices

Benchmarking produces comparative data for optimization decisions. Poor benchmarking methodology produces misleading comparisons; rigorous methodology produces actionable insights.

#### Coordinated Omission

Coordinated omission is a measurement artifact that causes most benchmarking tools to significantly underreport latency when the system under test experiences slowdowns. Understanding this phenomenon is critical for accurate benchmarking [Source: Gil Tene, wrk2 GitHub, 2025].

<!-- DIAGRAM: Two timeline comparisons: (1) "Naive measurement" showing requests sent only after previous response, with slow response (1000ms) reducing measurement opportunities, labeled "Underreports latency", (2) "Correct measurement (wrk2)" showing requests sent at constant rate regardless of response time, measuring from intended send time, labeled "Accurate latency" -->

![Coordinated Omission Explained](../assets/ch13-coordinated-omission.html)

**The Problem**

Consider a benchmarking tool that sends requests and waits for responses before sending the next request. When the server responds quickly (10ms), requests flow rapidly at 100 requests per second. When the server slows down (1000ms), the tool sends fewer requests during that period, only 1 request per second.

The tool's measurement of "average response time" over-represents the fast periods (when more requests completed) and under-represents the slow periods (when fewer requests completed). It is as if the tool coordinates with the server to avoid measuring during slow periods, hence "coordinated omission."

**The Impact**

The result is systematically underreported latency, especially at high percentiles:

| Actual Server Behavior | Naive Tool Reports | Reality |
|-----------------------|-------------------|---------|
| 99% at 10ms, 1% at 5000ms | p99 ~100ms | p99 = 5000ms |
| Occasional 10-second pauses | p99 ~200ms | p99 = 10000ms |

A system with occasional 5-second pauses might report p99 latency of 100ms because only a few requests experienced the pause, and those requests were underweighted in the measurement.

**The Solution**

wrk2 addresses coordinated omission by maintaining constant throughput regardless of response time. It measures latency from when the request *should* have been sent (according to the target rate) rather than when it was actually sent.

If the target rate is 100 RPS and a request is delayed because the previous response took 5 seconds, the delayed request's latency includes that 5-second delay. This produces accurate latency measurements even when the server experiences variable performance.

**Practical Implications**

- Use wrk2 or tools that handle coordinated omission for accurate latency measurement
- If using other tools, understand they may underreport tail latency
- Compare results only from the same tool with the same methodology
- For SLO validation, coordinated omission can mean your tests pass while production fails

#### Statistical Rigor

Single benchmark runs are insufficient for reliable conclusions. Random variation in system behavior, network conditions, and resource contention means a single run might not represent typical performance.

**Multiple Runs**

Run benchmarks multiple times (minimum 3-5 runs) and analyze the distribution:

| Run | p99 Latency |
|-----|-------------|
| 1 | 45ms |
| 2 | 47ms |
| 3 | 46ms |
| 4 | 48ms |
| 5 | 44ms |
| **Mean** | **46ms** |
| **Std Dev** | **1.6ms** |

This shows consistent results. Compare with:

| Run | p99 Latency |
|-----|-------------|
| 1 | 45ms |
| 2 | 120ms |
| 3 | 52ms |
| 4 | 48ms |
| 5 | 95ms |
| **Mean** | **72ms** |
| **Std Dev** | **33ms** |

High standard deviation indicates inconsistent behavior warranting investigation before drawing conclusions.

**Reporting Results**

Report results as ranges with confidence intervals:
- "p99 latency of 45-50ms across 5 runs" (honest)
- "p99 latency of 47ms" (misleading precision)

**Warmup Periods**

Exclude initial measurements to avoid cold-start artifacts:
- JVM JIT compilation
- Cache warming
- Connection pool initialization
- Operating system buffer caching

Typically exclude the first 10-30 seconds of measurements.

#### Baseline Comparisons

Benchmarks gain meaning through comparison. Absolute numbers (200ms latency) are less informative than relative changes (20% improvement from baseline).

**Establishing Baselines**

Before making changes:
1. Run the complete benchmark suite
2. Repeat 3-5 times to understand variance
3. Record environment configuration
4. Save results as the baseline

**After-Change Comparison**

After making changes:
1. Verify identical environment configuration
2. Run the same benchmark suite
3. Repeat 3-5 times
4. Compare against baseline using statistical tests

**Avoiding Confounding Variables**

If you upgrade the database and change the caching strategy simultaneously, you cannot attribute improvements to either change specifically. Benchmark after each change for clear attribution:

1. Baseline: 200ms p95
2. After database upgrade: 180ms p95 (10% improvement from database)
3. After caching change: 120ms p95 (33% improvement from caching)

### CI/CD Integration

Integrating performance testing into CI/CD pipelines catches regressions before they reach production. The goal is automated quality gates that fail builds when performance degrades.

<!-- DIAGRAM: CI/CD pipeline with performance gates: Code Commit -> Build -> Unit Tests -> Ephemeral Env -> [Smoke Perf Test: 2 min] -> Deploy to Staging -> [Load Test: 15 min] -> Deploy to Production. Show pass/fail gates at each perf test step with threshold examples -->

![CI/CD Performance Pipeline](../assets/ch13-cicd-pipeline.html)

#### Threshold-Based Quality Gates

Quality gates define pass/fail criteria based on measurable thresholds. These thresholds should align with SLOs: if our SLO requires p95 latency under 200ms, our quality gate should fail builds that exceed 200ms.

**Defining Thresholds**

Start with SLO requirements and add margins for test environment differences:

| SLO Requirement | Quality Gate Threshold | Reasoning |
|----------------|----------------------|-----------|
| p95 < 200ms | p95 < 180ms | 10% margin for prod differences |
| Error rate < 0.1% | Error rate < 0.05% | Tighter standard for testing |
| Availability 99.9% | Zero errors in test | Errors in controlled test are unacceptable |

**Progressive Thresholds**

Different pipeline stages warrant different thresholds:

| Stage | Test Type | Duration | Threshold Strictness |
|-------|-----------|----------|---------------------|
| Pre-merge | Smoke test | 2 min | Lenient (catch obvious issues) |
| Post-merge | Load test | 15 min | Standard (match SLOs) |
| Pre-production | Full suite | 1 hour | Strict (production-ready) |

**Threshold Tuning**

The challenge is defining thresholds that catch real regressions without blocking legitimate releases:

- **Too tight**: False failures block valid releases, teams lose trust
- **Too loose**: Real regressions reach production

Start conservative and adjust based on experience. Track false positive rates and tune thresholds that frequently cause unwarranted failures.

#### When to Run Performance Tests

Performance tests vary in duration and resource requirements. Not every test belongs on every commit:

| Trigger | Test Type | Duration | Purpose |
|---------|-----------|----------|---------|
| Every commit | Smoke test | 1-2 min | Catch obvious regressions |
| Merge to main | Load test | 10-30 min | Validate at expected load |
| Nightly | Soak test | 8 hours | Catch memory leaks, degradation |
| Pre-release | Full suite | 2-4 hours | Comprehensive validation |
| Weekly | Stress test | Variable | Verify capacity limits |

**Smoke Tests on Every Commit**

Quick tests (1-2 minutes) that verify basic functionality under light load. These catch obvious regressions like:
- Endpoints that now timeout
- Error rates that spiked dramatically
- Response times that increased by orders of magnitude

Smoke tests should be fast enough that developers do not skip them.

**Load Tests on Merge**

When code merges to main, run a substantive load test (10-30 minutes) validating performance at expected traffic levels. This catches:
- Regressions that only appear under load
- Concurrency issues
- Resource contention problems

**Nightly Soak Tests**

Extended tests that run overnight catch issues that accumulate over time:
- Memory leaks
- Connection pool exhaustion
- Log file growth
- Database connection aging

#### Handling Flaky Tests

Performance tests are inherently more variable than functional tests. Network fluctuations, garbage collection pauses, noisy neighbors, and resource contention introduce noise. Flaky performance tests erode confidence in the testing process [Source: Codepipes Blog, 2025].

**Sources of Flakiness**

| Source | Symptoms | Mitigation |
|--------|----------|------------|
| Shared infrastructure | Random latency spikes | Dedicated test environment |
| GC pauses | Occasional high latency | Warmup period, exclude outliers |
| Network variance | Inconsistent throughput | Longer test duration |
| Cold starts | First requests slow | Warmup before measuring |
| Background jobs | Periodic slowdowns | Schedule tests around jobs |

**Strategies for Stability**

1. **Statistical thresholds**: Fail if 3 of 5 runs exceed threshold, not single-run failures
2. **Percentage tolerance**: Fail if p95 exceeds baseline by more than 15%
3. **Warmup exclusion**: Ignore first 30 seconds of data
4. **Outlier handling**: Trim top/bottom 1% of measurements
5. **Dedicated infrastructure**: No shared resources with other tests or workloads
6. **Consistent scheduling**: Run at same time daily to avoid variance from time-of-day effects

**When Flakiness Persists**

If a test remains flaky after mitigation attempts:
1. Quarantine to non-blocking status while investigating
2. Track flakiness metrics (failure rate without code changes)
3. Either fix the underlying issue or accept the test provides limited value

A flaky test that teams learn to ignore teaches them to ignore all test failures.

### Distributed Testing at Scale

Single-machine load generation has limits. CPU, memory, and network constraints cap how much load one machine can generate. Distributed testing scales beyond these limits.

<!-- DIAGRAM: Distributed Locust architecture showing: Master node (coordinates test, aggregates stats, serves web UI) connected to multiple Worker nodes (generate actual load, report to master), all pointing to Target System. Show network topology and data flow directions -->

![Distributed Load Testing Architecture](../assets/ch13-distributed-architecture.html)

#### When Distributed Testing Is Needed

The need for distributed testing depends on target load and tool efficiency:

| Scenario | Single Machine Capable | Need Distribution |
|----------|----------------------|-------------------|
| 1,000 RPS, simple endpoints | Yes (any modern tool) | No |
| 10,000 RPS, simple endpoints | Yes (k6, Locust, Gatling) | Maybe |
| 50,000+ RPS | Depends on complexity | Likely |
| Geographic distribution required | N/A | Yes |
| Testing from inside VPC | N/A | Yes |

**Signs you need distributed testing:**
- Load generator CPU approaches 100% before reaching target load
- Load generator network becomes saturated
- Need to test from multiple geographic locations
- Need to test from inside a private network

**Before distributing:**
1. Optimize single-machine performance
2. Use efficient tools (k6 or Locust over JMeter)
3. Ensure realistic think times (reduces required VUs)
4. Profile the load generator itself

#### Locust Distributed Mode

Locust's distributed mode uses a master-worker architecture. The master coordinates the test, aggregating statistics from workers. Workers generate actual load, connecting to the target system [Source: Locust Documentation, 2025].

**Architecture:**
- **Master**: Single instance, runs web UI, aggregates statistics, does not generate load
- **Workers**: Multiple instances, generate actual load, report statistics to master
- **Communication**: Workers connect to master via TCP (ports 5557, 5558)

**Scaling considerations:**
- Each worker can handle 1,000-5,000 VUs (depending on test complexity)
- Network between workers and target is often the bottleneck
- Workers should be geographically close to targets (or intentionally distributed)

**Kubernetes deployment:**

Deploying Locust on Kubernetes enables elastic scaling:
- Master deployment (single replica)
- Worker deployment (scaled based on target load)
- ConfigMap for test scripts
- Services for master accessibility

#### Cloud-Based Load Testing

Cloud platforms offer managed load testing services that handle distribution automatically:

| Service | Strengths | Considerations |
|---------|-----------|----------------|
| k6 Cloud | Native k6 integration, Grafana ecosystem | Per-VUh pricing |
| BlazeMeter | JMeter compatible, broad protocol support | Enterprise pricing |
| AWS Load Testing | AWS integration, pay-per-use | Newer service |
| Azure Load Testing | Azure integration, JMeter scripts | Azure-focused |

**When to use cloud services:**
- Occasional large-scale tests (cheaper than maintaining infrastructure)
- Need geographic distribution across many regions
- Lack infrastructure team to manage load generators
- Regulatory requirements for testing from specific locations

**When to self-host:**
- Frequent testing (cost adds up)
- Need to test internal systems not accessible from cloud
- Want full control over test environment
- Already have Kubernetes infrastructure

### Synthetic Testing vs Production Testing

All testing discussed so far is synthetic: controlled tests against dedicated environments. Synthetic testing has inherent limitations that production testing addresses.

#### Limitations of Synthetic Testing

Synthetic tests cannot fully replicate production conditions [Source: Akamai, 2025]:

**Environment Differences**

| Aspect | Test Environment | Production |
|--------|-----------------|------------|
| Hardware | Often smaller instances | Full-size instances |
| Data volume | Sample data (GBs) | Full data (TBs) |
| Network | Low latency, same region | Variable, global |
| Dependencies | Mocks or staging versions | Real services |
| Configuration | May differ | Production config |

Test environment with a 10GB database will not reveal query performance issues that only appear with 10TB of data.

**Traffic Pattern Differences**

Synthetic traffic follows scripted patterns. Real traffic is messier:
- Unexpected request combinations
- Unusual parameter values
- Bots and scrapers
- Attack traffic
- Mobile vs desktop differences
- Time-zone effects

**Dependency Behavior**

Tests might mock external services or use staging versions. Production dependencies may:
- Have different latency characteristics
- Rate limit differently
- Experience their own performance issues
- Return different data volumes

#### Real User Monitoring Complement

Real User Monitoring (RUM) measures actual user experience in production. Unlike synthetic tests that measure what might happen, RUM measures what is happening.

**Synthetic vs RUM comparison:**

| Aspect | Synthetic Testing | RUM |
|--------|------------------|-----|
| Timing | Before deployment | After deployment |
| Coverage | Scripted scenarios | All user interactions |
| Environment | Test | Production |
| Consistency | Controlled | Real-world variance |
| Detection | Predictive | Reactive |

The combination provides comprehensive coverage: synthetic testing catches issues before deployment, RUM catches issues that synthetic testing missed. Chapter 4 covered RUM as part of monitoring infrastructure.

#### Canary and Shadow Testing

Beyond synthetic tests, production traffic can validate changes safely:

**Canary Deployments**

Route a small percentage (1-5%) of production traffic to new versions:
1. Deploy new version alongside current
2. Route small traffic percentage to new version
3. Compare metrics: latency, errors, resource usage
4. If metrics acceptable, gradually increase traffic
5. If metrics degrade, route all traffic back to old version

Canary testing uses real traffic patterns and real dependencies. Chapter 4 covered canary analysis metrics in detail.

**Shadow Testing (Dark Launching)**

Duplicate production traffic to test systems without affecting users:
1. Capture production requests
2. Replay to test system in parallel with production
3. Compare responses and timing
4. Discard test responses (users see only production responses)

Shadow testing validates behavior under real traffic patterns without user impact. Useful for:
- Major refactors
- Database migrations
- New service versions
- Algorithm changes

**Traffic Mirroring Challenges:**
- Requires infrastructure to duplicate traffic
- State-modifying requests need careful handling
- Test system must keep pace with production
- Storage for comparison data

## Common Pitfalls

- **Testing without clear goals**: Running load tests without defined success criteria produces data without actionable insight. Define SLO-aligned thresholds before testing. Know what question you are trying to answer.

- **Environment mismatch**: Testing on underpowered environments and extrapolating to production leads to surprises. A 2-CPU test environment will not reveal issues that appear with 16 CPUs. Match test environments to production as closely as budget allows.

- **Unrealistic test data**: Testing with a 1GB database when production has 1TB misses performance characteristics that emerge at scale. Query plans differ, indexes behave differently, and memory pressure is completely different. Use production-scale data or explicitly document the limitations.

- **Missing think time**: Tests without think time generate unrealistic request patterns. 100 users without think time might generate 10,000 RPS, while 100 real users with realistic think time generate 50 RPS. Include think time or accept that VU counts mean something different than real users.

- **Ignoring coordinated omission**: Tools that underreport latency produce false confidence. A test showing p99 of 100ms might be hiding real p99 of 5 seconds. Use wrk2 or understand your tool's limitations.

- **Testing too late**: Finding performance problems after feature complete is expensive. A 50ms regression discovered in development costs an hour to fix. The same regression discovered in production costs days of firefighting. Integrate performance testing early.

- **Flaky tests eroding trust**: Intermittent failures that teams learn to ignore defeat the purpose of automated testing. If a test fails randomly, teams will dismiss real failures. Fix or quarantine flaky tests promptly.

- **Shared test environments**: Running performance tests while other activity uses the environment produces unreliable results. A test showing 500ms latency might be caused by another team's integration test running simultaneously. Isolate performance testing infrastructure.

- **Underpowered load generators**: If the load generator saturates before the target system, you are measuring the wrong thing. Monitor load generator CPU, memory, and network during tests. If load generator CPU hits 100%, your measurements are invalid.

- **Ignoring tool measurement differences**: Different tools measure latency at different points. One tool might measure from request initiation, another from first byte sent, another from connection established. Understand what each tool measures before comparing results.

- **Benchmarking without warmup**: JIT compilation, cache warming, and connection pool initialization affect early measurements. Excluding the first 30-60 seconds of data produces more representative results.

- **Drawing conclusions from single runs**: Performance has variance. A single run might be unusually fast or slow. Run multiple times and analyze the distribution before claiming improvement or regression.

## Summary

- Performance testing validates optimization work and prevents regressions. Without testing, we are guessing at production behavior.

- **Load testing** validates performance at expected traffic levels. **Stress testing** finds breaking points and failure modes. **Spike testing** evaluates sudden traffic bursts and recovery. **Soak testing** catches issues that emerge over extended operation: memory leaks, connection exhaustion, resource degradation.

- **Tool architecture matters**: Thread-per-user (JMeter) is resource-intensive; event-driven (k6, Locust, Gatling) is efficient; constant-throughput (wrk2) avoids coordinated omission.

- Tool selection depends on team skills and requirements. k6 excels at CI/CD integration with built-in thresholds. Locust offers Python flexibility and simple distributed mode. JMeter provides broad protocol support. Gatling handles extreme concurrency with detailed reporting.

- **Virtual users are not requests per second**. Think time dramatically affects the relationship. 100 VUs with no think time might generate 10,000 RPS; 100 VUs with 5-second think time generate 20 RPS.

- **Coordinated omission** causes most benchmarking tools to systematically underreport latency when servers slow down. Use wrk2 for accurate latency measurement, or understand the limitations of other tools.

- **Statistical rigor** requires multiple runs, warmup periods, and reporting results as ranges with variance. Single benchmark runs are insufficient for reliable conclusions.

- **CI/CD integration** enables automated quality gates. Run smoke tests on every commit (2 minutes), load tests on merge (15-30 minutes), soak tests nightly (8+ hours). Define thresholds aligned to SLOs.

- **Distributed testing** scales beyond single-machine limits. Locust's master-worker architecture and k6 Operator enable tests generating hundreds of thousands of RPS.

- **Synthetic testing has inherent limitations**: environment differences, simplified traffic patterns, mocked dependencies. Complement synthetic testing with RUM and canary deployments for complete coverage.

- **Common pitfalls** include testing without goals, environment mismatches, missing think time, ignoring coordinated omission, and flaky tests eroding trust. Awareness of these pitfalls improves testing effectiveness.

## References

1. **BlazeMeter** (2025). "Performance Testing vs. Load Testing vs. Stress Testing." https://www.blazemeter.com/blog/performance-testing-vs-load-testing-vs-stress-testing

2. **BlazeMeter** (2025). "Stress Testing, Soak Testing and Spike Testing Best Practices." https://www.blazemeter.com/blog/stress-testing-vs-soak-testing-vs-spike-testing

3. **Abstracta** (2025). "API Performance Testing: Optimize Your User Experience." https://abstracta.us/blog/performance-testing/api-performance-testing/

4. **TestLeaf** (2025). "Top 5 Load Testing Tools 2025." https://www.testleaf.com/blog/5-best-load-testing-tools-in-2025/

5. **Grafana Labs** (2025). "Automated Performance Testing with k6." https://grafana.com/docs/k6/latest/testing-guides/automated-performance-testing/

6. **Locust Documentation** (2025). "What is Locust?" https://locust.io/

7. **Tene, Gil** (2015). "How NOT to Measure Latency." Strange Loop Conference. https://www.youtube.com/watch?v=lJ8ydIuPFeU

8. **wrk2 GitHub Repository**. "Coordinated Omission in Load Testing." https://github.com/giltene/wrk2

9. **LoadFocus** (2025). "What are Virtual Users in Load Testing." https://loadfocus.com/docs/guides/load-testing/what-are-virtual-users-load-testing/

10. **LoadFocus** (2025). "Think Time vs Pacing in Load Testing." https://medium.com/@lahirukavikara/think-time-vs-pacing-the-hidden-levers-of-realistic-load-testing-59a84ab668b0

11. **Grafana Labs** (2025). "Distributed Performance Testing: k6 Operator 1.0." https://grafana.com/blog/distributed-performance-testing-for-kubernetes-environments-grafana-k6-operator-1-0-is-here/

12. **Akamai** (2025). "RUM vs. Synthetic Testing." https://www.akamai.com/glossary/what-is-rum-vs-synthetic-testing

13. **Codepipes Blog**. "Software Testing Anti-patterns." https://blog.codepipes.com/testing/software-testing-antipatterns.html

14. **Microsoft Azure Architecture Center** (2025). "Performance Testing and Antipatterns." https://learn.microsoft.com/en-us/azure/architecture/antipatterns/

15. **OctoPerf** (2025). "Open Source Load Testing Tools Comparative Study." https://blog.octoperf.com/open-source-load-testing-tools-comparative-study/

16. **PFLB** (2025). "Best API Load Testing Tools." https://pflb.us/blog/best-api-load-testing-tools/

17. **Grafana Labs** (2025). "Performance Testing with Grafana k6 and GitHub Actions." https://grafana.com/blog/performance-testing-with-grafana-k6-and-github-actions/

## Next: [Chapter 14: Putting It All Together](./14-putting-it-all-together.md)

With testing strategies established, Chapter 14 synthesizes everything into a coherent methodology for API performance optimization, including decision frameworks and real-world case studies.
