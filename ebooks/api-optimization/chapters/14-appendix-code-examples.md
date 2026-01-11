# Appendix: Code Examples

This appendix consolidates all code examples from the book, organized by topic. Each example is labeled with its source chapter for cross-reference with the conceptual material.

---

## Performance Fundamentals (Chapter 2)

### Example A.1: Golden Signals Collector (Python, Rust, TypeScript)

The following examples demonstrate a simple class for tracking the four golden signals. In production, use a metrics library like Prometheus, but understanding the underlying mechanics helps choose appropriate metrics.

```python
# Golden signals collector in Python
from collections import defaultdict
from dataclasses import dataclass, field
from threading import Lock
from typing import List, Optional

@dataclass
class GoldenSignals:
    """Track the four golden signals for API monitoring."""

    # Latency tracking - store raw values for percentile calculation
    latencies_ms: List[float] = field(default_factory=list)

    # Traffic tracking - count requests per endpoint
    request_counts: dict = field(default_factory=lambda: defaultdict(int))

    # Error tracking - count by status code
    error_counts: dict = field(default_factory=lambda: defaultdict(int))

    # Saturation tracking - current resource usage
    active_requests: int = 0
    max_concurrent_requests: int = 100  # Capacity limit

    _lock: Lock = field(default_factory=Lock)

    def record_request(self, endpoint: str, latency_ms: float,
                       status_code: int) -> None:
        """Record metrics for a completed request."""
        with self._lock:
            # Traffic: increment request count
            self.request_counts[endpoint] += 1

            # Latency: store for percentile calculation
            self.latencies_ms.append(latency_ms)

            # Errors: track non-2xx responses
            if status_code >= 400:
                self.error_counts[status_code] += 1

    def get_latency_percentile(self, percentile: float) -> Optional[float]:
        """Calculate latency at given percentile (0-100)."""
        if not self.latencies_ms:
            return None
        sorted_latencies = sorted(self.latencies_ms)
        index = int(len(sorted_latencies) * percentile / 100)
        return sorted_latencies[min(index, len(sorted_latencies) - 1)]

    def get_saturation(self) -> float:
        """Return current saturation as percentage of capacity."""
        return (self.active_requests / self.max_concurrent_requests) * 100

    def get_error_rate(self) -> float:
        """Return error rate as percentage of total requests."""
        total = sum(self.request_counts.values())
        if total == 0:
            return 0.0
        total_errors = sum(self.error_counts.values())
        return (total_errors / total) * 100
```

```rust
// Golden signals collector in Rust
use std::collections::HashMap;

pub struct GoldenSignals {
    // Latency tracking - store raw values for percentile calculation
    latencies_ms: Vec<f64>,
    // Traffic tracking - count requests per endpoint
    request_counts: HashMap<String, u64>,
    // Error tracking - count by status code
    error_counts: HashMap<u16, u64>,
    // Saturation tracking
    active_requests: u32,
    max_concurrent_requests: u32,
}

impl GoldenSignals {
    pub fn new(max_concurrent: u32) -> Self {
        GoldenSignals {
            latencies_ms: Vec::new(),
            request_counts: HashMap::new(),
            error_counts: HashMap::new(),
            active_requests: 0,
            max_concurrent_requests: max_concurrent,
        }
    }

    /// Record metrics for a completed request
    pub fn record_request(&mut self, endpoint: &str, latency_ms: f64,
                          status_code: u16) {
        // Traffic: increment request count
        *self.request_counts.entry(endpoint.to_string()).or_insert(0) += 1;

        // Latency: store for percentile calculation
        self.latencies_ms.push(latency_ms);

        // Errors: track non-2xx responses
        if status_code >= 400 {
            *self.error_counts.entry(status_code).or_insert(0) += 1;
        }
    }

    /// Calculate latency at given percentile (0.0-100.0)
    pub fn get_latency_percentile(&self, percentile: f64) -> Option<f64> {
        if self.latencies_ms.is_empty() {
            return None;
        }
        let mut sorted = self.latencies_ms.clone();
        sorted.sort_by(|a, b| a.partial_cmp(b).unwrap());
        let index = ((sorted.len() as f64) * percentile / 100.0) as usize;
        Some(sorted[index.min(sorted.len() - 1)])
    }

    /// Return current saturation as percentage of capacity
    pub fn get_saturation(&self) -> f64 {
        (self.active_requests as f64 / self.max_concurrent_requests as f64) * 100.0
    }

    /// Return error rate as percentage of total requests
    pub fn get_error_rate(&self) -> f64 {
        let total: u64 = self.request_counts.values().sum();
        if total == 0 {
            return 0.0;
        }
        let total_errors: u64 = self.error_counts.values().sum();
        (total_errors as f64 / total as f64) * 100.0
    }
}
```

```typescript
// Golden signals collector in TypeScript

class GoldenSignals {
  private latenciesMs: number[] = [];
  private requestCounts: Map<string, number> = new Map();
  private errorCounts: Map<number, number> = new Map();
  private activeRequests: number = 0;
  private maxConcurrentRequests: number;

  constructor(maxConcurrent: number = 100) {
    this.maxConcurrentRequests = maxConcurrent;
  }

  /** Record metrics for a completed request */
  recordRequest(endpoint: string, latencyMs: number, statusCode: number): void {
    // Traffic: increment request count
    const currentCount = this.requestCounts.get(endpoint) || 0;
    this.requestCounts.set(endpoint, currentCount + 1);

    // Latency: store for percentile calculation
    this.latenciesMs.push(latencyMs);

    // Errors: track non-2xx responses
    if (statusCode >= 400) {
      const errorCount = this.errorCounts.get(statusCode) || 0;
      this.errorCounts.set(statusCode, errorCount + 1);
    }
  }

  /** Calculate latency at given percentile (0-100) */
  getLatencyPercentile(percentile: number): number | null {
    if (this.latenciesMs.length === 0) {
      return null;
    }
    const sorted = [...this.latenciesMs].sort((a, b) => a - b);
    const index = Math.floor(sorted.length * percentile / 100);
    return sorted[Math.min(index, sorted.length - 1)];
  }

  /** Return current saturation as percentage of capacity */
  getSaturation(): number {
    return (this.activeRequests / this.maxConcurrentRequests) * 100;
  }

  /** Return error rate as percentage of total requests */
  getErrorRate(): number {
    let total = 0;
    for (const count of this.requestCounts.values()) {
      total += count;
    }
    if (total === 0) {
      return 0;
    }
    let totalErrors = 0;
    for (const count of this.errorCounts.values()) {
      totalErrors += count;
    }
    return (totalErrors / total) * 100;
  }
}
```

### Example A.2: Histogram for Latency Distribution (Python, Rust, TypeScript)

Production systems use histograms with configurable buckets to efficiently track latency distributions without storing every value.

```python
# Histogram for latency tracking in Python
from dataclasses import dataclass, field
from typing import List
import bisect

@dataclass
class LatencyHistogram:
    """Fixed-bucket histogram for efficient latency percentile tracking."""

    # Bucket boundaries in milliseconds
    # Exponential buckets: 1, 2, 5, 10, 20, 50, 100, 200, 500, 1000, 2000, 5000
    bucket_boundaries: List[float] = field(
        default_factory=lambda: [1, 2, 5, 10, 20, 50, 100, 200, 500, 1000, 2000, 5000]
    )
    bucket_counts: List[int] = field(default_factory=list)
    total_count: int = 0
    total_sum: float = 0.0

    def __post_init__(self):
        # One extra bucket for values exceeding max boundary
        self.bucket_counts = [0] * (len(self.bucket_boundaries) + 1)

    def observe(self, value_ms: float) -> None:
        """Record a latency observation."""
        # Find the appropriate bucket using binary search
        bucket_index = bisect.bisect_right(self.bucket_boundaries, value_ms)
        self.bucket_counts[bucket_index] += 1
        self.total_count += 1
        self.total_sum += value_ms

    def get_percentile(self, percentile: float) -> float:
        """Estimate the value at the given percentile (0-100)."""
        if self.total_count == 0:
            return 0.0

        target_count = self.total_count * percentile / 100.0
        cumulative = 0

        for i, count in enumerate(self.bucket_counts):
            cumulative += count
            if cumulative >= target_count:
                # Return upper bound of this bucket
                if i < len(self.bucket_boundaries):
                    return self.bucket_boundaries[i]
                else:
                    return float('inf')  # Exceeded max bucket

        return self.bucket_boundaries[-1]

    def get_average(self) -> float:
        """Return average latency (use percentiles instead when possible)."""
        if self.total_count == 0:
            return 0.0
        return self.total_sum / self.total_count
```

```rust
// Histogram for latency tracking in Rust
pub struct LatencyHistogram {
    // Bucket boundaries in milliseconds
    bucket_boundaries: Vec<f64>,
    bucket_counts: Vec<u64>,
    total_count: u64,
    total_sum: f64,
}

impl LatencyHistogram {
    /// Create histogram with exponential bucket boundaries
    pub fn new() -> Self {
        let boundaries = vec![1.0, 2.0, 5.0, 10.0, 20.0, 50.0,
                              100.0, 200.0, 500.0, 1000.0, 2000.0, 5000.0];
        let bucket_count = boundaries.len() + 1;
        LatencyHistogram {
            bucket_boundaries: boundaries,
            bucket_counts: vec![0; bucket_count],
            total_count: 0,
            total_sum: 0.0,
        }
    }

    /// Record a latency observation
    pub fn observe(&mut self, value_ms: f64) {
        // Find appropriate bucket using binary search
        let bucket_index = self.bucket_boundaries
            .binary_search_by(|b| b.partial_cmp(&value_ms).unwrap())
            .unwrap_or_else(|i| i);

        self.bucket_counts[bucket_index] += 1;
        self.total_count += 1;
        self.total_sum += value_ms;
    }

    /// Estimate value at given percentile (0.0-100.0)
    pub fn get_percentile(&self, percentile: f64) -> f64 {
        if self.total_count == 0 {
            return 0.0;
        }

        let target_count = (self.total_count as f64) * percentile / 100.0;
        let mut cumulative: u64 = 0;

        for (i, &count) in self.bucket_counts.iter().enumerate() {
            cumulative += count;
            if cumulative as f64 >= target_count {
                if i < self.bucket_boundaries.len() {
                    return self.bucket_boundaries[i];
                } else {
                    return f64::INFINITY;
                }
            }
        }

        *self.bucket_boundaries.last().unwrap_or(&0.0)
    }

    /// Return average latency (prefer percentiles over averages)
    pub fn get_average(&self) -> f64 {
        if self.total_count == 0 {
            return 0.0;
        }
        self.total_sum / self.total_count as f64
    }
}
```

```typescript
// Histogram for latency tracking in TypeScript
class LatencyHistogram {
  // Exponential bucket boundaries in milliseconds
  private bucketBoundaries: number[] = [
    1, 2, 5, 10, 20, 50, 100, 200, 500, 1000, 2000, 5000
  ];
  private bucketCounts: number[];
  private totalCount: number = 0;
  private totalSum: number = 0;

  constructor() {
    // One extra bucket for values exceeding max boundary
    this.bucketCounts = new Array(this.bucketBoundaries.length + 1).fill(0);
  }

  /** Record a latency observation */
  observe(valueMs: number): void {
    // Find appropriate bucket using binary search
    let bucketIndex = this.findBucketIndex(valueMs);
    this.bucketCounts[bucketIndex]++;
    this.totalCount++;
    this.totalSum += valueMs;
  }

  private findBucketIndex(value: number): number {
    // Binary search for the correct bucket
    let low = 0;
    let high = this.bucketBoundaries.length;

    while (low < high) {
      const mid = Math.floor((low + high) / 2);
      if (this.bucketBoundaries[mid] < value) {
        low = mid + 1;
      } else {
        high = mid;
      }
    }
    return low;
  }

  /** Estimate value at given percentile (0-100) */
  getPercentile(percentile: number): number {
    if (this.totalCount === 0) {
      return 0;
    }

    const targetCount = this.totalCount * percentile / 100;
    let cumulative = 0;

    for (let i = 0; i < this.bucketCounts.length; i++) {
      cumulative += this.bucketCounts[i];
      if (cumulative >= targetCount) {
        if (i < this.bucketBoundaries.length) {
          return this.bucketBoundaries[i];
        } else {
          return Infinity;
        }
      }
    }

    return this.bucketBoundaries[this.bucketBoundaries.length - 1];
  }

  /** Return average latency (prefer percentiles over averages) */
  getAverage(): number {
    if (this.totalCount === 0) {
      return 0;
    }
    return this.totalSum / this.totalCount;
  }
}
```

### Example A.3: Load Test Harness with Correct Timing (Python, Rust, TypeScript)

This example demonstrates a load test harness that avoids coordinated omission by sending requests at a fixed rate regardless of response times.

