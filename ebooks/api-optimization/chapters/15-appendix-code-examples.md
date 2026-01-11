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

### Example A.14: WebSocket Server with Connection Management (Python)

A WebSocket server implementation that tracks connections, handles broadcasts, and manages connection lifecycle with proper cleanup.

```python
# WebSocket server with connection management in Python
import asyncio
from dataclasses import dataclass, field
from typing import Set
import websockets
from websockets.server import WebSocketServerProtocol
import json
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

@dataclass
class ConnectionManager:
    """Manages WebSocket connections with tracking and broadcast support."""
    connections: Set[WebSocketServerProtocol] = field(default_factory=set)
    max_connections: int = 10000

    async def connect(self, websocket: WebSocketServerProtocol) -> bool:
        """Register a new connection. Returns False if limit exceeded."""
        if len(self.connections) >= self.max_connections:
            logger.warning(f"Connection limit reached: {self.max_connections}")
            return False
        self.connections.add(websocket)
        logger.info(f"Client connected. Total: {len(self.connections)}")
        return True

    def disconnect(self, websocket: WebSocketServerProtocol) -> None:
        """Remove a connection from tracking."""
        self.connections.discard(websocket)
        logger.info(f"Client disconnected. Total: {len(self.connections)}")

    async def broadcast(self, message: str, exclude: WebSocketServerProtocol = None) -> None:
        """Send message to all connected clients, optionally excluding one."""
        if not self.connections:
            return

        targets = [ws for ws in self.connections if ws != exclude]
        if targets:
            await asyncio.gather(
                *[self._safe_send(ws, message) for ws in targets],
                return_exceptions=True
            )

    async def _safe_send(self, websocket: WebSocketServerProtocol, message: str) -> None:
        """Send message with error handling for disconnected clients."""
        try:
            await websocket.send(message)
        except websockets.exceptions.ConnectionClosed:
            self.disconnect(websocket)

manager = ConnectionManager()

async def handler(websocket: WebSocketServerProtocol) -> None:
    """Handle individual WebSocket connection."""
    if not await manager.connect(websocket):
        await websocket.close(1013, "Server at capacity")
        return

    try:
        async for message in websocket:
            data = json.loads(message)
            # Echo back and broadcast to others
            await websocket.send(json.dumps({"type": "ack", "id": data.get("id")}))
            await manager.broadcast(message, exclude=websocket)
    except websockets.exceptions.ConnectionClosed:
        pass
    finally:
        manager.disconnect(websocket)

async def main():
    async with websockets.serve(handler, "localhost", 8765, ping_interval=30, ping_timeout=10):
        await asyncio.Future()  # Run forever

# asyncio.run(main())
```

### Example A.15: WebSocket Heartbeat and Reconnection (TypeScript)

Client-side WebSocket wrapper with automatic heartbeat, reconnection with exponential backoff, and connection state tracking.

```typescript
// WebSocket client with heartbeat and reconnection in TypeScript
type ConnectionState = 'connecting' | 'connected' | 'disconnected' | 'reconnecting';
type MessageHandler = (data: unknown) => void;

interface WebSocketConfig {
  url: string;
  heartbeatIntervalMs: number;
  reconnectBaseDelayMs: number;
  maxReconnectDelayMs: number;
  maxReconnectAttempts: number;
}

class ResilientWebSocket {
  private ws: WebSocket | null = null;
  private state: ConnectionState = 'disconnected';
  private heartbeatTimer: ReturnType<typeof setInterval> | null = null;
  private reconnectAttempts = 0;
  private messageHandlers: Set<MessageHandler> = new Set();
  private config: WebSocketConfig;

  constructor(config: Partial<WebSocketConfig> & { url: string }) {
    this.config = {
      heartbeatIntervalMs: 30000,
      reconnectBaseDelayMs: 1000,
      maxReconnectDelayMs: 30000,
      maxReconnectAttempts: 10,
      ...config,
    };
  }

  connect(): void {
    if (this.state === 'connected' || this.state === 'connecting') return;

    this.state = this.reconnectAttempts > 0 ? 'reconnecting' : 'connecting';
    this.ws = new WebSocket(this.config.url);

    this.ws.onopen = () => {
      this.state = 'connected';
      this.reconnectAttempts = 0;
      this.startHeartbeat();
      console.log('WebSocket connected');
    };

    this.ws.onmessage = (event) => {
      const data = JSON.parse(event.data);
      if (data.type === 'pong') return; // Heartbeat response
      this.messageHandlers.forEach(handler => handler(data));
    };

    this.ws.onclose = (event) => {
      this.stopHeartbeat();
      this.state = 'disconnected';

      if (!event.wasClean && this.reconnectAttempts < this.config.maxReconnectAttempts) {
        this.scheduleReconnect();
      }
    };

    this.ws.onerror = (error) => {
      console.error('WebSocket error:', error);
    };
  }

  private startHeartbeat(): void {
    this.heartbeatTimer = setInterval(() => {
      if (this.ws?.readyState === WebSocket.OPEN) {
        this.ws.send(JSON.stringify({ type: 'ping', timestamp: Date.now() }));
      }
    }, this.config.heartbeatIntervalMs);
  }

  private stopHeartbeat(): void {
    if (this.heartbeatTimer) {
      clearInterval(this.heartbeatTimer);
      this.heartbeatTimer = null;
    }
  }

  private scheduleReconnect(): void {
    const delay = Math.min(
      this.config.reconnectBaseDelayMs * Math.pow(2, this.reconnectAttempts),
      this.config.maxReconnectDelayMs
    );
    this.reconnectAttempts++;
    console.log(`Reconnecting in ${delay}ms (attempt ${this.reconnectAttempts})`);
    setTimeout(() => this.connect(), delay);
  }

  send(data: unknown): void {
    if (this.ws?.readyState === WebSocket.OPEN) {
      this.ws.send(JSON.stringify(data));
    }
  }

  onMessage(handler: MessageHandler): () => void {
    this.messageHandlers.add(handler);
    return () => this.messageHandlers.delete(handler);
  }

  disconnect(): void {
    this.reconnectAttempts = this.config.maxReconnectAttempts; // Prevent reconnect
    this.ws?.close(1000, 'Client disconnect');
  }

  getState(): ConnectionState { return this.state; }
}

// Usage:
// const ws = new ResilientWebSocket({ url: 'wss://api.example.com/ws' });
// ws.onMessage((data) => console.log('Received:', data));
// ws.connect();
```

### Example A.16: SSE Server with Event Streaming (Python)

Server-Sent Events implementation with event ID tracking for resumption and heartbeat comments to keep connections alive.

```python
# SSE server with event streaming in Python (FastAPI)
from fastapi import FastAPI, Request
from fastapi.responses import StreamingResponse
from typing import AsyncGenerator
import asyncio
import json
from dataclasses import dataclass
from datetime import datetime

app = FastAPI()

@dataclass
class Event:
    id: int
    event_type: str
    data: dict

class EventStore:
    """Simple in-memory event store with ID tracking for resumption."""
    def __init__(self):
        self.events: list[Event] = []
        self.next_id = 1

    def add(self, event_type: str, data: dict) -> Event:
        event = Event(id=self.next_id, event_type=event_type, data=data)
        self.events.append(event)
        self.next_id += 1
        return event

    def get_since(self, last_id: int) -> list[Event]:
        """Get all events after the given ID for resumption."""
        return [e for e in self.events if e.id > last_id]

store = EventStore()

def format_sse(event: Event) -> str:
    """Format event as SSE message."""
    lines = [
        f"id: {event.id}",
        f"event: {event.event_type}",
        f"data: {json.dumps(event.data)}",
        "",  # Empty line ends the event
    ]
    return "\n".join(lines) + "\n"

async def event_generator(last_event_id: int) -> AsyncGenerator[str, None]:
    """Generate SSE events, starting from last_event_id for resumption."""
    # Send any missed events (for resumption)
    for event in store.get_since(last_event_id):
        yield format_sse(event)

    # Stream new events
    last_seen_id = store.next_id - 1
    while True:
        await asyncio.sleep(1)  # Poll interval

        # Send heartbeat comment to keep connection alive
        yield ": heartbeat\n\n"

        # Check for new events
        new_events = store.get_since(last_seen_id)
        for event in new_events:
            yield format_sse(event)
            last_seen_id = event.id

@app.get("/events")
async def stream_events(request: Request):
    # Support resumption via Last-Event-ID header
    last_event_id = int(request.headers.get("Last-Event-ID", "0"))

    return StreamingResponse(
        event_generator(last_event_id),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",  # Disable nginx buffering
        }
    )

@app.post("/publish")
async def publish_event(event_type: str, data: dict):
    """Publish a new event to all connected clients."""
    event = store.add(event_type, {**data, "timestamp": datetime.utcnow().isoformat()})
    return {"id": event.id}

# Run with: uvicorn sse_server:app --host 0.0.0.0 --port 8000
```

### Example A.17: gRPC Service with Bidirectional Streaming (Rust)

A gRPC service implementation using Tonic that demonstrates bidirectional streaming for a chat-like application.

```rust
// gRPC service with bidirectional streaming in Rust (using Tonic)
use tonic::{transport::Server, Request, Response, Status, Streaming};
use tokio::sync::broadcast;
use tokio_stream::wrappers::BroadcastStream;
use tokio_stream::StreamExt;
use std::pin::Pin;

// Proto definitions (normally generated from .proto file)
pub mod chat {
    tonic::include_proto!("chat");
}
use chat::{chat_server::{Chat, ChatServer}, ChatMessage, JoinRequest, Empty};

type ResponseStream = Pin<Box<dyn tokio_stream::Stream<Item = Result<ChatMessage, Status>> + Send>>;

pub struct ChatService {
    tx: broadcast::Sender<ChatMessage>,
}

impl ChatService {
    pub fn new() -> Self {
        let (tx, _) = broadcast::channel(1000);
        ChatService { tx }
    }
}

#[tonic::async_trait]
impl Chat for ChatService {
    type ChatStreamStream = ResponseStream;

    // Bidirectional streaming: receive messages and broadcast to all
    async fn chat_stream(
        &self,
        request: Request<Streaming<ChatMessage>>,
    ) -> Result<Response<Self::ChatStreamStream>, Status> {
        let tx = self.tx.clone();
        let mut inbound = request.into_inner();

        // Spawn task to handle incoming messages
        let tx_clone = tx.clone();
        tokio::spawn(async move {
            while let Some(result) = inbound.next().await {
                if let Ok(msg) = result {
                    let _ = tx_clone.send(msg);
                }
            }
        });

        // Return stream of all messages (including from other clients)
        let rx = self.tx.subscribe();
        let stream = BroadcastStream::new(rx)
            .filter_map(|result| result.ok())
            .map(Ok);

        Ok(Response::new(Box::pin(stream)))
    }

    // Server streaming: stream all messages to a subscriber
    type SubscribeStream = ResponseStream;

    async fn subscribe(
        &self,
        _request: Request<JoinRequest>,
    ) -> Result<Response<Self::SubscribeStream>, Status> {
        let rx = self.tx.subscribe();
        let stream = BroadcastStream::new(rx)
            .filter_map(|result| result.ok())
            .map(Ok);

        Ok(Response::new(Box::pin(stream)))
    }

    // Unary: send a single message
    async fn send_message(
        &self,
        request: Request<ChatMessage>,
    ) -> Result<Response<Empty>, Status> {
        let msg = request.into_inner();
        self.tx.send(msg).map_err(|_| Status::internal("Broadcast failed"))?;
        Ok(Response::new(Empty {}))
    }
}

#[tokio::main]
async fn main() -> Result<(), Box<dyn std::error::Error>> {
    let addr = "[::1]:50051".parse()?;
    let service = ChatService::new();

    println!("gRPC server listening on {}", addr);
    Server::builder()
        .add_service(ChatServer::new(service))
        .serve(addr)
        .await?;

    Ok(())
}
```

### Example A.18: gRPC Client with Channel Reuse (Python)

A gRPC client that demonstrates proper channel reuse, keepalive configuration, and connection pooling for high-throughput scenarios.

