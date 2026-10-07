"""Provider comparison (manual, informational — never part of the gate).

Usage:  python evaluation/compare_search.py   (from the repo root)

Runs the same company-research objectives against every configured provider
(keys read from the environment) and prints latency / volume / cost per call.
Relevance judgment is human: read the excerpts, fill the ADR table, pick the default.
Providers without keys are skipped, never failed.
"""

import os
import sys
import time
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT / "backend"))

from app.tools.search import (  # noqa: E402
    ParallelSearchProvider,
    SerperSearchProvider,
    TavilySearchProvider,
)

OBJECTIVES = [
    "What does Acme Logistics do? Company profile, industry, services.",
    "Operational pain signals at a mid-size logistics company: support backlog, hiring.",
    "Acme Logistics news: funding, expansions, leadership changes.",
]

COST_PER_1K = {"parallel": "$1", "tavily": "~$5-6 (basic depth)", "serper": "~$0.3-1"}


def configured() -> dict[str, object]:
    providers: dict[str, object] = {}
    if os.environ.get("PARALLEL_API_KEY"):
        providers["parallel"] = ParallelSearchProvider(api_key=os.environ["PARALLEL_API_KEY"])
    if os.environ.get("TAVILY_API_KEY"):
        providers["tavily"] = TavilySearchProvider(api_key=os.environ["TAVILY_API_KEY"])
    if os.environ.get("SERPER_API_KEY"):
        providers["serper"] = SerperSearchProvider(api_key=os.environ["SERPER_API_KEY"])
    return providers


def main() -> int:
    providers = configured()
    if not providers:
        print("no provider keys set (PARALLEL_API_KEY / TAVILY_API_KEY / SERPER_API_KEY)")
        return 0
    print(f"{'provider':10} {'objective':46} {'n':>3} {'chars':>6} {'ms':>6}  top_url")
    for name, provider in providers.items():
        for objective in OBJECTIVES:
            start = time.monotonic()
            try:
                results = provider.search(objective, max_results=5)
                elapsed = int((time.monotonic() - start) * 1000)
                chars = sum(len(r.excerpt) for r in results)
                top = results[0].url if results else "-"
                print(f"{name:10} {objective[:46]:46} {len(results):>3} {chars:>6} {elapsed:>6}  {top}")
                for result in results:
                    print(f"           - {result.title[:70]} :: {result.excerpt[:120]}")
            except Exception as exc:  # noqa: BLE001 — comparison must not crash
                print(f"{name:10} {objective[:46]:46} ERR {type(exc).__name__}: {exc}")
    print(f"reference cost/1k: {COST_PER_1K}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