```python
# Load test harness avoiding coordinated omission in Python
import asyncio
import aiohttp
import time
from dataclasses import dataclass
from typing import List

@dataclass
class LoadTestResult:
    latencies_ms: List[float]
    errors: int
    total_requests: int
    duration_seconds: float

    @property
    def throughput_rps(self) -> float:
        return self.total_requests / self.duration_seconds if self.duration_seconds > 0 else 0

async def load_test(
    url: str,
    target_rps: float,
    duration_seconds: float,
    warmup_seconds: float = 5.0
) -> LoadTestResult:
    """
    Run a load test at a fixed request rate.

    Avoids coordinated omission by scheduling requests based on wall clock
    time, not completion of previous requests.
    """
    latencies: List[float] = []
    errors = 0
    interval_ms = 1000.0 / target_rps  # Time between requests

    async with aiohttp.ClientSession() as session:
        # Warmup phase - results discarded
        warmup_start = time.monotonic()
        while time.monotonic() - warmup_start < warmup_seconds:
            try:
                async with session.get(url) as response:
                    await response.read()
            except Exception:
                pass
            await asyncio.sleep(interval_ms / 1000.0)

        # Measurement phase - fixed rate regardless of response time
        start_time = time.monotonic()
        request_count = 0

        while time.monotonic() - start_time < duration_seconds:
            # Calculate when this request should have been sent
            scheduled_time = start_time + (request_count * interval_ms / 1000.0)

            # Record latency from scheduled time, not actual send time
            # This captures queuing delay when system is slow
            request_start = scheduled_time

            try:
                async with session.get(url) as response:
                    await response.read()
                    request_end = time.monotonic()
                    latency_ms = (request_end - request_start) * 1000.0
                    latencies.append(latency_ms)
            except Exception:
                errors += 1

            request_count += 1

            # Sleep until next scheduled request time
            next_scheduled = start_time + (request_count * interval_ms / 1000.0)
            sleep_time = next_scheduled - time.monotonic()
            if sleep_time > 0:
                await asyncio.sleep(sleep_time)

    actual_duration = time.monotonic() - start_time

    return LoadTestResult(
        latencies_ms=latencies,
        errors=errors,
        total_requests=request_count,
        duration_seconds=actual_duration
    )
```

```rust
// Load test harness avoiding coordinated omission in Rust
use reqwest::Client;
use std::time::{Duration, Instant};
use tokio::time::sleep;

pub struct LoadTestResult {
    pub latencies_ms: Vec<f64>,
    pub errors: u64,
    pub total_requests: u64,
    pub duration_seconds: f64,
}

impl LoadTestResult {
    pub fn throughput_rps(&self) -> f64 {
        if self.duration_seconds > 0.0 {
            self.total_requests as f64 / self.duration_seconds
        } else {
            0.0
        }
    }
}

/// Run a load test at fixed request rate, avoiding coordinated omission
pub async fn load_test(
    url: &str,
    target_rps: f64,
    duration_seconds: f64,
    warmup_seconds: f64,
) -> Result<LoadTestResult, Box<dyn std::error::Error>> {
    let client = Client::new();
    let mut latencies: Vec<f64> = Vec::new();
    let mut errors: u64 = 0;
    let interval = Duration::from_secs_f64(1.0 / target_rps);

    // Warmup phase - results discarded
    let warmup_start = Instant::now();
    while warmup_start.elapsed().as_secs_f64() < warmup_seconds {
        let _ = client.get(url).send().await;
        sleep(interval).await;
    }

    // Measurement phase - fixed rate regardless of response time
    let start_time = Instant::now();
    let mut request_count: u64 = 0;

    while start_time.elapsed().as_secs_f64() < duration_seconds {
        // Calculate when this request should have been sent
        let scheduled_time = start_time + interval * request_count as u32;

        // Record latency from scheduled time to capture queuing delay
        let request_start = scheduled_time;

        match client.get(url).send().await {
            Ok(_response) => {
                let request_end = Instant::now();
                let latency_ms = (request_end - request_start).as_secs_f64() * 1000.0;
                latencies.push(latency_ms);
            }
            Err(_) => {
                errors += 1;
            }
        }

        request_count += 1;

        // Sleep until next scheduled request time
        let next_scheduled = start_time + interval * request_count as u32;
        let now = Instant::now();
        if next_scheduled > now {
            sleep(next_scheduled - now).await;
        }
    }

    let actual_duration = start_time.elapsed().as_secs_f64();

    Ok(LoadTestResult {
        latencies_ms: latencies,
        errors,
        total_requests: request_count,
        duration_seconds: actual_duration,
    })
}
```

```typescript
// Load test harness avoiding coordinated omission in TypeScript

interface LoadTestResult {
  latenciesMs: number[];
  errors: number;
  totalRequests: number;
  durationSeconds: number;
  throughputRps: number;
}

/**
 * Run a load test at fixed request rate, avoiding coordinated omission.
 * Uses scheduled send times to accurately measure latency including queue wait.
 */
async function loadTest(
  url: string,
  targetRps: number,
  durationSeconds: number,
  warmupSeconds: number = 5
): Promise<LoadTestResult> {
  const latencies: number[] = [];
  let errors = 0;
  const intervalMs = 1000 / targetRps;

  // Warmup phase - results discarded
  const warmupStart = performance.now();
  while ((performance.now() - warmupStart) / 1000 < warmupSeconds) {
    try {
      await fetch(url);
    } catch {
      // Ignore warmup errors
    }
    await sleep(intervalMs);
  }

  // Measurement phase - fixed rate regardless of response time
  const startTime = performance.now();
  let requestCount = 0;

  while ((performance.now() - startTime) / 1000 < durationSeconds) {
    // Calculate when this request should have been sent
    const scheduledTime = startTime + requestCount * intervalMs;

    // Record latency from scheduled time to capture queuing delay
    const requestStart = scheduledTime;

    try {
      await fetch(url);
      const requestEnd = performance.now();
      const latencyMs = requestEnd - requestStart;
      latencies.push(latencyMs);
    } catch {
      errors++;
    }

    requestCount++;

    // Sleep until next scheduled request time
    const nextScheduled = startTime + requestCount * intervalMs;
    const sleepTime = nextScheduled - performance.now();
    if (sleepTime > 0) {
      await sleep(sleepTime);
    }
  }

  const actualDuration = (performance.now() - startTime) / 1000;

  return {
    latenciesMs: latencies,
    errors,
    totalRequests: requestCount,
    durationSeconds: actualDuration,
    throughputRps: requestCount / actualDuration,
  };
}

function sleep(ms: number): Promise<void> {
  return new Promise((resolve) => setTimeout(resolve, ms));
}
```

### Example A.4: Apdex Score Calculator (Python, TypeScript)

This example demonstrates calculating Apdex scores from latency data.

```python
# Apdex score calculator in Python
from dataclasses import dataclass
from typing import List

@dataclass
class ApdexResult:
    score: float
    satisfied: int
    tolerating: int
    frustrated: int
    total: int
    threshold_ms: float

    @property
    def rating(self) -> str:
        """Return a human-readable rating based on the Apdex score."""
        if self.score >= 0.94:
            return "Excellent"
        elif self.score >= 0.85:
            return "Good"
        elif self.score >= 0.70:
            return "Fair"
        elif self.score >= 0.50:
            return "Poor"
        else:
            return "Unacceptable"

def calculate_apdex(latencies_ms: List[float], threshold_ms: float) -> ApdexResult:
    """
    Calculate the Apdex score for a set of latency measurements.

    Args:
        latencies_ms: List of response times in milliseconds
        threshold_ms: The "T" threshold representing satisfactory response time

    Returns:
        ApdexResult with score and breakdown

    Apdex formula:
        Score = (Satisfied + Tolerating/2) / Total

    Where:
        - Satisfied: response_time <= T
        - Tolerating: T < response_time <= 4T
        - Frustrated: response_time > 4T
    """
    if not latencies_ms:
        return ApdexResult(
            score=1.0,
            satisfied=0,
            tolerating=0,
            frustrated=0,
            total=0,
            threshold_ms=threshold_ms
        )

    satisfied = 0
    tolerating = 0
    frustrated = 0

    tolerating_threshold = threshold_ms * 4

    for latency in latencies_ms:
        if latency <= threshold_ms:
            satisfied += 1
        elif latency <= tolerating_threshold:
            tolerating += 1
        else:
            frustrated += 1

    total = len(latencies_ms)
    score = (satisfied + (tolerating / 2)) / total

    return ApdexResult(
        score=round(score, 3),
        satisfied=satisfied,
        tolerating=tolerating,
        frustrated=frustrated,
        total=total,
        threshold_ms=threshold_ms
    )

# Example usage
latencies = [45, 52, 120, 48, 350, 51, 49, 47, 450, 46, 95, 180, 55, 62, 88]
result = calculate_apdex(latencies, threshold_ms=100)
print(f"Apdex Score: {result.score} ({result.rating})")
print(f"Satisfied: {result.satisfied}, Tolerating: {result.tolerating}, Frustrated: {result.frustrated}")
# Output: Apdex Score: 0.767 (Fair)
# Satisfied: 10, Tolerating: 3, Frustrated: 2
```

```typescript
// Apdex score calculator in TypeScript

interface ApdexResult {
  score: number;
  satisfied: number;
  tolerating: number;
  frustrated: number;
  total: number;
  thresholdMs: number;
  rating: string;
}

/**
 * Calculate the Apdex score for a set of latency measurements.
 *
 * Apdex formula: Score = (Satisfied + Tolerating/2) / Total
 * - Satisfied: response_time <= T
 * - Tolerating: T < response_time <= 4T
 * - Frustrated: response_time > 4T
 */
function calculateApdex(latenciesMs: number[], thresholdMs: number): ApdexResult {
  if (latenciesMs.length === 0) {
    return {
      score: 1.0,
      satisfied: 0,
      tolerating: 0,
      frustrated: 0,
      total: 0,
      thresholdMs,
      rating: 'Excellent'
    };
  }

  let satisfied = 0;
  let tolerating = 0;
  let frustrated = 0;

  const toleratingThreshold = thresholdMs * 4;

  for (const latency of latenciesMs) {
    if (latency <= thresholdMs) {
      satisfied++;
    } else if (latency <= toleratingThreshold) {
      tolerating++;
    } else {
      frustrated++;
    }
  }

  const total = latenciesMs.length;
  const score = (satisfied + tolerating / 2) / total;

  const getRating = (s: number): string => {
    if (s >= 0.94) return 'Excellent';
    if (s >= 0.85) return 'Good';
    if (s >= 0.70) return 'Fair';
    if (s >= 0.50) return 'Poor';
    return 'Unacceptable';
  };

  return {
    score: Math.round(score * 1000) / 1000,
    satisfied,
    tolerating,
    frustrated,
    total,
    thresholdMs,
    rating: getRating(score)
  };
}

// Example usage
const latencies = [45, 52, 120, 48, 350, 51, 49, 47, 450, 46, 95, 180, 55, 62, 88];
const result = calculateApdex(latencies, 100);
console.log(`Apdex Score: ${result.score} (${result.rating})`);
console.log(`Satisfied: ${result.satisfied}, Tolerating: ${result.tolerating}, Frustrated: ${result.frustrated}`);
```

---

## Observability (Chapter 3)

### Example A.5: OpenTelemetry Instrumentation (TypeScript)

Setting up distributed tracing with OpenTelemetry requires initializing a tracer provider, configuring export, and instrumenting your code. This example shows SDK initialization with auto-instrumentation and manual span creation for custom operations.

```typescript
// OpenTelemetry instrumentation in TypeScript
import { NodeSDK } from '@opentelemetry/sdk-node';
import { OTLPTraceExporter } from '@opentelemetry/exporter-trace-otlp-grpc';
import { getNodeAutoInstrumentations } from '@opentelemetry/auto-instrumentations-node';
import { trace, SpanStatusCode } from '@opentelemetry/api';
import express from 'express';

// Initialize SDK with auto-instrumentation for HTTP, Express, etc.
const sdk = new NodeSDK({
  traceExporter: new OTLPTraceExporter({ url: 'http://otel-collector:4317' }),
  instrumentations: [getNodeAutoInstrumentations()],
});
sdk.start();

const tracer = trace.getTracer('api-service');
const app = express();

app.get('/users/:userId', async (req, res) => {
  const span = tracer.startSpan('fetch_user_data');
  span.setAttribute('user.id', req.params.userId);
  try {
    const user = await fetchFromDatabase(req.params.userId);
    if (!user) {
      span.setStatus({ code: SpanStatusCode.ERROR, message: 'User not found' });
      res.status(404).send('Not found');
    } else {
      res.json(user);
    }
  } finally {
    span.end();  // Always end the span
  }
});
```

### Example A.6: Custom Prometheus Metrics (Python)

While automatic instrumentation captures request-level metrics, custom metrics track business-specific values: items in cart, payment amounts, cache effectiveness. This example demonstrates the three primary metric types: counters, gauges, and histograms.

```python
# Custom Prometheus metrics in Python
from prometheus_client import Counter, Gauge, Histogram, start_http_server
import time

# Counter: monotonically increasing (requests, errors)
api_requests_total = Counter(
    'api_requests_total', 'Total API requests',
    ['method', 'endpoint', 'status']  # Labels for filtering
)

# Gauge: can go up or down (queue depth, connections)
active_connections = Gauge('active_connections', 'Active client connections')

# Histogram: distribution of values (latency)
request_duration_seconds = Histogram(
    'request_duration_seconds', 'Request duration',
    ['endpoint'],
    buckets=[0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0]
)

def handle_request(method: str, endpoint: str):
    active_connections.inc()
    start_time = time.time()
    try:
        result = process_request()
        api_requests_total.labels(method=method, endpoint=endpoint, status='success').inc()
        return result
    except Exception:
        api_requests_total.labels(method=method, endpoint=endpoint, status='error').inc()
        raise
    finally:
        request_duration_seconds.labels(endpoint=endpoint).observe(time.time() - start_time)
        active_connections.dec()
```