```python
# gRPC client with channel reuse in Python
import grpc
from dataclasses import dataclass
from typing import Optional
import time
from concurrent import futures
import logging

# Generated from .proto file
# from your_service_pb2 import GetUserRequest, User
# from your_service_pb2_grpc import UserServiceStub

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

@dataclass
class GrpcClientConfig:
    target: str
    keepalive_time_ms: int = 30000           # Send keepalive ping every 30s
    keepalive_timeout_ms: int = 10000        # Wait 10s for keepalive response
    keepalive_permit_without_calls: bool = True  # Send keepalive even when idle
    max_connection_idle_ms: int = 300000     # Close idle connections after 5min
    max_connection_age_ms: int = 0           # No max age (0 = infinite)
    enable_retries: bool = True

class GrpcClientPool:
    """
    gRPC client with proper channel reuse and configuration.
    Create once at application startup, reuse for all RPCs.
    """

    def __init__(self, config: GrpcClientConfig):
        self.config = config
        self._channel: Optional[grpc.Channel] = None
        self._stub = None

    def _create_channel(self) -> grpc.Channel:
        """Create a configured gRPC channel with keepalive and retry settings."""
        options = [
            ('grpc.keepalive_time_ms', self.config.keepalive_time_ms),
            ('grpc.keepalive_timeout_ms', self.config.keepalive_timeout_ms),
            ('grpc.keepalive_permit_without_calls',
             1 if self.config.keepalive_permit_without_calls else 0),
            ('grpc.max_connection_idle_ms', self.config.max_connection_idle_ms),
            ('grpc.enable_retries', 1 if self.config.enable_retries else 0),
            # Load balancing for multiple backends
            ('grpc.lb_policy_name', 'round_robin'),
            # Initial connection window size (for high-throughput)
            ('grpc.http2.initial_connection_window_size', 1024 * 1024),
        ]

        # Use secure channel in production
        # return grpc.secure_channel(self.config.target, credentials, options)
        return grpc.insecure_channel(self.config.target, options)

    @property
    def channel(self) -> grpc.Channel:
        """Get or create the shared channel."""
        if self._channel is None:
            self._channel = self._create_channel()
            logger.info(f"Created gRPC channel to {self.config.target}")
        return self._channel

    def get_stub(self, stub_class):
        """Get a stub for the given service class, reusing the channel."""
        return stub_class(self.channel)

    def close(self):
        """Close the channel. Call during application shutdown."""
        if self._channel:
            self._channel.close()
            self._channel = None
            logger.info("Closed gRPC channel")

# Usage example:
#
# # Create once at application startup
# client = GrpcClientPool(GrpcClientConfig(target="localhost:50051"))
#
# # Reuse for all RPCs throughout application lifecycle
# stub = client.get_stub(UserServiceStub)
# response = stub.GetUser(GetUserRequest(id=123))
#
# # For async operations with connection reuse:
# async def get_users_batch(user_ids: list[int]) -> list:
#     stub = client.get_stub(UserServiceStub)
#     with futures.ThreadPoolExecutor(max_workers=10) as executor:
#         tasks = [executor.submit(stub.GetUser, GetUserRequest(id=uid)) for uid in user_ids]
#         return [task.result() for task in futures.as_completed(tasks)]
#
# # Close during shutdown
# client.close()
```

---

## Caching Strategies (Chapter 6)

### Example A.19: Cache-Aside Pattern (TypeScript)

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

### Example A.20: TTL with Jitter (Python)

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

### Example A.21: Single-Flight Pattern (Rust)

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

### Example A.22: Cache Metrics Collection (TypeScript)

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

### Example A.23: Database Buffer Cache Monitoring (Python)

Monitor PostgreSQL buffer cache hit ratios to determine if shared_buffers is sized appropriately. A hit ratio below 90% suggests the buffer pool is too small.

```python
# Database buffer cache monitoring in Python (psycopg2)
import psycopg2
from dataclasses import dataclass

@dataclass
class CacheStats:
    overall_hit_ratio: float
    table_stats: list[dict]

def get_buffer_cache_stats(conn) -> CacheStats:
    """Get PostgreSQL buffer cache statistics."""
    with conn.cursor() as cur:
        # Overall buffer cache hit ratio
        cur.execute("""
            SELECT
                sum(blks_hit) / nullif(sum(blks_hit) + sum(blks_read), 0) AS hit_ratio
            FROM pg_stat_database
            WHERE datname = current_database()
        """)
        overall = cur.fetchone()[0] or 0.0

        # Per-table hit ratios (top 20 by reads)
        cur.execute("""
            SELECT
                schemaname,
                relname,
                heap_blks_hit,
                heap_blks_read,
                heap_blks_hit / nullif(heap_blks_hit + heap_blks_read, 0) AS heap_hit_ratio,
                idx_blks_hit / nullif(idx_blks_hit + idx_blks_read, 0) AS index_hit_ratio
            FROM pg_statio_user_tables
            WHERE heap_blks_read > 0
            ORDER BY heap_blks_read DESC
            LIMIT 20
        """)
        tables = [
            {
                "schema": row[0],
                "table": row[1],
                "heap_hits": row[2],
                "heap_reads": row[3],
                "heap_hit_ratio": row[4] or 0.0,
                "index_hit_ratio": row[5] or 0.0,
            }
            for row in cur.fetchall()
        ]

    return CacheStats(overall_hit_ratio=overall, table_stats=tables)

# Usage
conn = psycopg2.connect("postgresql://localhost/mydb")
stats = get_buffer_cache_stats(conn)
print(f"Overall buffer cache hit ratio: {stats.overall_hit_ratio:.2%}")
for table in stats.table_stats[:5]:
    print(f"  {table['table']}: heap={table['heap_hit_ratio']:.2%}")

# Alert if hit ratio is too low
if stats.overall_hit_ratio < 0.90:
    print("WARNING: Buffer cache hit ratio below 90%. Consider increasing shared_buffers.")
```

### Example A.24: HTTP Conditional Requests with ETags (TypeScript)

Generate and validate ETags for efficient cache revalidation. Returns 304 Not Modified when content hasn't changed, saving bandwidth.

```typescript
// HTTP conditional requests with ETags in TypeScript
import { createHash } from 'crypto';

/** Generate ETag from response data. */
function generateETag(data: unknown): string {
  const content = JSON.stringify(data);
  const hash = createHash('sha256').update(content).digest('hex');
  return `"${hash.slice(0, 16)}"`;  // Weak ETag
}

/** Express middleware for ETag handling. */
function etagMiddleware(
  req: Request,
  res: Response,
  next: NextFunction
): void {
  const originalJson = res.json.bind(res);

  res.json = (data: unknown) => {
    const etag = generateETag(data);
    res.setHeader('ETag', etag);

    // Check If-None-Match header
    const ifNoneMatch = req.headers['if-none-match'];
    if (ifNoneMatch === etag) {
      res.status(304).end();
      return res;
    }

    return originalJson(data);
  };

  next();
}

// Example API endpoint
app.get('/api/products/:id', etagMiddleware, async (req, res) => {
  const product = await db.findProduct(req.params.id);

  // Set caching headers
  res.setHeader('Cache-Control', 'public, max-age=60, stale-while-revalidate=600');

  res.json(product);
  // ETag is automatically added by middleware
  // 304 is returned if client's ETag matches
});
```

### Example A.25: Request-Scoped Memoization (Python)

Request-scoped caching stores computed values for a single request's duration. Safe because cache is discarded when request completes.

```python
# Request-scoped memoization in Python (FastAPI/Starlette)
from contextvars import ContextVar
from functools import wraps
from typing import TypeVar, Callable, Awaitable

T = TypeVar('T')

# Context variable holds per-request cache
_request_cache: ContextVar[dict] = ContextVar('request_cache')

def get_request_cache() -> dict:
    """Get or create the request-scoped cache."""
    try:
        return _request_cache.get()
    except LookupError:
        cache = {}
        _request_cache.set(cache)
        return cache

def request_cached(key_fn: Callable[..., str]):
    """Decorator for request-scoped caching."""
    def decorator(fn: Callable[..., Awaitable[T]]) -> Callable[..., Awaitable[T]]:
        @wraps(fn)
        async def wrapper(*args, **kwargs) -> T:
            cache = get_request_cache()
            key = key_fn(*args, **kwargs)

            if key in cache:
                return cache[key]

            result = await fn(*args, **kwargs)
            cache[key] = result
            return result
        return wrapper
    return decorator

# Usage example
@request_cached(lambda user_id: f"permissions:{user_id}")
async def get_user_permissions(user_id: str) -> list[str]:
    """Fetch user permissions, cached for this request."""
    return await db.fetch_permissions(user_id)

# Middleware to reset cache per request
@app.middleware("http")
async def request_cache_middleware(request: Request, call_next):
    _request_cache.set({})  # Fresh cache for each request
    response = await call_next(request)
    return response
```

### Example A.26: Redis Pub/Sub Cache Invalidation (Python)

Use Redis Pub/Sub to invalidate in-memory caches across multiple service instances when data changes.

```python
# Redis Pub/Sub cache invalidation in Python
import asyncio
import redis.asyncio as redis
from cachetools import TTLCache

# Local in-memory cache with TTL
local_cache: TTLCache = TTLCache(maxsize=10000, ttl=300)

# Redis client
redis_client: redis.Redis = None

async def init_redis(url: str = "redis://localhost:6379"):
    global redis_client
    redis_client = redis.from_url(url)

async def invalidate_cache(key: str):
    """Invalidate cache locally and broadcast to other instances."""
    # Delete from local cache
    local_cache.pop(key, None)

    # Broadcast to all instances
    await redis_client.publish('cache:invalidate', key)

async def cache_invalidation_listener():
    """Background task listening for invalidation messages."""
    pubsub = redis_client.pubsub()
    await pubsub.subscribe('cache:invalidate')

    async for message in pubsub.listen():
        if message['type'] == 'message':
            key = message['data'].decode('utf-8')
            local_cache.pop(key, None)
            print(f"Invalidated local cache: {key}")

async def get_user(user_id: str) -> dict:
    """Get user with local + Redis caching."""
    cache_key = f"user:{user_id}"

    # Check local cache first (fastest)
    if cache_key in local_cache:
        return local_cache[cache_key]

    # Check Redis (shared across instances)
    cached = await redis_client.get(cache_key)
    if cached:
        user = json.loads(cached)
        local_cache[cache_key] = user
        return user

    # Fetch from database
    user = await db.fetch_user(user_id)
    if user:
        await redis_client.setex(cache_key, 3600, json.dumps(user))
        local_cache[cache_key] = user

    return user

async def update_user(user_id: str, data: dict):
    """Update user and invalidate caches."""
    await db.update_user(user_id, data)
    await invalidate_cache(f"user:{user_id}")

# Start listener on application startup
asyncio.create_task(cache_invalidation_listener())
```

### Example A.27: Multi-Tier Cache Coordination (Rust)

Coordinate L1 (in-process) and L2 (Redis) caches with proper invalidation across tiers.

```rust
// Multi-tier cache coordination in Rust
use moka::sync::Cache;
use redis::AsyncCommands;
use serde::{Deserialize, Serialize};
use std::sync::Arc;
use std::time::Duration;

#[derive(Clone)]
pub struct MultiTierCache {
    l1: Cache<String, String>,  // In-process cache
    redis: redis::Client,
}

impl MultiTierCache {
    pub fn new(redis_url: &str) -> Self {
        Self {
            l1: Cache::builder()
                .max_capacity(10_000)
                .time_to_live(Duration::from_secs(60))  // Short L1 TTL
                .build(),
            redis: redis::Client::open(redis_url).unwrap(),
        }
    }

    /// Get value, checking L1 first, then L2, then fetching.
    pub async fn get_or_fetch<T, F, Fut>(
        &self,
        key: &str,
        fetch_fn: F,
    ) -> Result<T, Box<dyn std::error::Error>>
    where
        T: Serialize + for<'de> Deserialize<'de> + Clone,
        F: FnOnce() -> Fut,
        Fut: std::future::Future<Output = Result<T, Box<dyn std::error::Error>>>,
    {
        // L1: Check in-process cache
        if let Some(cached) = self.l1.get(key) {
            return Ok(serde_json::from_str(&cached)?);
        }

        // L2: Check Redis
        let mut conn = self.redis.get_async_connection().await?;
        if let Some(cached) = conn.get::<_, Option<String>>(key).await? {
            // Populate L1 from L2
            self.l1.insert(key.to_string(), cached.clone());
            return Ok(serde_json::from_str(&cached)?);
        }

        // Fetch from origin
        let value = fetch_fn().await?;
        let serialized = serde_json::to_string(&value)?;

        // Store in both tiers
        conn.set_ex::<_, _, ()>(key, &serialized, 3600).await?;
        self.l1.insert(key.to_string(), serialized);

        Ok(value)
    }

    /// Invalidate across both tiers and broadcast to other instances.
    pub async fn invalidate(&self, key: &str) -> Result<(), Box<dyn std::error::Error>> {
        // Remove from L1
        self.l1.invalidate(key);

        // Remove from L2
        let mut conn = self.redis.get_async_connection().await?;
        conn.del::<_, ()>(key).await?;

        // Broadcast to other instances
        conn.publish::<_, _, ()>("cache:invalidate", key).await?;

        Ok(())
    }
}
```

### Example A.28: Negative Caching Pattern (TypeScript)

Cache "not found" results to prevent repeated database queries for nonexistent data.

