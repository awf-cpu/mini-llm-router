"""Tests for task-type based routing and fallbacks."""

import pytest

from router.config import RouterConfig
from router.core import Router
from router.providers import Provider, ProviderResponse


class RecordingProvider(Provider):
    """A test double that records calls and can be made to fail."""

    def __init__(self, name="mock", fail=False):
        self.name = name
        self.fail = fail
        self.calls = []

    def complete(self, prompt, model, **params):
        self.calls.append((prompt, model))
        if self.fail:
            raise RuntimeError("simulated provider failure")
        return ProviderResponse(
            text=f"{self.name}:{model}:{prompt}",
            provider=self.name,
            model=model,
            prompt_tokens=3,
            completion_tokens=5,
            cost_usd=0.0001,
        )


def _config():
    return RouterConfig.from_dict(
        {
            "enabled_providers": ["primary", "backup"],
            "default_task": "default",
            "routes": {
                "classify": {"provider": "primary", "model": "small"},
                "code": {"provider": "primary", "model": "large"},
                "default": {"provider": "primary", "model": "small"},
            },
        }
    )


def test_routing_picks_model_per_task_type():
    primary = RecordingProvider("primary")
    router = Router(config=_config(), providers={"primary": primary})

    r1 = router.route("classify", "is this spam?")
    r2 = router.route("code", "write a function")

    assert r1.model == "small"
    assert r2.model == "large"
    assert primary.calls[0][1] == "small"
    assert primary.calls[1][1] == "large"


def test_unknown_task_falls_back_to_default_route():
    primary = RecordingProvider("primary")
    router = Router(config=_config(), providers={"primary": primary})
    result = router.route("some_unknown_task", "hello")
    assert result.model == "small"  # default route
    assert result.provider == "primary"