### Example A.7: Structured Logging with Correlation (Rust)

Structured logging transforms logs from human-readable text into queryable JSON documents. Including trace and span IDs enables correlation with distributed traces. This example uses the `tracing` crate with JSON formatting and automatic span field injection.

```rust
// Structured logging with trace correlation in Rust
use tracing::{info, error, instrument};
use tracing_subscriber::{fmt, layer::SubscriberExt, EnvFilter};

pub fn init_logging() {
    let subscriber = tracing_subscriber::registry()
        .with(EnvFilter::from_default_env())
        .with(fmt::layer().json().with_current_span(true));
    tracing::subscriber::set_global_default(subscriber).expect("Failed to set subscriber");
}

#[instrument(fields(order_id = %order_id, user_id = %user_id))]
async fn process_order(order_id: &str, user_id: &str) -> Result<(), OrderError> {
    // Fields from #[instrument] automatically included in all logs
    info!("order_processing_started");

    validate_order(order_id).await?;
    info!(items_count = 3, "order_validated");

    match charge_payment(order_id).await {
        Ok(payment) => {
            info!(amount = payment.amount, currency = %payment.currency, "payment_processed");
            Ok(())
        }
        Err(e) => {
            error!(error = %e, "payment_failed");
            Err(e.into())
        }
    }
}
```

### Example A.8: CPU Profiler Integration (Python)

Continuous profiling in production identifies code hotspots that synthetic benchmarks miss. This example shows both continuous profiling with Pyroscope and a decorator for on-demand profiling of specific endpoints.

```python
# CPU profiling integration in Python
import cProfile
import pstats
import io
from functools import wraps
import pyroscope

# Initialize continuous profiling with Pyroscope
pyroscope.configure(
    application_name="api-service",
    server_address="http://pyroscope:4040",
    sample_rate=100,
    tags={"environment": "production", "version": "1.2.3"}
)

# Decorator for on-demand profiling of specific endpoints
def profile_endpoint(func):
    @wraps(func)
    def wrapper(*args, **kwargs):
        profiler = cProfile.Profile()
        profiler.enable()
        try:
            return func(*args, **kwargs)
        finally:
            profiler.disable()
            stream = io.StringIO()
            stats = pstats.Stats(profiler, stream=stream)
            stats.sort_stats('cumulative').print_stats(20)
            logger.debug(f"Profile for {func.__name__}:\n{stream.getvalue()}")
    return wrapper
```

---

## Monitoring (Chapter 4)

### Example A.9: Canary Deployment Validation (Python)

```python
from dataclasses import dataclass
from scipy import stats
from typing import List

@dataclass
class CanaryMetrics:
    latencies_ms: List[float]
    error_count: int
    request_count: int

@dataclass
class CanaryAnalysis:
    should_proceed: bool
    latency_regression_detected: bool
    error_rate_elevated: bool
    confidence: float
    details: str

def analyze_canary(
    baseline: CanaryMetrics,
    canary: CanaryMetrics,
    latency_threshold_ms: float = 10.0,
    error_rate_threshold: float = 0.01,
    significance_level: float = 0.05
) -> CanaryAnalysis:
    """
    Compare canary metrics against baseline to determine if deployment
    should proceed. Uses statistical testing to avoid false positives
    from random variation.
    """
    # Latency comparison using Mann-Whitney U test (non-parametric)
    if len(canary.latencies_ms) < 30 or len(baseline.latencies_ms) < 30:
        return CanaryAnalysis(
            should_proceed=False, latency_regression_detected=False,
            error_rate_elevated=False, confidence=0.0,
            details="Insufficient samples for statistical analysis"
        )

    stat, p_value = stats.mannwhitneyu(
        canary.latencies_ms, baseline.latencies_ms, alternative='greater'
    )

    canary_p50 = sorted(canary.latencies_ms)[len(canary.latencies_ms) // 2]
    baseline_p50 = sorted(baseline.latencies_ms)[len(baseline.latencies_ms) // 2]
    latency_regression = (
        p_value < significance_level and
        (canary_p50 - baseline_p50) > latency_threshold_ms
    )

    # Error rate comparison
    canary_error_rate = canary.error_count / max(canary.request_count, 1)
    baseline_error_rate = baseline.error_count / max(baseline.request_count, 1)
    error_elevated = (canary_error_rate - baseline_error_rate) > error_rate_threshold

    should_proceed = not latency_regression and not error_elevated

    return CanaryAnalysis(
        should_proceed=should_proceed,
        latency_regression_detected=latency_regression,
        error_rate_elevated=error_elevated,
        confidence=1 - p_value,
        details=f"Canary p50: {canary_p50:.1f}ms, Baseline p50: {baseline_p50:.1f}ms"
    )
```

### Example A.10: Simple Anomaly Detection (Python)

```python
from collections import deque
from dataclasses import dataclass
from typing import Optional

@dataclass
class AnomalyResult:
    is_anomaly: bool
    value: float
    expected: float
    deviation_sigmas: float

class SimpleAnomalyDetector:
    """
    Detect anomalies using rolling statistics.
    Flags values that deviate significantly from recent history.
    """

    def __init__(self, window_size: int = 60, sigma_threshold: float = 3.0):
        self.window_size = window_size
        self.sigma_threshold = sigma_threshold
        self.values: deque = deque(maxlen=window_size)

    def check(self, value: float) -> Optional[AnomalyResult]:
        if len(self.values) < self.window_size:
            self.values.append(value)
            return None  # Not enough data yet

        mean = sum(self.values) / len(self.values)
        variance = sum((x - mean) ** 2 for x in self.values) / len(self.values)
        std_dev = variance ** 0.5

        if std_dev == 0:
            deviation = 0.0
        else:
            deviation = abs(value - mean) / std_dev

        self.values.append(value)

        return AnomalyResult(
            is_anomaly=deviation > self.sigma_threshold,
            value=value,
            expected=mean,
            deviation_sigmas=deviation
        )
```

---

## Network and Connections (Chapter 5)

### Example A.11: HTTP Client with Connection Pooling (Rust)

```rust
// HTTP client with connection pooling in Rust
use reqwest::{Client, ClientBuilder};
use std::time::Duration;
use serde::Deserialize;

#[derive(Deserialize)]
struct User { id: u64, name: String, email: String }

// Create a reusable client with connection pooling
fn create_http_client() -> Client {
    ClientBuilder::new()
        .pool_max_idle_per_host(20)                  // Idle connections per host
        .pool_idle_timeout(Duration::from_secs(30)) // Close idle after 30s
        .connect_timeout(Duration::from_secs(5))    // Connection establishment
        .timeout(Duration::from_secs(30))           // Total request timeout
        .gzip(true)
        .brotli(true)
        .build()
        .expect("Failed to create HTTP client")
}

async fn fetch_user(client: &Client, user_id: u64) -> Result<User, reqwest::Error> {
    client.get(format!("https://api.example.com/users/{}", user_id))
        .header("Accept-Encoding", "gzip, br")
        .send().await?
        .json::<User>().await
}
// Create client once at startup, reuse for all requests
```

### Example A.12: Connection Pool Health Checker (TypeScript)

```typescript
// Connection pool health checker in TypeScript
import { Pool, PoolClient, PoolConfig } from 'pg';

interface HealthCheckConfig {
  validationIntervalMs: number;
  validationTimeoutMs: number;
}

class HealthCheckedPool {
  private pool: Pool;
  private healthCheckInterval: NodeJS.Timeout | null = null;
  private config: HealthCheckConfig;

  constructor(poolConfig: PoolConfig, healthConfig: HealthCheckConfig) {
    this.config = healthConfig;
    this.pool = new Pool({ ...poolConfig, keepAlive: true });
    this.pool.on('error', (err) => console.error('Pool error:', err));
  }

  startHealthMonitor(): void {
    this.healthCheckInterval = setInterval(
      () => this.runHealthCheck(),
      this.config.validationIntervalMs
    );
  }

  private async runHealthCheck(): Promise<void> {
    let client: PoolClient | null = null;
    try {
      client = await this.pool.connect();
      await client.query('SELECT 1');  // Validate connection
      console.log(`Pool: ${this.pool.totalCount} total, ${this.pool.idleCount} idle`);
    } catch (error) {
      console.error('Health check failed:', error);
    } finally {
      client?.release();
    }
  }

  async acquire(): Promise<PoolClient> {
    const client = await this.pool.connect();
    await client.query('SELECT 1');  // Validate before returning
    return client;
  }

  async close(): Promise<void> {
    if (this.healthCheckInterval) clearInterval(this.healthCheckInterval);
    await this.pool.end();
  }
}
```

### Example A.13: Response Compression Middleware (Python)

```python
# Response compression middleware in Python (Starlette/FastAPI)
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response
import gzip
import brotli

COMPRESSIBLE_TYPES = {"application/json", "text/html", "text/plain", "application/xml"}
MIN_COMPRESSION_SIZE = 1024

class CompressionMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next) -> Response:
        accept_encoding = request.headers.get("accept-encoding", "")
        response = await call_next(request)

        # Skip if not compressible
        content_type = (response.media_type or "").split(";")[0].strip()
        if content_type not in COMPRESSIBLE_TYPES or "content-encoding" in response.headers:
            return response

        body = b"".join([chunk async for chunk in response.body_iterator])
        if len(body) < MIN_COMPRESSION_SIZE:
            return Response(content=body, status_code=response.status_code,
                          headers=dict(response.headers), media_type=response.media_type)

        # Compress: prefer Brotli, fall back to gzip
        if "br" in accept_encoding:
            compressed, encoding = brotli.compress(body, quality=4), "br"
        elif "gzip" in accept_encoding:
            compressed, encoding = gzip.compress(body, compresslevel=6), "gzip"
        else:
            return Response(content=body, status_code=response.status_code,
                          headers=dict(response.headers), media_type=response.media_type)

        if len(compressed) >= len(body):  # Only use if actually smaller
            return Response(content=body, status_code=response.status_code,
                          headers=dict(response.headers), media_type=response.media_type)

        headers = dict(response.headers)
        headers.update({"content-encoding": encoding, "vary": "accept-encoding"})
        return Response(content=compressed, status_code=response.status_code,
                       headers=headers, media_type=response.media_type)
```

---

## Caching Strategies (Chapter 6)

### Example A.14: Cache-Aside Pattern (TypeScript)

A complete cache-aside implementation that checks the cache first and falls back to the database on cache miss, then stores the result for future requests.

```typescript
// Cache-aside implementation in TypeScript
import Redis from 'ioredis';

class CacheAside {
  private redis: Redis;
  private defaultTtl: number;

  constructor(redisUrl: string, defaultTtl: number = 300) {
    this.redis = new Redis(redisUrl);
    this.defaultTtl = defaultTtl;
  }

  /** Get value from cache, or fetch and cache if missing. */
  async getOrSet<T>(key: string, fetchFunc: () => Promise<T>, ttl?: number): Promise<T> {
    const effectiveTtl = ttl ?? this.defaultTtl;

    // Try cache first
    const cached = await this.redis.get(key);
    if (cached !== null) {
      return JSON.parse(cached) as T;
    }

    // Cache miss - fetch from origin and store
    const value = await fetchFunc();
    await this.redis.setex(key, effectiveTtl, JSON.stringify(value));
    return value;
  }

  async invalidate(key: string): Promise<void> {
    await this.redis.del(key);
  }
}

// Usage
const cache = new CacheAside('redis://localhost:6379');
const user = await cache.getOrSet(`user:${userId}`, () => db.fetchUser(userId), 600);
```

### Example A.15: TTL with Jitter (Python)

A utility function that adds random jitter to TTL values, preventing synchronized cache expiration that can cause thundering herd events.

```python
# TTL with jitter in Python
import random

def ttl_with_jitter(base_ttl: int, jitter_percent: float = 0.1) -> int:
    """
    Calculate TTL with random jitter to prevent thundering herd.
    Args:
        base_ttl: Base TTL in seconds
        jitter_percent: Maximum jitter as percentage (0.1 = +/-10%)
    """
    jitter_range = int(base_ttl * jitter_percent)
    jitter = random.randint(-jitter_range, jitter_range)
    return base_ttl + jitter

# Usage: TTL of 300s +/- 30s
ttl = ttl_with_jitter(300, jitter_percent=0.1)  # Returns 270-330
```

### Example A.16: Single-Flight Pattern (Rust)

The single-flight pattern ensures only one request regenerates an expired cache entry while other concurrent requests wait for the result, preventing database overload.

