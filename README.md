# mini-llm-router

![Python 3.11+](https://img.shields.io/badge/python-3.11%2B-blue)
![License: MIT](https://img.shields.io/badge/license-MIT-green)
[![CI](https://github.com/awf-cpu/mini-llm-router/actions/workflows/ci.yml/badge.svg)](https://github.com/awf-cpu/mini-llm-router/actions/workflows/ci.yml)

A small **LLM gateway** that routes each request to the right provider and model for its **task type**, caches responses so you never pay twice for the same prompt, falls back when a provider fails, and logs **cost and latency** per request as structured JSON. It runs fully **offline** with a deterministic mock provider, and adds OpenAI and local Ollama providers through optional config. Zero runtime dependencies.

## The business problem

Once a company calls LLMs from more than one place, the bill and the risk spread: expensive models do trivial jobs, an outage in one provider stops everything, duplicate prompts are paid repeatedly, and nobody can say who spent what. A single chokepoint fixes this: cheap model for classification, capable model for drafting, local model when data must stay in-house, with an audit trail for every call.

## Try it in one line

```bash
python -m router.cli --task classify "is this spam? buy now, limited offer!!!"
```

Output (offline mock provider; the hash and cost vary with the prompt):

```
[mock:small] is this spam? buy now, limited offer!!! :: 0235059e

[task=classify provider=mock model=small cache_hit=False fallback=False latency=0.04ms cost=$0.000013]
```

Use your own routes with `--config config.example.json`. The cache works inside one process (or on disk with the SQLite cache):

```python
from router.core import Router
from router.config import default_config

r = Router(config=default_config())
r.route("classify", "hi")          # cache_hit=False
r.route("classify", "hi")          # cache_hit=True, cost=$0.000000
```

## Architecture

1. **Config** (`config.py`): maps each `task_type` to a primary `provider/model` plus ordered fallbacks, and lists enabled providers (JSON, or YAML if PyYAML is installed).
2. **Providers** (`providers.py`): a `Provider` interface returning text, token usage and estimated cost; always-on `MockProvider`, optional `OpenAIProvider` and `OllamaProvider`.
3. **Cache** (`cache.py`): keyed by a SHA-256 of `(task, prompt, params)`; in-memory or persistent SQLite. A hit skips the provider entirely.
4. **Router** (`core.py`): resolves the candidate chain, skips disabled providers, tries fallbacks on failure, caches the result and logs cost and latency (`logging_utils.py`, JSON lines).

Disabling a provider transparently shifts traffic to the next candidate, which is also how a "local models only" policy is expressed.

## Tests

```bash
pip install pytest && pytest -q
```

10 tests: correct model per task type, cache hits avoid a second provider call (asserted with a recording double), fallback when the primary fails or is disabled, and cost/latency log creation. CI runs them on Python 3.11 and 3.12 with no API keys.

## How this becomes a solution for your company

The production version of this idea adds per-project budgets with automatic pause, PII filtering before anything leaves your network, semantic caching, and local models for sensitive data. If your team needs control over LLM spend and data exposure, see **Work with me** below.

## Work with me

I am André Feix, founder of **Pindorama Tecnologia** (Florianópolis, Brazil). We build custom AI systems for companies and law firms: WhatsApp agents with compliance guardrails (LGPD, bar-association rules), RAG over documents, document and deadline automation, LLM routing with cost control, and local AI with data kept in Brazil.

- LinkedIn: https://www.linkedin.com/in/andrefeix
- Email: andrefeix777@gmail.com
- More: https://github.com/awf-cpu

## License

MIT © 2026 awf-cpu
