"""Action schemas for the execute endpoint."""

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel


class ActionRead(BaseModel):
    id: UUID
    lead_id: UUID
    approval_id: UUID
    idempotency_key: str
    channel_id: str
    text: str
    result: str
    created_at: datetime
