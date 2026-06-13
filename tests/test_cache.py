"""Tests for caching behaviour (a cache hit must avoid a second provider call)."""

import os
import tempfile

from router.cache import MemoryCache, SqliteCache, make_cache_key
from router.config import RouterConfig
from router.core import Router
from tests.test_routing import RecordingProvider, _config


def test_cache_key_is_stable_and_param_sensitive():
    a = make_cache_key("classify", "hello", {"temperature": 0})
    b = make_cache_key("classify", "hello", {"temperature": 0})
    c = make_cache_key("classify", "hello", {"temperature": 1})
    assert a == b
    assert a != c


def test_cache_hit_avoids_second_provider_call():
    primary = RecordingProvider("primary")
    router = Router(config=_config(), providers={"primary": primary}, cache=MemoryCache())

    first = router.route("classify", "is this spam?")
    second = router.route("classify", "is this spam?")

    assert first.text == second.text
    assert first.cache_hit is False
    assert second.cache_hit is True
    assert len(primary.calls) == 1  # provider called exactly once


def test_sqlite_cache_persists_values():
    with tempfile.TemporaryDirectory() as tmp:
        path = os.path.join(tmp, "cache.sqlite")
        cache = SqliteCache(path)
        cache.set("k", "v")
        cache.close()

        reopened = SqliteCache(path)
        assert reopened.get("k") == "v"
        reopened.close()
