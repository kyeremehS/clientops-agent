"""Run result schema. Single source of truth for the run endpoint contract."""

from uuid import UUID

from pydantic import BaseModel


class RunRead(BaseModel):
    lead_id: UUID
    state: str
    outcome: str
    fit: float
    approval_id: UUID | None = None
    reasons: list[str] = []