```rust
// Single-flight pattern in Rust
use std::collections::HashMap;
use std::future::Future;
use std::sync::Arc;
use tokio::sync::{Mutex, broadcast};

pub struct SingleFlight<T> {
    in_flight: Arc<Mutex<HashMap<String, broadcast::Sender<T>>>>,
}

impl<T: Clone + Send + 'static> SingleFlight<T> {
    pub fn new() -> Self {
        Self { in_flight: Arc::new(Mutex::new(HashMap::new())) }
    }

    /// Execute fetch_func for key, deduplicating concurrent calls.
    pub async fn do_call<F, Fut>(&self, key: &str, fetch_func: F)
        -> Result<T, Box<dyn std::error::Error + Send + Sync>>
    where
        F: FnOnce() -> Fut,
        Fut: Future<Output = Result<T, Box<dyn std::error::Error + Send + Sync>>>,
    {
        let mut in_flight = self.in_flight.lock().await;

        // If request already in flight, wait for its result
        if let Some(sender) = in_flight.get(key) {
            let mut receiver = sender.subscribe();
            drop(in_flight);
            return Ok(receiver.recv().await?);
        }

        // Create broadcast channel and register this request
        let (sender, _) = broadcast::channel(1);
        in_flight.insert(key.to_string(), sender.clone());
        drop(in_flight);

        let result = fetch_func().await;

        // Clean up and broadcast result to waiters
        self.in_flight.lock().await.remove(key);
        if let Ok(ref value) = result {
            let _ = sender.send(value.clone());
        }
        result
    }
}
```

### Example A.17: Cache Metrics Collection (TypeScript)

A metered cache wrapper that tracks hits, misses, and latency using Prometheus metrics, enabling data-driven tuning of cache configuration.

```typescript
// Cache metrics collection in TypeScript
import Redis from 'ioredis';
import { Counter, Histogram, Registry } from 'prom-client';

class MeteredCache {
  private redis: Redis;
  private name: string;
  private hits: Counter;
  private misses: Counter;
  private latency: Histogram;

  constructor(redisUrl: string, name: string, registry: Registry) {
    this.redis = new Redis(redisUrl);
    this.name = name;

    this.hits = new Counter({
      name: 'cache_hits_total', help: 'Total cache hits',
      labelNames: ['cache_name'], registers: [registry],
    });
    this.misses = new Counter({
      name: 'cache_misses_total', help: 'Total cache misses',
      labelNames: ['cache_name'], registers: [registry],
    });
    this.latency = new Histogram({
      name: 'cache_operation_duration_seconds', help: 'Cache operation latency',
      labelNames: ['cache_name', 'operation'],
      buckets: [0.001, 0.005, 0.01, 0.025, 0.05, 0.1],
      registers: [registry],
    });
  }

  async get(key: string): Promise<string | null> {
    const start = process.hrtime.bigint();
    try {
      const value = await this.redis.get(key);
      (value !== null ? this.hits : this.misses).inc({ cache_name: this.name });
      return value;
    } finally {
      const duration = Number(process.hrtime.bigint() - start) / 1e9;
      this.latency.observe({ cache_name: this.name, operation: 'get' }, duration);
    }
  }
}
```

---

## Database Performance Patterns (Chapter 7)

### Example A.18: N+1 Query Problem and Solution (Python)

```python
# The N+1 problem in Python (using SQLAlchemy)
from sqlalchemy.orm import Session, joinedload
from models import Post

def get_posts_with_authors_n_plus_one(db: Session):
    posts = db.query(Post).limit(100).all()
    result = []
    for post in posts:
        # Each access to post.author triggers a separate query!
        result.append({"title": post.title, "author_name": post.author.name})
    return result  # Total: 101 database round-trips

def get_posts_with_authors_optimized(db: Session):
    # Single query with JOIN - fetches posts and authors together
    posts = db.query(Post).options(joinedload(Post.author)).limit(100).all()
    result = []
    for post in posts:
        # No additional query - author is already loaded
        result.append({"title": post.title, "author_name": post.author.name})
    return result  # Total: 1 database round-trip
```

### Example A.19: Creating Indexes with SQLAlchemy/Alembic (Python)

```python
# Creating indexes in Python using SQLAlchemy migrations (Alembic)
from alembic import op
import sqlalchemy as sa

def upgrade():
    # B-tree index for equality and range queries on created_at
    op.create_index(
        'ix_posts_created_at',
        'posts',
        ['created_at'],
        unique=False
    )

    # Composite index for queries filtering by status and created_at
    # Index order matters: put equality columns first, range columns last
    op.create_index(
        'ix_posts_status_created_at',
        'posts',
        ['status', 'created_at'],
        unique=False
    )

    # Covering index: includes all columns needed by query
    # Avoids table lookup by reading directly from index
    op.create_index(
        'ix_posts_covering',
        'posts',
        ['author_id', 'status'],
        postgresql_include=['title', 'created_at']  # PostgreSQL INCLUDE clause
    )
```

### Example A.20: Creating Indexes with Diesel Migrations (Rust)

```rust
// Creating indexes in Rust using Diesel migrations
// In migrations/2024-01-01-000001_add_indexes/up.sql

-- B-tree index for equality and range queries on created_at
CREATE INDEX ix_posts_created_at ON posts (created_at);

-- Composite index for queries filtering by status and created_at
-- Put high-selectivity columns first for equality, range columns last
CREATE INDEX ix_posts_status_created_at ON posts (status, created_at);

-- Covering index with INCLUDE clause (PostgreSQL 11+)
-- All query columns are in the index, avoiding heap table access
CREATE INDEX ix_posts_covering ON posts (author_id, status)
    INCLUDE (title, created_at);
```

### Example A.21: Creating Indexes with Prisma Schema (TypeScript)

```typescript
// Creating indexes in TypeScript using Prisma schema
// In schema.prisma

model Post {
  id        Int      @id @default(autoincrement())
  title     String
  status    String
  createdAt DateTime @default(now()) @map("created_at")
  authorId  Int      @map("author_id")
  author    User     @relation(fields: [authorId], references: [id])

  // B-tree index on created_at (default index type)
  @@index([createdAt])

  // Composite index for filtering by status and created_at
  @@index([status, createdAt])

  // Composite index for author lookups with status filter
  @@index([authorId, status])

  @@map("posts")
}
```

### Example A.22: Analyzing Query Plans (Python)

```python
# Analyzing query plans in Python
from sqlalchemy import text

def analyze_query(db: Session, user_id: int):
    # Get the query plan with execution statistics
    explain_query = text("""
        EXPLAIN (ANALYZE, BUFFERS, FORMAT JSON)
        SELECT p.*, u.name as author_name
        FROM posts p
        JOIN users u ON p.author_id = u.id
        WHERE p.author_id = :user_id
        AND p.status = 'published'
        ORDER BY p.created_at DESC
        LIMIT 20
    """)

    result = db.execute(explain_query, {"user_id": user_id})
    plan = result.fetchone()[0]

    # Key metrics to examine:
    # - "Seq Scan" indicates a full table scan (often a red flag)
    # - "Index Scan" or "Index Only Scan" indicates index usage
    # - "Rows" vs "Actual Rows" shows estimation accuracy
    # - "Buffers" shows I/O operations
    return plan
```

### Example A.23: Analyzing Query Plans (Rust)

```rust
// Analyzing query plans in Rust
use diesel::prelude::*;
use diesel::sql_query;
use diesel::sql_types::Text;

#[derive(QueryableByName, Debug)]
struct ExplainResult {
    #[diesel(sql_type = Text)]
    #[diesel(column_name = "QUERY PLAN")]
    query_plan: String,
}

fn analyze_query(conn: &mut PgConnection, user_id: i32) -> Vec<String> {
    // Get the query plan with execution statistics
    let explain_sql = format!(
        "EXPLAIN (ANALYZE, BUFFERS) \
         SELECT p.*, u.name as author_name \
         FROM posts p \
         JOIN users u ON p.author_id = u.id \
         WHERE p.author_id = {} \
         AND p.status = 'published' \
         ORDER BY p.created_at DESC \
         LIMIT 20",
        user_id
    );

    sql_query(explain_sql)
        .load::<ExplainResult>(conn)
        .expect("Error running EXPLAIN")
        .into_iter()
        .map(|r| r.query_plan)
        .collect()
}
```

### Example A.24: Analyzing Query Plans (TypeScript)

```typescript
// Analyzing query plans in TypeScript
import { PrismaClient } from '@prisma/client';

const prisma = new PrismaClient();

async function analyzeQuery(userId: number) {
  // Get the query plan with execution statistics
  const plan = await prisma.$queryRaw`
    EXPLAIN (ANALYZE, BUFFERS, FORMAT JSON)
    SELECT p.*, u.name as author_name
    FROM posts p
    JOIN users u ON p.author_id = u.id
    WHERE p.author_id = ${userId}
    AND p.status = 'published'
    ORDER BY p.created_at DESC
    LIMIT 20
  `;

  // Key indicators in the plan:
  // - "Seq Scan" = full table scan (needs index)
  // - "Index Scan" = using index (good)
  // - "Index Only Scan" = covered by index (best)
  // - High "Actual Rows" vs "Rows" = statistics need updating
  return plan;
}
```

### Example A.25: Connection Pool Configuration (Python)

```python
# Connection pool configuration in Python with asyncpg
import asyncpg
from contextlib import asynccontextmanager

async def create_pool():
    # Create a connection pool with explicit bounds
    pool = await asyncpg.create_pool(
        dsn="postgresql://user:pass@localhost/dbname",
        min_size=5,           # Minimum connections to maintain warm
        max_size=20,          # Maximum connections (tune based on workload)
        max_inactive_connection_lifetime=300.0,  # Close idle connections after 5 min
        command_timeout=30.0,  # Query timeout in seconds
    )
    return pool

@asynccontextmanager
async def get_connection(pool: asyncpg.Pool):
    """Acquire a connection from the pool with proper cleanup."""
    conn = await pool.acquire()
    try:
        yield conn
    finally:
        await pool.release(conn)

# Usage
async def fetch_user(pool: asyncpg.Pool, user_id: int):
    async with get_connection(pool) as conn:
        return await conn.fetchrow(
            "SELECT * FROM users WHERE id = $1",
            user_id
        )
```

### Example A.26: Connection Pool Configuration (Rust)

```rust
// Connection pool configuration in Rust with SQLx
use sqlx::postgres::{PgPoolOptions, PgPool};
use std::time::Duration;

async fn create_pool() -> Result<PgPool, sqlx::Error> {
    // Create a connection pool with explicit bounds
    let pool = PgPoolOptions::new()
        .min_connections(5)      // Minimum connections to maintain warm
        .max_connections(20)     // Maximum connections (tune based on workload)
        .acquire_timeout(Duration::from_secs(30))  // Wait timeout for connection
        .idle_timeout(Duration::from_secs(300))    // Close idle connections after 5 min
        .max_lifetime(Duration::from_secs(1800))   // Recycle connections after 30 min
        .connect("postgresql://user:pass@localhost/dbname")
        .await?;

    Ok(pool)
}

// Usage - connections automatically return to pool when dropped
async fn fetch_user(pool: &PgPool, user_id: i32) -> Result<User, sqlx::Error> {
    sqlx::query_as::<_, User>("SELECT * FROM users WHERE id = $1")
        .bind(user_id)
        .fetch_one(pool)
        .await
}
```

### Example A.27: Connection Pool Configuration (TypeScript)

```typescript
// Connection pool configuration in TypeScript with pg
import { Pool, PoolConfig } from 'pg';

function createPool(): Pool {
  const config: PoolConfig = {
    connectionString: 'postgresql://user:pass@localhost/dbname',
    min: 5,                    // Minimum connections to maintain warm
    max: 20,                   // Maximum connections (tune based on workload)
    idleTimeoutMillis: 300000, // Close idle connections after 5 min
    connectionTimeoutMillis: 30000,  // Wait timeout for connection
    maxUses: 7500,             // Recycle connections after N uses
  };

  return new Pool(config);
}

// Usage with proper connection release
async function fetchUser(pool: Pool, userId: number) {
  const client = await pool.connect();
  try {
    const result = await client.query(
      'SELECT * FROM users WHERE id = $1',
      [userId]
    );
    return result.rows[0];
  } finally {
    client.release();  // Always release back to pool
  }
}
```

### Example A.28: Read Replica Routing (Rust)

```rust
// Read replica routing in Rust
use sqlx::postgres::{PgPool, PgPoolOptions};
use rand::seq::SliceRandom;

pub struct DatabaseRouter {
    primary: PgPool,
    replicas: Vec<PgPool>,
}

impl DatabaseRouter {
    pub async fn new(primary_url: &str, replica_urls: &[&str]) -> Result<Self, sqlx::Error> {
        let primary = PgPoolOptions::new().max_connections(10).connect(primary_url).await?;
        let mut replicas = Vec::new();
        for url in replica_urls {
            replicas.push(PgPoolOptions::new().max_connections(10).connect(url).await?);
        }
        Ok(Self { primary, replicas })
    }

    /// Get the primary pool for write operations
    pub fn write_pool(&self) -> &PgPool {
        &self.primary
    }

    /// Get a random replica pool for read operations
    pub fn read_pool(&self) -> &PgPool {
        self.replicas.choose(&mut rand::thread_rng()).unwrap_or(&self.primary)
    }
}

// Usage: router.read_pool() for SELECTs, router.write_pool() for INSERT/UPDATE/DELETE
```

---

## Asynchronous Processing and Queuing (Chapter 8)

### Example A.29: Background Job Producer and Consumer (TypeScript)

This example demonstrates enqueueing work for background processing and consuming it reliably using BullMQ with Redis as the backing store.

