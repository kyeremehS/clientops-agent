"""Lead state derived from rows present. No status column, one source of truth.

Terminal states (rejected, actioned, expired) come from written rows, never
from memory. Transient in-run steps (researching, qualifying) appear as
audit events while the run executes, not as stored state.
"""

from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.events import is_approval_expired
from app.db.models import Action, Approval, Decision, Qualification, ResearchArtifact
from app.schemas.common import ApprovalStatus, DecisionOutcome


def lead_state(session: Session, lead_id: UUID) -> str:
    """Return the workflow state name for a lead (see docs/workflow.md)."""
    approval = session.scalar(select(Approval).where(Approval.lead_id == lead_id))
    if approval is not None:
        if (
            session.scalar(select(Action.id).where(Action.approval_id == approval.id))
            is not None
        ):
            return "actioned"
        if approval.status == ApprovalStatus.APPROVED:
            return "approved"
        if approval.status == ApprovalStatus.REJECTED:
            return "rejected_by_human"
        if approval.status == ApprovalStatus.EXPIRED or is_approval_expired(
            approval.expires_at
        ):
            return "expired"
        return "review_pending"
    decision = session.scalar(select(Decision).where(Decision.lead_id == lead_id))
    if decision is not None:
        if decision.outcome == DecisionOutcome.REJECT:
            return "rejected"
        return "qualified"
    if (
        session.scalar(select(Qualification.id).where(Qualification.lead_id == lead_id))
        is not None
    ):
        return "qualified"
    if (
        session.scalar(
            select(ResearchArtifact.id).where(ResearchArtifact.lead_id == lead_id)
        )
        is not None
    ):
        return "researched"
    return "new"
