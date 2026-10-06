"""B3: deterministic scoring + policy branches. No I/O, no model, no DB."""

import pytest

from app.policy import FIT_REJECT_BELOW, REJECT, REVIEW, decide, score


def _dims(pain=2, plaus=2, rel=2, eq=2) -> dict:
    return {
        "operational_pain": pain,
        "automation_plausibility": plaus,
        "relevance": rel,
        "evidence_quality": eq,
    }


def test_score_math():
    assert score(_dims(3, 3, 3, 3)) == 100.0
    assert score(_dims(0, 0, 0, 0)) == 0.0
    assert score(_dims(2, 2, 2, 2)) == pytest.approx(66.67, abs=0.01)


def test_llm_cannot_invent_score():
    # Score is derived here; there is no input slot for a model-made 0-100.
    assert score(_dims(2, 2, 2, 2)) != 84.0


def test_evidence_quality_0_goes_to_review():
    outcome, reasons = decide(_dims(eq=0), supporting_count=5)
    assert outcome == REVIEW
    assert any("insufficient_evidence" in r for r in reasons)


def test_evidence_quality_1_goes_to_review():
    outcome, _ = decide(_dims(eq=1), supporting_count=5)
    assert outcome == REVIEW


def test_single_supporting_item_goes_to_review():
    outcome, reasons = decide(_dims(eq=3), supporting_count=1)
    assert outcome == REVIEW
    assert any("fewer_than_2" in r for r in reasons)


def test_low_fit_rejects_with_sufficient_evidence():
    # sum=4 -> 33.3 < 40, eq=2, count=2
    outcome, reasons = decide(_dims(pain=1, plaus=1, rel=0, eq=2), supporting_count=2)
    assert outcome == REJECT
    assert any(str(int(FIT_REJECT_BELOW)) in r for r in reasons)


def test_sufficient_case_goes_to_review_not_auto_action():
    outcome, _ = decide(_dims(2, 2, 2, 2), supporting_count=2)
    assert outcome == REVIEW  # human approval still required; never auto-allow


def test_bad_dimensions_fail_closed():
    with pytest.raises(ValueError):
        score(_dims(eq=9))
    with pytest.raises(ValueError):
        score({**_dims(), "evidence_quality": -1})
    with pytest.raises(ValueError):
        decide(_dims(), supporting_count=-1)
    with pytest.raises(ValueError):
        score({"operational_pain": 2})  # missing dimensions
