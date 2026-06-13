"""Response caches keyed by a hash of the request.

Two interchangeable implementations behind the :class:`Cache` interface: an
in-memory dict cache and a persistent SQLite cache. The cache key is a stable
hash of provider-independent request fields (task type, prompt, params), so a
repeated identical request is served without calling a provider again.
"""

from __future__ import annotations

import hashlib
import json
import sqlite3
from abc import ABC, abstractmethod
from typing import Any, Dict, Optional


def make_cache_key(task_type: str, prompt: str, params: Dict[str, Any]) -> str:
    """Return a deterministic cache key for a request."""
    payload = json.dumps(
        {"task": task_type, "prompt": prompt, "params": params},
        sort_keys=True,
        ensure_ascii=False,
    )
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


class Cache(ABC):
    """A minimal string-keyed cache of completion strings."""

    @abstractmethod
    def get(self, key: str) -> Optional[str]:
        """Return the cached value for ``key`` or ``None``."""
        raise NotImplementedError

    @abstractmethod
    def set(self, key: str, value: str) -> None:
        """Store ``value`` under ``key``."""
        raise NotImplementedError


class MemoryCache(Cache):
    """Process-local dict cache (default)."""

    def __init__(self) -> None:
        self._store: Dict[str, str] = {}

    def get(self, key: str) -> Optional[str]:
        return self._store.get(key)

    def set(self, key: str, value: str) -> None:
        self._store[key] = value


class SqliteCache(Cache):
    """Persistent cache backed by a SQLite file (or ``:memory:``)."""

    def __init__(self, path: str = ":memory:") -> None:
        self._conn = sqlite3.connect(path)
        self._conn.execute(
            "CREATE TABLE IF NOT EXISTS cache (key TEXT PRIMARY KEY, value TEXT)"
        )
        self._conn.commit()

    def get(self, key: str) -> Optional[str]:
        row = self._conn.execute(
            "SELECT value FROM cache WHERE key = ?", (key,)
        ).fetchone()
        return row[0] if row else None

    def set(self, key: str, value: str) -> None:
        self._conn.execute(
            "INSERT OR REPLACE INTO cache (key, value) VALUES (?, ?)", (key, value)
        )
        self._conn.commit()

    def close(self) -> None:
        self._conn.close()
