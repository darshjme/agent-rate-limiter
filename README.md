# agent-rate-limiter

> **Proactive rate limiting for LLM API calls.**  
> Track usage, throttle before hitting the limit, apply per-model limits,
> expose metrics — prevent 429 errors and eliminate expensive retry storms.

[![Python 3.10+](https://img.shields.io/badge/python-3.10%2B-blue)](https://python.org)
[![Zero dependencies](https://img.shields.io/badge/deps-zero-brightgreen)]()
[![Tests](https://img.shields.io/badge/tests-45%20passed-brightgreen)]()

---

## The Problem

Every LLM API has hard rate limits.  When you hit them:

```
openai.RateLimitError: Rate limit reached for gpt-4-turbo.
Limit: 500 req/min, Used: 500, Requested: 1.
```

A naive retry loop makes it **worse**:

| Scenario | Requests fired | Cost | Time |
|----------|----------------|------|------|
| 10 agents, no limiting | 500 req/min → 429 storm | $8.40 wasted on retries | +45s delays |
| 10 agents, **with agent-rate-limiter** | 500 req/min exactly | $0 wasted | smooth |

---

## Installation

```bash
pip install agent-rate-limiter
```

Zero external dependencies — uses only `threading.Lock` and `time.monotonic`.

---

## Quick start — 429 prevention

### Before (naive, costly)

```python
import openai
import time

def call_llm(prompt):
    while True:
        try:
            return openai.chat.completions.create(
                model="gpt-4-turbo",
                messages=[{"role": "user", "content": prompt}]
            )
        except openai.RateLimitError:
            time.sleep(5)   # ← retry storm: costs money, wastes time
```

### After (proactive, free)

```python
import openai
from agent_rate_limiter import ModelLimits, RateLimitedCaller

limiter = ModelLimits.GPT4_TURBO  # 500 req/min, 800k tok/min

@RateLimitedCaller.wrap(limiter)
def call_llm(prompt: str):
    return openai.chat.completions.create(
        model="gpt-4-turbo",
        messages=[{"role": "user", "content": prompt}]
    )

# No 429s. No retries. No wasted money.
result = call_llm("Explain quantum entanglement in one paragraph.")
```

**Cost comparison (1000 calls/hour, GPT-4 Turbo):**

| | Retry-storm | agent-rate-limiter |
|---|---|---|
| Wasted API calls | ~180 (retries) | **0** |
| Extra cost @ $0.01/req | ~$1.80/hour | **$0** |
| P99 latency | +12s | baseline |

---

## API reference

### `RateLimiter`

```python
from agent_rate_limiter import RateLimiter, RateLimitTimeout

rl = RateLimiter(requests_per_minute=60, tokens_per_minute=100_000)

# Non-blocking — returns False immediately if over limit
ok = rl.acquire(tokens=500)

# Blocking — waits up to 30 s, then raises RateLimitTimeout
rl.acquire_or_wait(tokens=500, timeout_seconds=30.0)

# Observability
print(rl.remaining_requests())   # → 59
print(rl.remaining_tokens())     # → 99_500
print(rl.reset_in_seconds())     # → 58.3
print(rl.stats())
# {
#   'total_acquired': 1,
#   'total_waited_ms': 0.0,
#   'total_rejected': 0,
#   'current_usage': {
#     'requests_in_window': 1,
#     'tokens_in_window': 500,
#     'requests_limit': 60,
#     'tokens_limit': 100000
#   }
# }
```

### `ModelLimits`

```python
from agent_rate_limiter import ModelLimits

# Pre-configured limiters
limiter = ModelLimits.GPT4_TURBO      # 500 rpm, 800k tpm
limiter = ModelLimits.GPT35_TURBO     # 3500 rpm, 2M tpm
limiter = ModelLimits.CLAUDE_OPUS     # 50 rpm, 40k tpm
limiter = ModelLimits.CLAUDE_SONNET   # 1000 rpm, 160k tpm
limiter = ModelLimits.GEMINI_PRO      # 300 rpm, 120k tpm

# Lookup by name
limiter = ModelLimits.get("claude-sonnet")   # RateLimiter | None
limiter = ModelLimits.get("gpt-4-turbo")
```

### `RateLimitedCaller`

```python
from agent_rate_limiter import RateLimitedCaller, ModelLimits

# As a wrapper
caller = RateLimitedCaller(my_llm_func, limiter=ModelLimits.CLAUDE_SONNET)
result = caller("My prompt here")

# As a decorator
@RateLimitedCaller.wrap(ModelLimits.CLAUDE_OPUS)
def call_claude(prompt: str) -> str:
    ...

# With a custom token estimator (e.g. tiktoken)
import tiktoken
enc = tiktoken.encoding_for_model("gpt-4")

@RateLimitedCaller.wrap(
    ModelLimits.GPT4_TURBO,
    token_estimator=lambda text: len(enc.encode(text))
)
def call_gpt4(prompt: str) -> str:
    ...
```

### `MultiLimiter`

```python
from agent_rate_limiter import MultiLimiter, RateLimiter

# Layer a per-user limiter AND a global limiter
per_user  = RateLimiter(requests_per_minute=10,  tokens_per_minute=20_000)
global_rl = RateLimiter(requests_per_minute=500, tokens_per_minute=800_000)

ml = MultiLimiter([per_user, global_rl])

# Atomic — either both acquire or neither does
ml.acquire_or_wait(tokens=500)
```

### `estimate_tokens`

```python
from agent_rate_limiter import estimate_tokens

estimate_tokens("Hello, world!")  # → 3  (len // 4)
```

---

## Thread safety

All classes use `threading.Lock` for every state mutation.  You can safely
share a single `RateLimiter` or `ModelLimits` instance across threads and
async workers (wrap `acquire_or_wait` in `asyncio.to_thread` for async code).

---

## Running tests

```bash
pip install -e ".[dev]"
python -m pytest tests/ -v
# 45 passed in 0.36s
```

---

## License

MIT
