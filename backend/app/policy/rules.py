"""Deterministic scoring + policy. Pure functions: no I/O, no LLM, no DB.

Locked rules (see docs/policy.md):
- score = sum(4 dims) / 12 * 100, computed here, never from the model.
- evidence_quality <= 1 → REVIEW (weak evidence escalates, never rejects).
- supporting items < 2 → REVIEW.
- score < 40 (with sufficient evidence) → REJECT.
- otherwise → REVIEW. Zero automatic external action in Slice 1.
"""

DIMENSIONS = (
    "operational_pain",
    "automation_plausibility",
    "relevance",
    "evidence_quality",
)

REJECT = "REJECT"
REVIEW = "REVIEW"

FIT_REJECT_BELOW = 40.0
MIN_SUPPORTING_ITEMS = 2
INSUFFICIENT_EVIDENCE_QUALITY = 1


def score(dimensions: dict[str, int]) -> float:
    """Compute fit 0-100 from the four 0-3 dimensions. Raises on bad input."""
    try:
        values = [dimensions[name] for name in DIMENSIONS]
    except KeyError as exc:
        raise ValueError(f"missing dimension: {exc}")
    for name, value in zip(DIMENSIONS, values):
        if not isinstance(value, int) or isinstance(value, bool) or not 0 <= value <= 3:
            raise ValueError(f"dimension {name} must be an int 0-3, got {value!r}")
    return sum(values) / 12 * 100


def decide(dimensions: dict[str, int], supporting_count: int) -> tuple[str, list[str]]:
    """Apply the locked policy. Returns (outcome, reasons)."""
    if supporting_count < 0:
        raise ValueError("supporting_count cannot be negative")
    fit = score(dimensions)
    if dimensions["evidence_quality"] <= INSUFFICIENT_EVIDENCE_QUALITY:
        return REVIEW, ["insufficient_evidence:weak_evidence_escalates"]
    if supporting_count < MIN_SUPPORTING_ITEMS:
        return REVIEW, ["insufficient_evidence:fewer_than_2_supporting_items"]
    if fit < FIT_REJECT_BELOW:
        return REJECT, [f"low_fit:{fit:.1f}_below_{FIT_REJECT_BELOW:.0f}"]
    return REVIEW, [f"qualified_for_review:fit_{fit:.1f}"]
