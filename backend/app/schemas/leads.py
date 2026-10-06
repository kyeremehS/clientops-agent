"""API schemas. Pydantic is the single source of truth for the contract."""

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel


class LeadCreate(BaseModel):
    company: str
    website: str = ""
    contact: str = ""
    message: str = ""


class LeadRead(BaseModel):
    id: UUID
    company: str
    website: str
    contact: str
    message: str
    created_at: datetime


class ApprovalRead(BaseModel):
    id: UUID
    lead_id: UUID
    status: str
    requested_at: datetime
    expires_at: datetime
    decided_at: datetime | None