```typescript
// Negative caching pattern in TypeScript
import Redis from 'ioredis';

const redis = new Redis();
const NOT_FOUND_SENTINEL = '__NOT_FOUND__';
const POSITIVE_TTL = 3600;  // 1 hour for found items
const NEGATIVE_TTL = 300;   // 5 minutes for not-found items

interface User {
  id: string;
  name: string;
  email: string;
}

async function getUserById(userId: string): Promise<User | null> {
  const cacheKey = `user:${userId}`;

  // Check cache
  const cached = await redis.get(cacheKey);

  if (cached === NOT_FOUND_SENTINEL) {
    // Cached negative result - user definitively doesn't exist
    return null;
  }

  if (cached) {
    // Cached positive result
    return JSON.parse(cached) as User;
  }

  // Cache miss - fetch from database
  const user = await db.findUser(userId);

  if (user) {
    // Cache positive result with longer TTL
    await redis.setex(cacheKey, POSITIVE_TTL, JSON.stringify(user));
  } else {
    // Cache negative result with shorter TTL
    // Short TTL allows recovery if user is created later
    await redis.setex(cacheKey, NEGATIVE_TTL, NOT_FOUND_SENTINEL);
  }

  return user;
}

// When a user is created, invalidate any negative cache
async function createUser(userData: Omit<User, 'id'>): Promise<User> {
  const user = await db.createUser(userData);

  // Invalidate potential negative cache entry
  await redis.del(`user:${user.id}`);

  return user;
}
```

### Example 6.7: GraphQL N+1 Query Pattern (GraphQL)

This query demonstrates the N+1 problem in GraphQL. Without DataLoader, fetching users with their posts results in 1 query for users + N queries for posts.

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

### Example 6.8: DataLoader Pattern Implementation (Python)

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

---

## Database and Storage Selection (Chapter 7)

### Example 7.1: Database Selection Decision Helper (Python)

A utility function that recommends database types based on access pattern characteristics. Useful for documenting architectural decisions.

```python
# Database selection decision helper in Python
from dataclasses import dataclass
from enum import Enum
from typing import Optional

class DatabaseType(Enum):
    SQL = "relational"
    DOCUMENT = "document"
    KEY_VALUE = "key_value"
    WIDE_COLUMN = "wide_column"
    VECTOR = "vector"
    SEARCH = "search"

@dataclass
class AccessPattern:
    needs_acid: bool = False
    needs_complex_joins: bool = False
    read_write_ratio: float = 0.8  # 0.8 = 80% reads
    writes_per_second: int = 100
    needs_full_text_search: bool = False
    needs_similarity_search: bool = False
    schema_flexibility: str = "fixed"  # "fixed", "moderate", "high"
    consistency: str = "strong"  # "strong", "eventual"

def recommend_database(pattern: AccessPattern) -> list[tuple[DatabaseType, str]]:
    """Return ranked database recommendations with rationale."""
    recommendations = []

    # ACID requirements strongly suggest SQL
    if pattern.needs_acid or pattern.needs_complex_joins:
        recommendations.append((
            DatabaseType.SQL,
            "ACID transactions and/or complex joins required"
        ))

    # Vector search is specialized
    if pattern.needs_similarity_search:
        recommendations.append((
            DatabaseType.VECTOR,
            "Semantic similarity search required (embeddings)"
        ))

    # Full-text search is specialized
    if pattern.needs_full_text_search:
        recommendations.append((
            DatabaseType.SEARCH,
            "Full-text search is primary access pattern"
        ))

    # Write-heavy with eventual consistency -> wide-column
    if (pattern.writes_per_second > 10000 and
        pattern.consistency == "eventual"):
        recommendations.append((
            DatabaseType.WIDE_COLUMN,
            f"High write throughput ({pattern.writes_per_second}/s) with eventual consistency"
        ))

    # Simple key lookups with high read ratio -> key-value
    if (pattern.read_write_ratio > 0.9 and
        not pattern.needs_complex_joins and
        pattern.schema_flexibility == "high"):
        recommendations.append((
            DatabaseType.KEY_VALUE,
            "Simple key-based lookups with high read ratio"
        ))

    # Flexible schema without joins -> document
    if (pattern.schema_flexibility in ("moderate", "high") and
        not pattern.needs_complex_joins):
        recommendations.append((
            DatabaseType.DOCUMENT,
            "Flexible schema requirements without complex joins"
        ))

    # Default to SQL if nothing else matches
    if not recommendations:
        recommendations.append((
            DatabaseType.SQL,
            "General-purpose; consider specialized stores as needs clarify"
        ))

    return recommendations

# Usage
pattern = AccessPattern(
    needs_acid=False,
    needs_full_text_search=True,
    read_write_ratio=0.95,
    consistency="eventual"
)
for db_type, reason in recommend_database(pattern):
    print(f"{db_type.value}: {reason}")
```

### Example 7.2: SQL vs Document Store Comparison (Python)

Shows the same product API implemented with PostgreSQL and MongoDB, highlighting when each approach works better.

```python
# Comparing SQL and Document store approaches for a product API

# === PostgreSQL approach (SQL) ===
# Best when: Products have consistent structure, need complex queries/reporting

import asyncpg

async def get_product_sql(pool: asyncpg.Pool, product_id: str) -> dict:
    """Fetch product with category from normalized tables."""
    return await pool.fetchrow("""
        SELECT p.*, c.name as category_name, c.parent_id
        FROM products p
        JOIN categories c ON p.category_id = c.id
        WHERE p.id = $1
    """, product_id)

async def search_products_sql(pool: asyncpg.Pool, filters: dict) -> list:
    """Complex filtering across normalized data."""
    return await pool.fetch("""
        SELECT p.*, c.name as category_name
        FROM products p
        JOIN categories c ON p.category_id = c.id
        WHERE ($1::text IS NULL OR c.name = $1)
          AND ($2::numeric IS NULL OR p.price <= $2)
          AND ($3::text[] IS NULL OR p.tags && $3)
        ORDER BY p.created_at DESC
        LIMIT 50
    """, filters.get('category'), filters.get('max_price'), filters.get('tags'))


# === MongoDB approach (Document) ===
# Best when: Products have varying attributes, schema evolves frequently

from motor.motor_asyncio import AsyncIOMotorClient

async def get_product_mongo(db, product_id: str) -> dict:
    """Fetch complete product document - no joins needed."""
    return await db.products.find_one({"_id": product_id})
    # Document contains embedded category, attributes, variants - all in one read

async def search_products_mongo(db, filters: dict) -> list:
    """Query with flexible document structure."""
    query = {}
    if filters.get('category'):
        query['category.name'] = filters['category']
    if filters.get('max_price'):
        query['price'] = {'$lte': filters['max_price']}
    if filters.get('tags'):
        query['tags'] = {'$in': filters['tags']}

    # Can query nested fields without schema changes
    if filters.get('color'):
        query['attributes.color'] = filters['color']

    return await db.products.find(query).sort('created_at', -1).limit(50).to_list(50)

# Key decision factors:
# - SQL: Need reporting, complex joins, strong consistency, ACID
# - Document: Varying product attributes, embedded data, horizontal scale
```

### Example 7.3: Key-Value Session Storage (Rust)

High-performance session management using Redis with sub-millisecond lookups.

```rust
// Key-value session storage in Rust using Redis
use redis::{AsyncCommands, Client};
use serde::{Deserialize, Serialize};
use uuid::Uuid;

#[derive(Serialize, Deserialize, Clone)]
pub struct Session {
    pub user_id: String,
    pub roles: Vec<String>,
    pub created_at: i64,
    pub last_accessed: i64,
}

pub struct SessionStore {
    client: Client,
    ttl_seconds: u64,
}

impl SessionStore {
    pub fn new(redis_url: &str, ttl_seconds: u64) -> Result<Self, redis::RedisError> {
        Ok(Self {
            client: Client::open(redis_url)?,
            ttl_seconds,
        })
    }

    /// Create a new session, returns session token
    pub async fn create(&self, user_id: &str, roles: Vec<String>) -> Result<String, redis::RedisError> {
        let mut conn = self.client.get_multiplexed_async_connection().await?;
        let token = Uuid::new_v4().to_string();
        let session = Session {
            user_id: user_id.to_string(),
            roles,
            created_at: chrono::Utc::now().timestamp(),
            last_accessed: chrono::Utc::now().timestamp(),
        };

        let key = format!("session:{}", token);
        let value = serde_json::to_string(&session).unwrap();
        conn.set_ex(&key, value, self.ttl_seconds).await?;

        Ok(token)
    }

    /// Get session by token - O(1) lookup, typically <1ms
    pub async fn get(&self, token: &str) -> Result<Option<Session>, redis::RedisError> {
        let mut conn = self.client.get_multiplexed_async_connection().await?;
        let key = format!("session:{}", token);

        let value: Option<String> = conn.get(&key).await?;
        Ok(value.map(|v| serde_json::from_str(&v).unwrap()))
    }

    /// Refresh session TTL on activity
    pub async fn touch(&self, token: &str) -> Result<bool, redis::RedisError> {
        let mut conn = self.client.get_multiplexed_async_connection().await?;
        let key = format!("session:{}", token);
        conn.expire(&key, self.ttl_seconds as i64).await
    }

    /// Invalidate session on logout
    pub async fn delete(&self, token: &str) -> Result<(), redis::RedisError> {
        let mut conn = self.client.get_multiplexed_async_connection().await?;
        conn.del(format!("session:{}", token)).await
    }
}
```

### Example 7.4: Write-Heavy Analytics with Wide-Column Store (TypeScript)

Ingesting high-volume analytics events using Cassandra/ScyllaDB patterns.

```typescript
// Write-heavy analytics with Cassandra in TypeScript
import { Client, types } from 'cassandra-driver';

const client = new Client({
  contactPoints: ['cassandra-1', 'cassandra-2', 'cassandra-3'],
  localDataCenter: 'datacenter1',
  keyspace: 'analytics',
});

interface AnalyticsEvent {
  userId: string;
  eventType: string;
  properties: Record<string, unknown>;
  timestamp?: Date;
}

// Partition by user_id and date for efficient time-range queries
// Clustering by timestamp for ordered retrieval within partition
const INSERT_EVENT = `
  INSERT INTO events (user_id, event_date, timestamp, event_type, properties)
  VALUES (?, ?, ?, ?, ?)
`;

async function recordEvent(event: AnalyticsEvent): Promise<void> {
  const timestamp = event.timestamp ?? new Date();
  const eventDate = timestamp.toISOString().split('T')[0]; // YYYY-MM-DD

  // Async write - doesn't block the API response
  await client.execute(INSERT_EVENT, [
    event.userId,
    eventDate,
    timestamp,
    event.eventType,
    JSON.stringify(event.properties),
  ], { prepare: true });
}

// Batch writes for higher throughput (use unlogged batch for performance)
async function recordEventsBatch(events: AnalyticsEvent[]): Promise<void> {
  const queries = events.map(event => {
    const timestamp = event.timestamp ?? new Date();
    const eventDate = timestamp.toISOString().split('T')[0];
    return {
      query: INSERT_EVENT,
      params: [event.userId, eventDate, timestamp, event.eventType, JSON.stringify(event.properties)],
    };
  });

  // Unlogged batch: no atomicity guarantee, but much faster for analytics
  await client.batch(queries, { prepare: true, logged: false });
}

// Query events for a user within a time range (efficient due to partition design)
async function getUserEvents(userId: string, startDate: string, endDate: string) {
  const result = await client.execute(`
    SELECT * FROM events
    WHERE user_id = ? AND event_date >= ? AND event_date <= ?
    ORDER BY timestamp DESC
    LIMIT 1000
  `, [userId, startDate, endDate], { prepare: true });

  return result.rows;
}
```

### Example 7.5: Fire-and-Forget Analytics Pattern (Python)

Async event ingestion that prioritizes API latency over guaranteed delivery.

