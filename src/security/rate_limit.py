"""Small bounded in-process rate limiter for public authentication endpoints.

Deployments with multiple workers should also apply equivalent limits at the edge.
"""
from __future__ import annotations

import threading
import time
from collections import deque
from dataclasses import dataclass
from math import ceil
from typing import Callable


@dataclass(frozen=True)
class RateLimitDecision:
    allowed: bool
    retry_after_seconds: int = 0


class InMemoryRateLimiter:
    """Sliding-window limiter with bounded client-key storage."""

    def __init__(
        self,
        *,
        max_keys: int = 4096,
        clock: Callable[[], float] = time.monotonic,
    ) -> None:
        if max_keys < 1:
            raise ValueError("max_keys must be positive")
        self.max_keys = max_keys
        self._clock = clock
        self._lock = threading.Lock()
        self._events: dict[str, deque[float]] = {}

    def check(
        self,
        key: str,
        *,
        limit: int,
        window_seconds: float,
    ) -> RateLimitDecision:
        if limit < 1 or window_seconds <= 0:
            raise ValueError("limit and window_seconds must be positive")
        now = self._clock()
        cutoff = now - window_seconds
        with self._lock:
            events = self._events.setdefault(key, deque())
            while events and events[0] <= cutoff:
                events.popleft()
            if len(events) >= limit:
                return RateLimitDecision(
                    allowed=False,
                    retry_after_seconds=max(1, ceil(window_seconds - (now - events[0]))),
                )
            events.append(now)
            if len(self._events) > self.max_keys:
                oldest_key = min(
                    self._events,
                    key=lambda item: self._events[item][-1] if self._events[item] else float("-inf"),
                )
                if oldest_key != key:
                    self._events.pop(oldest_key, None)
            return RateLimitDecision(allowed=True)
