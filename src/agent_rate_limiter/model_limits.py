"""Pre-defined rate limits for common LLM providers."""

from __future__ import annotations

from .limiter import RateLimiter


class ModelLimits:
    """
    Class-level constants for common LLM rate limits.

    Usage::

        limiter = ModelLimits.CLAUDE_SONNET
        limiter.acquire_or_wait(tokens=500)

    Or by name::

        limiter = ModelLimits.get("gpt-4-turbo")
    """

    # OpenAI
    GPT4_TURBO: RateLimiter = RateLimiter(
        requests_per_minute=500,
        tokens_per_minute=800_000,
    )
    GPT35_TURBO: RateLimiter = RateLimiter(
        requests_per_minute=3_500,
        tokens_per_minute=2_000_000,
    )

    # Anthropic
    CLAUDE_OPUS: RateLimiter = RateLimiter(
        requests_per_minute=50,
        tokens_per_minute=40_000,
    )
    CLAUDE_SONNET: RateLimiter = RateLimiter(
        requests_per_minute=1_000,
        tokens_per_minute=160_000,
    )

    # Google
    GEMINI_PRO: RateLimiter = RateLimiter(
        requests_per_minute=300,
        tokens_per_minute=120_000,
    )

    # Name → constant mapping (lowercase, hyphenated)
    _REGISTRY: dict[str, RateLimiter] = {}

    @classmethod
    def _build_registry(cls) -> None:
        cls._REGISTRY = {
            "gpt-4-turbo": cls.GPT4_TURBO,
            "gpt4-turbo": cls.GPT4_TURBO,
            "gpt-3.5-turbo": cls.GPT35_TURBO,
            "gpt35-turbo": cls.GPT35_TURBO,
            "claude-opus": cls.CLAUDE_OPUS,
            "claude-3-opus": cls.CLAUDE_OPUS,
            "claude-sonnet": cls.CLAUDE_SONNET,
            "claude-3-sonnet": cls.CLAUDE_SONNET,
            "gemini-pro": cls.GEMINI_PRO,
        }

    @classmethod
    def get(cls, model_name: str) -> RateLimiter | None:
        """
        Look up a RateLimiter by model name string (case-insensitive).

        Returns None if the model is not registered.
        """
        if not cls._REGISTRY:
            cls._build_registry()
        return cls._REGISTRY.get(model_name.lower().strip())


# Build registry on import
ModelLimits._build_registry()