```python
# Fire-and-forget analytics pattern in Python
import asyncio
from collections import deque
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any
import json

@dataclass
class AnalyticsEvent:
    event_type: str
    properties: dict[str, Any]
    timestamp: datetime = field(default_factory=datetime.utcnow)
    user_id: str | None = None

class FireAndForgetBuffer:
    """In-memory buffer that flushes to durable storage periodically."""

    def __init__(self, flush_interval: float = 1.0, max_buffer_size: int = 1000):
        self._buffer: deque[AnalyticsEvent] = deque(maxlen=max_buffer_size)
        self._flush_interval = flush_interval
        self._flush_task: asyncio.Task | None = None
        self._storage = None  # Injected storage backend

    async def start(self, storage):
        """Start the background flush loop."""
        self._storage = storage
        self._flush_task = asyncio.create_task(self._flush_loop())

    async def stop(self):
        """Graceful shutdown - flush remaining events."""
        if self._flush_task:
            self._flush_task.cancel()
            await self._flush_remaining()

    def record(self, event: AnalyticsEvent) -> None:
        """Record event - returns immediately, no await needed."""
        self._buffer.append(event)
        # If buffer is full, oldest events are dropped (maxlen behavior)
        # This is acceptable for analytics - we trade completeness for latency

    async def _flush_loop(self):
        """Background task that periodically flushes buffer to storage."""
        while True:
            await asyncio.sleep(self._flush_interval)
            await self._flush_remaining()

    async def _flush_remaining(self):
        """Flush current buffer contents to durable storage."""
        if not self._buffer:
            return

        # Drain buffer atomically
        events_to_flush = []
        while self._buffer:
            events_to_flush.append(self._buffer.popleft())

        # Batch write to durable storage (Kafka, S3, database)
        try:
            await self._storage.write_batch([
                {"event_type": e.event_type, "properties": e.properties,
                 "timestamp": e.timestamp.isoformat(), "user_id": e.user_id}
                for e in events_to_flush
            ])
        except Exception as e:
            # Log error but don't crash - data loss is acceptable for analytics
            print(f"Failed to flush {len(events_to_flush)} events: {e}")

# Usage in API endpoint
buffer = FireAndForgetBuffer(flush_interval=1.0)

async def track_event(event_type: str, properties: dict, user_id: str = None):
    """Non-blocking event tracking - adds ~0.01ms to request latency."""
    buffer.record(AnalyticsEvent(event_type, properties, user_id=user_id))
    # Returns immediately - no await, no network call
```

### Example 7.6: WORM Audit Log Pattern (Rust)

Append-only audit logging with immutability guarantees for compliance.

```rust
// WORM audit log pattern in Rust
use chrono::{DateTime, Utc};
use serde::{Deserialize, Serialize};
use sqlx::{PgPool, Row};
use uuid::Uuid;

#[derive(Debug, Serialize, Deserialize)]
pub struct AuditEntry {
    pub id: Uuid,
    pub timestamp: DateTime<Utc>,
    pub actor_id: String,
    pub action: String,
    pub resource_type: String,
    pub resource_id: String,
    pub old_value: Option<serde_json::Value>,
    pub new_value: Option<serde_json::Value>,
    pub metadata: serde_json::Value,
}

pub struct AuditLog {
    pool: PgPool,
}

impl AuditLog {
    pub fn new(pool: PgPool) -> Self {
        Self { pool }
    }

    /// Append an audit entry - INSERT only, no UPDATE or DELETE
    pub async fn append(&self, entry: AuditEntry) -> Result<Uuid, sqlx::Error> {
        // Audit table has no UPDATE or DELETE permissions
        // Uses append-only table structure
        sqlx::query(r#"
            INSERT INTO audit_log (id, timestamp, actor_id, action, resource_type,
                                   resource_id, old_value, new_value, metadata)
            VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9)
        "#)
        .bind(entry.id)
        .bind(entry.timestamp)
        .bind(&entry.actor_id)
        .bind(&entry.action)
        .bind(&entry.resource_type)
        .bind(&entry.resource_id)
        .bind(&entry.old_value)
        .bind(&entry.new_value)
        .bind(&entry.metadata)
        .execute(&self.pool)
        .await?;

        Ok(entry.id)
    }

    /// Query audit entries by resource - read-only operations
    pub async fn get_by_resource(
        &self,
        resource_type: &str,
        resource_id: &str,
    ) -> Result<Vec<AuditEntry>, sqlx::Error> {
        sqlx::query_as::<_, AuditEntry>(r#"
            SELECT * FROM audit_log
            WHERE resource_type = $1 AND resource_id = $2
            ORDER BY timestamp DESC
        "#)
        .bind(resource_type)
        .bind(resource_id)
        .fetch_all(&self.pool)
        .await
    }

    /// Query audit entries by time range for compliance reporting
    pub async fn get_by_time_range(
        &self,
        start: DateTime<Utc>,
        end: DateTime<Utc>,
    ) -> Result<Vec<AuditEntry>, sqlx::Error> {
        sqlx::query_as::<_, AuditEntry>(r#"
            SELECT * FROM audit_log
            WHERE timestamp >= $1 AND timestamp < $2
            ORDER BY timestamp ASC
        "#)
        .bind(start)
        .bind(end)
        .fetch_all(&self.pool)
        .await
    }
}

// Helper to create audit entries with consistent structure
pub fn audit_update(
    actor_id: &str,
    resource_type: &str,
    resource_id: &str,
    old_value: serde_json::Value,
    new_value: serde_json::Value,
) -> AuditEntry {
    AuditEntry {
        id: Uuid::new_v4(),
        timestamp: Utc::now(),
        actor_id: actor_id.to_string(),
        action: "update".to_string(),
        resource_type: resource_type.to_string(),
        resource_id: resource_id.to_string(),
        old_value: Some(old_value),
        new_value: Some(new_value),
        metadata: serde_json::json!({}),
    }
}
```

### Example 7.7: Read Replica Routing (Rust)

Route reads to replicas while ensuring writes go to primary.

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
        let primary = PgPoolOptions::new()
            .max_connections(10)
            .connect(primary_url)
            .await?;

        let mut replicas = Vec::new();
        for url in replica_urls {
            replicas.push(
                PgPoolOptions::new()
                    .max_connections(10)
                    .connect(url)
                    .await?
            );
        }

        Ok(Self { primary, replicas })
    }

    /// Get the primary pool for write operations
    pub fn write_pool(&self) -> &PgPool {
        &self.primary
    }

    /// Get a random replica pool for read operations
    /// Falls back to primary if no replicas available
    pub fn read_pool(&self) -> &PgPool {
        self.replicas
            .choose(&mut rand::thread_rng())
            .unwrap_or(&self.primary)
    }

    /// Get primary for read-after-write consistency
    pub fn consistent_read_pool(&self) -> &PgPool {
        &self.primary
    }
}

// Usage pattern:
// - router.read_pool() for general SELECT queries
// - router.write_pool() for INSERT/UPDATE/DELETE
// - router.consistent_read_pool() when user just wrote and needs to read back
```

### Example 7.8: Vector Search with pgvector (Python)

Semantic similarity search using PostgreSQL with the pgvector extension.

```python
# Vector search with pgvector in Python
import asyncpg
from openai import AsyncOpenAI

client = AsyncOpenAI()

async def generate_embedding(text: str) -> list[float]:
    """Generate embedding using OpenAI's API."""
    response = await client.embeddings.create(
        model="text-embedding-3-small",
        input=text
    )
    return response.data[0].embedding

async def store_product_embedding(pool: asyncpg.Pool, product_id: str, description: str):
    """Store product with its embedding for similarity search."""
    embedding = await generate_embedding(description)

    await pool.execute("""
        INSERT INTO products (id, description, embedding)
        VALUES ($1, $2, $3)
        ON CONFLICT (id) DO UPDATE SET
            description = EXCLUDED.description,
            embedding = EXCLUDED.embedding
    """, product_id, description, embedding)

async def search_similar_products(
    pool: asyncpg.Pool,
    query: str,
    limit: int = 10
) -> list[dict]:
    """Find products semantically similar to the query."""
    query_embedding = await generate_embedding(query)

    # Use cosine distance for similarity (1 - cosine_similarity)
    # Lower distance = more similar
    results = await pool.fetch("""
        SELECT id, description,
               1 - (embedding <=> $1::vector) as similarity
        FROM products
        ORDER BY embedding <=> $1::vector
        LIMIT $2
    """, query_embedding, limit)

    return [
        {"id": r["id"], "description": r["description"], "similarity": r["similarity"]}
        for r in results
    ]

# Hybrid search: combine vector similarity with traditional filters
async def search_products_hybrid(
    pool: asyncpg.Pool,
    query: str,
    category: str | None = None,
    max_price: float | None = None,
    limit: int = 10
) -> list[dict]:
    """Combine semantic search with traditional SQL filters."""
    query_embedding = await generate_embedding(query)

    results = await pool.fetch("""
        SELECT id, description, price, category,
               1 - (embedding <=> $1::vector) as similarity
        FROM products
        WHERE ($2::text IS NULL OR category = $2)
          AND ($3::numeric IS NULL OR price <= $3)
        ORDER BY embedding <=> $1::vector
        LIMIT $4
    """, query_embedding, category, max_price, limit)

    return [dict(r) for r in results]
```

### Example 7.9: Elasticsearch Integration (TypeScript)

Full-text search and faceted navigation alongside a primary database.

```typescript
// Elasticsearch integration in TypeScript
import { Client } from '@elastic/elasticsearch';

const es = new Client({ node: 'http://localhost:9200' });

interface Product {
  id: string;
  name: string;
  description: string;
  category: string;
  price: number;
  tags: string[];
}

// Index a product for search (called after database write)
async function indexProduct(product: Product): Promise<void> {
  await es.index({
    index: 'products',
    id: product.id,
    document: {
      name: product.name,
      description: product.description,
      category: product.category,
      price: product.price,
      tags: product.tags,
      // Combine fields for unified search
      searchable: `${product.name} ${product.description} ${product.tags.join(' ')}`,
    },
  });
}

// Full-text search with facets
async function searchProducts(query: string, filters?: {
  category?: string;
  minPrice?: number;
  maxPrice?: number;
  tags?: string[];
}) {
  const must: object[] = [
    { multi_match: { query, fields: ['name^3', 'description', 'tags'] } }
  ];

  const filter: object[] = [];
  if (filters?.category) {
    filter.push({ term: { category: filters.category } });
  }
  if (filters?.minPrice || filters?.maxPrice) {
    filter.push({ range: { price: {
      ...(filters.minPrice && { gte: filters.minPrice }),
      ...(filters.maxPrice && { lte: filters.maxPrice }),
    }}});
  }
  if (filters?.tags?.length) {
    filter.push({ terms: { tags: filters.tags } });
  }

  const result = await es.search({
    index: 'products',
    query: { bool: { must, filter } },
    aggs: {
      categories: { terms: { field: 'category' } },
      price_ranges: { range: { field: 'price', ranges: [
        { to: 50 }, { from: 50, to: 100 }, { from: 100, to: 500 }, { from: 500 }
      ]}},
      tags: { terms: { field: 'tags', size: 20 } },
    },
    highlight: { fields: { name: {}, description: {} } },
    size: 20,
  });

  return {
    hits: result.hits.hits.map(hit => ({
      ...hit._source,
      score: hit._score,
      highlights: hit.highlight,
    })),
    facets: result.aggregations,
    total: (result.hits.total as { value: number }).value,
  };
}

// Keep Elasticsearch in sync with database changes
async function onProductUpdated(product: Product): Promise<void> {
  await indexProduct(product);
}

async function onProductDeleted(productId: string): Promise<void> {
  await es.delete({ index: 'products', id: productId });
}
```

### Example 7.10: Polyglot Persistence Coordinator (Python)

Managing data consistency across multiple database types.

```python
# Polyglot persistence coordinator in Python
import asyncio
from dataclasses import dataclass
from typing import Any
import asyncpg
import redis.asyncio as redis
from elasticsearch import AsyncElasticsearch

@dataclass
class Product:
    id: str
    name: str
    description: str
    price: float
    category: str
    tags: list[str]

class DataCoordinator:
    """Coordinates writes across PostgreSQL, Redis, and Elasticsearch."""

    def __init__(self, pg_pool: asyncpg.Pool, redis_client: redis.Redis, es_client: AsyncElasticsearch):
        self.pg = pg_pool  # Source of truth
        self.redis = redis_client  # Cache
        self.es = es_client  # Search index

    async def create_product(self, product: Product) -> None:
        """Create product with coordinated writes to all stores."""
        # 1. Write to PostgreSQL first (source of truth)
        await self.pg.execute("""
            INSERT INTO products (id, name, description, price, category, tags)
            VALUES ($1, $2, $3, $4, $5, $6)
        """, product.id, product.name, product.description,
           product.price, product.category, product.tags)

        # 2. Update secondary stores (can be async/eventual)
        await asyncio.gather(
            self._update_cache(product),
            self._update_search_index(product),
            return_exceptions=True  # Don't fail if secondary stores fail
        )

    async def update_product(self, product: Product) -> None:
        """Update product across all stores."""
        # 1. Update PostgreSQL (source of truth)
        await self.pg.execute("""
            UPDATE products SET name=$2, description=$3, price=$4, category=$5, tags=$6
            WHERE id = $1
        """, product.id, product.name, product.description,
           product.price, product.category, product.tags)

        # 2. Invalidate cache and update search
        await asyncio.gather(
            self._invalidate_cache(product.id),
            self._update_search_index(product),
            return_exceptions=True
        )

    async def get_product(self, product_id: str) -> Product | None:
        """Get product, checking cache first."""
        # Try cache first
        cached = await self.redis.get(f"product:{product_id}")
        if cached:
            return Product(**json.loads(cached))

        # Cache miss - fetch from PostgreSQL
        row = await self.pg.fetchrow(
            "SELECT * FROM products WHERE id = $1", product_id
        )
        if not row:
            return None

        product = Product(**dict(row))

        # Populate cache for next time (fire and forget)
        asyncio.create_task(self._update_cache(product))

        return product

    async def _update_cache(self, product: Product) -> None:
        """Update Redis cache with product data."""
        await self.redis.setex(
            f"product:{product.id}",
            3600,  # 1 hour TTL
            json.dumps(product.__dict__)
        )

    async def _invalidate_cache(self, product_id: str) -> None:
        """Invalidate product cache on update."""
        await self.redis.delete(f"product:{product_id}")

    async def _update_search_index(self, product: Product) -> None:
        """Update Elasticsearch index."""
        await self.es.index(
            index="products",
            id=product.id,
            document={
                "name": product.name,
                "description": product.description,
                "price": product.price,
                "category": product.category,
                "tags": product.tags,
            }
        )
