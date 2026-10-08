"""Live-eval check helpers. Canned summaries only — the live path never runs here."""

from live_eval import check_case


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
