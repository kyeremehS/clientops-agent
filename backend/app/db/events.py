"""Audit-chain + approval-expiry helpers. Deterministic, no LLM calls."""

import hashlib
from datetime import datetime, timedelta, timezone
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.models import APPROVAL_TTL_HOURS, Approval, AuditEvent, utcnow
from app.schemas.common import ApprovalStatus


def sha256_hex(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def approval_expiry(requested_at: datetime) -> datetime:
    return requested_at + timedelta(hours=APPROVAL_TTL_HOURS)


def create_approval(session: Session, lead_id: UUID) -> Approval:
    """Create a pending approval + audit event. Shared by the API and the pipeline."""
    requested_at = utcnow()
    approval = Approval(
        lead_id=lead_id,
        status=ApprovalStatus.PENDING,
        requested_at=requested_at,
        expires_at=approval_expiry(requested_at),
    )
    session.add(approval)
    session.flush()
    append_audit_event(session, lead_id, "approval.requested")
    return approval


def _as_aware(moment: datetime) -> datetime:
    """SQLite returns naive datetimes; Postgres returns aware. Normalize to UTC."""
    if moment.tzinfo is None:
        return moment.replace(tzinfo=timezone.utc)
    return moment


def is_approval_expired(expires_at: datetime, now: datetime | None = None) -> bool:
    return _as_aware(now or utcnow()) >= _as_aware(expires_at)


def latest_event_id(session: Session, lead_id: UUID) -> UUID | None:
    stmt = (
        select(AuditEvent.event_id)
        .where(AuditEvent.lead_id == lead_id)
        .order_by(AuditEvent.timestamp.desc())
    )
    return session.scalar(stmt)


def append_audit_event(
    session: Session,
    lead_id: UUID,
    event_type: str,
    actor: str = "system",
    payload: dict | None = None,
    content_hash: str | None = None,
) -> AuditEvent:
    event = AuditEvent(
        lead_id=lead_id,
        event_type=event_type,
        actor=actor,
        payload=payload or {},
        previous_event_id=latest_event_id(session, lead_id),
        content_hash=content_hash,
    )
    session.add(event)
    session.flush()
    return event
