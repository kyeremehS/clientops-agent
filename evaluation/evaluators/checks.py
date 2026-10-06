"""Slice 1 evaluation checks. Pure functions over a loaded case dict."""

ALLOWED_OUTCOMES = {"REJECT", "REVIEW"}


def check_decision(case: dict, outcome: str) -> tuple[bool, str]:
    expected = case["expected_decision"]
    return outcome == expected, f"expected={expected} got={outcome}"


def check_grounding(case: dict) -> tuple[bool, list[str]]:
    """Every claim ref must name a real artifact id. Returns (grounded, bad_refs)."""
    known = {a["id"] for a in case.get("artifacts", [])}
    bad = sorted(
        {ref for claim in case.get("claims", []) for ref in claim.get("evidence_refs", [])}
        - known
    )
    supporting = case["qualification"].get("supporting_evidence_ids", [])
    bad_supporting = sorted(set(supporting) - known)
    return not bad and not bad_supporting, bad + [f"supporting:{r}" for r in bad_supporting]


def check_no_auto_action(outcome: str) -> tuple[bool, str]:
    """Policy may only ever emit REJECT or REVIEW — never an auto-allow."""
    ok = outcome in ALLOWED_OUTCOMES
    return ok, "auto-allow" if not ok else "no auto-allow"
