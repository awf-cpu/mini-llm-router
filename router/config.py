"""Routing configuration loading.

The config maps each ``task_type`` to a primary provider/model plus an ordered
list of fallbacks, and lists which providers are enabled. JSON is supported out
of the box; YAML is supported when :mod:`PyYAML` is installed.
"""

from __future__ import annotations

import json
import os
from dataclasses import dataclass, field
from typing import Dict, List


@dataclass
class Route:
    """A single task_type -> provider/model route with fallbacks."""

    provider: str
    model: str
    #: ordered list of ``{"provider": ..., "model": ...}`` fallbacks
    fallbacks: List[Dict[str, str]] = field(default_factory=list)


@dataclass
class RouterConfig:
    """Full router configuration."""

    enabled_providers: List[str]
    routes: Dict[str, Route]
    default_task: str = "default"

    @classmethod
    def from_dict(cls, data: dict) -> "RouterConfig":
        routes = {
            task: Route(
                provider=spec["provider"],
                model=spec["model"],
                fallbacks=spec.get("fallbacks", []),
            )
            for task, spec in data.get("routes", {}).items()
        }
        return cls(
            enabled_providers=data.get("enabled_providers", ["mock"]),
            routes=routes,
            default_task=data.get("default_task", "default"),
        )

    @classmethod
    def load(cls, path: str) -> "RouterConfig":
        """Load config from a ``.json`` or ``.yaml``/``.yml`` file."""
        ext = os.path.splitext(path)[1].lower()
        with open(path, "r", encoding="utf-8") as fh:
            text = fh.read()
        if ext in (".yaml", ".yml"):
            import yaml  # optional dependency

            data = yaml.safe_load(text)
        else:
            data = json.loads(text)
        return cls.from_dict(data)


def default_config() -> RouterConfig:
    """A sensible built-in config that works fully offline (all mock)."""
    return RouterConfig.from_dict(
        {
            "enabled_providers": ["mock"],
            "default_task": "default",
            "routes": {
                # cheap/classification tasks -> small/local model
                "classify": {
                    "provider": "mock",
                    "model": "small",
                    "fallbacks": [{"provider": "mock", "model": "tiny"}],
                },
                "cheap": {"provider": "mock", "model": "small"},
                # code / long-form -> larger model
                "code": {
                    "provider": "mock",
                    "model": "large",
                    "fallbacks": [{"provider": "mock", "model": "small"}],
                },
                "longform": {"provider": "mock", "model": "large"},
                "default": {"provider": "mock", "model": "small"},
            },
        }
    )