```

### Example 7.11: Connection Pool Configuration (Multi-language)

Connection pooling patterns that apply regardless of database type.

```python
# Python: asyncpg pool for PostgreSQL
import asyncpg

pool = await asyncpg.create_pool(
    dsn="postgresql://user:pass@localhost/db",
    min_size=5,       # Keep connections warm
    max_size=20,      # Limit total connections
    max_inactive_connection_lifetime=300,  # Recycle idle connections
    command_timeout=30,  # Query timeout
)
```

```rust
// Rust: SQLx pool configuration
use sqlx::postgres::PgPoolOptions;
use std::time::Duration;

let pool = PgPoolOptions::new()
    .min_connections(5)
    .max_connections(20)
    .acquire_timeout(Duration::from_secs(30))
    .idle_timeout(Duration::from_secs(300))
    .connect("postgresql://localhost/db")
    .await?;
```

```typescript
// TypeScript: pg pool configuration
import { Pool } from 'pg';

const pool = new Pool({
  connectionString: 'postgresql://localhost/db',
  min: 5,
  max: 20,
  idleTimeoutMillis: 300000,
  connectionTimeoutMillis: 30000,
});
```

---

## Asynchronous Processing and Queuing (Chapter 8)

### Example A.40: Background Job Producer and Consumer (TypeScript)

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

### Example A.41: Backpressure Implementation (Python)

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

### Example A.42: Retry with Exponential Backoff and Jitter (Rust)

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

### Example A.43: Async HTTP Endpoint with Job Status (Python)

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

### Example A.44: Transactional Outbox Pattern (Python)

This example demonstrates the transactional outbox pattern where events are written to an outbox table in the same database transaction as business data, ensuring atomicity between state changes and event publishing.

```python
# Transactional outbox pattern in Python with SQLAlchemy
from sqlalchemy import create_engine, Column, String, DateTime, Text, Boolean
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from datetime import datetime
import json
import uuid

Base = declarative_base()

class Order(Base):
    __tablename__ = 'orders'
    id = Column(String(36), primary_key=True)
    customer_id = Column(String(36), nullable=False)
    total_amount = Column(String(20), nullable=False)
    status = Column(String(20), default='pending')
    created_at = Column(DateTime, default=datetime.utcnow)

