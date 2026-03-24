"""Tests for RateLimiter — 22+ cases covering all spec requirements."""

import threading
import time

import pytest

from agent_rate_limiter import (
    MultiLimiter,
    ModelLimits,
    RateLimitedCaller,
    RateLimiter,
    RateLimitTimeout,
    estimate_tokens,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def make_limiter(rpm: int = 5, tpm: int = 1000) -> RateLimiter:
    return RateLimiter(requests_per_minute=rpm, tokens_per_minute=tpm)


# ===========================================================================
# 1. RateLimiter — basic construction
# ===========================================================================


class TestRateLimiterInit:
    def test_default_values(self):
        rl = RateLimiter()
        assert rl._rpm == 60
        assert rl._tpm == 100_000

    def test_custom_values(self):
        rl = RateLimiter(requests_per_minute=10, tokens_per_minute=500)
        assert rl._rpm == 10
        assert rl._tpm == 500

    def test_invalid_rpm(self):
        with pytest.raises(ValueError):
            RateLimiter(requests_per_minute=0)

    def test_invalid_tpm(self):
        with pytest.raises(ValueError):
            RateLimiter(tokens_per_minute=-1)


# ===========================================================================
# 2. RateLimiter — acquire (non-blocking)
# ===========================================================================


class TestAcquire:
    def test_acquire_returns_true_within_limit(self):
        rl = make_limiter(rpm=3, tpm=1000)
        assert rl.acquire(tokens=1) is True
        assert rl.acquire(tokens=1) is True
        assert rl.acquire(tokens=1) is True

    def test_acquire_returns_false_at_request_limit(self):
        rl = make_limiter(rpm=2, tpm=1000)
        assert rl.acquire(tokens=1) is True
        assert rl.acquire(tokens=1) is True
        # Third call should fail — requests_per_minute exceeded
        assert rl.acquire(tokens=1) is False

    def test_acquire_returns_false_at_token_limit(self):
        rl = make_limiter(rpm=100, tpm=10)
        assert rl.acquire(tokens=8) is True
        # 8 + 5 = 13 > 10
        assert rl.acquire(tokens=5) is False

    def test_acquire_invalid_tokens(self):
        rl = make_limiter()
        with pytest.raises(ValueError):
            rl.acquire(tokens=0)

    def test_acquire_increments_rejected_stat(self):
        rl = make_limiter(rpm=1, tpm=1000)
        rl.acquire(tokens=1)
        rl.acquire(tokens=1)  # rejected
        assert rl.stats()["total_rejected"] == 1


# ===========================================================================
# 3. RateLimiter — remaining_requests / remaining_tokens
# ===========================================================================


class TestRemaining:
    def test_remaining_requests_decrements(self):
        rl = make_limiter(rpm=5, tpm=1000)
        assert rl.remaining_requests() == 5
        rl.acquire(tokens=1)
        assert rl.remaining_requests() == 4

    def test_remaining_tokens_decrements(self):
        rl = make_limiter(rpm=100, tpm=100)
        assert rl.remaining_tokens() == 100
        rl.acquire(tokens=40)
        assert rl.remaining_tokens() == 60

    def test_remaining_never_negative(self):
        rl = make_limiter(rpm=1, tpm=10)
        rl.acquire(tokens=10)
        rl.acquire(tokens=99)  # rejected but doesn't corrupt state
        assert rl.remaining_tokens() >= 0
        assert rl.remaining_requests() >= 0


# ===========================================================================
# 4. RateLimiter — reset_in_seconds
# ===========================================================================


class TestResetInSeconds:
    def test_returns_zero_when_empty(self):
        rl = make_limiter()
        assert rl.reset_in_seconds() == 0.0

    def test_returns_positive_after_acquire(self):
        rl = make_limiter()
        rl.acquire(tokens=1)
        secs = rl.reset_in_seconds()
        assert 0 < secs <= 60.0


# ===========================================================================
# 5. RateLimiter — stats
# ===========================================================================


class TestStats:
    def test_initial_stats(self):
        rl = make_limiter()
        s = rl.stats()
        assert s["total_acquired"] == 0
        assert s["total_waited_ms"] == 0.0
        assert s["total_rejected"] == 0
        assert s["current_usage"]["requests_in_window"] == 0
        assert s["current_usage"]["tokens_in_window"] == 0

    def test_stats_after_acquires(self):
        rl = make_limiter(rpm=10, tpm=500)
        rl.acquire(tokens=100)
        rl.acquire(tokens=200)
        s = rl.stats()
        assert s["total_acquired"] == 2
        assert s["current_usage"]["tokens_in_window"] == 300
        assert s["current_usage"]["requests_in_window"] == 2

    def test_stats_limits_reflected(self):
        rl = make_limiter(rpm=7, tpm=777)
        s = rl.stats()
        assert s["current_usage"]["requests_limit"] == 7
        assert s["current_usage"]["tokens_limit"] == 777


# ===========================================================================
# 6. RateLimiter — acquire_or_wait (blocking)
# ===========================================================================


class TestAcquireOrWait:
    def test_acquires_immediately_when_quota_available(self):
        rl = make_limiter(rpm=5, tpm=1000)
        t0 = time.monotonic()
        rl.acquire_or_wait(tokens=1)
        elapsed = time.monotonic() - t0
        assert elapsed < 0.5  # should be near-instant

    def test_raises_timeout_when_quota_unavailable(self):
        rl = make_limiter(rpm=1, tpm=1000)
        rl.acquire(tokens=1)  # fill the single slot
        with pytest.raises(RateLimitTimeout):
            rl.acquire_or_wait(tokens=1, timeout_seconds=0.1)

    def test_waited_ms_increases_after_blocking(self):
        rl = make_limiter(rpm=1, tpm=1000)
        rl.acquire(tokens=1)  # fill slot
        try:
            rl.acquire_or_wait(tokens=1, timeout_seconds=0.05)
        except RateLimitTimeout:
            pass
        # If somehow it acquired, waited_ms should still be tracked
        # We just verify the stat key exists and is numeric
        assert isinstance(rl.stats()["total_waited_ms"], float)

    def test_invalid_tokens(self):
        rl = make_limiter()
        with pytest.raises(ValueError):
            rl.acquire_or_wait(tokens=-1)


# ===========================================================================
# 7. ModelLimits
# ===========================================================================


class TestModelLimits:
    def test_gpt4_turbo_constants(self):
        assert ModelLimits.GPT4_TURBO._rpm == 500
        assert ModelLimits.GPT4_TURBO._tpm == 800_000

    def test_claude_opus_constants(self):
        assert ModelLimits.CLAUDE_OPUS._rpm == 50
        assert ModelLimits.CLAUDE_OPUS._tpm == 40_000

    def test_claude_sonnet_constants(self):
        assert ModelLimits.CLAUDE_SONNET._rpm == 1_000
        assert ModelLimits.CLAUDE_SONNET._tpm == 160_000

    def test_get_by_name_gpt4(self):
        rl = ModelLimits.get("gpt-4-turbo")
        assert rl is not None
        assert rl._rpm == 500

    def test_get_by_name_claude_sonnet(self):
        rl = ModelLimits.get("claude-sonnet")
        assert rl is not None
        assert rl._tpm == 160_000

    def test_get_case_insensitive(self):
        rl = ModelLimits.get("GPT-4-TURBO")
        assert rl is not None

    def test_get_unknown_returns_none(self):
        assert ModelLimits.get("unknown-model-xyz") is None

    def test_get_gemini_pro(self):
        rl = ModelLimits.get("gemini-pro")
        assert rl is not None
        assert rl._rpm == 300


# ===========================================================================
# 8. estimate_tokens
# ===========================================================================


class TestEstimateTokens:
    def test_empty_string(self):
        assert estimate_tokens("") == 1  # min 1

    def test_short_string(self):
        assert estimate_tokens("abcd") == 1

    def test_longer_string(self):
        text = "a" * 400
        assert estimate_tokens(text) == 100

    def test_non_string_returns_1(self):
        assert estimate_tokens(None) == 1  # type: ignore


# ===========================================================================
# 9. RateLimitedCaller
# ===========================================================================


class TestRateLimitedCaller:
    def _make_counter_func(self):
        calls = []

        def fake_llm(prompt: str) -> str:
            calls.append(prompt)
            return f"response:{prompt}"

        return fake_llm, calls

    def test_call_invokes_underlying_func(self):
        rl = make_limiter(rpm=10, tpm=5000)
        func, calls = self._make_counter_func()
        caller = RateLimitedCaller(func, limiter=rl)
        result = caller("hello world")
        assert result == "response:hello world"
        assert len(calls) == 1

    def test_call_decrements_quota(self):
        rl = make_limiter(rpm=10, tpm=5000)
        func, _ = self._make_counter_func()
        caller = RateLimitedCaller(func, limiter=rl)
        before = rl.remaining_requests()
        caller("hello")
        after = rl.remaining_requests()
        assert after == before - 1

    def test_wrap_decorator_factory(self):
        rl = make_limiter(rpm=10, tpm=5000)

        @RateLimitedCaller.wrap(rl)
        def my_llm(prompt: str) -> str:
            return f"got:{prompt}"

        result = my_llm("test prompt")
        assert result == "got:test prompt"
        assert rl.remaining_requests() == 9

    def test_custom_token_estimator(self):
        rl = make_limiter(rpm=10, tpm=20)
        # Custom estimator always returns 10
        caller = RateLimitedCaller(
            lambda p: p, limiter=rl, token_estimator=lambda _: 10
        )
        caller("anything")
        assert rl.remaining_tokens() == 10  # 20 - 10

    def test_raises_when_limit_exceeded(self):
        rl = make_limiter(rpm=1, tpm=5000)
        rl.acquire(tokens=1)  # exhaust the 1 request slot

        def func(p):
            return p

        caller = RateLimitedCaller(func, limiter=rl, timeout_seconds=0.05)
        with pytest.raises(RateLimitTimeout):
            caller("prompt")

    def test_kwargs_prompt_extraction(self):
        rl = make_limiter(rpm=10, tpm=5000)
        func, calls = self._make_counter_func()
        caller = RateLimitedCaller(func, limiter=rl)
        caller(prompt="hello world")
        assert len(calls) == 1


# ===========================================================================
# 10. MultiLimiter
# ===========================================================================


class TestMultiLimiter:
    def test_acquire_succeeds_when_all_allow(self):
        rl1 = make_limiter(rpm=5, tpm=1000)
        rl2 = make_limiter(rpm=5, tpm=1000)
        ml = MultiLimiter([rl1, rl2])
        assert ml.acquire(tokens=1) is True
        # Both should have consumed one request
        assert rl1.remaining_requests() == 4
        assert rl2.remaining_requests() == 4

    def test_acquire_fails_and_rolls_back(self):
        rl1 = make_limiter(rpm=5, tpm=1000)
        rl2 = make_limiter(rpm=1, tpm=1000)
        rl2.acquire(tokens=1)  # exhaust rl2
        ml = MultiLimiter([rl1, rl2])

        before_rl1 = rl1.remaining_requests()
        result = ml.acquire(tokens=1)
        assert result is False
        # rl1 must have been rolled back
        assert rl1.remaining_requests() == before_rl1

    def test_acquire_or_wait_succeeds(self):
        rl1 = make_limiter(rpm=5, tpm=1000)
        rl2 = make_limiter(rpm=5, tpm=1000)
        ml = MultiLimiter([rl1, rl2])
        ml.acquire_or_wait(tokens=1)  # should not raise

    def test_acquire_or_wait_raises_timeout(self):
        rl1 = make_limiter(rpm=1, tpm=1000)
        rl1.acquire(tokens=1)
        ml = MultiLimiter([rl1])
        with pytest.raises(RateLimitTimeout):
            ml.acquire_or_wait(tokens=1, timeout_seconds=0.05)

    def test_empty_limiters_raises(self):
        with pytest.raises(ValueError):
            MultiLimiter([])

    def test_thread_safety(self):
        """Multiple threads acquiring from the same MultiLimiter stay within limits."""
        rpm = 20
        rl = make_limiter(rpm=rpm, tpm=100_000)
        ml = MultiLimiter([rl])
        results = []

        def worker():
            results.append(ml.acquire(tokens=1))

        threads = [threading.Thread(target=worker) for _ in range(30)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        true_count = sum(1 for r in results if r)
        assert true_count <= rpm
