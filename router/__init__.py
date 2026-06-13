"""router: a small LLM gateway with task-based routing, caching and logging.

A :class:`~router.core.Router` reads a config mapping task types to a primary
provider/model plus ordered fallbacks, caches responses by a hash of the request,
and logs per-request cost and latency as structured JSON lines.

A deterministic offline ``mock`` provider is always available, so everything runs
and is testable without any API keys. OpenAI and Ollama providers are optional
and activate only when configured/installed.
"""

from .providers import (
    Provider,
    ProviderResponse,
    MockProvider,
    get_provider,
)
from .cache import Cache, MemoryCache, SqliteCache
from .logging_utils import RequestLog, RequestLogger
from .core import Router, RouteResult

__all__ = [
    "Provider",
    "ProviderResponse",
    "MockProvider",
    "get_provider",
    "Cache",
    "MemoryCache",
    "SqliteCache",
    "RequestLog",
    "RequestLogger",
    "Router",
    "RouteResult",
]

__version__ = "0.1.0"
