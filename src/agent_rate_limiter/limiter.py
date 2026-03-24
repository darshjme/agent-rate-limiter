"""Core RateLimiter — token bucket + sliding window, zero external deps."""

import threading
import time
from collections import deque
from typing import Optional


class RateLimitTimeout(Exception):
    """Raised when acquire_or_wait exceeds the given timeout."""


class RateLimiter:
    """
    Thread-safe sliding-window rate limiter that tracks both
    requests-per-minute and tokens-per-minute.

    Algorithm: sliding window with deque.  Each successful acquire appends
    a (timestamp, tokens) entry.  On every check, entries older than 60 s
    are evicted so the window reflects the last minute only.
    """

    _WINDOW = 60.0  # seconds

    def __init__(
        self,
        requests_per_minute: int = 60,
        tokens_per_minute: int = 100_000,
    ) -> None:
        if requests_per_minute <= 0:
            raise ValueError("requests_per_minute must be > 0")
        if tokens_per_minute <= 0:
            raise ValueError("tokens_per_minute must be > 0")

        self._rpm = requests_per_minute
        self._tpm = tokens_per_minute
        self._lock = threading.Lock()

        # deque of (timestamp: float, tokens: int)
        self._window: deque = deque()

        # stats
        self._total_acquired: int = 0
        self._total_waited_ms: float = 0.0
        self._total_rejected: int = 0

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _evict(self, now: float) -> None:
        """Remove entries outside the sliding window. Must hold _lock."""
        cutoff = now - self._WINDOW
        while self._window and self._window[0][0] <= cutoff:
            self._window.popleft()

    def _current_requests(self, now: float) -> int:
        self._evict(now)
        return len(self._window)

    def _current_tokens(self, now: float) -> int:
        self._evict(now)
        return sum(t for _, t in self._window)

    def _can_acquire(self, tokens: int, now: float) -> bool:
        reqs = self._current_requests(now)
        toks = self._current_tokens(now)
        return (reqs + 1) <= self._rpm and (toks + tokens) <= self._tpm

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def acquire(self, tokens: int = 1) -> bool:
        """
        Non-blocking attempt to acquire *tokens* from the limiter.

        Returns True on success, False if the request or token limit
        would be exceeded.
        """
        if tokens <= 0:
            raise ValueError("tokens must be > 0")
        with self._lock:
            now = time.monotonic()
            if self._can_acquire(tokens, now):
                self._window.append((now, tokens))
                self._total_acquired += 1
                return True
            self._total_rejected += 1
            return False

    def acquire_or_wait(
        self,
        tokens: int = 1,
        timeout_seconds: float = 30.0,
    ) -> None:
        """
        Block until quota is available, then acquire.

        Raises RateLimitTimeout if *timeout_seconds* elapses before
        quota becomes available.
        """
        if tokens <= 0:
            raise ValueError("tokens must be > 0")

        deadline = time.monotonic() + timeout_seconds
        poll_interval = 0.05  # 50 ms

        start = time.monotonic()

        while True:
            with self._lock:
                now = time.monotonic()
                if now > deadline:
                    raise RateLimitTimeout(
                        f"Could not acquire {tokens} tokens within "
                        f"{timeout_seconds}s"
                    )
                if self._can_acquire(tokens, now):
                    self._window.append((now, tokens))
                    self._total_acquired += 1
                    waited_ms = (time.monotonic() - start) * 1000
                    self._total_waited_ms += waited_ms
                    return
                # Compute how long until the oldest entry expires
                # so we can sleep a smarter amount.
                if self._window:
                    oldest_ts = self._window[0][0]
                    sleep_hint = (oldest_ts + self._WINDOW) - now
                    sleep_time = max(0.001, min(sleep_hint, poll_interval))
                else:
                    sleep_time = poll_interval

            remaining_timeout = deadline - time.monotonic()
            if remaining_timeout <= 0:
                raise RateLimitTimeout(
                    f"Could not acquire {tokens} tokens within "
                    f"{timeout_seconds}s"
                )
            time.sleep(min(sleep_time, remaining_timeout))

    def remaining_requests(self) -> int:
        """Requests available in the current 60-second window."""
        with self._lock:
            used = self._current_requests(time.monotonic())
            return max(0, self._rpm - used)

    def remaining_tokens(self) -> int:
        """Tokens available in the current 60-second window."""
        with self._lock:
            used = self._current_tokens(time.monotonic())
            return max(0, self._tpm - used)

    def reset_in_seconds(self) -> float:
        """
        Seconds until the oldest entry in the window expires,
        freeing at least one request slot.  Returns 0.0 if window empty.
        """
        with self._lock:
            if not self._window:
                return 0.0
            oldest_ts = self._window[0][0]
            remaining = (oldest_ts + self._WINDOW) - time.monotonic()
            return max(0.0, remaining)

    def stats(self) -> dict:
        """Return usage statistics snapshot."""
        with self._lock:
            now = time.monotonic()
            self._evict(now)
            return {
                "total_acquired": self._total_acquired,
                "total_waited_ms": round(self._total_waited_ms, 3),
                "total_rejected": self._total_rejected,
                "current_usage": {
                    "requests_in_window": len(self._window),
                    "tokens_in_window": sum(t for _, t in self._window),
                    "requests_limit": self._rpm,
                    "tokens_limit": self._tpm,
                },
            }

    # ------------------------------------------------------------------
    # Internal helpers exposed for MultiLimiter
    # ------------------------------------------------------------------

    def _release_last(self) -> None:
        """Remove the most recently added entry (for atomic rollback)."""
        if self._window:
            self._window.pop()
            self._total_acquired -= 1

    def __repr__(self) -> str:
        return (
            f"RateLimiter(rpm={self._rpm}, tpm={self._tpm}, "
            f"remaining_req={self.remaining_requests()}, "
            f"remaining_tok={self.remaining_tokens()})"
        )