```typescript
// Background job system in TypeScript using BullMQ
import { Queue, Worker, Job } from 'bullmq';
import Redis from 'ioredis';

const redis = new Redis({ host: 'localhost', port: 6379, maxRetriesPerRequest: null });

interface OrderJobData { orderId: string; userEmail: string; }
interface OrderJobResult { orderId: string; status: 'completed' | 'failed'; }

const orderQueue = new Queue<OrderJobData, OrderJobResult>('orders', {
  connection: redis,
  defaultJobOptions: {
    attempts: 3,
    backoff: { type: 'exponential', delay: 1000 },
    removeOnComplete: { count: 1000 },
    removeOnFail: { age: 7 * 24 * 3600 },
  },
});

// Producer: Enqueue order for processing
async function enqueueOrder(orderId: string, userEmail: string): Promise<string> {
  const job = await orderQueue.add('process-order', { orderId, userEmail },
    { priority: 1, jobId: `order-${orderId}` });
  return job.id!;
}

// Consumer: Process orders with retry on failure
const orderWorker = new Worker<OrderJobData, OrderJobResult>('orders',
  async (job: Job<OrderJobData, OrderJobResult>) => {
    console.log(`Processing order ${job.data.orderId}, attempt ${job.attemptsMade + 1}`);
    await processOrder(job.data.orderId, job.data.userEmail);
    return { orderId: job.data.orderId, status: 'completed' };
  },
  { connection: redis, concurrency: 10 }
);
```

### Example A.30: Backpressure Implementation (Python)

This example shows rate-limited consumers that implement backpressure when overwhelmed, using a token bucket algorithm for rate limiting combined with semaphore-based concurrency control.

```python
# Rate-limited consumer with backpressure in Python
import asyncio
from dataclasses import dataclass
from datetime import datetime

@dataclass
class BackpressureConfig:
    max_queue_depth: int = 1000
    max_concurrent: int = 50
    rate_limit_per_second: float = 100.0

class BackpressureConsumer:
    def __init__(self, config: BackpressureConfig):
        self.config = config
        self.semaphore = asyncio.Semaphore(config.max_concurrent)
        self.last_process_time = datetime.now()
        self.tokens = config.rate_limit_per_second

    async def can_accept(self, queue_depth: int) -> bool:
        return queue_depth < self.config.max_queue_depth

    async def acquire_rate_limit(self) -> bool:
        """Token bucket rate limiting."""
        now = datetime.now()
        elapsed = (now - self.last_process_time).total_seconds()
        self.last_process_time = now
        self.tokens = min(self.config.rate_limit_per_second,
                         self.tokens + elapsed * self.config.rate_limit_per_second)
        if self.tokens >= 1.0:
            self.tokens -= 1.0
            return True
        return False

    async def process_with_backpressure(self, handler, message, queue_depth):
        if not await self.can_accept(queue_depth):
            raise BackpressureError("Queue depth exceeded")
        while not await self.acquire_rate_limit():
            await asyncio.sleep(0.01)
        async with self.semaphore:
            return await handler(message)

class BackpressureError(Exception):
    pass
```

### Example A.31: Retry with Exponential Backoff and Jitter (Rust)

This implementation provides a reusable retry wrapper with configurable backoff parameters and jitter to prevent thundering herd problems.

```rust
// Retry logic with exponential backoff and jitter in Rust
use rand::Rng;
use std::future::Future;
use std::time::Duration;
use tokio::time::sleep;
use tracing::{warn, error};

pub struct RetryConfig {
    pub max_attempts: u32,
    pub base_delay: Duration,
    pub max_delay: Duration,
    pub exponential_base: f64,
    pub jitter_factor: f64,
}

impl Default for RetryConfig {
    fn default() -> Self {
        Self { max_attempts: 3, base_delay: Duration::from_secs(1),
               max_delay: Duration::from_secs(60), exponential_base: 2.0, jitter_factor: 0.1 }
    }
}

fn calculate_backoff_delay(attempt: u32, config: &RetryConfig) -> Duration {
    let delay_secs = config.base_delay.as_secs_f64() * config.exponential_base.powi(attempt as i32);
    let delay_secs = delay_secs.min(config.max_delay.as_secs_f64());
    let jitter = delay_secs * config.jitter_factor * (2.0 * rand::thread_rng().gen::<f64>() - 1.0);
    Duration::from_secs_f64((delay_secs + jitter).max(0.0))
}

pub async fn retry_with_backoff<F, Fut, T, E>(mut operation: F, config: &RetryConfig) -> Result<T, E>
where F: FnMut() -> Fut, Fut: Future<Output = Result<T, E>>, E: std::fmt::Debug {
    for attempt in 0..config.max_attempts {
        match operation().await {
            Ok(result) => return Ok(result),
            Err(e) if attempt + 1 >= config.max_attempts => return Err(e),
            Err(e) => {
                warn!(attempt = attempt + 1, error = ?e, "Retrying after backoff");
                sleep(calculate_backoff_delay(attempt, config)).await;
            }
        }
    }
    unreachable!()
}
```

### Example A.32: Async HTTP Endpoint with Job Status (Python)

This FastAPI implementation demonstrates the async request pattern where the API accepts work, returns immediately with a job ID, and provides a polling endpoint for status updates.

```python
# Async API endpoint in Python with FastAPI
from fastapi import FastAPI, BackgroundTasks
from pydantic import BaseModel
from uuid import uuid4
from datetime import datetime
from enum import Enum

app = FastAPI()

class JobStatus(str, Enum):
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"

class JobRequest(BaseModel):
    data: dict

jobs: dict = {}  # Use Redis in production

async def process_job(job_id: str, data: dict):
    jobs[job_id]["status"] = JobStatus.PROCESSING
    try:
        # Simulate work
        import asyncio
        await asyncio.sleep(5)
        jobs[job_id]["status"] = JobStatus.COMPLETED
        jobs[job_id]["result"] = {"processed": True}
    except Exception as e:
        jobs[job_id]["status"] = JobStatus.FAILED
        jobs[job_id]["error"] = str(e)

@app.post("/api/jobs")
async def create_job(request: JobRequest, background_tasks: BackgroundTasks):
    """Accept work and return immediately. Client polls for completion."""
    job_id = str(uuid4())
    jobs[job_id] = {"job_id": job_id, "status": JobStatus.PENDING, "created_at": datetime.utcnow()}
    background_tasks.add_task(process_job, job_id, request.data)
    return {"job_id": job_id, "status": JobStatus.PENDING, "status_url": f"/api/jobs/{job_id}"}

@app.get("/api/jobs/{job_id}")
async def get_job_status(job_id: str):
    return jobs.get(job_id, {"error": "Job not found"})
```

---

## Compute and Scaling Patterns (Chapter 9)

### Example A.33: Stateless Service with External Session Store (Python)

```python
# Stateless service design in Python
# Session stored in Redis, not server memory
import redis
import json
from fastapi import FastAPI, Request, Response
from typing import Optional
import uuid

app = FastAPI()

# External session store - all instances share this
session_store = redis.Redis(host='redis-cluster', port=6379, db=0)
SESSION_TTL = 3600  # 1 hour expiration

async def get_session(session_id: str) -> Optional[dict]:
    """Retrieve session from external store."""
    data = session_store.get(f"session:{session_id}")
    if data:
        return json.loads(data)
    return None

async def save_session(session_id: str, data: dict) -> None:
    """Save session to external store with TTL."""
    session_store.setex(
        f"session:{session_id}",
        SESSION_TTL,
        json.dumps(data)
    )

@app.post("/login")
async def login(request: Request, response: Response):
    # Create session and store externally
    session_id = str(uuid.uuid4())
    user_data = await request.json()

    await save_session(session_id, {
        "user_id": user_data["user_id"],
        "authenticated": True
    })

    # Return session ID to client (typically in a cookie)
    response.set_cookie("session_id", session_id, httponly=True)
    return {"status": "authenticated"}

@app.get("/profile")
async def get_profile(request: Request):
    # Any instance can handle this - state is external
    session_id = request.cookies.get("session_id")
    session = await get_session(session_id)

    if not session or not session.get("authenticated"):
        return {"error": "Not authenticated"}, 401

    return {"user_id": session["user_id"]}
```

### Example A.34: Multi-Metric Kubernetes HPA Configuration (YAML)

```yaml
# Kubernetes HPA with multiple metrics
apiVersion: autoscaling/v2
kind: HorizontalPodAutoscaler
metadata:
  name: api-service
spec:
  scaleTargetRef:
    apiVersion: apps/v1
    kind: Deployment
    name: api-service
  minReplicas: 3
  maxReplicas: 50
  metrics:
    # Scale based on CPU utilization
    - type: Resource
      resource:
        name: cpu
        target:
          type: Utilization
          averageUtilization: 70
    # Also scale based on requests per second
    - type: Pods
      pods:
        metric:
          name: http_requests_per_second
        target:
          type: AverageValue
          averageValue: 1000
  behavior:
    scaleDown:
      stabilizationWindowSeconds: 300  # Wait 5 minutes before scaling down
      policies:
        - type: Percent
          value: 10            # Scale down max 10% at a time
          periodSeconds: 60
    scaleUp:
      stabilizationWindowSeconds: 0    # Scale up immediately
      policies:
        - type: Percent
          value: 100           # Can double capacity
          periodSeconds: 15
        - type: Pods
          value: 4             # Or add 4 pods
          periodSeconds: 15
      selectPolicy: Max        # Use whichever allows more scaling
```

### Example A.35: Cold Start Mitigation in AWS Lambda (TypeScript)

```typescript
// Cold start mitigation in TypeScript Lambda
// Initialize outside handler, reuse across invocations
import { DynamoDBClient, GetItemCommand } from '@aws-sdk/client-dynamodb';
import { createClient, RedisClientType } from 'redis';
import { APIGatewayProxyHandler, APIGatewayProxyResult } from 'aws-lambda';

// Initialize expensive clients OUTSIDE the handler
// This code runs during cold start, then is reused
const dynamoClient = new DynamoDBClient({});

// For Redis, we handle connection state carefully
let redisClient: RedisClientType | null = null;

async function getRedisClient(): Promise<RedisClientType> {
  if (!redisClient) {
    redisClient = createClient({
      url: process.env.REDIS_URL,
      socket: {
        connectTimeout: 5000,
        keepAlive: 5000,
      },
    });
    await redisClient.connect();
  }
  return redisClient;
}

// Handler runs on every invocation - keep it fast
export const handler: APIGatewayProxyHandler = async (event): Promise<APIGatewayProxyResult> => {
  const userId = event.queryStringParameters?.user_id ?? 'unknown';

  try {
    // Check cache first (connection reused from cold start)
    const cache = await getRedisClient();
    const cached = await cache.get(`user:${userId}`);

    if (cached) {
      return {
        statusCode: 200,
        body: cached,
      };
    }

    // Fall back to DynamoDB (client already initialized)
    const command = new GetItemCommand({
      TableName: 'users',
      Key: { user_id: { S: userId } },
    });

    const result = await dynamoClient.send(command);
    const userData = JSON.stringify(result.Item ?? {});

    // Cache for future requests
    await cache.setEx(`user:${userId}`, 300, userData);

    return {
      statusCode: 200,
      body: userData,
    };
  } catch (error) {
    return {
      statusCode: 500,
      body: JSON.stringify({ error: 'Internal server error' }),
    };
  }
};
```

### Example A.36: Graceful Shutdown and Health Checks (Rust)

```rust
// Graceful shutdown and health checks in Rust
use actix_web::{web, App, HttpServer, HttpResponse};
use std::sync::atomic::{AtomicBool, AtomicUsize, Ordering};
use std::sync::Arc;
use tokio::signal;

// Track application state
struct AppState {
    is_ready: AtomicBool,
    is_shutting_down: AtomicBool,
    active_requests: AtomicUsize,
}

// Liveness probe: Is this process alive?
async fn liveness() -> HttpResponse {
    HttpResponse::Ok().json(serde_json::json!({"status": "alive"}))
}

// Readiness probe: Can this instance serve traffic?
async fn readiness(state: web::Data<Arc<AppState>>) -> HttpResponse {
    if !state.is_ready.load(Ordering::SeqCst)
        || state.is_shutting_down.load(Ordering::SeqCst) {
        return HttpResponse::ServiceUnavailable()
            .json(serde_json::json!({
                "status": "not ready",
                "accepting_traffic": false
            }));
    }
    HttpResponse::Ok().json(serde_json::json!({
        "status": "ready",
        "accepting_traffic": true
    }))
}

async fn graceful_shutdown(state: Arc<AppState>) {
    signal::ctrl_c().await.expect("Failed to listen for ctrl+c");
    println!("Received shutdown signal, draining connections...");

    // Mark as shutting down - load balancer will stop sending traffic
    state.is_shutting_down.store(true, Ordering::SeqCst);
    state.is_ready.store(false, Ordering::SeqCst);

    // Wait for active requests (with timeout)
    let timeout = std::time::Duration::from_secs(25);
    let start = std::time::Instant::now();
    while state.active_requests.load(Ordering::SeqCst) > 0
        && start.elapsed() < timeout {
        tokio::time::sleep(std::time::Duration::from_millis(100)).await;
    }
    println!("Shutdown complete");
}

#[actix_web::main]
async fn main() -> std::io::Result<()> {
    let state = Arc::new(AppState {
        is_ready: AtomicBool::new(true),
        is_shutting_down: AtomicBool::new(false),
        active_requests: AtomicUsize::new(0),
    });

    let shutdown_state = state.clone();
    tokio::spawn(async move {
        graceful_shutdown(shutdown_state).await;
        std::process::exit(0);
    });

    let state_clone = state.clone();
    HttpServer::new(move || {
        App::new()
            .app_data(web::Data::new(state_clone.clone()))
            .route("/health/live", web::get().to(liveness))
            .route("/health/ready", web::get().to(readiness))
    })
    .bind("0.0.0.0:8080")?
    .run()
    .await
}
```

