"""Qualification prompt builder. Text lands in the implementation step."""

from app.schemas.leads import LeadCreate


def build_qualification_prompt(lead: LeadCreate, evidence: list[dict]) -> str:
    """Ratings prompt over lead + artifacts. No tools, evidence only."""
    raise NotImplementedError