class OutboxEvent(Base):
    __tablename__ = 'outbox_events'
    id = Column(String(36), primary_key=True)
    aggregate_type = Column(String(100), nullable=False)
    aggregate_id = Column(String(36), nullable=False)
    event_type = Column(String(100), nullable=False)
    payload = Column(Text, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    published = Column(Boolean, default=False)

class OrderService:
    def __init__(self, session_factory):
        self.session_factory = session_factory

    def create_order(self, customer_id: str, total_amount: str) -> Order:
        """Create order and outbox event in single transaction."""
        session = self.session_factory()
        try:
            # Create the order
            order = Order(
                id=str(uuid.uuid4()),
                customer_id=customer_id,
                total_amount=total_amount,
                status='created'
            )
            session.add(order)

            # Write event to outbox in SAME transaction
            event = OutboxEvent(
                id=str(uuid.uuid4()),
                aggregate_type='Order',
                aggregate_id=order.id,
                event_type='OrderCreated',
                payload=json.dumps({
                    'order_id': order.id,
                    'customer_id': customer_id,
                    'total_amount': total_amount,
                    'status': 'created'
                })
            )
            session.add(event)

            # Both writes commit or both rollback
            session.commit()
            return order
        except Exception as e:
            session.rollback()
            raise
        finally:
            session.close()

class OutboxRelay:
    """Reads outbox and publishes to message broker."""
    def __init__(self, session_factory, publisher):
        self.session_factory = session_factory
        self.publisher = publisher

    async def process_outbox(self, batch_size: int = 100):
        session = self.session_factory()
        try:
            events = session.query(OutboxEvent)\
                .filter(OutboxEvent.published == False)\
                .order_by(OutboxEvent.created_at)\
                .limit(batch_size)\
                .all()

            for event in events:
                # Publish to broker (Kafka, RabbitMQ, etc.)
                await self.publisher.publish(
                    topic=f"{event.aggregate_type.lower()}.events",
                    key=event.aggregate_id,
                    value=event.payload,
                    headers={'event_type': event.event_type}
                )
                # Mark as published
                event.published = True

            session.commit()
        finally:
            session.close()
```

### Example A.45: Idempotent Consumer with Deduplication (TypeScript)

This example shows how to implement an idempotent consumer that tracks processed message IDs to handle duplicate deliveries safely.

```typescript
// Idempotent consumer with deduplication in TypeScript
import { Pool } from 'pg';

interface Message {
  id: string;
  type: string;
  payload: Record<string, unknown>;
  timestamp: Date;
}

interface ProcessedMessage {
  messageId: string;
  processedAt: Date;
}

class IdempotentConsumer {
  private pool: Pool;
  private handlers: Map<string, (payload: Record<string, unknown>) => Promise<void>>;

  constructor(connectionString: string) {
    this.pool = new Pool({ connectionString });
    this.handlers = new Map();
  }

  registerHandler(
    eventType: string,
    handler: (payload: Record<string, unknown>) => Promise<void>
  ): void {
    this.handlers.set(eventType, handler);
  }

  async processMessage(message: Message): Promise<boolean> {
    const client = await this.pool.connect();

    try {
      // Start transaction
      await client.query('BEGIN');

      // Check if already processed (with row lock to prevent races)
      const checkResult = await client.query(
        `SELECT message_id FROM processed_messages
         WHERE message_id = $1 FOR UPDATE SKIP LOCKED`,
        [message.id]
      );

      if (checkResult.rows.length > 0) {
        // Already processed - skip silently
        await client.query('ROLLBACK');
        console.log(`Skipping duplicate message: ${message.id}`);
        return false;
      }

      // Get handler for this message type
      const handler = this.handlers.get(message.type);
      if (!handler) {
        throw new Error(`No handler for message type: ${message.type}`);
      }

      // Process the message
      await handler(message.payload);

      // Record as processed (in same transaction as business logic)
      await client.query(
        `INSERT INTO processed_messages (message_id, event_type, processed_at)
         VALUES ($1, $2, NOW())`,
        [message.id, message.type]
      );

      // Commit both the business logic AND the deduplication record
      await client.query('COMMIT');
      return true;

    } catch (error) {
      await client.query('ROLLBACK');
      throw error;
    } finally {
      client.release();
    }
  }

  async cleanupOldRecords(retentionDays: number = 7): Promise<number> {
    const result = await this.pool.query(
      `DELETE FROM processed_messages
       WHERE processed_at < NOW() - INTERVAL '${retentionDays} days'`
    );
    return result.rowCount ?? 0;
  }
}

// Usage example
const consumer = new IdempotentConsumer(process.env.DATABASE_URL!);

consumer.registerHandler('OrderCreated', async (payload) => {
  const { order_id, customer_id } = payload as { order_id: string; customer_id: string };
  // Process order - safe to run multiple times due to idempotency check
  console.log(`Processing order ${order_id} for customer ${customer_id}`);
});
```

### Example A.46: Saga Orchestrator Pattern (TypeScript)

This example demonstrates a saga orchestrator that coordinates distributed transactions across multiple services with compensating actions for rollback.

```typescript
// Saga orchestrator pattern in TypeScript
type SagaStatus = 'pending' | 'running' | 'completed' | 'compensating' | 'failed';

interface SagaStep<T> {
  name: string;
  execute: (context: T) => Promise<void>;
  compensate: (context: T) => Promise<void>;
}

interface SagaState<T> {
  id: string;
  status: SagaStatus;
  currentStep: number;
  completedSteps: string[];
  context: T;
  error?: string;
}

class SagaOrchestrator<T> {
  private steps: SagaStep<T>[] = [];
  private stateStore: Map<string, SagaState<T>> = new Map();

  addStep(step: SagaStep<T>): this {
    this.steps.push(step);
    return this;
  }

  async execute(sagaId: string, initialContext: T): Promise<SagaState<T>> {
    const state: SagaState<T> = {
      id: sagaId,
      status: 'running',
      currentStep: 0,
      completedSteps: [],
      context: initialContext,
    };
    this.stateStore.set(sagaId, state);

    try {
      // Execute steps in order
      for (let i = 0; i < this.steps.length; i++) {
        const step = this.steps[i];
        state.currentStep = i;

        console.log(`Saga ${sagaId}: Executing step "${step.name}"`);

        try {
          await step.execute(state.context);
          state.completedSteps.push(step.name);
        } catch (error) {
          console.error(`Saga ${sagaId}: Step "${step.name}" failed:`, error);
          state.error = error instanceof Error ? error.message : String(error);

          // Begin compensation
          await this.compensate(state);
          return state;
        }
      }

      state.status = 'completed';
      console.log(`Saga ${sagaId}: Completed successfully`);

    } catch (error) {
      state.status = 'failed';
      state.error = error instanceof Error ? error.message : String(error);
    }

    return state;
  }

  private async compensate(state: SagaState<T>): Promise<void> {
    state.status = 'compensating';
    console.log(`Saga ${state.id}: Starting compensation`);

    // Compensate in reverse order
    for (let i = state.completedSteps.length - 1; i >= 0; i--) {
      const stepName = state.completedSteps[i];
      const step = this.steps.find(s => s.name === stepName);

      if (step) {
        console.log(`Saga ${state.id}: Compensating step "${step.name}"`);

        // Retry compensation until it succeeds (with backoff)
        let attempts = 0;
        while (attempts < 10) {
          try {
            await step.compensate(state.context);
            break;
          } catch (error) {
            attempts++;
            console.error(`Compensation attempt ${attempts} failed:`, error);
            await this.delay(Math.min(1000 * Math.pow(2, attempts), 30000));
          }
        }
      }
    }

    state.status = 'failed';
    console.log(`Saga ${state.id}: Compensation complete`);
  }

  private delay(ms: number): Promise<void> {
    return new Promise(resolve => setTimeout(resolve, ms));
  }

  getState(sagaId: string): SagaState<T> | undefined {
    return this.stateStore.get(sagaId);
  }
}

// Example: Order processing saga
interface OrderContext {
  orderId: string;
  customerId: string;
  amount: number;
  paymentId?: string;
  inventoryReservationId?: string;
}

const orderSaga = new SagaOrchestrator<OrderContext>()
  .addStep({
    name: 'createOrder',
    execute: async (ctx) => {
      // Create order in order service
      console.log(`Creating order ${ctx.orderId}`);
    },
    compensate: async (ctx) => {
      // Cancel order
      console.log(`Cancelling order ${ctx.orderId}`);
    },
  })
  .addStep({
    name: 'reserveInventory',
    execute: async (ctx) => {
      // Reserve inventory
      ctx.inventoryReservationId = `inv-${ctx.orderId}`;
      console.log(`Reserved inventory: ${ctx.inventoryReservationId}`);
    },
    compensate: async (ctx) => {
      // Release inventory
      console.log(`Releasing inventory: ${ctx.inventoryReservationId}`);
    },
  })
  .addStep({
    name: 'processPayment',
    execute: async (ctx) => {
      // Charge payment
      ctx.paymentId = `pay-${ctx.orderId}`;
      console.log(`Processed payment: ${ctx.paymentId}`);
    },
    compensate: async (ctx) => {
      // Refund payment
      console.log(`Refunding payment: ${ctx.paymentId}`);
    },
  });

// Execute the saga
// const result = await orderSaga.execute('saga-123', {
//   orderId: 'order-456',
//   customerId: 'cust-789',
//   amount: 99.99
// });
```

---

## Compute and Scaling Patterns (Chapter 9)

### Example A.44: Stateless Service with External Session Store (Python)

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

### Example A.45: Multi-Metric Kubernetes HPA Configuration (YAML)

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

### Example A.46: Cold Start Mitigation in AWS Lambda (TypeScript)

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

### Example A.47: Graceful Shutdown and Health Checks (Rust)

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

### Example A.48: Token Bucket Rate Limiter (Python)

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

### Example A.49: Circuit Breaker Implementation (TypeScript)

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

### Example A.50: Retry with Exponential Backoff and Jitter (Rust)

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

### Example A.51: Bulkhead with Semaphore (TypeScript)

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

### Example 10.5: Hedged Requests for Tail Latency Reduction (Python)

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

## Edge Infrastructure (Chapter 12)

### Example 12.1: A/B Test Routing Edge Function (TypeScript)

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

### Example 12.2: Edge JWT Validation (TypeScript)

```typescript
// Edge JWT validation with KV-cached public keys (Cloudflare Workers)
interface Env {
  JWT_KEYS: KVNamespace;
}

interface JWTPayload {
  sub: string;
  exp: number;
  iat: number;
  iss: string;
  roles?: string[];
}

async function validateJWT(
  token: string,
  env: Env
): Promise<JWTPayload | null> {
  const [headerB64, payloadB64, signatureB64] = token.split('.');
  if (!headerB64 || !payloadB64 || !signatureB64) {
    return null;
  }

  // Decode payload
  const payload: JWTPayload = JSON.parse(atob(payloadB64));

  // Check expiration
  if (payload.exp * 1000 < Date.now()) {
    return null;
  }

  // Get public key from KV (cached JWKS)
  const publicKeyPem = await env.JWT_KEYS.get(`key:${payload.iss}`);
  if (!publicKeyPem) {
    return null;
  }

  // Import public key
  const publicKey = await crypto.subtle.importKey(
    'spki',
    pemToArrayBuffer(publicKeyPem),
    { name: 'RSASSA-PKCS1-v1_5', hash: 'SHA-256' },
    false,
    ['verify']
  );

  // Verify signature
  const data = new TextEncoder().encode(`${headerB64}.${payloadB64}`);
  const signature = base64UrlDecode(signatureB64);

  const valid = await crypto.subtle.verify(
    'RSASSA-PKCS1-v1_5',
    publicKey,
    signature,
    data
  );

  return valid ? payload : null;
}

export default {
  async fetch(request: Request, env: Env): Promise<Response> {
    const authHeader = request.headers.get('Authorization');
    if (!authHeader?.startsWith('Bearer ')) {
      return new Response('Unauthorized', { status: 401 });
    }

    const token = authHeader.slice(7);
    const payload = await validateJWT(token, env);

    if (!payload) {
      return new Response('Invalid token', { status: 401 });
    }

    // Forward validated claims to origin
    const headers = new Headers(request.headers);
    headers.set('X-User-ID', payload.sub);
    headers.set('X-User-Roles', (payload.roles || []).join(','));
    headers.delete('Authorization'); // Don't forward token to origin

    return fetch(request.url, {
      method: request.method,
      headers,
      body: request.body,
    });
  }
};

function pemToArrayBuffer(pem: string): ArrayBuffer {
  const b64 = pem.replace(/-----[^-]+-----/g, '').replace(/\s/g, '');
  const binary = atob(b64);
  const bytes = new Uint8Array(binary.length);
  for (let i = 0; i < binary.length; i++) {
    bytes[i] = binary.charCodeAt(i);
  }
  return bytes.buffer;
}

function base64UrlDecode(str: string): ArrayBuffer {
  const base64 = str.replace(/-/g, '+').replace(/_/g, '/');
  const padded = base64 + '==='.slice(0, (4 - base64.length % 4) % 4);
  const binary = atob(padded);
  const bytes = new Uint8Array(binary.length);
  for (let i = 0; i < binary.length; i++) {
    bytes[i] = binary.charCodeAt(i);
  }
  return bytes.buffer;
}
```

### Example 12.3: KV Store Session Lookup (TypeScript)

```typescript
// Session lookup with KV store and origin fallback (Cloudflare Workers)
interface Env {
  SESSIONS: KVNamespace;
  ORIGIN_URL: string;
}

interface Session {
  userId: string;
  roles: string[];
  expiresAt: number;
}

export default {
  async fetch(request: Request, env: Env): Promise<Response> {
    const sessionId = getSessionIdFromCookie(request);
    if (!sessionId) {
      return new Response('No session', { status: 401 });
    }

    // Try KV first (fast path)
    let session = await env.SESSIONS.get<Session>(sessionId, { type: 'json' });

    if (!session) {
      // Fallback to origin for session lookup
      const originResponse = await fetch(
        `${env.ORIGIN_URL}/internal/session/${sessionId}`,
        { headers: { 'X-Internal-Auth': 'edge-service' } }
      );

      if (!originResponse.ok) {
        return new Response('Invalid session', { status: 401 });
      }

      session = await originResponse.json();

      // Cache in KV for future requests
      const ttl = Math.floor((session.expiresAt - Date.now()) / 1000);
      if (ttl > 0) {
        await env.SESSIONS.put(sessionId, JSON.stringify(session), {
          expirationTtl: ttl,
        });
      }
    }

    // Check expiration
    if (session.expiresAt < Date.now()) {
      await env.SESSIONS.delete(sessionId);
      return new Response('Session expired', { status: 401 });
    }

    // Forward validated session to origin
    const headers = new Headers(request.headers);
    headers.set('X-User-ID', session.userId);
    headers.set('X-User-Roles', session.roles.join(','));

    return fetch(request.url, {
      method: request.method,
      headers,
      body: request.body,
    });
  }
};

function getSessionIdFromCookie(request: Request): string | null {
  const cookie = request.headers.get('Cookie') || '';
  const match = cookie.match(/session_id=([^;]+)/);
  return match ? match[1] : null;
}
```

### Example 12.4: Cloudflare Rate Limiting Rule (JSON)

```json
{
  "description": "API rate limit: 100 requests per minute per IP",
  "expression": "(http.request.uri.path contains \"/api/\")",
  "action": "block",
  "ratelimit": {
    "characteristics": ["ip.src"],
    "period": 60,
    "requests_per_period": 100,
    "mitigation_timeout": 60,
    "counting_expression": "",
    "requests_to_origin": true
  }
}
```

```json
{
  "description": "Login endpoint: 5 attempts per 5 minutes per IP",
  "expression": "(http.request.uri.path eq \"/api/login\")",
  "action": "challenge",
  "ratelimit": {
    "characteristics": ["ip.src"],
    "period": 300,
    "requests_per_period": 5,
    "mitigation_timeout": 300
  }
}
```

```json
{
  "description": "API key quota: 10,000 requests per hour",
  "expression": "(http.request.uri.path contains \"/api/v2/\")",
  "action": "block",
  "ratelimit": {
    "characteristics": ["http.request.headers[\"x-api-key\"]"],
    "period": 3600,
    "requests_per_period": 10000,
    "mitigation_timeout": 3600
  }
}
```

### Example 12.5: Durable Object Counter (TypeScript)

```typescript
// Durable Object for strongly consistent counting (Cloudflare Workers)
export class RateLimitCounter implements DurableObject {
  private count: number = 0;
  private windowStart: number = 0;
  private readonly windowMs: number = 60000; // 1 minute window

  constructor(
    private readonly state: DurableObjectState,
    private readonly env: Env
  ) {}

  async fetch(request: Request): Promise<Response> {
    const url = new URL(request.url);

    if (url.pathname === '/increment') {
      return this.increment();
    } else if (url.pathname === '/check') {
      return this.check();
    }

    return new Response('Not found', { status: 404 });
  }

  private async increment(): Promise<Response> {
    const now = Date.now();

    // Reset counter if window expired
    if (now - this.windowStart > this.windowMs) {
      this.windowStart = now;
      this.count = 0;
    }

    this.count++;

    // Persist state
    await this.state.storage.put({
      count: this.count,
      windowStart: this.windowStart,
    });

    return Response.json({
      count: this.count,
      remaining: Math.max(0, 100 - this.count),
      resetAt: this.windowStart + this.windowMs,
    });
  }

  private async check(): Promise<Response> {
    // Load state if needed
    const stored = await this.state.storage.get<{
      count: number;
      windowStart: number;
    }>(['count', 'windowStart']);

    if (stored) {
      this.count = stored.count || 0;
      this.windowStart = stored.windowStart || 0;
    }

    const now = Date.now();
    if (now - this.windowStart > this.windowMs) {
      this.count = 0;
    }

    return Response.json({
      count: this.count,
      remaining: Math.max(0, 100 - this.count),
      limited: this.count >= 100,
    });
  }
}

// Worker that uses the Durable Object
export default {
  async fetch(request: Request, env: Env): Promise<Response> {
    const clientIP = request.headers.get('CF-Connecting-IP') || 'unknown';

    // Get Durable Object for this IP
    const id = env.RATE_LIMITER.idFromName(clientIP);
    const rateLimiter = env.RATE_LIMITER.get(id);

    // Check rate limit
    const checkResponse = await rateLimiter.fetch(
      new Request('https://internal/check')
    );
    const { limited, remaining } = await checkResponse.json();

    if (limited) {
      return new Response('Rate limit exceeded', {
        status: 429,
        headers: { 'X-RateLimit-Remaining': '0' },
      });
    }

    // Increment counter
    await rateLimiter.fetch(new Request('https://internal/increment'));

    // Forward to origin
    const response = await fetch(request);
    const newResponse = new Response(response.body, response);
    newResponse.headers.set('X-RateLimit-Remaining', String(remaining - 1));

    return newResponse;
  }
};
```

### Example 12.6: Multi-Origin Aggregation Worker (TypeScript)

```typescript
// Edge aggregation: fetch from multiple origins in parallel (Cloudflare Workers)
interface Env {
  USER_SERVICE: string;
  ORDER_SERVICE: string;
  RECOMMENDATION_SERVICE: string;
}

interface AggregatedResponse {
  user: UserProfile | null;
  recentOrders: Order[] | null;
  recommendations: Product[] | null;
  timing: {
    user: number;
    orders: number;
    recommendations: number;
    total: number;
  };
}

export default {
  async fetch(request: Request, env: Env): Promise<Response> {
    const url = new URL(request.url);
    const userId = url.searchParams.get('userId');

    if (!userId) {
      return Response.json({ error: 'userId required' }, { status: 400 });
    }

    const startTime = performance.now();

    // Fetch from all three services in parallel
    const [userResult, ordersResult, recsResult] = await Promise.allSettled([
      timedFetch(`${env.USER_SERVICE}/users/${userId}`),
      timedFetch(`${env.ORDER_SERVICE}/orders?userId=${userId}&limit=5`),
      timedFetch(`${env.RECOMMENDATION_SERVICE}/recommendations/${userId}`),
    ]);

    // Extract results, handling failures gracefully
    const response: AggregatedResponse = {
      user: userResult.status === 'fulfilled' ? userResult.value.data : null,
      recentOrders: ordersResult.status === 'fulfilled' ? ordersResult.value.data : null,
      recommendations: recsResult.status === 'fulfilled' ? recsResult.value.data : null,
      timing: {
        user: userResult.status === 'fulfilled' ? userResult.value.duration : -1,
        orders: ordersResult.status === 'fulfilled' ? ordersResult.value.duration : -1,
        recommendations: recsResult.status === 'fulfilled' ? recsResult.value.duration : -1,
        total: performance.now() - startTime,
      },
    };

    // Log any failures for monitoring
    if (userResult.status === 'rejected') {
      console.error('User service failed:', userResult.reason);
    }
    if (ordersResult.status === 'rejected') {
      console.error('Order service failed:', ordersResult.reason);
    }
    if (recsResult.status === 'rejected') {
      console.error('Recommendation service failed:', recsResult.reason);
    }

    return Response.json(response, {
      headers: {
        'Cache-Control': 'private, max-age=60',
        'X-Aggregation-Time': String(response.timing.total),
      },
    });
  }
};

async function timedFetch<T>(url: string): Promise<{ data: T; duration: number }> {
  const start = performance.now();
  const response = await fetch(url);

  if (!response.ok) {
    throw new Error(`HTTP ${response.status}: ${response.statusText}`);
  }

  const data = await response.json() as T;
  return { data, duration: performance.now() - start };
}

interface UserProfile {
  id: string;
  name: string;
  email: string;
}

interface Order {
  id: string;
  date: string;
  total: number;
}

interface Product {
  id: string;
  name: string;
  price: number;
}
```

### Example 12.7: Edge Streaming Response (TypeScript)

```typescript
// Edge streaming: SSE response with chunked data (Cloudflare Workers)
interface Env {
  AI_SERVICE: string;
}

export default {
  async fetch(request: Request, env: Env): Promise<Response> {
    const url = new URL(request.url);
    const prompt = url.searchParams.get('prompt');

    if (!prompt) {
      return Response.json({ error: 'prompt required' }, { status: 400 });
    }

    // Create a TransformStream for streaming SSE
    const { readable, writable } = new TransformStream();
    const writer = writable.getWriter();
    const encoder = new TextEncoder();

    // Start streaming in the background
    streamAIResponse(env.AI_SERVICE, prompt, writer, encoder);

    return new Response(readable, {
      headers: {
        'Content-Type': 'text/event-stream',
        'Cache-Control': 'no-cache',
        'Connection': 'keep-alive',
        'Access-Control-Allow-Origin': '*',
      },
    });
  }
};

async function streamAIResponse(
  aiService: string,
  prompt: string,
  writer: WritableStreamDefaultWriter,
  encoder: TextEncoder
): Promise<void> {
  try {
    // Fetch streaming response from AI service
    const response = await fetch(`${aiService}/generate`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ prompt }),
    });

    if (!response.ok || !response.body) {
      await sendSSE(writer, encoder, 'error', { message: 'AI service unavailable' });
      await writer.close();
      return;
    }

    // Stream chunks as SSE events
    const reader = response.body.getReader();
    const decoder = new TextDecoder();
    let tokenCount = 0;

    while (true) {
      const { done, value } = await reader.read();

      if (done) {
        await sendSSE(writer, encoder, 'done', {
          totalTokens: tokenCount,
          timestamp: new Date().toISOString(),
        });
        break;
      }

      const chunk = decoder.decode(value, { stream: true });
      tokenCount += chunk.split(/\s+/).length;

      await sendSSE(writer, encoder, 'token', { content: chunk });
    }
  } catch (error) {
    await sendSSE(writer, encoder, 'error', {
      message: error instanceof Error ? error.message : 'Unknown error',
    });
  } finally {
    await writer.close();
  }
}