---

## Traffic Management and Resilience (Chapter 10)

### Example A.37: Token Bucket Rate Limiter (Python)

```python
import time
import threading
from dataclasses import dataclass
from typing import Tuple

@dataclass
class TokenBucket:
    """Token bucket rate limiter with thread-safe operations."""

    capacity: float          # Maximum tokens in bucket
    refill_rate: float       # Tokens added per second
    tokens: float = None     # Current token count
    last_refill: float = None
    _lock: threading.Lock = None

    def __post_init__(self):
        self.tokens = self.capacity
        self.last_refill = time.monotonic()
        self._lock = threading.Lock()

    def _refill(self) -> None:
        """Add tokens based on elapsed time since last refill."""
        now = time.monotonic()
        elapsed = now - self.last_refill
        tokens_to_add = elapsed * self.refill_rate
        self.tokens = min(self.capacity, self.tokens + tokens_to_add)
        self.last_refill = now

    def acquire(self, tokens: float = 1.0) -> Tuple[bool, float]:
        """
        Attempt to acquire tokens from the bucket.

        Returns:
            Tuple of (success: bool, wait_time: float)
            wait_time is 0 if successful, otherwise seconds until tokens available
        """
        with self._lock:
            self._refill()

            if self.tokens >= tokens:
                self.tokens -= tokens
                return True, 0.0

            # Calculate wait time for tokens to become available
            tokens_needed = tokens - self.tokens
            wait_time = tokens_needed / self.refill_rate
            return False, wait_time

# Usage example
rate_limiter = TokenBucket(capacity=100, refill_rate=10)  # 10 req/sec, burst of 100

def handle_request(user_id: str):
    allowed, wait_time = rate_limiter.acquire()
    if not allowed:
        raise RateLimitExceeded(f"Rate limit exceeded. Retry after {wait_time:.2f}s")
    # Process request...
```

### Example A.38: Circuit Breaker Implementation (TypeScript)

```typescript
enum CircuitState {
  Closed = "closed",
  Open = "open",
  HalfOpen = "half_open",
}

interface CircuitBreakerConfig {
  failureThreshold: number;    // Failures before opening
  recoveryTimeout: number;     // Milliseconds before testing recovery
  halfOpenMaxCalls: number;    // Test calls in half-open state
}

class CircuitOpenError extends Error {
  constructor(message: string = "Circuit is open, failing fast") {
    super(message);
    this.name = "CircuitOpenError";
  }
}

class CircuitBreaker {
  private state: CircuitState = CircuitState.Closed;
  private failureCount: number = 0;
  private lastFailureTime: number | null = null;
  private halfOpenCalls: number = 0;
  private config: CircuitBreakerConfig;

  constructor(config: CircuitBreakerConfig) {
    this.config = config;
  }

  async call<T>(func: () => Promise<T>): Promise<T> {
    this.checkStateTransition();

    if (this.state === CircuitState.Open) {
      throw new CircuitOpenError();
    }

    if (this.state === CircuitState.HalfOpen) {
      if (this.halfOpenCalls >= this.config.halfOpenMaxCalls) {
        throw new CircuitOpenError("Half-open call limit reached");
      }
      this.halfOpenCalls++;
    }

    try {
      const result = await func();
      this.onSuccess();
      return result;
    } catch (error) {
      this.onFailure();
      throw error;
    }
  }

  private checkStateTransition(): void {
    if (this.state === CircuitState.Open && this.lastFailureTime !== null) {
      const elapsed = Date.now() - this.lastFailureTime;
      if (elapsed >= this.config.recoveryTimeout) {
        this.state = CircuitState.HalfOpen;
        this.halfOpenCalls = 0;
      }
    }
  }

  private onSuccess(): void {
    if (this.state === CircuitState.HalfOpen) {
      this.state = CircuitState.Closed;
      this.failureCount = 0;
    } else if (this.state === CircuitState.Closed) {
      this.failureCount = 0;
    }
  }

  private onFailure(): void {
    this.failureCount++;
    this.lastFailureTime = Date.now();

    if (this.state === CircuitState.HalfOpen) {
      this.state = CircuitState.Open;
    } else if (this.failureCount >= this.config.failureThreshold) {
      this.state = CircuitState.Open;
    }
  }

  getState(): CircuitState {
    return this.state;
  }
}

// Usage example
const circuit = new CircuitBreaker({
  failureThreshold: 5,
  recoveryTimeout: 30000,
  halfOpenMaxCalls: 3,
});

async function fetchPaymentStatus(orderId: string): Promise<PaymentStatus> {
  try {
    return await circuit.call(async () => {
      const response = await fetch(`/api/payments/${orderId}`);
      if (!response.ok) throw new Error("Payment service error");
      return response.json();
    });
  } catch (error) {
    if (error instanceof CircuitOpenError) {
      return getCachedPaymentStatus(orderId);
    }
    throw error;
  }
}
```

### Example A.39: Retry with Exponential Backoff and Jitter (Rust)

```rust
use rand::Rng;
use std::time::Duration;
use tokio::time::sleep;

#[derive(Clone)]
pub struct RetryConfig {
    pub max_retries: u32,
    pub base_delay: Duration,
    pub max_delay: Duration,
    pub exponential_base: f64,
    pub jitter: JitterStrategy,
}

#[derive(Clone, Copy)]
pub enum JitterStrategy {
    None,
    Full,
    Equal,
}

impl Default for RetryConfig {
    fn default() -> Self {
        RetryConfig {
            max_retries: 3,
            base_delay: Duration::from_secs(1),
            max_delay: Duration::from_secs(60),
            exponential_base: 2.0,
            jitter: JitterStrategy::Full,
        }
    }
}

fn calculate_delay(attempt: u32, config: &RetryConfig) -> Duration {
    let mut rng = rand::thread_rng();

    // Exponential backoff
    let delay_secs = config.base_delay.as_secs_f64()
        * config.exponential_base.powi(attempt as i32);
    let delay_secs = delay_secs.min(config.max_delay.as_secs_f64());

    // Apply jitter
    let final_delay = match config.jitter {
        JitterStrategy::None => delay_secs,
        JitterStrategy::Full => rng.gen_range(0.0..delay_secs),
        JitterStrategy::Equal => {
            delay_secs / 2.0 + rng.gen_range(0.0..delay_secs / 2.0)
        }
    };

    Duration::from_secs_f64(final_delay)
}

/// Execute async function with retry and exponential backoff.
pub async fn retry_with_backoff<T, E, F, Fut>(
    mut func: F,
    config: &RetryConfig,
) -> Result<T, E>
where
    F: FnMut() -> Fut,
    Fut: std::future::Future<Output = Result<T, E>>,
    E: std::fmt::Debug,
{
    let mut last_error: Option<E> = None;

    for attempt in 0..=config.max_retries {
        match func().await {
            Ok(result) => return Ok(result),
            Err(e) => {
                if attempt >= config.max_retries {
                    last_error = Some(e);
                    break;
                }

                let delay = calculate_delay(attempt, config);
                eprintln!(
                    "Attempt {} failed: {:?}. Retrying in {:?}",
                    attempt + 1, e, delay
                );
                sleep(delay).await;
                last_error = Some(e);
            }
        }
    }

    Err(last_error.unwrap())
}

// Usage example
async fn fetch_user_data(user_id: &str) -> Result<User, reqwest::Error> {
    let config = RetryConfig {
        max_retries: 3,
        base_delay: Duration::from_millis(500),
        max_delay: Duration::from_secs(10),
        jitter: JitterStrategy::Full,
        ..Default::default()
    };

    retry_with_backoff(
        || async {
            reqwest::get(&format!("/users/{}", user_id))
                .await?
                .json::<User>()
                .await
        },
        &config,
    )
    .await
}
```

### Example A.40: Bulkhead with Semaphore (TypeScript)

```typescript
class BulkheadFullError extends Error {
  constructor(
    public name: string,
    public active: number,
    public waiting: number
  ) {
    super(
      `Bulkhead '${name}' full: ${active} active, ${waiting} waiting`
    );
    this.name = "BulkheadFullError";
  }
}

class Bulkhead {
  private name: string;
  private maxConcurrent: number;
  private maxWait: number;
  private active: number = 0;
  private waiting: number = 0;
  private queue: Array<{
    resolve: () => void;
    reject: (error: Error) => void;
  }> = [];

  constructor(name: string, maxConcurrent: number, maxWait: number = 10000) {
    this.name = name;
    this.maxConcurrent = maxConcurrent;
    this.maxWait = maxWait;
  }

  private async acquire(): Promise<void> {
    if (this.active < this.maxConcurrent) {
      this.active++;
      return;
    }

    // Wait for a slot
    this.waiting++;
    return new Promise((resolve, reject) => {
      const timeoutId = setTimeout(() => {
        // Remove from queue
        const index = this.queue.findIndex((item) => item.resolve === resolve);
        if (index !== -1) {
          this.queue.splice(index, 1);
          this.waiting--;
          reject(
            new BulkheadFullError(this.name, this.active, this.waiting)
          );
        }
      }, this.maxWait);

      this.queue.push({
        resolve: () => {
          clearTimeout(timeoutId);
          this.waiting--;
          this.active++;
          resolve();
        },
        reject,
      });
    });
  }

  private release(): void {
    this.active--;
    if (this.queue.length > 0) {
      const next = this.queue.shift();
      next?.resolve();
    }
  }

  async call<T>(func: () => Promise<T>): Promise<T> {
    await this.acquire();
    try {
      return await func();
    } finally {
      this.release();
    }
  }

  stats(): { name: string; maxConcurrent: number; active: number; waiting: number } {
    return {
      name: this.name,
      maxConcurrent: this.maxConcurrent,
      active: this.active,
      waiting: this.waiting,
    };
  }
}

// Usage: Create separate bulkheads for each dependency
const paymentBulkhead = new Bulkhead("payment-service", 10, 5000);
const inventoryBulkhead = new Bulkhead("inventory-service", 20, 5000);
const notificationBulkhead = new Bulkhead("notification-service", 5, 2000);

async function processOrder(order: Order): Promise<void> {
  // Each service call is isolated in its own bulkhead
  const payment = await paymentBulkhead.call(() =>
    paymentClient.charge(order.paymentInfo)
  );

  const inventory = await inventoryBulkhead.call(() =>
    inventoryClient.reserve(order.items)
  );

  // Non-critical: don't fail the order if notification bulkhead is full
  try {
    await notificationBulkhead.call(() =>
      notificationClient.sendConfirmation(order)
    );
  } catch (error) {
    if (error instanceof BulkheadFullError) {
      console.warn("Notification bulkhead full, confirmation delayed");
    } else {
      throw error;
    }
  }
}
```

---

## Authentication Performance (Chapter 11)

### Example 11.1: JWT Validation with Caching (Python)

This example demonstrates caching JWT validation results to avoid redundant cryptographic operations. The cache key is derived from a hash of the token, and TTL is calculated based on token expiration.

```python
import hashlib
import time
from typing import Optional
from dataclasses import dataclass
import jwt
import redis

@dataclass
class ValidatedUser:
    user_id: str
    roles: list[str]
    expires_at: int

    def to_cache(self) -> dict:
        return {
            "user_id": self.user_id,
            "roles": self.roles,
            "expires_at": self.expires_at
        }

    @classmethod
    def from_cache(cls, data: dict) -> "ValidatedUser":
        return cls(
            user_id=data["user_id"],
            roles=data["roles"],
            expires_at=data["expires_at"]
        )

class CachingJWTValidator:
    def __init__(
        self,
        secret_key: str,
        cache: redis.Redis,
        max_cache_ttl: int = 300,  # 5 minutes max
        clock_skew_buffer: int = 60  # 1 minute buffer
    ):
        self.secret_key = secret_key
        self.cache = cache
        self.max_cache_ttl = max_cache_ttl
        self.clock_skew_buffer = clock_skew_buffer

    def _hash_token(self, token: str) -> str:
        """Create cache key from token hash (never cache raw tokens)."""
        return hashlib.sha256(token.encode()).hexdigest()[:32]

    def _calculate_cache_ttl(self, token_exp: int) -> int:
        """Calculate cache TTL based on token expiration."""
        remaining = token_exp - int(time.time()) - self.clock_skew_buffer
        return max(0, min(self.max_cache_ttl, remaining))

    async def validate(self, token: str) -> ValidatedUser:
        cache_key = f"auth:valid:{self._hash_token(token)}"

        # Check cache first
        cached = await self.cache.get(cache_key)
        if cached:
            return ValidatedUser.from_cache(cached)

        # Cache miss - perform full validation
        try:
            payload = jwt.decode(
                token,
                self.secret_key,
                algorithms=["HS256"],
                options={"require": ["exp", "sub"]}
            )
        except jwt.ExpiredSignatureError:
            raise AuthenticationError("Token expired")
        except jwt.InvalidTokenError as e:
            raise AuthenticationError(f"Invalid token: {e}")

        user = ValidatedUser(
            user_id=payload["sub"],
            roles=payload.get("roles", []),
            expires_at=payload["exp"]
        )

        # Cache with calculated TTL
        cache_ttl = self._calculate_cache_ttl(payload["exp"])
        if cache_ttl > 0:
            await self.cache.setex(cache_key, cache_ttl, user.to_cache())

        return user
```

