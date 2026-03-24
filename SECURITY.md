# Security Policy

## Supported versions

| Version | Supported |
|---------|-----------|
| 0.1.x   | ✅ Yes    |

## Reporting a vulnerability

**Do not open a public GitHub issue for security vulnerabilities.**

Email: security@example.com

Please include:
- A description of the vulnerability
- Steps to reproduce
- Impact assessment
- Any suggested remediation

We aim to respond within **72 hours** and release a patch within **14 days**
for confirmed vulnerabilities.

## Scope

This library is a pure in-process rate limiter with no network access,
no file I/O, and no authentication.  The main security-relevant concerns
are:

1. **Thread safety** — incorrect locking could allow quota bypass.
   All shared state is protected by `threading.Lock`.

2. **Denial of Service via busy-wait** — `acquire_or_wait` sleeps
   between polls and respects a caller-supplied timeout to avoid
   infinite blocking.

3. **Integer overflow** — token counts use Python native integers
   (arbitrary precision), so overflow is not a concern.
