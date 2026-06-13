"""CLI entry point: ``python -m router.cli --task classify "is this spam? ..."``."""

from __future__ import annotations

import argparse

from .config import RouterConfig, default_config
from .core import Router


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="router.cli",
        description="Route an LLM request to the best provider for a task type.",
    )
    parser.add_argument("prompt", help="the prompt text")
    parser.add_argument(
        "--task", default="default", help="task type (e.g. classify|cheap|code|longform)"
    )
    parser.add_argument("--config", default=None, help="path to a JSON/YAML config")
    args = parser.parse_args(argv)

    config = RouterConfig.load(args.config) if args.config else default_config()
    router = Router(config=config)
    result = router.route(args.task, args.prompt)

    print(result.text)
    print(
        f"\n[task={result.task_type} provider={result.provider} model={result.model} "
        f"cache_hit={result.cache_hit} fallback={result.fallback_used} "
        f"latency={result.latency_ms:.2f}ms cost=${result.cost_usd:.6f}]"
    )
    return 0


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
