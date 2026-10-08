"""Leads + approvals router. UI never executes actions — it only records decisions.

Every state-changing call re-validates: exists → pending → not expired.
Late approve/reject → 409 approval_expired and the approval is marked expired.
"""

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.deps import get_session
from app.db.events import (
    append_audit_event,
    create_approval,
    is_approval_expired,
    utcnow,
)
from app.db.models import Approval, Lead
from app.schemas.common import ApprovalStatus
from app.schemas.leads import ApprovalRead, LeadCreate, LeadRead

router = APIRouter()


def _get_lead_or_404(session: Session, lead_id: UUID) -> Lead:
    lead = session.get(Lead, lead_id)
    if lead is None:
        raise HTTPException(status_code=404, detail="lead_not_found")
    return lead


def _get_approval_or_404(session: Session, approval_id: UUID) -> Approval:
    approval = session.get(Approval, approval_id)
    if approval is None:
        raise HTTPException(status_code=404, detail="approval_not_found")
    return approval


def _require_actionable(approval: Approval) -> None:
    if approval.status != ApprovalStatus.PENDING:
        raise HTTPException(status_code=409, detail="wrong_state")
    if is_approval_expired(approval.expires_at):
        raise HTTPException(status_code=409, detail="approval_expired")


@router.post("/leads", response_model=LeadRead, status_code=201)
def create_lead(payload: LeadCreate, session: Session = Depends(get_session)) -> Lead:
    lead = Lead(
        company=payload.company,
        website=payload.website,
        contact=payload.contact,
        message=payload.message,
    )
    session.add(lead)
    session.flush()
    append_audit_event(session, lead.id, "run.created", payload={"company": lead.company})
    session.commit()
    session.refresh(lead)
    return lead


@router.get("/leads/{lead_id}", response_model=LeadRead)
def get_lead(lead_id: UUID, session: Session = Depends(get_session)) -> Lead:
    return _get_lead_or_404(session, lead_id)


@router.get("/approvals/pending", response_model=list[ApprovalRead])
def list_pending_approvals(session: Session = Depends(get_session)) -> list[Approval]:
    stmt = select(Approval).where(Approval.status == ApprovalStatus.PENDING).order_by(Approval.requested_at)
    return list(session.scalars(stmt))


@router.post("/leads/{lead_id}/approvals", response_model=ApprovalRead, status_code=201)
def request_approval(lead_id: UUID, session: Session = Depends(get_session)) -> Approval:
    _get_lead_or_404(session, lead_id)
    existing = session.scalar(select(Approval).where(Approval.lead_id == lead_id))
    if existing is not None and existing.status == ApprovalStatus.PENDING:
        raise HTTPException(status_code=409, detail="wrong_state")
    if existing is not None and existing.status == ApprovalStatus.APPROVED:
        raise HTTPException(status_code=409, detail="wrong_state")
    approval = create_approval(session, lead_id)
    session.commit()
    session.refresh(approval)
    return approval


@router.post("/approvals/{approval_id}/approve", response_model=ApprovalRead)
def approve(approval_id: UUID, session: Session = Depends(get_session)) -> Approval:
    approval = _get_approval_or_404(session, approval_id)
    try:
        _require_actionable(approval)
    except HTTPException as exc:
        if exc.detail == "approval_expired":
            approval.status = ApprovalStatus.EXPIRED
            approval.decided_at = utcnow()
            append_audit_event(session, approval.lead_id, "approval.expired")
            session.commit()
        raise
    approval.status = ApprovalStatus.APPROVED
    approval.decided_at = utcnow()
    append_audit_event(session, approval.lead_id, "approval.approved", actor="human")
    session.commit()
    session.refresh(approval)
    return approval


@router.post("/approvals/{approval_id}/reject", response_model=ApprovalRead)
def reject(approval_id: UUID, session: Session = Depends(get_session)) -> Approval:
    approval = _get_approval_or_404(session, approval_id)
    try:
        _require_actionable(approval)
    except HTTPException as exc:
        if exc.detail == "approval_expired":
            approval.status = ApprovalStatus.EXPIRED
            approval.decided_at = utcnow()
            append_audit_event(session, approval.lead_id, "approval.expired")
            session.commit()
        raise
    approval.status = ApprovalStatus.REJECTED
    approval.decided_at = utcnow()
    append_audit_event(session, approval.lead_id, "approval.rejected", actor="human")
    session.commit()
    session.refresh(approval)
    return approval
