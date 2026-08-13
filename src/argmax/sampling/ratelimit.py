"""Token-bucket rate limiter and retry policy.

Concurrency is configured per model, not global: one model's 429s should not
throttle another's throughput.
"""

from __future__ import annotations

import random
import threading
import time
from dataclasses import dataclass


class TokenBucket:
    """Requests per second with a burst allowance."""

    def __init__(self, rate_per_sec: float, burst: int | None = None) -> None:
        self.rate = rate_per_sec
        self.capacity = burst if burst is not None else max(1, int(rate_per_sec))
        self._tokens = float(self.capacity)
        self._last = time.monotonic()
        self._lock = threading.Lock()

    def acquire(self) -> None:
        while True:
            with self._lock:
                now = time.monotonic()
                self._tokens = min(
                    self.capacity, self._tokens + (now - self._last) * self.rate
                )
                self._last = now
                if self._tokens >= 1.0:
                    self._tokens -= 1.0
                    return
                deficit = (1.0 - self._tokens) / self.rate
            time.sleep(deficit)


@dataclass(frozen=True)
class RetryPolicy:
    """Exponential backoff with jitter on 429 and 5xx, honouring Retry-After.

    Every attempt increments `attempt_count` on the eventual record. A sample
    that exhausts retries is written as an `api_failure` record so the gap is
    visible rather than inferred from a count mismatch.
    """

    max_attempts: int = 5
    base_delay_s: float = 1.0
    max_delay_s: float = 60.0
    retry_on_status: frozenset[int] = frozenset({429, 500, 502, 503, 504})

    def should_retry(self, status: int | None, attempt: int) -> bool:
        if attempt >= self.max_attempts:
            return False
        if status is None:  # transport error
            return True
        return status in self.retry_on_status

    def delay_s(self, attempt: int, retry_after: float | None = None) -> float:
        if retry_after is not None:
            return min(retry_after, self.max_delay_s)
        backoff = min(self.base_delay_s * (2 ** (attempt - 1)), self.max_delay_s)
        return backoff * (0.5 + random.random() / 2)  # full-ish jitter
