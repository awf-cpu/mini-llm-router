"""The Router: pick a provider/model per task, with caching and fallbacks."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, List, Optional

from .cache import Cache, MemoryCache, make_cache_key
from .config import RouterConfig, default_config
from .logging_utils import RequestLog, RequestLogger
from .providers import Provider, ProviderResponse, get_provider


@dataclass
class RouteResult:
    """Outcome of a routed request."""

    text: str
    provider: str
    model: str
    task_type: str
    cache_hit: bool
    latency_ms: float
    cost_usd: float
    fallback_used: bool


class Router:
    """Routes requests to providers based on task type.

    Resolution order for a task: the configured primary route, then its
    fallbacks, skipping any provider not in ``enabled_providers``. Responses are
    cached by a hash of (task, prompt, params); a cache hit returns immediately
    without invoking a provider. Every request is logged with cost and latency.
    """

    def __init__(
        self,
        config: Optional[RouterConfig] = None,
        cache: Optional[Cache] = None,
        logger: Optional[RequestLogger] = None,
        providers: Optional[Dict[str, Provider]] = None,
    ) -> None:
        self.config = config or default_config()
        self.cache = cache if cache is not None else MemoryCache()
        self.logger = logger or RequestLogger()
        # lazily-built provider instances, keyed by name; injectable for tests
        self._providers: Dict[str, Provider] = providers or {}

    # -- provider resolution ---------------------------------------------- #
    def _get_provider(self, name: str) -> Provider:
        if name not in self._providers:
            self._providers[name] = get_provider(name)
        return self._providers[name]

    def _candidates(self, task_type: str) -> List[Dict[str, str]]:
        """Ordered list of ``{provider, model}`` candidates for a task type."""
        route = self.config.routes.get(task_type) or self.config.routes.get(
            self.config.default_task
        )
        if route is None:
            raise ValueError(f"no route for task {task_type!r} and no default route")
        chain = [{"provider": route.provider, "model": route.model}]
        chain.extend(route.fallbacks)
        # keep only enabled providers, preserving order
        enabled = set(self.config.enabled_providers)
        return [c for c in chain if c["provider"] in enabled]

    # -- main entry point -------------------------------------------------- #
    def route(self, task_type: str, prompt: str, **params: Any) -> RouteResult:
        """Route ``prompt`` for ``task_type`` and return a :class:`RouteResult`."""
        key = make_cache_key(task_type, prompt, params)

        start = RequestLogger.now_ms()
        cached = self.cache.get(key)
        if cached is not None:
            latency = RequestLogger.now_ms() - start
            candidate = self._candidates(task_type)[0]
            self.logger.log(
                RequestLog(
                    ts=start,
                    task_type=task_type,
                    provider=candidate["provider"],
                    model=candidate["model"],
                    cache_hit=True,
                    latency_ms=round(latency, 4),
                    prompt_tokens=0,
                    completion_tokens=0,
                    cost_usd=0.0,
                    fallback_used=False,
                )
            )
            return RouteResult(
                text=cached,
                provider=candidate["provider"],
                model=candidate["model"],
                task_type=task_type,
                cache_hit=True,
                latency_ms=round(latency, 4),
                cost_usd=0.0,
                fallback_used=False,
            )

        candidates = self._candidates(task_type)
        if not candidates:
            raise ValueError(
                f"no enabled provider available for task {task_type!r}"
            )

        last_error: Optional[Exception] = None
        for i, candidate in enumerate(candidates):
            provider = self._get_provider(candidate["provider"])
            try:
                resp: ProviderResponse = provider.complete(
                    prompt, candidate["model"], **params
                )
            except Exception as exc:  # try the next fallback
                last_error = exc
                continue

            latency = RequestLogger.now_ms() - start
            self.cache.set(key, resp.text)
            self.logger.log(
                RequestLog(
                    ts=start,
                    task_type=task_type,
                    provider=resp.provider,
                    model=resp.model,
                    cache_hit=False,
                    latency_ms=round(latency, 4),
                    prompt_tokens=resp.prompt_tokens,
                    completion_tokens=resp.completion_tokens,
                    cost_usd=resp.cost_usd,
                    fallback_used=i > 0,
                )
            )
            return RouteResult(
                text=resp.text,
                provider=resp.provider,
                model=resp.model,
                task_type=task_type,
                cache_hit=False,
                latency_ms=round(latency, 4),
                cost_usd=resp.cost_usd,
                fallback_used=i > 0,
            )

        raise RuntimeError(
            f"all providers failed for task {task_type!r}: {last_error}"
        )
