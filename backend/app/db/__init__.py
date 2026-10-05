"""DB package: models, base, and event-chain helpers."""

from app.db.base import Base, get_engine, get_session_factory, session_scope
from app.db.events import (
    append_audit_event,
    approval_expiry,
    is_approval_expired,
    latest_event_id,
    sha256_hex,
)
from app.db.models import (
    APPROVAL_TTL_HOURS,
    Action,
    Approval,
    AuditEvent,
    Decision,
    Lead,
    Qualification,
    ResearchArtifact,
    utcnow,
)

__all__ = [
    "APPROVAL_TTL_HOURS",
    "Action",
    "Approval",
    "AuditEvent",
    "Base",
    "Decision",
    "Lead",
    "Qualification",
    "ResearchArtifact",
    "append_audit_event",
    "approval_expiry",
    "get_engine",
    "get_session_factory",
    "is_approval_expired",
    "latest_event_id",
    "session_scope",
    "sha256_hex",
    "utcnow",
]
