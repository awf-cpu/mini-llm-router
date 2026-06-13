"""Provider abstractions and implementations.

A :class:`Provider` turns a prompt into a :class:`ProviderResponse` carrying the
text, a token estimate, and an estimated cost. The deterministic
:class:`MockProvider` is always available (no network); OpenAI and Ollama
providers are optional and imported lazily.
"""

from __future__ import annotations

import hashlib
from abc import ABC, abstractmethod
from dataclasses import dataclass


@dataclass
class ProviderResponse:
    """The result of a single provider call."""

    text: str
    provider: str
    model: str
    prompt_tokens: int
    completion_tokens: int
    cost_usd: float


class Provider(ABC):
    """Generates a completion for a prompt and reports usage/cost."""

    name: str

    @abstractmethod
    def complete(self, prompt: str, model: str, **params) -> ProviderResponse:
        """Return a :class:`ProviderResponse` for ``prompt``."""
        raise NotImplementedError


def _estimate_tokens(text: str) -> int:
    """Rough token estimate (~4 chars/token), good enough for cost logging."""
    return max(1, len(text) // 4)


class MockProvider(Provider):
    """Deterministic, offline provider.

    Produces a stable, prompt-dependent reply (so caching is observable) and a
    deterministic cost derived from a configurable per-1k-token price. It never
    hits the network, which makes the whole router testable without keys.
    """

    name = "mock"

    def __init__(self, price_per_1k: float = 0.0005) -> None:
        self.price_per_1k = price_per_1k

    def complete(self, prompt: str, model: str, **params) -> ProviderResponse:
        digest = hashlib.sha1(f"{model}:{prompt}".encode("utf-8")).hexdigest()[:8]
        text = f"[mock:{model}] {prompt.strip()[:80]} :: {digest}"
        p_tok = _estimate_tokens(prompt)
        c_tok = _estimate_tokens(text)
        cost = (p_tok + c_tok) / 1000.0 * self.price_per_1k
        return ProviderResponse(
            text=text,
            provider=self.name,
            model=model,
            prompt_tokens=p_tok,
            completion_tokens=c_tok,
            cost_usd=round(cost, 8),
        )


class OpenAIProvider(Provider):
    """OpenAI chat-completions provider (optional, needs OPENAI_API_KEY)."""

    name = "openai"

    # very rough public per-1k-token prices (USD), for cost logging only
    _PRICES = {"gpt-4o-mini": 0.00060, "gpt-4o": 0.01000}

    def __init__(self) -> None:
        from openai import OpenAI  # lazy import keeps it optional

        self._client = OpenAI()

    def complete(self, prompt: str, model: str, **params) -> ProviderResponse:  # pragma: no cover
        resp = self._client.chat.completions.create(
            model=model,
            messages=[{"role": "user", "content": prompt}],
            temperature=params.get("temperature", 0.0),
        )
        usage = resp.usage
        p_tok = usage.prompt_tokens if usage else _estimate_tokens(prompt)
        text = resp.choices[0].message.content or ""
        c_tok = usage.completion_tokens if usage else _estimate_tokens(text)
        price = self._PRICES.get(model, 0.001)
        cost = (p_tok + c_tok) / 1000.0 * price
        return ProviderResponse(text, self.name, model, p_tok, c_tok, round(cost, 8))


class OllamaProvider(Provider):
    """Local Ollama provider (optional, needs a running Ollama + requests)."""

    name = "ollama"

    def __init__(self, host: str = "http://127.0.0.1:11434") -> None:
        self.host = host

    def complete(self, prompt: str, model: str, **params) -> ProviderResponse:  # pragma: no cover
        import requests

        resp = requests.post(
            f"{self.host}/api/generate",
            json={"model": model, "prompt": prompt, "stream": False},
            timeout=params.get("timeout", 120),
        )
        resp.raise_for_status()
        data = resp.json()
        text = data.get("response", "")
        p_tok = data.get("prompt_eval_count", _estimate_tokens(prompt))
        c_tok = data.get("eval_count", _estimate_tokens(text))
        # local models are free to run
        return ProviderResponse(text, self.name, model, p_tok, c_tok, 0.0)


_REGISTRY = {
    "mock": MockProvider,
    "openai": OpenAIProvider,
    "ollama": OllamaProvider,
}


def get_provider(name: str) -> Provider:
    """Instantiate a provider by name (``mock`` | ``openai`` | ``ollama``)."""
    name = name.lower()
    if name not in _REGISTRY:
        raise ValueError(f"unknown provider: {name!r}")
    return _REGISTRY[name]()
