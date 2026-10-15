"""Live pipeline evaluation (manual runs only — never CI, never gated).

Usage:  python evaluation/live_eval.py [--limit 1]   (from the repo root)

Runs evaluation/live_cases/*.json through the REAL pipeline (configured
search provider + live LLM + real websites) on scratch SQLite files and
records evaluation/runs/live-<ts>/{<case>.json, summary.json}.

Each case is compared against loose expectations (outcome, fit floor,
approval presence, no external action, grounded citations). The live web
shifts, so a mismatch exits nonzero for HUMAN TRIAGE — it never fails a
build and never auto-changes code. Costs real provider credits per run.
"""

import argparse
import json
import statistics
import sys
import tempfile
import time
import traceback
from datetime import datetime, timezone
from pathlib import Path
from uuid import UUID

REPO_ROOT = Path(__file__).resolve().parent.parent

# Strong-fit cases must outscore weak-fit cases by this much. A relative
# assertion: the live web shifts and model wording drifts, but a system
# that discriminates good leads from bad keeps this margin.
ORDERING_MARGIN = 15.0
sys.path.insert(0, str(REPO_ROOT / "backend"))
sys.path.insert(0, str(REPO_ROOT / "evaluation"))

from sqlalchemy import create_engine, select  # noqa: E402
from sqlalchemy.orm import sessionmaker  # noqa: E402

from app.config import settings  # noqa: E402
from app.db.base import Base  # noqa: E402
from app.db.models import Action, Lead, Qualification, ResearchArtifact  # noqa: E402
from app.llm import llm_client_from_settings  # noqa: E402
from app.orchestrator.runner import run_lead  # noqa: E402
from app.tools.fetch import WebsiteFetcher  # noqa: E402
from app.tools.search import create_search_provider  # noqa: E402
from search_eval.envkeys import load_dotenv_fallback  # noqa: E402


def check_ordering(records: list[dict]) -> dict:
    """Cross-case discrimination: strong-fit leads must outscore weak-fit ones.

    The per-case fit bands are hand-tuned to observed values and generalize
    poorly. This is the assertion that survives: if the system can tell a
    strong lead from a weak one at all, the group means keep their order.
    """
    roles: dict[str, list[float]] = {"strong": [], "weak": []}
    for record in records:
        role = record.get("role")
        if role in roles:
            roles[role].append(float(record["result"]["fit"]))
    if not roles["strong"] or not roles["weak"]:
        return {"applicable": False, "reason": "needs both strong and weak cases"}
    strong_mean = round(statistics.mean(roles["strong"]), 1)
    weak_mean = round(statistics.mean(roles["weak"]), 1)
    margin = round(strong_mean - weak_mean, 1)
    return {
        "applicable": True,
        "strong_mean": strong_mean,
        "weak_mean": weak_mean,
        "margin": margin,
        "required_margin": ORDERING_MARGIN,
        "passed": margin >= ORDERING_MARGIN,
    }


def check_case(expectations: dict, result: dict) -> dict:
    """Compare a recorded run summary against expectations. No I/O."""
    failures: list[str] = []
    expected = expectations["expected_outcome"]
    if isinstance(expected, str):
        expected = [expected]
    if result["outcome"] not in expected:
        failures.append(
            f"outcome {result['outcome']} != expected {'|'.join(expected)}"
        )
    min_fit = expectations.get("min_fit")
    if min_fit is not None and result["fit"] < min_fit:
        failures.append(f"fit {result['fit']:.1f} < floor {min_fit}")
    max_fit = expectations.get("max_fit")
    if max_fit is not None and result["fit"] > max_fit:
        failures.append(f"fit {result['fit']:.1f} > ceiling {max_fit}")
    if expectations.get("require_approval") and not result["approval_id"]:
        failures.append("expected a pending approval, found none")
    if expectations.get("forbid_action", True) and result["actions"] > 0:
        failures.append(f"external action taken {result['actions']}x — human gate bypassed")
    cited = {url for claim in result["claims"] for url in claim["source_urls"]}
    unknown = sorted(cited - set(result["artifact_urls"]))
    if unknown:
        failures.append(f"ungrounded citations (not fetched artifacts): {unknown}")
    return {"passed": not failures, "failures": failures}


def run_case(case: dict, search, fetcher, llm, max_results: int) -> dict:
    """Execute one live case on a scratch database. Returns the run summary."""
    with tempfile.TemporaryDirectory() as tmp:
        engine = create_engine(f"sqlite:///{tmp}/live.db", future=True)
        Base.metadata.create_all(engine)
        factory = sessionmaker(bind=engine, expire_on_commit=False, future=True)
        session = factory()
        lead = Lead(
            company=case["lead"]["company"],
            website=case["lead"].get("website", ""),
            contact=case["lead"].get("contact", ""),
            message=case["lead"].get("message", ""),
        )
        session.add(lead)
        session.commit()
        try:
            summary = run_lead(
                lead.id, session, search, fetcher, llm, max_results=max_results
            )
        finally:
            artifact_urls = [
                row.source_url
                for row in session.scalars(select(ResearchArtifact)).all()
            ]
            actions = session.query(Action).count()
            qualification = session.scalar(
                select(Qualification).where(Qualification.lead_id == lead.id)
            )
            session.close()
            engine.dispose()  # release the sqlite file handle (Windows locks it)
        return {
            "case": case["id"],
            "outcome": summary["outcome"],
            "fit": round(summary["fit"], 1),
            "approval_id": str(summary["approval_id"]) if summary["approval_id"] else None,
            "reasons": summary["reasons"],
            "claims": summary["claims"],
            "dimensions": (
                {
                    "operational_pain": qualification.operational_pain,
                    "automation_plausibility": qualification.automation_plausibility,
                    "relevance": qualification.relevance,
                    "evidence_quality": qualification.evidence_quality,
                    "summary": qualification.summary,
                }
                if qualification is not None
                else None
            ),
            "artifact_urls": artifact_urls,
            "actions": actions,
        }


