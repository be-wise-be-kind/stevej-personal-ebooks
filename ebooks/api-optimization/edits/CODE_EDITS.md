# Code Example Edit Plan

## Summary

This document outlines the edit plan to simplify code examples across all 11 chapters of the API Performance Optimization ebook. The goal is to:
- Reduce each example from 3 languages (Python, Rust, TypeScript) to 1 language per example
- Shorten examples from 40-70 lines to 15-30 lines
- Maintain roughly equal distribution: ~4 Python, ~4 Rust, ~3 TypeScript examples per chapter
- Preserve essential logic and key educational comments while removing redundant boilerplate

---

## Chapter 1: Introduction - The Empirical Discipline

**Total Examples: 3**

### Example 1: Basic Latency Measurement (lines 175-271)
- **Current Languages**: Python (lines 175-201), Rust (lines 203-236), TypeScript (lines 238-271)
- **Selected Language**: Python
- **Lines to Remove**: 203-271 (Rust and TypeScript versions)
- **Trimming Notes for Python version**:
  - Keep decorator structure and timing logic (essential pattern)
  - Remove verbose docstring, trim comments
  - Target: ~18 lines

### Example 2: Percentile Calculation (lines 281-417)
- **Current Languages**: Python (lines 281-321), Rust (lines 323-366), TypeScript (lines 368-417)
- **Selected Language**: TypeScript
- **Lines to Remove**: 281-366 (Python and Rust versions)
- **Trimming Notes for TypeScript version**:
  - Keep percentile calculation function and interface
  - Remove example usage section and some comments
  - Target: ~25 lines

### Example 3: Before/After Comparison (lines 423-594)
- **Current Languages**: Python (lines 423-472), Rust (lines 474-535), TypeScript (lines 537-594)
- **Selected Language**: Rust
- **Lines to Remove**: 423-472, 537-594 (Python and TypeScript versions)
- **Trimming Notes for Rust version**:
  - Keep both slow and fast functions (core teaching point)
  - Remove main function, trim struct definitions
  - Target: ~30 lines

---

## Chapter 2: Understanding Performance Fundamentals

**Total Examples: 3**

### Example 1: Golden Signals Collector (lines 121-326)
- **Current Languages**: Python (lines 121-181), Rust (lines 183-255), TypeScript (lines 257-326)
- **Selected Language**: Python
- **Lines to Remove**: 183-326 (Rust and TypeScript versions)
- **Trimming Notes for Python version**:
  - Keep dataclass and key methods (record_request, get_latency_percentile)
  - Remove get_saturation and get_error_rate methods
  - Target: ~28 lines

### Example 2: Histogram for Latency Distribution (lines 331-530)
- **Current Languages**: Python (lines 332-387), Rust (lines 389-456), TypeScript (lines 458-530)
- **Selected Language**: Rust
- **Lines to Remove**: 332-387, 458-530 (Python and TypeScript versions)
- **Trimming Notes for Rust version**:
  - Keep struct and observe/get_percentile methods
  - Remove get_average method and Default impl
  - Target: ~28 lines

### Example 3: Load Test Harness with Correct Timing (lines 536-786)
- **Current Languages**: Python (lines 537-619), Rust (lines 621-703), TypeScript (lines 706-786)
- **Selected Language**: TypeScript
- **Lines to Remove**: 537-703 (Python and Rust versions)
- **Trimming Notes for TypeScript version**:
  - Keep interface and main function logic
  - Remove warmup phase details, simplify sleep function
  - Target: ~30 lines

---

## Chapter 3: Observability - The Foundation of Optimization

**Total Examples: 4**

### Example 1: OpenTelemetry Instrumentation (lines 136-268)
- **Current Languages**: Python (lines 136-171), Rust (lines 173-221), TypeScript (lines 223-268)
- **Selected Language**: TypeScript
- **Lines to Remove**: 136-221 (Python and Rust versions)
- **Trimming Notes for TypeScript version**:
  - Keep SDK initialization and tracer usage
  - Remove Express route handler, keep core span creation
  - Target: ~25 lines