### Example 11.2: Session Middleware with Connection Pooling (TypeScript)

This Express middleware demonstrates session-based authentication with Redis connection pooling. The pool maintains warm connections to minimize per-request latency.

```typescript
import { Request, Response, NextFunction } from "express";
import Redis from "ioredis";

interface SessionData {
  userId: string;
  roles: string[];
  createdAt: number;
  lastAccessed: number;
}

interface SessionConfig {
  redisUrl: string;
  sessionTtl: number; // seconds
  poolSize: number;
}

class SessionStore {
  private redis: Redis;

  constructor(config: SessionConfig) {
    // Connection pool configuration
    this.redis = new Redis(config.redisUrl, {
      maxRetriesPerRequest: 3,
      enableReadyCheck: true,
      // Connection pool settings
      connectionName: "session-store",
      lazyConnect: false,
      keepAlive: 30000,
      // Pool size managed by ioredis cluster/sentinel
    });

    this.redis.on("error", (err) => {
      console.error("Session store connection error:", err);
    });
  }

  async get(sessionId: string): Promise<SessionData | null> {
    const key = `session:${sessionId}`;
    const data = await this.redis.get(key);

    if (!data) return null;

    const session = JSON.parse(data) as SessionData;

    // Update last accessed time (fire and forget)
    session.lastAccessed = Date.now();
    this.redis.setex(key, 3600, JSON.stringify(session)).catch(() => {
      // Ignore update failures - session still valid
    });

    return session;
  }

  async create(userId: string, roles: string[]): Promise<string> {
    const sessionId = crypto.randomUUID();
    const session: SessionData = {
      userId,
      roles,
      createdAt: Date.now(),
      lastAccessed: Date.now(),
    };

    await this.redis.setex(
      `session:${sessionId}`,
      3600,
      JSON.stringify(session)
    );

    return sessionId;
  }

  async destroy(sessionId: string): Promise<void> {
    await this.redis.del(`session:${sessionId}`);
  }
}

// Middleware factory
function sessionMiddleware(store: SessionStore) {
  return async (req: Request, res: Response, next: NextFunction) => {
    const sessionId = req.cookies?.sessionId;

    if (!sessionId) {
      return res.status(401).json({ error: "No session" });
    }

    const startTime = process.hrtime.bigint();

    try {
      const session = await store.get(sessionId);

      const durationMs =
        Number(process.hrtime.bigint() - startTime) / 1_000_000;
      res.setHeader("X-Session-Lookup-Ms", durationMs.toFixed(2));

      if (!session) {
        return res.status(401).json({ error: "Invalid session" });
      }

      req.user = { id: session.userId, roles: session.roles };
      next();
    } catch (error) {
      console.error("Session lookup failed:", error);
      res.status(500).json({ error: "Authentication error" });
    }
  };
}
```

### Example 11.3: Proactive Token Refresh Strategy (Rust)

This Rust example demonstrates proactive token refresh, refreshing tokens before they expire to avoid user-visible latency during refresh.

```rust
use std::sync::Arc;
use std::time::{Duration, Instant};
use tokio::sync::RwLock;
use reqwest::Client;
use serde::{Deserialize, Serialize};

#[derive(Clone, Serialize, Deserialize)]
struct TokenResponse {
    access_token: String,
    refresh_token: String,
    expires_in: u64,
}

struct TokenInfo {
    access_token: String,
    refresh_token: String,
    expires_at: Instant,
}

pub struct ProactiveTokenManager {
    client: Client,
    token_url: String,
    current_token: Arc<RwLock<Option<TokenInfo>>>,
    refresh_threshold: Duration, // Refresh when this much time remains
}

impl ProactiveTokenManager {
    pub fn new(token_url: String, refresh_threshold_secs: u64) -> Self {
        Self {
            client: Client::new(),
            token_url,
            current_token: Arc::new(RwLock::new(None)),
            refresh_threshold: Duration::from_secs(refresh_threshold_secs),
        }
    }

    /// Get a valid access token, refreshing proactively if needed
    pub async fn get_token(&self) -> Result<String, TokenError> {
        // Check if we have a valid token with sufficient remaining time
        {
            let token_guard = self.current_token.read().await;
            if let Some(ref token_info) = *token_guard {
                let remaining = token_info.expires_at.saturating_duration_since(Instant::now());
                if remaining > self.refresh_threshold {
                    return Ok(token_info.access_token.clone());
                }
            }
        }

        // Need to refresh - acquire write lock
        let mut token_guard = self.current_token.write().await;

        // Double-check (another task may have refreshed)
        if let Some(ref token_info) = *token_guard {
            let remaining = token_info.expires_at.saturating_duration_since(Instant::now());
            if remaining > self.refresh_threshold {
                return Ok(token_info.access_token.clone());
            }
        }

        // Perform refresh
        let refresh_token = token_guard
            .as_ref()
            .map(|t| t.refresh_token.clone())
            .ok_or(TokenError::NoRefreshToken)?;

        let response: TokenResponse = self
            .client
            .post(&self.token_url)
            .form(&[
                ("grant_type", "refresh_token"),
                ("refresh_token", &refresh_token),
            ])
            .send()
            .await?
            .json()
            .await?;

        let new_token_info = TokenInfo {
            access_token: response.access_token.clone(),
            refresh_token: response.refresh_token,
            expires_at: Instant::now() + Duration::from_secs(response.expires_in),
        };

        *token_guard = Some(new_token_info);
        Ok(response.access_token)
    }

    /// Start background refresh task
    pub fn start_background_refresh(self: Arc<Self>) {
        tokio::spawn(async move {
            loop {
                // Sleep until we're within refresh threshold
                let sleep_duration = {
                    let token_guard = self.current_token.read().await;
                    match &*token_guard {
                        Some(token_info) => {
                            let remaining = token_info
                                .expires_at
                                .saturating_duration_since(Instant::now());
                            remaining.saturating_sub(self.refresh_threshold)
                        }
                        None => Duration::from_secs(60), // No token, check again later
                    }
                };

                tokio::time::sleep(sleep_duration).await;

                // Trigger refresh
                if let Err(e) = self.get_token().await {
                    eprintln!("Background token refresh failed: {:?}", e);
                }
            }
        });
    }
}

#[derive(Debug)]
enum TokenError {
    NoRefreshToken,
    NetworkError(reqwest::Error),
}

impl From<reqwest::Error> for TokenError {
    fn from(err: reqwest::Error) -> Self {
        TokenError::NetworkError(err)
    }
}
```

### Example 11.4: Auth Metrics Middleware (Python)

This FastAPI middleware captures authentication metrics for monitoring dashboards. It tracks validation latency, cache hit rates, and error types.

```python
import time
from typing import Callable
from fastapi import Request, Response
from prometheus_client import Counter, Histogram, Gauge

# Prometheus metrics
AUTH_VALIDATION_DURATION = Histogram(
    "auth_validation_duration_seconds",
    "Time spent validating authentication",
    buckets=[0.001, 0.005, 0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1.0]
)

AUTH_CACHE_HITS = Counter(
    "auth_cache_hits_total",
    "Number of authentication cache hits"
)

AUTH_CACHE_MISSES = Counter(
    "auth_cache_misses_total",
    "Number of authentication cache misses"
)

AUTH_ERRORS = Counter(
    "auth_errors_total",
    "Number of authentication errors",
    ["error_type"]  # expired, invalid_signature, missing_token, etc.
)

AUTH_REQUESTS = Counter(
    "auth_requests_total",
    "Total authentication requests",
    ["method", "path", "status"]
)

class AuthMetricsMiddleware:
    """Middleware that captures authentication performance metrics."""

    def __init__(self, validator: "CachingJWTValidator"):
        self.validator = validator

    async def __call__(
        self,
        request: Request,
        call_next: Callable
    ) -> Response:
        # Skip auth for health checks
        if request.url.path in ["/health", "/metrics"]:
            return await call_next(request)

        auth_header = request.headers.get("Authorization")
        if not auth_header or not auth_header.startswith("Bearer "):
            AUTH_ERRORS.labels(error_type="missing_token").inc()
            AUTH_REQUESTS.labels(
                method=request.method,
                path=request.url.path,
                status="401"
            ).inc()
            return Response(
                content='{"error": "Missing authorization"}',
                status_code=401,
                media_type="application/json"
            )

        token = auth_header[7:]  # Remove "Bearer "

        start_time = time.perf_counter()
        try:
            # Track cache hit/miss
            cache_key = f"auth:valid:{self.validator._hash_token(token)}"
            was_cached = await self.validator.cache.exists(cache_key)

            if was_cached:
                AUTH_CACHE_HITS.inc()
            else:
                AUTH_CACHE_MISSES.inc()

            user = await self.validator.validate(token)

            duration = time.perf_counter() - start_time
            AUTH_VALIDATION_DURATION.observe(duration)

            # Attach user to request state
            request.state.user = user

            response = await call_next(request)

            AUTH_REQUESTS.labels(
                method=request.method,
                path=request.url.path,
                status=str(response.status_code)
            ).inc()

            # Add timing header for debugging
            response.headers["X-Auth-Duration-Ms"] = f"{duration * 1000:.2f}"

            return response

        except ExpiredTokenError:
            duration = time.perf_counter() - start_time
            AUTH_VALIDATION_DURATION.observe(duration)
            AUTH_ERRORS.labels(error_type="expired").inc()
            AUTH_REQUESTS.labels(
                method=request.method,
                path=request.url.path,
                status="401"
            ).inc()
            return Response(
                content='{"error": "Token expired"}',
                status_code=401,
                media_type="application/json"
            )

        except InvalidSignatureError:
            duration = time.perf_counter() - start_time
            AUTH_VALIDATION_DURATION.observe(duration)
            AUTH_ERRORS.labels(error_type="invalid_signature").inc()
            AUTH_REQUESTS.labels(
                method=request.method,
                path=request.url.path,
                status="401"
            ).inc()
            return Response(
                content='{"error": "Invalid token"}',
                status_code=401,
                media_type="application/json"
            )

        except Exception as e:
            duration = time.perf_counter() - start_time
            AUTH_VALIDATION_DURATION.observe(duration)
            AUTH_ERRORS.labels(error_type="unknown").inc()
            AUTH_REQUESTS.labels(
                method=request.method,
                path=request.url.path,
                status="500"
            ).inc()
            return Response(
                content='{"error": "Authentication error"}',
                status_code=500,
                media_type="application/json"
            )
```

---

## Advanced Optimization Techniques (Chapter 12)

### Example A.41: A/B Test Routing Edge Function (TypeScript)

```typescript
// Edge function example: A/B test routing (Cloudflare Workers)
import { createHash } from 'crypto';

type Variant = 'control' | 'treatment';

function getExperimentVariant(userId: string, experimentId: string): Variant {
  // Create stable hash from user and experiment
  const hashInput = `${userId}:${experimentId}`;
  const hash = createHash('sha256').update(hashInput).digest('hex');

  // Convert first 8 hex chars to number, mod 100 for percentage
  const percentage = parseInt(hash.substring(0, 8), 16) % 100;

  // 50/50 split between control and treatment
  return percentage < 50 ? 'treatment' : 'control';
}

export default {
  async fetch(request: Request): Promise<Response> {
    const cookies = parseCookies(request.headers.get('Cookie') || '');
    const userId = cookies.user_id || request.headers.get('x-device-id') || 'anonymous';

    const variant = getExperimentVariant(userId, 'new-checkout-flow');

    // Route to appropriate backend based on variant
    const url = new URL(request.url);
    const origin = variant === 'treatment'
      ? 'https://new-checkout.example.com'
      : 'https://api.example.com';

    return fetch(`${origin}${url.pathname}${url.search}`, {
      method: request.method,
      headers: request.headers,
      body: request.body,
    });
  }
};

function parseCookies(cookieHeader: string): Record<string, string> {
  return Object.fromEntries(
    cookieHeader.split(';').map(c => c.trim().split('='))
  );
}
```

### Example A.42: GraphQL N+1 Query Pattern (GraphQL)

```graphql
query {
  users {
    id
    name
    posts {
      title
    }
  }
}
```

### Example A.43: DataLoader Pattern Implementation (Python)

