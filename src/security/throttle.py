import logging
import time
from collections import defaultdict
from threading import Lock

logger = logging.getLogger(__name__)


class APIRateLimiter:
    def __init__(self, max_requests: int = 10, window_seconds: int = 60):
        self.max_requests = max_requests
        self.window_seconds = window_seconds
        self._buckets: dict[str, list[float]] = defaultdict(list)
        self._lock = Lock()

    def _clean(self, key: str, now: float):
        cutoff = now - self.window_seconds
        self._buckets[key] = [
            t for t in self._buckets[key] if t > cutoff
        ]

    def is_allowed(self, key: str) -> bool:
        now = time.time()
        with self._lock:
            self._clean(key, now)
            if len(self._buckets[key]) >= self.max_requests:
                logger.warning(f" Rate limit exceeded for {key}")
                return False
            self._buckets[key].append(now)
            return True

    def remaining(self, key: str) -> int:
        now = time.time()
        with self._lock:
            self._clean(key, now)
            return max(0, self.max_requests - len(self._buckets[key]))

    def reset(self, key: str):
        with self._lock:
            self._buckets[key].clear()