### Example 2: Custom Prometheus Metrics (lines 274-428)
- **Current Languages**: Python (lines 274-319), Rust (lines 321-372), TypeScript (lines 374-428)
- **Selected Language**: Python
- **Lines to Remove**: 321-428 (Rust and TypeScript versions)
- **Trimming Notes for Python version**:
  - Keep Counter, Gauge, Histogram declarations
  - Remove handle_request function, keep metric definitions
  - Target: ~22 lines

### Example 3: Structured Logging with Correlation (lines 434-589)
- **Current Languages**: Python (lines 434-484), Rust (lines 486-534), TypeScript (lines 536-589)
- **Selected Language**: Rust
- **Lines to Remove**: 434-484, 536-589 (Python and TypeScript versions)
- **Trimming Notes for Rust version**:
  - Keep init_logging and instrument macro usage
  - Remove full process_order function body
  - Target: ~25 lines

### Example 4: CPU Profiler Integration (lines 595-769)
- **Current Languages**: Python (lines 595-653), Rust (lines 655-702), TypeScript (lines 704-769)
- **Selected Language**: Python
- **Lines to Remove**: 655-769 (Rust and TypeScript versions)
- **Trimming Notes for Python version**:
  - Keep pyroscope.configure and profile_endpoint decorator
  - Remove debug_profile endpoint
  - Target: ~20 lines

---

## Chapter 4: Network and Connection Optimization

**Total Examples: 3**

### Example 1: HTTP Client with Connection Pooling (lines 77-193)
- **Current Languages**: Python (lines 77-109), Rust (lines 111-152), TypeScript (lines 154-193)
- **Selected Language**: Rust
- **Lines to Remove**: 77-109, 154-193 (Python and TypeScript versions)
- **Trimming Notes for Rust version**:
  - Keep create_http_client function with pool config
  - Remove User struct, simplify fetch_user
  - Target: ~25 lines

### Example 2: Connection Pool Health Checker (lines 199-514)
- **Current Languages**: Python (lines 199-286), Rust (lines 288-378), TypeScript (lines 380-514)
- **Selected Language**: TypeScript
- **Lines to Remove**: 199-378 (Python and Rust versions)
- **Trimming Notes for TypeScript version**:
  - Keep HealthCheckedPool class with constructor and runHealthCheck
  - Remove startHealthMonitor, acquire, getStats methods
  - Target: ~30 lines

### Example 3: Response Compression Middleware (lines 520-886)
- **Current Languages**: Python (lines 520-626), Rust (lines 629-748), TypeScript (lines 750-886)
- **Selected Language**: Python
- **Lines to Remove**: 629-886 (Rust and TypeScript versions)
- **Trimming Notes for Python version**:
  - Keep CompressionMiddleware class with dispatch method
  - Remove _should_compress method (inline the logic)
  - Target: ~30 lines

---

## Chapter 5: Caching Strategies

**Total Examples: 4**

### Example 1: Cache-Aside Pattern (lines 133-321)
- **Current Languages**: Python (lines 133-192), Rust (lines 194-259), TypeScript (lines 261-321)
- **Selected Language**: TypeScript
- **Lines to Remove**: 133-259 (Python and Rust versions)
- **Trimming Notes for TypeScript version**:
  - Keep CacheAside class with getOrSet method
  - Remove invalidate method and usage example
  - Target: ~25 lines

### Example 2: TTL with Jitter (lines 326-391)
- **Current Languages**: Python (lines 327-349), Rust (lines 351-371), TypeScript (lines 373-391)
- **Selected Language**: Python
- **Lines to Remove**: 351-391 (Rust and TypeScript versions)
- **Trimming Notes for Python version**:
  - Keep function as-is (already concise at ~15 lines)
  - Target: ~15 lines

