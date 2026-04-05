"""Sliding window rate limiter for tool calls."""

from __future__ import annotations

import time
from collections import defaultdict


class RateLimiter:
    """Sliding window rate limiter.

    Tracks call timestamps per tool name and rejects calls
    that exceed the configured rate.
    """

    def __init__(self, default_per_minute: int = 30, destructive_per_minute: int = 5) -> None:
        self._default_limit = default_per_minute
        self._destructive_limit = destructive_per_minute
        self._calls: defaultdict[str, list[float]] = defaultdict(list)

    def check(self, tool_name: str, is_destructive: bool = False) -> bool:
        """Check if a call is allowed under the rate limit.

        Returns True if allowed, False if rate-limited.
        """
        limit = self._destructive_limit if is_destructive else self._default_limit
        now = time.monotonic()
        window_start = now - 60.0

        # Clean old entries
        self._calls[tool_name] = [
            t for t in self._calls[tool_name] if t > window_start
        ]

        return len(self._calls[tool_name]) < limit

    def record(self, tool_name: str) -> None:
        """Record a tool call."""
        self._calls[tool_name].append(time.monotonic())

    def reset(self) -> None:
        """Reset all rate limit counters."""
        self._calls.clear()