async function sendSSE(
  writer: WritableStreamDefaultWriter,
  encoder: TextEncoder,
  event: string,
  data: object
): Promise<void> {
  const message = `event: ${event}\ndata: ${JSON.stringify(data)}\n\n`;
  await writer.write(encoder.encode(message));
}
```

### Example 12.8: Canary Deployment Router (TypeScript)

```typescript
// Canary deployment router with metrics (Cloudflare Workers)
interface Env {
  CANARY_CONFIG: KVNamespace;
  ANALYTICS: AnalyticsEngineDataset;
}

interface CanaryConfig {
  enabled: boolean;
  percentage: number;       // 0-100: percentage of traffic to canary
  canaryOrigin: string;
  stableOrigin: string;
  rollbackThreshold: number; // Error rate threshold for auto-rollback
}

export default {
  async fetch(request: Request, env: Env): Promise<Response> {
    const config = await getCanaryConfig(env);

    if (!config.enabled) {
      return fetchWithMetrics(config.stableOrigin, request, 'stable', env);
    }

    // Determine variant based on stable user assignment
    const variant = getVariant(request, config.percentage);

    const origin = variant === 'canary' ? config.canaryOrigin : config.stableOrigin;
    const response = await fetchWithMetrics(origin, request, variant, env);

    // Add variant header for debugging
    const newResponse = new Response(response.body, response);
    newResponse.headers.set('X-Canary-Variant', variant);

    return newResponse;
  }
};

function getVariant(request: Request, canaryPercentage: number): 'canary' | 'stable' {
  // Use stable identifier for consistent assignment
  const userId = request.headers.get('X-User-ID') ||
                 request.headers.get('CF-Connecting-IP') ||
                 'anonymous';

  // Simple hash-based assignment
  let hash = 0;
  for (let i = 0; i < userId.length; i++) {
    hash = ((hash << 5) - hash) + userId.charCodeAt(i);
    hash = hash & hash; // Convert to 32-bit integer
  }

  const bucket = Math.abs(hash) % 100;
  return bucket < canaryPercentage ? 'canary' : 'stable';
}

async function fetchWithMetrics(
  origin: string,
  request: Request,
  variant: string,
  env: Env
): Promise<Response> {
  const startTime = performance.now();
  let status = 0;
  let error = false;

  try {
    const url = new URL(request.url);
    const response = await fetch(`${origin}${url.pathname}${url.search}`, {
      method: request.method,
      headers: request.headers,
      body: request.body,
    });

    status = response.status;
    error = status >= 500;

    return response;
  } catch (e) {
    error = true;
    throw e;
  } finally {
    const duration = performance.now() - startTime;

    // Record metrics for canary analysis
    env.ANALYTICS.writeDataPoint({
      blobs: [variant, request.url],
      doubles: [duration, status, error ? 1 : 0],
      indexes: [variant],
    });
  }
}

async function getCanaryConfig(env: Env): Promise<CanaryConfig> {
  const cached = await env.CANARY_CONFIG.get('config', { type: 'json' });

  if (cached) {
    return cached as CanaryConfig;
  }

  // Default config if not set
  return {
    enabled: false,
    percentage: 0,
    canaryOrigin: '',
    stableOrigin: 'https://api.example.com',
    rollbackThreshold: 5,
  };
}
```

### Example 12.9: Early Hints Implementation (TypeScript)

```typescript
// Early Hints implementation with dynamic resource detection (Cloudflare Workers)
interface Env {
  HINTS_CACHE: KVNamespace;
}

interface HintConfig {
  resources: ResourceHint[];
  lastUpdated: number;
}

interface ResourceHint {
  url: string;
  as: 'script' | 'style' | 'font' | 'image';
  crossorigin?: boolean;
}

export default {
  async fetch(request: Request, env: Env): Promise<Response> {
    const url = new URL(request.url);

    // Only apply Early Hints to HTML pages
    const acceptHeader = request.headers.get('Accept') || '';
    if (!acceptHeader.includes('text/html')) {
      return fetch(request);
    }

    // Check for cached hints for this path
    const cacheKey = `hints:${url.pathname}`;
    const hintConfig = await env.HINTS_CACHE.get<HintConfig>(cacheKey, { type: 'json' });

    // Send Early Hints if we have cached resource information
    if (hintConfig && hintConfig.resources.length > 0) {
      // Limit to 3 resources for mobile performance
      const isMobile = isMobileDevice(request);
      const resourceLimit = isMobile ? 3 : 6;
      const hints = hintConfig.resources.slice(0, resourceLimit);

      // Build Link header for Early Hints
      const linkHeader = hints.map(hint => {
        let link = `<${hint.url}>; rel=preload; as=${hint.as}`;
        if (hint.crossorigin) {
          link += '; crossorigin';
        }
        return link;
      }).join(', ');

      // Note: Cloudflare automatically sends 103 Early Hints when Link headers
      // are present. This simulates the pattern for documentation.
      console.log(`Sending Early Hints: ${linkHeader}`);
    }

    // Fetch the actual response
    const response = await fetch(request);

    // Learn from response for future hints (if HTML)
    if (response.headers.get('Content-Type')?.includes('text/html')) {
      // Schedule hint learning in background
      scheduleHintLearning(response.clone(), cacheKey, env);
    }

    return response;
  }
};

function isMobileDevice(request: Request): boolean {
  const userAgent = request.headers.get('User-Agent') || '';
  return /Mobile|Android|iPhone|iPad/i.test(userAgent);
}

async function scheduleHintLearning(
  response: Response,
  cacheKey: string,
  env: Env
): Promise<void> {
  try {
    const html = await response.text();
    const resources = extractCriticalResources(html);

    if (resources.length > 0) {
      const config: HintConfig = {
        resources,
        lastUpdated: Date.now(),
      };

      // Cache hints for 1 hour
      await env.HINTS_CACHE.put(cacheKey, JSON.stringify(config), {
        expirationTtl: 3600,
      });
    }
  } catch (error) {
    console.error('Failed to learn hints:', error);
  }
}

