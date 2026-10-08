"""Qualification runner. Reasons over artifacts; receives no tools by construction."""

from sqlalchemy.orm import Session

from app.llm.client import OpenRouterClient
from app.schemas.leads import LeadCreate
from app.schemas.qualification import QualificationResult


def run_qualification(
    lead: LeadCreate,
    artifacts: list[dict],
    llm: OpenRouterClient,
    session: Session,
) -> QualificationResult:
    """Rate dimensions, persist the qualification row, return code-computed score inputs."""
    raise NotImplementedError