### Example 3: Single-Flight Pattern (lines 396-590)
- **Current Languages**: Python (lines 397-463), Rust (lines 465-520), TypeScript (lines 522-590)
- **Selected Language**: Rust
- **Lines to Remove**: 397-463, 522-590 (Python and TypeScript versions)
- **Trimming Notes for Rust version**:
  - Keep struct and do_call method
  - Remove usage example and some error handling
  - Target: ~28 lines

### Example 4: Cache Metrics Collection (lines 596-808)
- **Current Languages**: Python (lines 596-654), Rust (lines 656-731), TypeScript (lines 733-808)
- **Selected Language**: TypeScript
- **Lines to Remove**: 596-731 (Python and Rust versions)
- **Trimming Notes for TypeScript version**:
  - Keep MeteredCache class with get method
  - Remove set method and hitRate method
  - Target: ~28 lines

---

## Chapter 6: Database Performance Patterns

**Total Examples: 2 (main N+1 examples plus supporting code)**

### Example 1: N+1 Problem and Solution (lines 24-166)
- **Current Languages**: Python (lines 24-125), Rust (lines 44-143), TypeScript (lines 73-166)
- **Note**: These examples interleave N+1 problem and solution across languages
- **Selected Language**: Python
- **Lines to Remove**: Rust sections (44-70, 127-143), TypeScript sections (73-97, 145-166)
- **Trimming Notes for Python version**:
  - Keep both N+1 problem function AND optimized solution
  - Remove some inline comments
  - Target: ~25 lines total (both functions)

### Example 2: Read Replica Routing (lines 496-693)
- **Current Languages**: Python (lines 496-555), Rust (lines 557-625), TypeScript (lines 627-693)
- **Selected Language**: Rust
- **Lines to Remove**: 496-555, 627-693 (Python and TypeScript versions)
- **Trimming Notes for Rust version**:
  - Keep DatabaseRouter struct with new and write_pool/read_pool methods
  - Remove usage example functions
  - Target: ~28 lines

---

## Chapter 7: Asynchronous Processing and Queuing

**Total Examples: 4**

### Example 1: Background Job Producer and Consumer (lines 135-427)
- **Current Languages**: Python (lines 135-201), Rust (lines 203-318), TypeScript (lines 320-427)
- **Selected Language**: TypeScript
- **Lines to Remove**: 135-318 (Python and Rust versions)
- **Trimming Notes for TypeScript version**:
  - Keep orderQueue creation and worker definition
  - Remove queueEvents handlers and processOrder stub
  - Target: ~30 lines

### Example 2: Backpressure Implementation (lines 433-790)
- **Current Languages**: Python (lines 433-512), Rust (lines 514-649), TypeScript (lines 651-790)
- **Selected Language**: Python
- **Lines to Remove**: 514-790 (Rust and TypeScript versions)
- **Trimming Notes for Python version**:
  - Keep BackpressureConsumer class with acquire_rate_limit
  - Remove process_with_backpressure method
  - Target: ~28 lines

### Example 3: Retry with Exponential Backoff (lines 794-1039)
- **Current Languages**: Python (lines 794-859), Rust (lines 861-947), TypeScript (lines 950-1039)
- **Selected Language**: Rust
- **Lines to Remove**: 794-859, 950-1039 (Python and TypeScript versions)
- **Trimming Notes for Rust version**:
  - Keep RetryConfig struct and calculate_backoff_delay function
  - Simplify retry_with_backoff function
  - Target: ~28 lines

### Example 4: Async HTTP Endpoint with Job Status (lines 1044-1371)
- **Current Languages**: Python (lines 1044-1137), Rust (lines 1139-1271), TypeScript (lines 1274-1371)
- **Selected Language**: Python
- **Lines to Remove**: 1139-1371 (Rust and TypeScript versions)
- **Trimming Notes for Python version**:
  - Keep JobStatus enum and create_job endpoint
  - Remove get_job_status endpoint, simplify process_job
  - Target: ~30 lines

---

## Chapter 8: Compute and Scaling Patterns

**Total Examples: 3**