function extractCriticalResources(html: string): ResourceHint[] {
  const resources: ResourceHint[] = [];

  // Extract critical CSS (in <head>)
  const cssRegex = /<link[^>]+rel=["']stylesheet["'][^>]+href=["']([^"']+)["'][^>]*>/gi;
  let match;
  while ((match = cssRegex.exec(html)) !== null) {
    resources.push({ url: match[1], as: 'style' });
  }

  // Extract critical JS (with async/defer or in <head>)
  const jsRegex = /<script[^>]+src=["']([^"']+)["'][^>]*>/gi;
  while ((match = jsRegex.exec(html)) !== null) {
    resources.push({ url: match[1], as: 'script' });
  }

  // Extract preloaded fonts
  const fontRegex = /<link[^>]+rel=["']preload["'][^>]+as=["']font["'][^>]+href=["']([^"']+)["'][^>]*>/gi;
  while ((match = fontRegex.exec(html)) !== null) {
    resources.push({ url: match[1], as: 'font', crossorigin: true });
  }

  // Return only first 6 most critical resources
  return resources.slice(0, 6);
}
```

### Example 12.10: Edge ML Classification (TypeScript)

```typescript
// Edge ML classification for request routing (Cloudflare Workers with Workers AI)
interface Env {
  AI: Ai;
  PRIORITY_QUEUE: string;
  STANDARD_QUEUE: string;
}

interface ClassificationResult {
  label: 'high_priority' | 'standard' | 'low_priority';
  confidence: number;
  reasoning: string;
}

export default {
  async fetch(request: Request, env: Env): Promise<Response> {
    // Only classify POST requests with JSON bodies
    if (request.method !== 'POST') {
      return forwardToStandard(request, env);
    }

    try {
      const body = await request.clone().text();
      const classification = await classifyRequest(body, env);

      // Route based on classification
      if (classification.label === 'high_priority' && classification.confidence > 0.8) {
        return forwardToPriority(request, env, classification);
      }

      return forwardToStandard(request, env);
    } catch (error) {
      // On classification failure, use standard path
      console.error('Classification failed:', error);
      return forwardToStandard(request, env);
    }
  }
};

async function classifyRequest(body: string, env: Env): Promise<ClassificationResult> {
  // Use a small, fast model for classification
  const prompt = `Classify this API request as high_priority, standard, or low_priority.
High priority: payment processing, security alerts, user authentication issues
Standard: normal CRUD operations, data queries
Low priority: analytics, batch updates, non-urgent notifications

Request body: ${body.slice(0, 500)}

Respond with JSON: {"label": "...", "confidence": 0.0-1.0, "reasoning": "..."}`;

  const response = await env.AI.run('@cf/meta/llama-3.1-8b-instruct', {
    prompt,
    max_tokens: 100,
  }) as { response: string };

  try {
    // Parse the JSON response
    const jsonMatch = response.response.match(/\{[^}]+\}/);
    if (jsonMatch) {
      return JSON.parse(jsonMatch[0]) as ClassificationResult;
    }
  } catch {
    // Parsing failed
  }

  // Default to standard if parsing fails
  return {
    label: 'standard',
    confidence: 0.5,
    reasoning: 'Classification parsing failed',
  };
}

async function forwardToPriority(
  request: Request,
  env: Env,
  classification: ClassificationResult
): Promise<Response> {
  const headers = new Headers(request.headers);
  headers.set('X-Priority-Classification', classification.label);
  headers.set('X-Priority-Confidence', String(classification.confidence));

  return fetch(env.PRIORITY_QUEUE, {
    method: request.method,
    headers,
    body: request.body,
  });
}

async function forwardToStandard(request: Request, env: Env): Promise<Response> {
  return fetch(env.STANDARD_QUEUE, {
    method: request.method,
    headers: request.headers,
    body: request.body,
  });
}
```

---

## Testing Performance (Chapter 13)

### Example 13.1: Basic Locust Load Test with Realistic Think Time (Python)

This example demonstrates a Locust test with realistic user behavior, including varied think times and weighted task distribution.

```python
# Basic Locust load test with realistic think time
from locust import HttpUser, task, between, constant_pacing
import random


class APIUser(HttpUser):
    """Simulates a user interacting with an e-commerce API."""

    # Wait 2-5 seconds between tasks to simulate real user behavior
    wait_time = between(2, 5)

    def on_start(self):
        """Called when a simulated user starts."""
        # Authenticate and store token for subsequent requests
        response = self.client.post("/api/auth/login", json={
            "username": f"user_{random.randint(1, 10000)}",
            "password": "test_password"
        })
        if response.status_code == 200:
            self.token = response.json().get("access_token")
            self.client.headers["Authorization"] = f"Bearer {self.token}"

    @task(6)  # 60% of traffic - most common action
    def browse_products(self):
        """Browse product listings with pagination."""
        page = random.randint(1, 10)
        self.client.get(f"/api/products?page={page}&limit=20")

    @task(3)  # 30% of traffic
    def view_product_details(self):
        """View a specific product with realistic read time."""
        product_id = random.randint(1, 1000)
        self.client.get(f"/api/products/{product_id}")
        # User reads product details - additional think time
        self._simulate_reading_time()

    @task(1)  # 10% of traffic - less common action
    def add_to_cart(self):
        """Add item to cart - requires form fill simulation."""
        product_id = random.randint(1, 1000)
        quantity = random.randint(1, 3)
        self.client.post("/api/cart/items", json={
            "product_id": product_id,
            "quantity": quantity
        })

    def _simulate_reading_time(self):
        """Simulate additional time spent reading content."""
        # Users spend 5-15 seconds reading product details
        import gevent
        gevent.sleep(random.uniform(5, 15))
```

### Example 13.2: Locust Test with Staged Load Profile (Python)

This example shows how to implement a realistic load test with ramp-up, steady state, and ramp-down phases using Locust's LoadTestShape.

```python
# Locust test with staged load profile
from locust import HttpUser, task, between, LoadTestShape
import random
import math


class StagedLoadShape(LoadTestShape):
    """
    Staged load profile:
    - Ramp up to target over 5 minutes
    - Hold steady for 10 minutes
    - Ramp down over 2 minutes
    """

    stages = [
        {"duration": 60, "users": 50, "spawn_rate": 1},    # Warm up
        {"duration": 300, "users": 200, "spawn_rate": 0.5}, # Ramp to target
        {"duration": 600, "users": 200, "spawn_rate": 0},   # Steady state
        {"duration": 120, "users": 0, "spawn_rate": 2},     # Ramp down
    ]

    def tick(self):
        """Return user count and spawn rate for current time."""
        run_time = self.get_run_time()

        for stage in self.stages:
            if run_time < stage["duration"]:
                try:
                    tick_data = (stage["users"], stage["spawn_rate"])
                    return tick_data
                except Exception:
                    return None
            run_time -= stage["duration"]

        return None  # Test complete


class RealisticAPIUser(HttpUser):
    """User with varied data to avoid cache artifacts."""

    wait_time = between(1, 3)

    # Pre-generated test data for realistic variety
    user_ids = list(range(1, 10001))
    product_ids = list(range(1, 5001))
    search_terms = ["laptop", "phone", "tablet", "headphones", "camera",
                    "watch", "speaker", "keyboard", "mouse", "monitor"]

    @task(4)
    def search_products(self):
        """Search with varied terms to test search performance."""
        term = random.choice(self.search_terms)
        self.client.get(f"/api/products/search?q={term}")

    @task(3)
    def get_user_profile(self):
        """Fetch user profile with varied IDs."""
        user_id = random.choice(self.user_ids)
        self.client.get(f"/api/users/{user_id}/profile")

    @task(2)
    def get_product_reviews(self):
        """Fetch product reviews - potentially slow endpoint."""
        product_id = random.choice(self.product_ids)
        with self.client.get(
            f"/api/products/{product_id}/reviews",
            catch_response=True
        ) as response:
            if response.elapsed.total_seconds() > 2.0:
                response.failure(f"Slow response: {response.elapsed}")

    @task(1)
    def checkout_flow(self):
        """Multi-step checkout - most complex user journey."""
        # Step 1: Get cart
        self.client.get("/api/cart")

        # Step 2: Apply discount (optional)
        if random.random() < 0.3:
            self.client.post("/api/cart/discount", json={
                "code": "SAVE10"
            })

        # Step 3: Calculate shipping
        self.client.post("/api/cart/shipping", json={
            "zip_code": f"{random.randint(10000, 99999)}"
        })

        # Step 4: Submit order
        self.client.post("/api/orders", json={
            "payment_method": "credit_card",
            "shipping_method": "standard"
        })
```

### Example 13.3: Distributed Locust Configuration (Python)

This example shows master and worker configuration for distributed load testing, plus Kubernetes deployment manifests.

```python
# locustfile.py - Shared test definition for distributed testing
from locust import HttpUser, task, between, events
import logging
import os

# Configure logging for distributed debugging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


@events.init.add_listener
def on_locust_init(environment, **kwargs):
    """Log worker initialization for distributed debugging."""
    worker_id = os.environ.get("LOCUST_WORKER_ID", "unknown")
    logger.info(f"Locust worker {worker_id} initialized")


@events.test_start.add_listener
def on_test_start(environment, **kwargs):
    """Called when test starts on each worker."""
    logger.info("Test starting - warming up connections")


@events.test_stop.add_listener
def on_test_stop(environment, **kwargs):
    """Called when test stops - log final statistics."""
    stats = environment.stats
    logger.info(f"Test complete: {stats.total.num_requests} requests, "
                f"{stats.total.num_failures} failures")


class DistributedAPIUser(HttpUser):
    """User class optimized for distributed execution."""

    wait_time = between(1, 2)

    # Connection pooling for efficiency
    pool_manager = None

    def on_start(self):
        """Per-worker initialization."""
        self.worker_id = os.environ.get("LOCUST_WORKER_ID", "0")
        # Use worker ID to partition test data
        self.user_range_start = int(self.worker_id) * 1000
        self.user_range_end = self.user_range_start + 999

    @task
    def api_request(self):
        """Standard API request with worker-partitioned data."""
        import random
        user_id = random.randint(self.user_range_start, self.user_range_end)
        self.client.get(f"/api/users/{user_id}")
```

```yaml
# kubernetes/locust-master.yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: locust-master
  labels:
    app: locust
    role: master
spec:
  replicas: 1
  selector:
    matchLabels:
      app: locust
      role: master
  template:
    metadata:
      labels:
        app: locust
        role: master
    spec:
      containers:
      - name: locust
        image: locustio/locust:2.20.0
        args: ["--master"]
        ports:
        - containerPort: 8089  # Web UI
        - containerPort: 5557  # Worker communication
        env:
        - name: LOCUST_HOST
          value: "https://api.example.com"
        volumeMounts:
        - name: locustfile
          mountPath: /home/locust
      volumes:
      - name: locustfile
        configMap:
          name: locust-script
---
apiVersion: apps/v1
kind: Deployment
metadata:
  name: locust-worker
  labels:
    app: locust
    role: worker
spec:
  replicas: 10  # Scale workers based on target load
  selector:
    matchLabels:
      app: locust
      role: worker
  template:
    metadata:
      labels:
        app: locust
        role: worker
    spec:
      containers:
      - name: locust
        image: locustio/locust:2.20.0
        args: ["--worker", "--master-host=locust-master"]
        env:
        - name: LOCUST_HOST
          value: "https://api.example.com"
        - name: LOCUST_WORKER_ID
          valueFrom:
            fieldRef:
              fieldPath: metadata.name
        resources:
          requests:
            cpu: "500m"
            memory: "512Mi"
          limits:
            cpu: "1000m"
            memory: "1Gi"
        volumeMounts:
        - name: locustfile
          mountPath: /home/locust
      volumes:
      - name: locustfile
        configMap:
          name: locust-script
```

### Example 13.4: CI/CD Pipeline with Locust Quality Gates (Python/YAML)

This example demonstrates integrating Locust into a CI/CD pipeline with automated pass/fail criteria based on SLOs.

```python
# load_test_runner.py - CI/CD integration script
import subprocess
import json
import sys
from dataclasses import dataclass
from typing import List


@dataclass
class SLOThreshold:
    """SLO-based threshold for quality gates."""
    metric: str
    max_value: float
    description: str


# Define SLOs as quality gates
THRESHOLDS = [
    SLOThreshold("p95_response_time", 200, "p95 latency must be under 200ms"),
    SLOThreshold("p99_response_time", 500, "p99 latency must be under 500ms"),
    SLOThreshold("failure_rate", 1.0, "Error rate must be under 1%"),
    SLOThreshold("avg_response_time", 100, "Average latency must be under 100ms"),
]


def run_locust_test(host: str, users: int, duration: str) -> dict:
    """Run Locust test and return statistics."""
    cmd = [
        "locust",
        "-f", "locustfile.py",
        "--host", host,
        "--users", str(users),
        "--spawn-rate", "10",
        "--run-time", duration,
        "--headless",
        "--json",
    ]

    result = subprocess.run(cmd, capture_output=True, text=True)

    if result.returncode != 0:
        print(f"Locust failed: {result.stderr}")
        sys.exit(1)

    # Parse JSON output from Locust
    return json.loads(result.stdout)


def check_thresholds(stats: dict) -> List[str]:
    """Check if test results meet SLO thresholds."""
    failures = []

    # Extract aggregate statistics
    total_stats = stats.get("stats", [{}])[-1]  # Last entry is aggregate

    metrics = {
        "p95_response_time": total_stats.get("response_time_percentile_95", 0),
        "p99_response_time": total_stats.get("response_time_percentile_99", 0),
        "avg_response_time": total_stats.get("avg_response_time", 0),
        "failure_rate": (total_stats.get("num_failures", 0) /
                        max(total_stats.get("num_requests", 1), 1) * 100),
    }

    for threshold in THRESHOLDS:
        actual = metrics.get(threshold.metric, 0)
        if actual > threshold.max_value:
            failures.append(
                f"FAILED: {threshold.description} "
                f"(actual: {actual:.2f}, max: {threshold.max_value})"
            )
        else:
            print(f"PASSED: {threshold.description} "
                  f"(actual: {actual:.2f}, max: {threshold.max_value})")

    return failures


def main():
    """Main entry point for CI/CD integration."""
    import argparse

    parser = argparse.ArgumentParser(description="Run load test with quality gates")
    parser.add_argument("--host", required=True, help="Target API host")
    parser.add_argument("--users", type=int, default=100, help="Number of users")
    parser.add_argument("--duration", default="5m", help="Test duration")
    args = parser.parse_args()

    print(f"Running load test against {args.host}")
    print(f"Users: {args.users}, Duration: {args.duration}")
    print("-" * 50)

    stats = run_locust_test(args.host, args.users, args.duration)

    print("\nChecking SLO thresholds:")
    print("-" * 50)

    failures = check_thresholds(stats)

    if failures:
        print("\n" + "=" * 50)
        print("QUALITY GATE FAILED")
        print("=" * 50)
        for failure in failures:
            print(f"  - {failure}")
        sys.exit(1)
    else:
        print("\n" + "=" * 50)
        print("QUALITY GATE PASSED")
        print("=" * 50)
        sys.exit(0)


if __name__ == "__main__":
    main()
```

```yaml
# .github/workflows/performance-test.yml
name: Performance Test

on:
  push:
    branches: [main]
  pull_request:
    branches: [main]

jobs:
  smoke-test:
    name: Quick Performance Smoke Test
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4

      - name: Set up Python
        uses: actions/setup-python@v5
        with:
          python-version: '3.11'

      - name: Install dependencies
        run: |
          pip install locust requests

      - name: Run smoke test
        run: |
          python load_test_runner.py \
            --host ${{ secrets.STAGING_API_URL }} \
            --users 10 \
            --duration 2m

  load-test:
    name: Full Load Test
    runs-on: ubuntu-latest
    if: github.event_name == 'push' && github.ref == 'refs/heads/main'
    needs: smoke-test
    steps:
      - uses: actions/checkout@v4

      - name: Set up Python
        uses: actions/setup-python@v5
        with:
          python-version: '3.11'

      - name: Install dependencies
        run: |
          pip install locust requests

      - name: Run full load test
        run: |
          python load_test_runner.py \
            --host ${{ secrets.STAGING_API_URL }} \
            --users 100 \
            --duration 10m

      - name: Upload test results
        if: always()
        uses: actions/upload-artifact@v4
        with:
          name: load-test-results
          path: locust_stats.json
```

---

## Putting It All Together (Chapter 14)

### Example A.57: Performance Budget Checker (TypeScript)

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

### Example A.58: Optimization Decision Helper (Python)

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
- 13.1, 13.2, 13.3, 13.4: Testing Performance (Locust)
- A.51, A.52: Synthesis

### Rust
- A.1, A.2, A.3: Performance Fundamentals
- A.7: Observability
- A.11: Network/Connections
- A.16: Caching
- A.20, A.23, A.26, A.28: Database
- A.31: Async Processing
- A.36, A.39: Scaling/Traffic
- 13.3: Advanced Techniques (gRPC)

### TypeScript
- A.1, A.2, A.3, A.4: Performance Fundamentals
- A.5: Observability
- A.12: Network/Connections
- A.14, A.17: Caching
- A.21, A.24, A.27: Database
- A.29: Async Processing
- A.35, A.38, A.40: Scaling/Traffic
- 12.1, 12.2, 12.3, 12.5: Edge Infrastructure
- A.51: Synthesis

### JSON
- 12.4: Edge Infrastructure (Rate Limiting Rules)

### YAML
- A.34: Kubernetes HPA Configuration
- 13.3: Testing Performance (Locust Kubernetes Deployment)
- 13.4: Testing Performance (GitHub Actions Workflow)
