"""Live comparison runner. One provider failure never stops the run."""

import os
import time
from datetime import datetime, timezone

from app.tools.search import SearchProvider, create_search_provider

PROVIDER_NAMES = ("parallel", "tavily", "serper")
_PROVIDER_KEY = {
    "parallel": "PARALLEL_API_KEY",
    "tavily": "TAVILY_API_KEY",
    "serper": "SERPER_API_KEY",
}

COST_PER_1K = {"parallel": "$1", "tavily": "~$5-6 (basic depth)", "serper": "~$0.3-1"}


def format_cost_reference() -> str:
    return "; ".join(f"{name} {COST_PER_1K[name]}" for name in PROVIDER_NAMES)


def build_providers(wanted: list[str] | None = None) -> dict[str, SearchProvider]:
    """Instantiate keyed providers. Unkeyed names are skipped, never failed."""
    wanted = list(wanted or PROVIDER_NAMES)
    unknown = [name for name in wanted if name not in PROVIDER_NAMES]
    if unknown:
        raise ValueError(f"unknown providers: {unknown} (choose from {PROVIDER_NAMES})")
    providers: dict[str, SearchProvider] = {}
    for name in wanted:
        key = os.environ.get(_PROVIDER_KEY[name], "")
        if not key:
            continue
        providers[name] = create_search_provider(
            name,
            parallel_key=os.environ.get("PARALLEL_API_KEY", ""),
            tavily_key=os.environ.get("TAVILY_API_KEY", ""),
            serper_key=os.environ.get("SERPER_API_KEY", ""),
        )
    return providers


def run_comparison(
    providers: dict[str, SearchProvider],
    objectives: list[dict],
) -> dict:
    """Run every objective against every provider. Returns a JSON-able run dict."""
    calls: list[dict] = []
    for objective in objectives:
        for name, provider in providers.items():
            max_results = objective["max_results"]
            start = time.monotonic()
            try:
                results = provider.search(objective["objective"], max_results=max_results)
                calls.append(
                    {
                        "provider": name,
                        "objective_id": objective["id"],
                        "objective": objective["objective"],
                        "max_results": max_results,
                        "latency_ms": int((time.monotonic() - start) * 1000),
                        "results": [
                            {"title": r.title, "url": r.url, "excerpt": r.excerpt}
                            for r in results
                        ],
                        "error": None,
                    }
                )
            except Exception as exc:  # noqa: BLE001 — comparison must not crash
                calls.append(
                    {
                        "provider": name,
                        "objective_id": objective["id"],
                        "objective": objective["objective"],
                        "max_results": max_results,
                        "latency_ms": None,
                        "results": [],
                        "error": {"type": type(exc).__name__, "message": str(exc)[:200]},
                    }
                )
    return {
        "created_utc": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "providers": sorted(providers),
        "objectives": objectives,
        "calls": calls,
    }