### Example 1: Stateless Service Design (lines 51-265)
- **Current Languages**: Python (lines 51-106), Rust (lines 108-196), TypeScript (lines 198-265)
- **Selected Language**: Python
- **Lines to Remove**: 108-265 (Rust and TypeScript versions)
- **Trimming Notes for Python version**:
  - Keep get_session, save_session, and one route example
  - Remove login endpoint, keep just get_profile
  - Target: ~25 lines

### Example 2: Cold Start Mitigation (lines 373-535)
- **Current Languages**: Python (lines 373-414), Rust (lines 416-466), TypeScript (lines 469-535)
- **Selected Language**: TypeScript
- **Lines to Remove**: 373-466 (Python and Rust versions)
- **Trimming Notes for TypeScript version**:
  - Keep module-level client initialization
  - Simplify handler function
  - Target: ~25 lines

### Example 3: Graceful Shutdown and Health Checks (lines 561-871)
- **Current Languages**: Python (lines 561-669), Rust (lines 671-749), TypeScript (lines 751-871)
- **Selected Language**: Rust
- **Lines to Remove**: 561-669, 751-871 (Python and TypeScript versions)
- **Trimming Notes for Rust version**:
  - Keep AppState struct and liveness/readiness probes
  - Remove graceful_shutdown function details
  - Target: ~30 lines

---

## Chapter 9: Traffic Management and Resilience

**Total Examples: 4**

### Example 1: Token Bucket Rate Limiter (lines 163-345)
- **Current Languages**: Python (lines 163-220), Rust (lines 222-289), TypeScript (lines 291-345)
- **Selected Language**: Python
- **Lines to Remove**: 222-345 (Rust and TypeScript versions)
- **Trimming Notes for Python version**:
  - Keep TokenBucket dataclass with acquire method
  - Remove _refill as separate method (inline it)
  - Target: ~25 lines

### Example 2: Circuit Breaker Implementation (lines 349-693)
- **Current Languages**: Python (lines 349-447), Rust (lines 449-580), TypeScript (lines 582-693)
- **Selected Language**: TypeScript
- **Lines to Remove**: 349-580 (Python and Rust versions)
- **Trimming Notes for TypeScript version**:
  - Keep CircuitBreaker class with call method
  - Remove onSuccess, onFailure as separate methods
  - Target: ~30 lines

### Example 3: Retry with Exponential Backoff and Jitter (lines 697-983)
- **Current Languages**: Python (lines 697-775), Rust (lines 777-886), TypeScript (lines 888-983)
- **Selected Language**: Rust
- **Lines to Remove**: 697-775, 888-983 (Python and TypeScript versions)
- **Trimming Notes for Rust version**:
  - Keep JitterStrategy enum and calculate_delay function
  - Simplify retry_with_backoff function
  - Target: ~28 lines

### Example 4: Bulkhead with Semaphore (lines 987-1284)
- **Current Languages**: Python (lines 987-1072), Rust (lines 1074-1163), TypeScript (lines 1166-1284)
- **Selected Language**: TypeScript
- **Lines to Remove**: 987-1163 (Python and Rust versions)
- **Trimming Notes for TypeScript version**:
  - Keep Bulkhead class with acquire and call methods
  - Remove release and stats methods
  - Target: ~28 lines

---

## Chapter 10: Advanced Optimization Techniques

**Total Examples: 4**

### Example 1: Edge Function A/B Test Routing (lines 38-160)
- **Current Languages**: Python (lines 38-67), Rust (lines 69-113), TypeScript (lines 115-160)
- **Selected Language**: TypeScript
- **Lines to Remove**: 38-113 (Python and Rust versions)
- **Trimming Notes for TypeScript version**:
  - Keep getExperimentVariant function and handler
  - Remove parseCookies helper function
  - Target: ~25 lines

### Example 2: DataLoader Pattern (lines 202-400)
- **Current Languages**: Python (lines 202-259), Rust (lines 261-334), TypeScript (lines 336-400)
- **Selected Language**: Python
- **Lines to Remove**: 261-400 (Rust and TypeScript versions)
- **Trimming Notes for Python version**:
  - Keep UserLoader class with batch_load_fn
  - Remove PostLoader class
  - Target: ~25 lines

