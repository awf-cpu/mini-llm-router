"""Tests for fallback resolution and structured cost/latency logging."""

from router.config import RouterConfig
from router.core import Router
from router.logging_utils import RequestLogger
from tests.test_routing import RecordingProvider


def _fallback_config():
    return RouterConfig.from_dict(
        {
            "enabled_providers": ["primary", "backup"],
            "default_task": "default",
            "routes": {
                "code": {
                    "provider": "primary",
                    "model": "large",
                    "fallbacks": [{"provider": "backup", "model": "small"}],
                },
                "default": {"provider": "primary", "model": "small"},
            },
        }
    )


def test_fallback_used_when_primary_fails():
    primary = RecordingProvider("primary", fail=True)
    backup = RecordingProvider("backup")
    router = Router(
        config=_fallback_config(),
        providers={"primary": primary, "backup": backup},
    )
    result = router.route("code", "build it")
    assert result.provider == "backup"
    assert result.fallback_used is True
    assert len(backup.calls) == 1


def test_disabled_primary_is_skipped():
    """If the primary provider is not enabled, the enabled fallback is used."""
    config = RouterConfig.from_dict(
        {
            "enabled_providers": ["backup"],  # primary disabled
            "default_task": "default",
            "routes": {
                "code": {
                    "provider": "primary",
                    "model": "large",
                    "fallbacks": [{"provider": "backup", "model": "small"}],
                },
                "default": {"provider": "backup", "model": "small"},
            },
        }
    )
    backup = RecordingProvider("backup")
    router = Router(config=config, providers={"backup": backup})
    result = router.route("code", "build it")
    assert result.provider == "backup"


def test_log_entry_created_with_cost_and_latency():
    logger = RequestLogger()
    primary = RecordingProvider("primary")
    config = RouterConfig.from_dict(
        {
            "enabled_providers": ["primary"],
            "default_task": "default",
            "routes": {"default": {"provider": "primary", "model": "small"}},
        }
    )
    router = Router(config=config, providers={"primary": primary}, logger=logger)
    router.route("default", "hello")

    assert len(logger.entries) == 1
    entry = logger.entries[0]
    assert entry.provider == "primary"
    assert entry.cost_usd > 0
    assert entry.latency_ms >= 0
    assert entry.cache_hit is False
