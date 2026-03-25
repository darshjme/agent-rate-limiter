<div align="center">

<img src="assets/niyantrana-hero.png" alt="नियंत्रण — niyantrana by Darshankumar Joshi" width="100%" />

# 🌊 नियंत्रण
## `niyantrana`

> *Yoga Sutras of Patanjali*

### Control — restraint of cosmic flow

**Rate limiting for LLM API calls. Token bucket, sliding window, per-model limits. Zero dependencies.**

[![Python](https://img.shields.io/badge/Python-3.8%2B-blue?style=flat-square&logo=python)](https://python.org)
[![Zero Dependencies](https://img.shields.io/badge/Dependencies-Zero-brightgreen?style=flat-square)](https://github.com/darshjme/niyantrana)
[![Vedic Arsenal](https://img.shields.io/badge/Vedic%20Arsenal-100%20libs-blue?style=flat-square)](https://github.com/darshjme/arsenal)
[![License](https://img.shields.io/badge/License-MIT-blue?style=flat-square)](LICENSE)

*Formerly `agent-rate-limiter` — Part of the [**Vedic Arsenal**](https://github.com/darshjme/arsenal): 100 production-grade Python libraries for LLM agents, each named from the Vedas, Puranas, and Mahakavyas.*

</div>

---

## The Vedic Principle

The ancient *Niyantrana* principle from Yoga Sutras of Patanjali finds its modern expression in this library.

Just as the Vedic sages understood that every phenomenon in the universe follows deep patterns — patterns of creation, maintenance, and dissolution — `niyantrana` applies this wisdom to LLM agent engineering.

The concept of *नियंत्रण* (Control — restraint of cosmic flow) speaks directly to the technical problem this library solves. When the sages codified this principle in Yoga Sutras of Patanjali, they were describing not just a spiritual truth but a computational truth that would take humanity millennia to rediscover in silicon.

This is not coincidence. The universe has one nature. The Vedas described it first.

---

## How It Works

```mermaid
flowchart LR
    A[Input] --> B[niyantrana]
    B --> C{Process}
    C -- Success --> D[Output]
    C -- Error --> E[Handle]
    E --> B
    style B fill:#6b21a8,color:#fff
```

---

## Installation

```bash
pip install niyantrana
```

Or from source:
```bash
git clone https://github.com/darshjme/niyantrana.git
cd niyantrana && pip install -e .
```

## Quick Start

```python
from niyantrana import *

# See examples/ for full usage
```

---

## The Vedic Arsenal

`niyantrana` is one of 100 libraries in **[darshjme/arsenal](https://github.com/darshjme/arsenal)** — each named from sacred Indian literature:

| Sanskrit Name | Source | Technical Function |
|---|---|---|
| `niyantrana` | Yoga Sutras of Patanjali | Control — restraint of cosmic flow |

Each library solves one problem. Zero external dependencies. Pure Python 3.8+.

---

## Contributing

1. Fork the repo
2. Create feature branch (`git checkout -b fix/your-fix`)  
3. Add tests — zero dependencies only
4. Open a PR

---

<div align="center">

**🌊 Built by [Darshankumar Joshi](https://github.com/darshjme)** · [@thedarshanjoshi](https://twitter.com/thedarshanjoshi)

*"कर्मण्येवाधिकारस्ते मा फलेषु कदाचन"*
*Your right is to action alone, never to its fruits. — Bhagavad Gita 2.47*

[Vedic Arsenal](https://github.com/darshjme/arsenal) · [GitHub](https://github.com/darshjme) · [Twitter](https://twitter.com/thedarshanjoshi)

</div>
