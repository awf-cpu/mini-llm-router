# mini-llm-router

A small **LLM gateway** that routes each request to the best provider/model for
its **task type**, caches responses to avoid duplicate calls, and logs per-request
**cost and latency** as structured JSON. It runs fully **offline** with a
deterministic mock provider, and adds OpenAI / local Ollama providers behind
optional config — no API keys needed to run or test.

## Why it matters

Once you call LLMs from more than one place, you want a single chokepoint that
decides *which* model handles *which* job (cheap classifier vs. capable coder),
falls back when a provider is down, never pays twice for the same prompt, and
gives you an audit trail of spend and latency. That is exactly the boring,
load-bearing infrastructure this repo demonstrates in a compact, tested form.

## Architecture (in 4 lines)

1. **Config** (`config.py`) — maps each `task_type` to a primary `provider/model` plus ordered fallbacks, and lists enabled providers (JSON, or YAML if PyYAML is installed).
2. **Providers** (`providers.py`) — `Provider` interface returning text + token usage + estimated cost; always-on `MockProvider`, optional `OpenAIProvider` / `OllamaProvider`.
3. **Cache** (`cache.py`) — keyed by a SHA-256 of `(task, prompt, params)`; in-memory or persistent SQLite. A hit skips the provider entirely.
4. **Router** (`core.py`) — resolves the candidate chain, skips disabled providers, tries fallbacks on failure, caches the result, and logs cost/latency via `logging_utils.py`.

## Install

```bash
python -m venv .venv && source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -r requirements.txt
# optional: pip install pyyaml openai requests
```

## Usage

```bash
python -m router.cli --task classify "is this spam? buy now, limited offer!!!"
```

Output (offline mock provider):

```
[mock:small] is this spam? buy now, limited offer!!! :: 9f1c2a7b

[task=classify provider=mock model=small cache_hit=False fallback=False latency=0.05ms cost=$0.000000]
```

Run it twice and the second call reports `cache_hit=True` with `cost=$0.000000`.
Point at a custom config with `--config config.example.json`.

## How it works

- **Task-based routing.** "classify"/"cheap" map to a small model; "code"/
  "longform" map to a large model. Each route may declare fallbacks, and the
  router only considers providers listed in `enabled_providers` — so disabling a
  provider transparently shifts traffic to the next candidate.
- **Caching.** The cache key is a stable hash of the task type, prompt, and
  params. On a hit the router returns immediately and logs a zero-cost entry,
  guaranteeing the underlying provider is invoked at most once per unique request.
- **Cost & latency logging.** Every request appends a structured `RequestLog`
  (provider, model, tokens, cost, latency, cache/fallback flags) to an in-memory
  list and, optionally, a JSON-lines file — the basis for spend dashboards.
- **Determinism for tests.** `MockProvider` derives a stable reply and a computed
  cost from the prompt, so routing, caching, and fallback behaviour are all
  unit-testable with no network.

## Tests

```bash
pytest -q
```

Covers: routing picks the correct model per task type, cache hits avoid a second
provider call (asserted via a recording double), fallback when the primary fails
or is disabled, and creation of a cost/latency log entry.

## License

MIT © 2026 awf-cpu