```python
# DataLoader implementation in Python (using aiodataloader)
from aiodataloader import DataLoader
from typing import List, Optional
import asyncpg

class UserLoader(DataLoader):
    """Batch loads users by ID, resolving N+1 queries to a single batch query."""

    def __init__(self, db_pool: asyncpg.Pool):
        super().__init__()
        self.db_pool = db_pool

    async def batch_load_fn(self, user_ids: List[int]) -> List[Optional[dict]]:
        """Load multiple users in a single database query."""
        async with self.db_pool.acquire() as conn:
            # Single query for all requested users
            rows = await conn.fetch(
                "SELECT id, name, email FROM users WHERE id = ANY($1)",
                user_ids
            )

        # Create lookup map for O(1) access
        user_map = {row['id']: dict(row) for row in rows}

        # Return results in same order as requested IDs
        # Return None for IDs not found
        return [user_map.get(user_id) for user_id in user_ids]

class PostLoader(DataLoader):
    """Batch loads posts by user ID."""

    def __init__(self, db_pool: asyncpg.Pool):
        super().__init__()
        self.db_pool = db_pool

    async def batch_load_fn(self, user_ids: List[int]) -> List[List[dict]]:
        """Load posts for multiple users in a single query."""
        async with self.db_pool.acquire() as conn:
            rows = await conn.fetch(
                "SELECT id, user_id, title, content FROM posts WHERE user_id = ANY($1)",
                user_ids
            )

        # Group posts by user_id
        posts_by_user: dict[int, List[dict]] = {uid: [] for uid in user_ids}
        for row in rows:
            posts_by_user[row['user_id']].append(dict(row))

        return [posts_by_user[user_id] for user_id in user_ids]

# Usage in GraphQL resolver
async def resolve_user_posts(user, info):
    """Resolver that uses DataLoader for efficient batching."""
    # DataLoader instance should be created per-request and stored in context
    post_loader = info.context['post_loader']
    return await post_loader.load(user['id'])
```

### Example A.44: gRPC Service with Streaming (Rust)

```rust
// gRPC service implementation in Rust using tonic
use tonic::{Request, Response, Status};

// Generated from .proto file by tonic-build
pub mod user_service {
    tonic::include_proto!("userservice");
}

use user_service::user_service_server::{UserService, UserServiceServer};
use user_service::{CreateUserRequest, GetUserRequest, ListUsersRequest, User};

pub struct UserServiceImpl {
    pool: sqlx::PgPool,
}

#[tonic::async_trait]
impl UserService for UserServiceImpl {
    /// Unary RPC: single request, single response
    async fn get_user(&self, request: Request<GetUserRequest>) -> Result<Response<User>, Status> {
        let user_id = request.into_inner().id;

        let user = sqlx::query_as!(
            UserRow,
            "SELECT id, name, email, created_at FROM users WHERE id = $1",
            user_id
        )
        .fetch_optional(&self.pool)
        .await
        .map_err(|e| Status::internal(format!("Database error: {}", e)))?;

        match user {
            Some(row) => Ok(Response::new(User {
                id: row.id,
                name: row.name,
                email: row.email,
                created_at: row.created_at.timestamp(),
            })),
            None => Err(Status::not_found(format!("User {} not found", user_id))),
        }
    }

    /// Server streaming RPC: efficient for large result sets
    type ListUsersStream = tokio_stream::wrappers::ReceiverStream<Result<User, Status>>;

    async fn list_users(
        &self,
        request: Request<ListUsersRequest>,
    ) -> Result<Response<Self::ListUsersStream>, Status> {
        let page_size = request.into_inner().page_size.max(1).min(1000);
        let pool = self.pool.clone();

        let (tx, rx) = tokio::sync::mpsc::channel(32);

        // Spawn task to stream results
        tokio::spawn(async move {
            let mut rows = sqlx::query_as!(
                UserRow,
                "SELECT id, name, email, created_at FROM users ORDER BY id LIMIT $1",
                page_size as i64
            )
            .fetch(&pool);

            while let Some(row) = rows.next().await {
                match row {
                    Ok(user) => {
                        let _ = tx.send(Ok(User {
                            id: user.id,
                            name: user.name,
                            email: user.email,
                            created_at: user.created_at.timestamp(),
                        })).await;
                    }
                    Err(e) => {
                        let _ = tx.send(Err(Status::internal(e.to_string()))).await;
                        break;
                    }
                }
            }
        });

        Ok(Response::new(tokio_stream::wrappers::ReceiverStream::new(rx)))
    }
}
```

### Example A.45: Hedged Requests for Tail Latency Reduction (Python)

```python
# Hedged request implementation in Python
import asyncio
from typing import TypeVar, Callable, Awaitable
import time

T = TypeVar('T')

async def hedged_request(
    request_fn: Callable[[], Awaitable[T]],
    hedge_delay_ms: float = 50.0,
    max_attempts: int = 2,
) -> T:
    """
    Execute a request with hedging for tail latency reduction.

    Sends the initial request immediately. If no response arrives within
    hedge_delay_ms, sends a parallel hedge request. Returns the first
    successful response and cancels remaining requests.
    """
    tasks: list[asyncio.Task] = []
    result_queue: asyncio.Queue[tuple[int, T | Exception]] = asyncio.Queue()

    async def attempt(attempt_id: int, delay_ms: float = 0):
        """Execute a single attempt, optionally after a delay."""
        if delay_ms > 0:
            await asyncio.sleep(delay_ms / 1000)
        try:
            result = await request_fn()
            await result_queue.put((attempt_id, result))
        except Exception as e:
            await result_queue.put((attempt_id, e))

    # Start initial request immediately
    tasks.append(asyncio.create_task(attempt(0)))

    # Schedule hedge requests with staggered delays
    for i in range(1, max_attempts):
        tasks.append(asyncio.create_task(attempt(i, hedge_delay_ms * i)))

    # Wait for first successful response
    errors: list[Exception] = []
    try:
        while len(errors) < max_attempts:
            attempt_id, result = await result_queue.get()

            if isinstance(result, Exception):
                errors.append(result)
                continue

            # Success - cancel remaining tasks
            for task in tasks:
                if not task.done():
                    task.cancel()

            return result

        # All attempts failed
        raise ExceptionGroup("All hedged requests failed", errors)

    finally:
        # Ensure all tasks are cancelled on exit
        for task in tasks:
            if not task.done():
                task.cancel()


# Usage example
async def fetch_user_with_hedging(user_id: int) -> dict:
    """Fetch user with hedged requests for reduced tail latency."""
    async def fetch():
        async with aiohttp.ClientSession() as session:
            async with session.get(f"http://api.example.com/users/{user_id}") as resp:
                return await resp.json()

    # Hedge after 50ms (our p95 latency), max 2 attempts
    return await hedged_request(fetch, hedge_delay_ms=50, max_attempts=2)
```

---

## Putting It All Together (Chapter 13)

### Example A.46: Performance Budget Checker (TypeScript)

This CI integration fails the build if key performance metrics regress. Integrate it into your deployment pipeline to catch regressions before they reach production.

```typescript
// Performance budget checker in TypeScript
import * as fs from 'fs';

interface PerformanceBudget {
  p50_ms: number;
  p95_ms: number;
  p99_ms: number;
  error_rate_percent: number;
}

interface MeasuredPerformance {
  p50_ms: number;
  p95_ms: number;
  p99_ms: number;
  error_rate_percent: number;
}

interface BudgetCheckResult {
  metric: string;
  passed: boolean;
  measured: number;
  budget: number;
}

function checkBudget(
  budget: PerformanceBudget,
  measured: MeasuredPerformance
): BudgetCheckResult[] {
  return [
    {
      metric: 'p50',
      passed: measured.p50_ms <= budget.p50_ms,
      measured: measured.p50_ms,
      budget: budget.p50_ms,
    },
    {
      metric: 'p95',
      passed: measured.p95_ms <= budget.p95_ms,
      measured: measured.p95_ms,
      budget: budget.p95_ms,
    },
    {
      metric: 'p99',
      passed: measured.p99_ms <= budget.p99_ms,
      measured: measured.p99_ms,
      budget: budget.p99_ms,
    },
    {
      metric: 'error_rate',
      passed: measured.error_rate_percent <= budget.error_rate_percent,
      measured: measured.error_rate_percent,
      budget: budget.error_rate_percent,
    },
  ];
}

function runBudgetCheck(budgetsFile: string, resultsFile: string): number {
  const budgets: Record<string, PerformanceBudget> = JSON.parse(
    fs.readFileSync(budgetsFile, 'utf-8')
  );
  const results: Record<string, MeasuredPerformance> = JSON.parse(
    fs.readFileSync(resultsFile, 'utf-8')
  );

  let allPassed = true;

  for (const [endpoint, budget] of Object.entries(budgets)) {
    const measured = results[endpoint];
    if (!measured) {
      console.log(`WARNING: No results for ${endpoint}`);
      continue;
    }

    const checks = checkBudget(budget, measured);
    for (const check of checks) {
      const status = check.passed ? 'PASS' : 'FAIL';
      console.log(
        `[${status}] ${endpoint} ${check.metric}: ${check.measured} (budget: ${check.budget})`
      );
      if (!check.passed) {
        allPassed = false;
      }
    }
  }

  return allPassed ? 0 : 1;
}

// Run the check
process.exit(runBudgetCheck('budgets.json', 'load_test_results.json'));
```

### Example A.47: Optimization Decision Helper (Python)

This utility helps select optimization strategies based on observed symptoms. It encodes the decision framework in code, providing a starting point for investigation.

```python
# Optimization decision helper in Python
from dataclasses import dataclass
from enum import Enum
from typing import List

class Symptom(Enum):
    HIGH_P95_LATENCY = "high_p95_latency"
    HIGH_P99_LATENCY = "high_p99_latency"
    LOW_THROUGHPUT = "low_throughput"
    HIGH_ERROR_RATE = "high_error_rate"
    CPU_SATURATION = "cpu_saturation"
    MEMORY_PRESSURE = "memory_pressure"
    CONNECTION_EXHAUSTION = "connection_exhaustion"
    CASCADE_FAILURES = "cascade_failures"
    GEOGRAPHIC_LATENCY = "geographic_latency"

@dataclass
class Recommendation:
    pattern: str
    chapter: int
    description: str
    priority: int  # 1 = highest priority

# Knowledge base mapping symptoms to recommendations
RECOMMENDATIONS = {
    Symptom.HIGH_P95_LATENCY: [
        Recommendation("Cache-aside caching", 5, "Add caching for frequently accessed data", 1),
        Recommendation("Database indexing", 6, "Review and optimize query indexes", 2),
        Recommendation("Connection pooling", 4, "Ensure connections are reused", 3),
    ],
    Symptom.LOW_THROUGHPUT: [
        Recommendation("Horizontal scaling", 8, "Add more service instances", 1),
        Recommendation("Async processing", 7, "Move work to background queues", 2),
        Recommendation("Connection pool tuning", 4, "Increase pool size for concurrency", 3),
    ],
    Symptom.CASCADE_FAILURES: [
        Recommendation("Circuit breakers", 9, "Fail fast on unhealthy dependencies", 1),
        Recommendation("Timeout tuning", 9, "Set aggressive timeouts with fallbacks", 2),
        Recommendation("Bulkhead isolation", 9, "Isolate failure domains", 3),
    ],
    Symptom.CPU_SATURATION: [
        Recommendation("Horizontal scaling", 8, "Distribute load across instances", 1),
        Recommendation("Algorithmic optimization", 10, "Profile and optimize hot paths", 2),
        Recommendation("Caching computed results", 5, "Cache expensive computations", 3),
    ],
    Symptom.GEOGRAPHIC_LATENCY: [
        Recommendation("CDN caching", 5, "Cache at edge locations", 1),
        Recommendation("Edge computing", 10, "Execute logic at the edge", 2),
        Recommendation("Regional deployment", 8, "Deploy closer to users", 3),
    ],
}

def diagnose(symptoms: List[Symptom]) -> List[Recommendation]:
    """Given symptoms, return prioritized recommendations."""
    all_recommendations = []
    for symptom in symptoms:
        if symptom in RECOMMENDATIONS:
            all_recommendations.extend(RECOMMENDATIONS[symptom])

    # Deduplicate by pattern, keeping highest priority
    seen = {}
    for rec in all_recommendations:
        if rec.pattern not in seen or rec.priority < seen[rec.pattern].priority:
            seen[rec.pattern] = rec

    # Sort by priority
    return sorted(seen.values(), key=lambda r: r.priority)

# Example usage
if __name__ == "__main__":
    symptoms = [Symptom.HIGH_P95_LATENCY, Symptom.CPU_SATURATION]
    recommendations = diagnose(symptoms)

    print("Recommended optimizations:")
    for rec in recommendations:
        print(f"  - {rec.pattern} (Chapter {rec.chapter}): {rec.description}")
```

---

## Index of Examples by Language

### Python
- A.1, A.2, A.3, A.4: Performance Fundamentals
- A.6, A.8: Observability
- A.9, A.10: Monitoring
- A.13: Network/Connections
- A.15: Caching
- A.18, A.19, A.22, A.25: Database
- A.30, A.31, A.32: Async Processing
- A.33, A.37: Scaling/Traffic
- A.43, A.45: Advanced Techniques
- A.47: Synthesis

### Rust
- A.1, A.2, A.3: Performance Fundamentals
- A.7: Observability
- A.11: Network/Connections
- A.16: Caching
- A.20, A.23, A.26, A.28: Database
- A.31: Async Processing
- A.36, A.39: Scaling/Traffic
- A.44: Advanced Techniques

### TypeScript
- A.1, A.2, A.3, A.4: Performance Fundamentals
- A.5: Observability
- A.12: Network/Connections
- A.14, A.17: Caching
- A.21, A.24, A.27: Database
- A.29: Async Processing
- A.35, A.38, A.40: Scaling/Traffic
- A.41: Advanced Techniques
- A.46: Synthesis

### YAML
- A.34: Kubernetes HPA Configuration

### GraphQL
- A.42: N+1 Query Pattern
