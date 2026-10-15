"""Live-eval check helpers. Canned summaries only — the live path never runs here."""

import pytest

from live_eval import ORDERING_MARGIN, check_case, check_ordering


def _result(**overrides):
    base = {
        "case": "x",
        "outcome": "REVIEW",
        "fit": 66.7,
        "approval_id": "00000000-0000-0000-0000-000000000001",
        "reasons": ["qualified_for_review"],
        "claims": [{"claim": "Runs trucks.", "source_urls": ["https://a.test/"]}],
        "artifact_urls": ["https://a.test/"],
        "actions": 0,
    }
    return {**base, **overrides}


def _expect(**overrides):
    base = {"expected_outcome": "REVIEW", "require_approval": True, "forbid_action": True}
    return {**base, **overrides}


def test_check_case_pass():
    """Matching outcome, fit floor met, approval present, citations grounded."""
    verdict = check_case(_expect(min_fit=40), _result())
    assert verdict == {"passed": True, "failures": []}


def test_check_case_outcome_mismatch():
    """Wrong outcome fails with both values named."""
    verdict = check_case(_expect(), _result(outcome="REJECT"))
    assert verdict["passed"] is False
    assert any("REJECT" in f and "REVIEW" in f for f in verdict["failures"])


def test_check_case_fit_floor():
    """Fit below the floor fails even when the outcome matches."""
    verdict = check_case(_expect(min_fit=40), _result(fit=33.3))
    assert verdict["passed"] is False
    assert any("33.3" in f for f in verdict["failures"])


def test_check_case_accepts_outcome_list():
    """Both escalating outcomes are correct for a weak-signal company."""
    for outcome in ("REVIEW", "REJECT"):
        verdict = check_case(
            _expect(expected_outcome=["REVIEW", "REJECT"]), _result(outcome=outcome)
        )
        assert verdict["passed"] is True


def _record(case_id: str, role: str, fit: float, outcome: str = "REVIEW") -> dict:
    return {
        "case": case_id,
        "expectations": {"id": case_id, "role": role},
        "result": _result(outcome=outcome, fit=fit),
        "passed": True,
        "failures": [],
    }


def test_ordering_passes_when_strong_beats_weak():
    """The discriminator: strong-fit leads must outscore weak-fit ones."""
    records = [
        _record("s1", "strong", 90.0),
        _record("w1", "weak", 45.0),
        _record("s2", "strong", 70.0),
        _record("w2", "weak", 50.0),
    ]
    verdict = check_ordering(records)
    assert verdict["applicable"] and verdict["passed"] is True
    assert verdict["margin"] == pytest.approx(32.5, abs=0.1)


def test_ordering_fails_when_no_discrimination():
    """Everything scoring alike means the system cannot tell lead quality."""
    verdict = check_ordering(
        [_record("s1", "strong", 80.0), _record("w1", "weak", 78.0)]
    )
    assert verdict["applicable"] and verdict["passed"] is False
    assert verdict["margin"] < ORDERING_MARGIN


def test_ordering_skipped_without_both_roles():
    """Thin-evidence-only runs have nothing to compare."""
    verdict = check_ordering([_record("t1", "thin", 0.0)])
    assert verdict["applicable"] is False


def test_check_case_artifact_urls_are_isolated_set():
    """Grounding must compare against fetched artifacts only."""
    result = _result(
        claims=[{"claim": "x", "source_urls": ["https://a.test"]}], artifact_urls=[]
    )
    assert check_case(_expect(), result)["passed"] is False


def test_check_case_fit_ceiling():
    """A boring company scoring highly fails the inflation check."""
    verdict = check_case(_expect(max_fit=40), _result(fit=66.7))
    assert verdict["passed"] is False
    assert any("66.7" in f for f in verdict["failures"])


def test_check_case_missing_approval():
    """REVIEW without a pending approval fails the human-gate check."""
    verdict = check_case(_expect(), _result(approval_id=None))
    assert verdict["passed"] is False
    assert any("approval" in f for f in verdict["failures"])


def test_check_case_action_taken():
    """Any external action row means the human gate was bypassed."""
    verdict = check_case(_expect(), _result(actions=1))
    assert verdict["passed"] is False
    assert any("bypassed" in f for f in verdict["failures"])


def test_check_case_ungrounded_citation():
    """Citations must name fetched artifacts; unknown urls fail grounding."""
    verdict = check_case(
        _expect(),
        _result(
            claims=[{"claim": "Hunch.", "source_urls": ["https://evil.test/"]}],
            artifact_urls=["https://a.test/"],
        ),
    )
    assert verdict["passed"] is False
    assert any("evil.test" in f for f in verdict["failures"])
