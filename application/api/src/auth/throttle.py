"""Sliding-window failure counter used to slow down password guessing.

In memory and per process: each replica counts on its own. The cluster-wide limit
belongs in the WAF (rate-based rule). The table size is capped so that an attacker
sending random keys cannot use this component to exhaust memory.
"""
import math
import threading
import time
from collections import deque


class FailureThrottle:
    def __init__(self, max_failures, window_seconds, max_keys=10_000, clock=time.monotonic):
        self.max_failures = max_failures
        self.window = window_seconds
        self.max_keys = max_keys
        self._clock = clock
        self._failures = {}
        self._lock = threading.Lock()

    def __len__(self):
        with self._lock:
            return len(self._failures)

    def _live_events(self, key, now):
        events = self._failures.get(key)
        if events is None:
            return None
        while events and now - events[0] >= self.window:
            events.popleft()
        if not events:
            del self._failures[key]
            return None
        return events

    def _make_room(self, now):
        for key in list(self._failures):
            self._live_events(key, now)
        while len(self._failures) >= self.max_keys:
            del self._failures[next(iter(self._failures))]

    def retry_after(self, key) -> int:
        """Seconds until another attempt is allowed; 0 when allowed now."""
        with self._lock:
            now = self._clock()
            events = self._live_events(key, now)
            if events is None or len(events) < self.max_failures:
                return 0
            return max(1, math.ceil(events[0] + self.window - now))

    def record_failure(self, key) -> None:
        with self._lock:
            now = self._clock()
            events = self._live_events(key, now)
            if events is None:
                if len(self._failures) >= self.max_keys:
                    self._make_room(now)
                events = self._failures.setdefault(key, deque())
            events.append(now)

    def reset(self, key) -> None:
        with self._lock:
            self._failures.pop(key, None)
