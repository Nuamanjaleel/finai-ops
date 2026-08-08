import time
import hashlib
from collections import OrderedDict
from threading import Lock


class TTLCache:
    """
    Thread-safe in-memory LRU cache with TTL (time-to-live).
    - Evicts oldest entries when max_size reached
    - Expires entries after ttl_seconds
    - Tracks hit/miss stats
    """

    def __init__(self, max_size: int = 100, ttl_seconds: int = 3600):
        self.max_size = max_size
        self.ttl = ttl_seconds
        self._cache = OrderedDict()
        self._lock = Lock()
        self.hits = 0
        self.misses = 0

    def _make_key(self, question: str, top_k: int) -> str:
        raw = f"{question.strip().lower()}::{top_k}"
        return hashlib.sha256(raw.encode()).hexdigest()

    def get(self, question: str, top_k: int):
        key = self._make_key(question, top_k)
        with self._lock:
            if key not in self._cache:
                self.misses += 1
                return None

            entry = self._cache[key]
            if time.time() - entry["timestamp"] > self.ttl:
                # Expired
                del self._cache[key]
                self.misses += 1
                return None

            # Move to end (LRU: most recently used)
            self._cache.move_to_end(key)
            self.hits += 1
            return entry["value"]

    def set(self, question: str, top_k: int, value: dict):
        key = self._make_key(question, top_k)
        with self._lock:
            if key in self._cache:
                self._cache.move_to_end(key)
            self._cache[key] = {"value": value, "timestamp": time.time()}

            # Evict oldest if over capacity
            if len(self._cache) > self.max_size:
                self._cache.popitem(last=False)

    def stats(self):
        with self._lock:
            total = self.hits + self.misses
            hit_rate = round(self.hits / total * 100, 2) if total > 0 else 0.0
            return {
                "size": len(self._cache),
                "max_size": self.max_size,
                "ttl_seconds": self.ttl,
                "hits": self.hits,
                "misses": self.misses,
                "hit_rate_percent": hit_rate,
            }

    def clear(self):
        with self._lock:
            self._cache.clear()
            self.hits = 0
            self.misses = 0


# Global singleton cache instance
query_cache = TTLCache(max_size=100, ttl_seconds=3600)
