"""Research prompt builders. Text lands in the implementation step."""

from app.schemas.leads import LeadCreate


def build_claim_queries(company: str) -> list[str]:
    """Fixed 3-angle query plan. Plan text lands in the implementation step."""
    raise NotImplementedError


def build_research_prompt(lead: LeadCreate, evidence: list[dict]) -> str:
    """Synthesis prompt over code-gathered evidence. Implementation step."""
    raise NotImplementedError
