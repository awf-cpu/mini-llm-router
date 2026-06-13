"""Tests for the always-available offline mock provider and default config."""

from router.config import default_config
from router.core import Router
from router.providers import MockProvider


def test_mock_provider_is_deterministic_and_reports_cost():
    p = MockProvider()
    r1 = p.complete("hello world", "small")
    r2 = p.complete("hello world", "small")
    assert r1.text == r2.text  # deterministic
    assert r1.cost_usd > 0
    assert r1.prompt_tokens >= 1 and r1.completion_tokens >= 1


def test_default_config_routes_offline_end_to_end():
    router = Router(config=default_config())
    result = router.route("classify", "is this spam? buy now!!!")
    assert result.provider == "mock"
    assert result.model == "small"
    assert "[mock:small]" in result.text
