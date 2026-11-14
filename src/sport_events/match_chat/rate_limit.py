"""In-memory sliding-window rate limiter keyed by an opaque client identifier."""

import time
from collections import deque
from collections.abc import Callable


class SlidingWindowRateLimiter:
    """Allow at most `max_requests` per key in any `window_seconds` interval.

    State lives in this process only, so the effective limit is per worker process.
    """

    def __init__(
        self,
        max_requests: int,
        window_seconds: float,
        clock: Callable[[], float] = time.monotonic,
        max_keys: int = 10_000,
    ) -> None:
        if max_requests < 1 or window_seconds <= 0 or max_keys < 1:
            raise ValueError("limits must be positive")
        self._max_requests = max_requests
        self._window = window_seconds
        self._clock = clock
        self._max_keys = max_keys
        self._hits: dict[str, deque[float]] = {}

    def check(self, key: str) -> float | None:
        """Record a request and return None, or return seconds to wait when over the limit."""
        now = self._clock()
        cutoff = now - self._window
        hits = self._hits.get(key)
        if hits is None:
            if len(self._hits) >= self._max_keys:
                self._drop_idle_keys(cutoff)
            if len(self._hits) >= self._max_keys:
                # Fail closed instead of growing without bound.
                return self._window
            hits = self._hits[key] = deque()
        while hits and hits[0] <= cutoff:
            hits.popleft()
        if len(hits) >= self._max_requests:
            return hits[0] + self._window - now
        hits.append(now)
        return None

    def _drop_idle_keys(self, cutoff: float) -> None:
        idle = [key for key, hits in self._hits.items() if not hits or hits[-1] <= cutoff]
        for key in idle:
            del self._hits[key]
