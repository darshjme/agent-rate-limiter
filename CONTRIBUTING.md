# Contributing to agent-rate-limiter

Thank you for your interest in contributing!

## Getting started

```bash
git clone https://github.com/example/agent-rate-limiter.git
cd agent-rate-limiter
pip install -e ".[dev]"
```

## Running tests

```bash
python -m pytest tests/ -v --cov=agent_rate_limiter
```

All tests must pass and coverage should remain ≥ 95 %.

## Coding standards

- Python ≥ 3.10 syntax only
- Zero external runtime dependencies — use only the standard library
- Type annotations on all public methods
- Docstrings on all public classes and functions
- `threading.Lock` for synchronisation; `time.monotonic()` for timing

## Pull request checklist

- [ ] Tests added / updated for every changed behaviour
- [ ] `CHANGELOG.md` updated under `[Unreleased]`
- [ ] `pyproject.toml` version bumped if releasing
- [ ] `README.md` examples still accurate

## Reporting bugs

Open a GitHub Issue with:
1. Python version and OS
2. Minimal reproducible example
3. Expected vs actual behaviour
