"""Structured per-request logging of cost and latency."""

from __future__ import annotations

import json
import time
from dataclasses import asdict, dataclass
from typing import List, Optional, TextIO


@dataclass
class RequestLog:
    """One structured log entry for a routed request."""

    ts: float
    task_type: str
    provider: str
    model: str
    cache_hit: bool
    latency_ms: float
    prompt_tokens: int
    completion_tokens: int
    cost_usd: float
    fallback_used: bool


class RequestLogger:
    """Collects :class:`RequestLog` entries and optionally writes JSON lines.

    Entries are always kept in-memory (queryable in tests) and, if a file path
    or stream is given, appended as one JSON object per line.
    """

    def __init__(self, stream: Optional[TextIO] = None, path: Optional[str] = None) -> None:
        self.entries: List[RequestLog] = []
        self._stream = stream
        self._path = path

    def log(self, entry: RequestLog) -> None:
        """Record ``entry`` in memory and to the configured sink, if any."""
        self.entries.append(entry)
        line = json.dumps(asdict(entry))
        if self._stream is not None:
            self._stream.write(line + "\n")
            self._stream.flush()
        if self._path is not None:
            with open(self._path, "a", encoding="utf-8") as fh:
                fh.write(line + "\n")

    @staticmethod
    def now_ms() -> float:
        """Monotonic timestamp in milliseconds (for latency measurement)."""
        return time.perf_counter() * 1000.0
