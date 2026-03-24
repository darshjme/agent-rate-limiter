"""RateLimitedCaller — wrap any LLM callable with automatic rate limiting."""

from __future__ import annotations

import functools
from typing import Any, Callable, Optional

from .limiter import RateLimiter


def estimate_tokens(text: str) -> int:
    """
    Rough token estimation: len(text) // 4.

    This is intentionally simple — a proper tokenizer (tiktoken, etc.)
    can be passed as *token_estimator* to RateLimitedCaller instead.
    """
    if not isinstance(text, str):
        return 1
    return max(1, len(text) // 4)


class RateLimitedCaller:
    """
    Wraps a callable (LLM API function) so every invocation first
    acquires rate-limit quota, then calls the wrapped function.

    Parameters
    ----------
    func:
        The LLM callable to wrap (e.g. ``openai.ChatCompletion.create``).
    limiter:
        A :class:`RateLimiter` instance to throttle calls through.
    token_estimator:
        Optional callable ``(str) -> int`` that estimates the token cost
        of a call from the first string argument.  Defaults to
        :func:`estimate_tokens` (``len(text) // 4``).
    timeout_seconds:
        Passed to :meth:`RateLimiter.acquire_or_wait`.  Default 30 s.
    """

    def __init__(
        self,
        func: Callable,
        limiter: RateLimiter,
        token_estimator: Optional[Callable[[str], int]] = None,
        timeout_seconds: float = 30.0,
    ) -> None:
        self._func = func
        self._limiter = limiter
        self._token_estimator = token_estimator or estimate_tokens
        self._timeout = timeout_seconds
        functools.update_wrapper(self, func)

    def __call__(self, *args: Any, **kwargs: Any) -> Any:
        """Acquire quota then call the wrapped function."""
        # Estimate tokens from first positional string arg, or kwargs["prompt"]
        # / kwargs["messages"], falling back to 1 token.
        tokens = self._estimate(*args, **kwargs)
        self._limiter.acquire_or_wait(tokens=tokens, timeout_seconds=self._timeout)
        return self._func(*args, **kwargs)

    def _estimate(self, *args: Any, **kwargs: Any) -> int:
        # Try the first positional string argument
        for arg in args:
            if isinstance(arg, str):
                return self._token_estimator(arg)
        # Try common keyword names
        for key in ("prompt", "content", "text", "message"):
            val = kwargs.get(key)
            if isinstance(val, str):
                return self._token_estimator(val)
        # Messages list (OpenAI-style)
        messages = kwargs.get("messages")
        if isinstance(messages, list):
            combined = " ".join(
                m.get("content", "") for m in messages if isinstance(m, dict)
            )
            return self._token_estimator(combined)
        return 1

    # ------------------------------------------------------------------
    # Decorator factory
    # ------------------------------------------------------------------

    @classmethod
    def wrap(
        cls,
        limiter: RateLimiter,
        token_estimator: Optional[Callable[[str], int]] = None,
        timeout_seconds: float = 30.0,
    ) -> Callable:
        """
        Decorator factory::

            @RateLimitedCaller.wrap(ModelLimits.CLAUDE_SONNET)
            def call_claude(prompt: str) -> str:
                ...
        """

        def decorator(func: Callable) -> "RateLimitedCaller":
            return cls(
                func,
                limiter=limiter,
                token_estimator=token_estimator,
                timeout_seconds=timeout_seconds,
            )

        return decorator

    def __repr__(self) -> str:
        return (
            f"RateLimitedCaller(func={getattr(self._func, '__name__', repr(self._func))!r}, "
            f"limiter={self._limiter!r})"
        )