def _build_live_clients():
    load_dotenv_fallback(REPO_ROOT / ".env")
    name = settings.search_provider
    if name == "mock":
        raise SystemExit("live eval needs a real SEARCH_PROVIDER (mock touches no network)")
    keys = {
        "parallel_key": settings.parallel_api_key,
        "tavily_key": settings.tavily_api_key,
        "serper_key": settings.serper_api_key,
    }
    search = create_search_provider(
        name,
        **keys,
        timeout_s=settings.search_timeout_s,
        max_retries=settings.search_max_retries,
    )
    if not getattr(search, "_api_key", ""):
        raise SystemExit(f"live eval needs a key for SEARCH_PROVIDER={name}")
    fetcher = WebsiteFetcher(
        timeout_s=settings.fetch_timeout_s,
        max_bytes=settings.fetch_max_bytes,
        max_chars=settings.fetch_max_chars,
    )
    llm = llm_client_from_settings(settings)
    return search, fetcher, llm


def main(argv: list[str] | None = None) -> int:
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except (AttributeError, OSError):
        pass  # non-console stdout (pipes) — print() already handles it
    parser = argparse.ArgumentParser(description="Live pipeline eval (manual, costs credits).")
    parser.add_argument("--cases", default=str(REPO_ROOT / "evaluation" / "live_cases"))
    parser.add_argument("--limit", type=int, default=0)
    parser.add_argument(
        "--only",
        default="",
        help="Comma-separated case ids to run (for triage reruns).",
    )
    parser.add_argument("--out-dir", default="")
    parser.add_argument(
        "--pause-s",
        type=float,
        default=20.0,
        help="Sleep between cases so free-tier rate limits recover.",
    )
    args = parser.parse_args(argv if argv is not None else sys.argv[1:])

    paths = sorted(Path(args.cases).glob("*.json"))
    if args.limit and args.limit > 0:
        paths = paths[: args.limit]
    if args.only.strip():
        wanted = {part.strip() for part in args.only.split(",") if part.strip()}
        paths = [p for p in paths if p.stem in wanted]
    if not paths:
        print("no live cases found")
        return 1
    search, fetcher, llm = _build_live_clients()
    out = Path(
        args.out_dir
        or str(REPO_ROOT / "evaluation" / "runs" / f"live-{datetime.now(timezone.utc):%Y%m%d-%H%M%S}")
    )
    out.mkdir(parents=True, exist_ok=True)

    records = []
    for i, path in enumerate(paths):
        case = json.loads(path.read_text(encoding="utf-8"))
        if i > 0 and args.pause_s > 0:
            time.sleep(args.pause_s)
        print(f"running {case['id']} ...")
        try:
            result = run_case(case, search, fetcher, llm, settings.search_max_results)
        except Exception as exc:  # noqa: BLE001 — one case never kills the run
            location = "".join(traceback.format_exception(exc))
            result = {
                "case": case["id"],
                "outcome": "ERROR",
                "fit": 0.0,
                "approval_id": None,
                "reasons": [f"{type(exc).__name__}: {exc}"],
                "traceback_tail": location[-2000:],
                "claims": [],
                "dimensions": None,
                "artifact_urls": [],
                "actions": 0,
            }
        verdict = check_case(case, result)
        record = {"expectations": {k: v for k, v in case.items() if k != "lead"}, "result": result, **verdict}
        (out / f"{case['id']}.json").write_text(json.dumps(record, indent=2), encoding="utf-8")
        status = "PASS" if verdict["passed"] else "FAIL"
        print(f"[{status}] {case['id']}: outcome={result['outcome']} fit={result['fit']}")
        for failure in verdict["failures"]:
            print(f"    - {failure}")
        if result["outcome"] == "ERROR":
            for reason in result["reasons"]:
                print(f"    ! {reason}")
        records.append(record)

    passed = sum(1 for r in records if r["passed"])
    ordering = check_ordering(records)
    if ordering["applicable"]:
        ordering_ok = ordering["passed"]
        print(
            f"ordering: strong_mean={ordering['strong_mean']} "
            f"weak_mean={ordering['weak_mean']} margin={ordering['margin']} "
            f"(required >= {ordering['required_margin']}) -> "
            f"{'PASS' if ordering_ok else 'FAIL'}"
        )
    else:
        ordering_ok = True
        print(f"ordering: skipped ({ordering['reason']})")
    (out / "summary.json").write_text(
        json.dumps(
            {
                "passed": passed,
                "total": len(records),
                "ordering": ordering,
                "ordering_passed": ordering_ok,
            },
            indent=2,
        ),
        encoding="utf-8",
    )
    clean = passed == len(records) and ordering_ok
    print(f"summary: {passed}/{len(records)} passed | ordering "
          f"{'ok' if ordering_ok else 'FAILED'} -> {out}")
    print("Mismatches need human triage (live web shifts). Never gate CI on this script.")
    return 0 if clean else 1


if __name__ == "__main__":
    sys.exit(main())
