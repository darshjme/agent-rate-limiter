"""MultiLimiter — atomically acquire from multiple RateLimiters."""

from __future__ import annotations

import time
from typing import List

from .limiter import RateLimiter, RateLimitTimeout


class MultiLimiter:
    """
    Applies *all* provided :class:`RateLimiter` instances simultaneously.

    Useful for layering limits, e.g. a per-user limiter **and** a global
    limiter must both grant quota before a call proceeds.

    Atomicity
    ---------
    :meth:`acquire` acquires each limiter in order.  If any limiter
    rejects, all previously acquired limiters are rolled back via
    ``_release_last()``.
    """

    def __init__(self, limiters: List[RateLimiter]) -> None:
        if not limiters:
            raise ValueError("limiters must be a non-empty list")
        self._limiters = list(limiters)

    def acquire(self, tokens: int = 1) -> bool:
        """
        Attempt to acquire *tokens* from ALL limiters atomically.

        Returns True only if every limiter grants the request.
        If any limiter rejects, previously acquired limiters are released
        and False is returned.
        """
        acquired: list[RateLimiter] = []
        for limiter in self._limiters:
            if limiter.acquire(tokens=tokens):
                acquired.append(limiter)
            else:
                # Rollback
                for prev in acquired:
                    with prev._lock:
                        prev._release_last()
                return False
        return True

    def acquire_or_wait(
        self,
        tokens: int = 1,
        timeout_seconds: float = 30.0,
    ) -> None:
        """
        Block until ALL limiters can be acquired simultaneously.

        Uses a polling loop with the same 50 ms cadence as
        :meth:`RateLimiter.acquire_or_wait`.

        Raises :exc:`RateLimitTimeout` if the deadline passes.
        """
        if tokens <= 0:
            raise ValueError("tokens must be > 0")
        deadline = time.monotonic() + timeout_seconds
        poll_interval = 0.05

        while True:
            if self.acquire(tokens=tokens):
                return
            remaining = deadline - time.monotonic()
            if remaining <= 0:
                raise RateLimitTimeout(
                    f"MultiLimiter could not acquire {tokens} tokens within "
                    f"{timeout_seconds}s"
                )
            time.sleep(min(poll_interval, remaining))

    def __repr__(self) -> str:
        return f"MultiLimiter(limiters={self._limiters!r})"
