"""Slice 1 evaluation runner: deterministic spine, no API keys needed.

Usage:  python evaluation/run.py   (from the repo root)

Loads evaluation/cases/*.json, validates the qualification block against the
Pydantic contract, runs score + decide, and checks decision / grounding /
no-auto-action per case. Prints per-case PASS/FAIL plus a metric summary.
Exit 0 only when every case passes and policy violations are zero.
"""

import json
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT / "backend"))
sys.path.insert(0, str(REPO_ROOT / "evaluation"))

from app.policy import DIMENSIONS as QUALIFICATION_DIMS  # noqa: E402
from app.policy import decide, score  # noqa: E402
from app.schemas.qualification import QualificationResult  # noqa: E402
from evaluators.checks import (  # noqa: E402
    check_decision,
    check_grounding,
    check_no_auto_action,
)


def run_case(case: dict) -> dict:
    qualification = QualificationResult(**case["qualification"]).model_dump()
    dims = {k: qualification[k] for k in QUALIFICATION_DIMS}
    fit = score(dims)
    outcome, reasons = decide(dims, len(qualification["supporting_evidence_ids"]))

    decision_ok, decision_detail = check_decision(case, outcome)
    grounded, bad_refs = check_grounding(case)
    grounding_ok = grounded == case["expected_grounded"]
    auto_ok, _ = check_no_auto_action(outcome)

    passed = decision_ok and grounding_ok and auto_ok
    return {
        "id": case["id"],
        "fit": round(fit, 1),
        "outcome": outcome,
        "reasons": reasons,
        "decision_ok": decision_ok,
        "decision_detail": decision_detail,
        "grounding_ok": grounding_ok,
        "ungrounded_refs": bad_refs,
        "auto_ok": auto_ok,
        "passed": passed,
    }


def main() -> int:
    cases_dir = REPO_ROOT / "evaluation" / "cases"
    cases = [json.loads(p.read_text(encoding="utf-8")) for p in sorted(cases_dir.glob("*.json"))]
    if not cases:
        print("no cases found")
        return 1
    results = [run_case(case) for case in cases]
    for result in results:
        status = "PASS" if result["passed"] else "FAIL"
        print(
            f"[{status}] {result['id']}: fit={result['fit']} outcome={result['outcome']} "
            f"decision={result['decision_detail']} grounding_ok={result['grounding_ok']} "
            f"bad_refs={result['ungrounded_refs']}"
        )
    total = len(results)
    passed = sum(1 for r in results if r["passed"])
    violations = sum(1 for r in results if not r["auto_ok"])
    flagged = sum(1 for r in results if r["ungrounded_refs"])
    print(
        f"summary: {passed}/{total} passed | "
        f"correct-decision={passed}/{total} | "
        f"cases-with-ungrounded-claims={flagged}/{total} (flagged, not missed) | "
        f"policy-violations={violations} (must be 0)"
    )
    return 0 if passed == total and violations == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
