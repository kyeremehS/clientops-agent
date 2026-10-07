"""Provider comparison (manual, informational — never part of the gate).

Usage:  python evaluation/compare_search.py   (from the repo root)

Runs the dataset in evaluation/objectives.json against every keyed provider
(keys from the environment, falling back to root .env), persists
runs/<utc-timestamp>/{raw_results.json, metrics.json, report.md}, and prints
a console summary. Flags: --providers parallel,tavily --limit 2 --out-dir DIR.
Relevance judgment is human: read report.md, record the verdict in ADR-0006.
Providers without keys are skipped, never failed.
"""

import argparse
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT / "backend"))
sys.path.insert(0, str(REPO_ROOT / "evaluation"))

from search_eval.envkeys import load_dotenv_fallback  # noqa: E402
from search_eval.objectives import load_objectives  # noqa: E402
from search_eval.report import save_run  # noqa: E402
from search_eval.runner import PROVIDER_NAMES, format_cost_reference  # noqa: E402
from search_eval.runner import build_providers, run_comparison  # noqa: E402


def _parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Compare search providers (informational).")
    parser.add_argument(
        "--objectives",
        default=str(REPO_ROOT / "evaluation" / "objectives.json"),
        help="Path to objectives JSON.",
    )
    parser.add_argument(
        "--providers",
        default=",".join(PROVIDER_NAMES),
        help=f"Comma-separated subset of {','.join(PROVIDER_NAMES)}.",
    )
    parser.add_argument("--limit", type=int, default=0, help="Run only the first N objectives.")
    parser.add_argument("--out-dir", default="", help="Output dir (default: runs/<utc-ts>/).")
    return parser.parse_args(argv)


def _resolve_objectives_path(raw: str) -> Path:
    path = Path(raw)
    if path.is_file():
        return path
    fallback = REPO_ROOT / raw
    return fallback if fallback.is_file() else path


def _print_console(run: dict) -> None:
    print(f"{'provider':10} {'objective':46} {'n':>3} {'chars':>6} {'ms':>6}  top_url")
    for call in run["calls"]:
        if call["error"] is not None:
            print(
                f"{call['provider']:10} {call['objective'][:46]:46} "
                f"ERR {call['error']['type']}: {call['error']['message']}"
            )
            continue
        chars = sum(len(r["excerpt"]) for r in call["results"])
        top = call["results"][0]["url"] if call["results"] else "-"
        print(
            f"{call['provider']:10} {call['objective'][:46]:46} "
            f"{len(call['results']):>3} {chars:>6} {call['latency_ms']:>6}  {top}"
        )
    print(f"reference cost/1k: {format_cost_reference()}")


def main(argv: list[str] | None = None) -> int:
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except (AttributeError, OSError):
        pass  # non-console stdout (pipes) — print() already handles it
    args = _parse_args(argv if argv is not None else sys.argv[1:])
    load_dotenv_fallback(REPO_ROOT / ".env")

    objectives = load_objectives(_resolve_objectives_path(args.objectives))
    if args.limit and args.limit > 0:
        objectives = objectives[: args.limit]
    wanted = [name.strip() for name in args.providers.split(",") if name.strip()]
    started = time.monotonic()
    providers = build_providers(wanted)
    if not providers:
        print("no provider keys set (PARALLEL_API_KEY / TAVILY_API_KEY / SERPER_API_KEY)")
        return 0
    run = run_comparison(providers, objectives)
    out_dir = args.out_dir or str(
        REPO_ROOT / "evaluation" / "runs" / datetime.now(timezone.utc).strftime("%Y%m%d-%H%M%S")
    )
    saved = save_run(out_dir, run)
    _print_console(run)
    print(f"saved to {saved['dir']} in {int((time.monotonic() - started) * 1000)}ms total")
    return 0


if __name__ == "__main__":
    sys.exit(main())