### Example 3: gRPC Service Implementation (lines 430-700)
- **Current Languages**: Python (lines 430-519), Rust (lines 521-604), TypeScript (lines 607-700)
- **Selected Language**: Rust
- **Lines to Remove**: 430-519, 607-700 (Python and TypeScript versions)
- **Trimming Notes for Rust version**:
  - Keep get_user implementation
  - Remove list_users streaming implementation
  - Target: ~30 lines

### Example 4: Hedged Request Implementation (lines 734-973)
- **Current Languages**: Python (lines 734-811), Rust (lines 813-896), TypeScript (lines 899-973)
- **Selected Language**: Python
- **Lines to Remove**: 813-973 (Rust and TypeScript versions)
- **Trimming Notes for Python version**:
  - Keep hedged_request function
  - Simplify attempt inner function
  - Target: ~28 lines

---

## Chapter 11: Putting It All Together

**Total Examples: 2**

### Example 1: Performance Budget Checker (lines 183-435)
- **Current Languages**: Python (lines 183-249), Rust (lines 251-341), TypeScript (lines 343-435)
- **Selected Language**: TypeScript
- **Lines to Remove**: 183-341 (Python and Rust versions)
- **Trimming Notes for TypeScript version**:
  - Keep interfaces and checkBudget function
  - Remove runBudgetCheck function
  - Target: ~28 lines

### Example 2: Optimization Decision Helper (lines 439-753)
- **Current Languages**: Python (lines 439-518), Rust (lines 520-631), TypeScript (lines 633-753)
- **Selected Language**: Python
- **Lines to Remove**: 520-753 (Rust and TypeScript versions)
- **Trimming Notes for Python version**:
  - Keep Symptom enum and RECOMMENDATIONS dict
  - Simplify diagnose function
  - Target: ~30 lines

---

## Language Distribution Summary

| Chapter | Python | Rust | TypeScript |
|---------|--------|------|------------|
| 1       | 1      | 1    | 1          |
| 2       | 1      | 1    | 1          |
| 3       | 2      | 1    | 1          |
| 4       | 1      | 1    | 1          |
| 5       | 1      | 1    | 2          |
| 6       | 1      | 1    | 0          |
| 7       | 2      | 1    | 1          |
| 8       | 1      | 1    | 1          |
| 9       | 1      | 1    | 2          |
| 10      | 2      | 1    | 1          |
| 11      | 1      | 0    | 1          |
| **Total** | **14** | **10** | **12** |

**Distribution Ratio**: Python 39%, Rust 28%, TypeScript 33%

---

## Trimming Guidelines

When reducing examples from 40-70 lines to 15-30 lines, follow these principles:

1. **Keep the core pattern implementation** - The main algorithm or data structure that teaches the concept
2. **Remove usage examples** - "Usage example" or main() functions can be removed
3. **Consolidate comments** - Remove redundant comments, keep 1-2 key explanatory comments
4. **Inline helper functions** - Small helper methods can be inlined if they add 3-5 lines
5. **Remove error handling verbosity** - Keep essential error handling, remove verbose error messages
6. **Remove import statements where possible** - Only keep imports essential for understanding
7. **Keep type annotations** - They aid readability and understanding

---

## Implementation Order

Recommended order for implementing edits:

1. Start with Chapter 1 (foundational, sets the pattern)
2. Do Chapters 2-4 (build observability and network foundations)
3. Do Chapters 5-6 (caching and database - most examples)
4. Do Chapters 7-8 (async and scaling)
5. Do Chapter 9 (resilience patterns - complex examples)
6. Do Chapter 10 (advanced - complex examples)
7. Finish with Chapter 11 (synthesis)

After each chapter, verify that:
- Code examples still compile/run conceptually
- Core teaching point is preserved
- Line counts are within target range
