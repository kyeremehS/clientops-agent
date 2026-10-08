"""Shared vocabulary. One definition per status word — import, never retype."""

from enum import StrEnum


class ApprovalStatus(StrEnum):
    """Approval lifecycle. Terminal states never transition again."""

    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"
    EXPIRED = "expired"


class DecisionOutcome(StrEnum):
    """Policy outcomes. Zero automatic external action in Slice 1."""

    REJECT = "REJECT"
    REVIEW = "REVIEW"
