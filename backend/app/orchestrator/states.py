"""Lead state derived from rows present. No status column, one source of truth."""

from uuid import UUID

from sqlalchemy.orm import Session


def lead_state(session: Session, lead_id: UUID) -> str:
    """Return the workflow state name for a lead (see docs/workflow.md)."""
    raise NotImplementedError
