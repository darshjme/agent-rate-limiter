# Changelog

All notable changes to **agent-rate-limiter** are documented here.

Format follows [Keep a Changelog](https://keepachangelog.com/en/1.0.0/).
This project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

---

## [Unreleased]

## [0.1.0] — 2026-03-24

### Added
- `RateLimiter` — thread-safe sliding-window limiter (requests + tokens per minute)
- `RateLimitTimeout` — exception raised when `acquire_or_wait` times out
- `ModelLimits` — predefined limits for GPT-4 Turbo, GPT-3.5 Turbo, Claude Opus,
  Claude Sonnet, Gemini Pro
- `RateLimitedCaller` — decorator/wrapper that auto-acquires quota before calling
  any LLM function
- `estimate_tokens(text)` — built-in rough token estimator (`len(text) // 4`)
- `MultiLimiter` — atomically acquire from multiple limiters (per-user + global)
- 22 pytest tests — 100 % pass rate
- Zero external dependencies (uses `threading.Lock` + `time.monotonic`)

[0.1.0]: https://github.com/example/agent-rate-limiter/releases/tag/v0.1.0
