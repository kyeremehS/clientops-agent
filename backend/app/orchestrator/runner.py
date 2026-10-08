"""End-to-end run pipeline: research → qualify → decide → approval."""

from uuid import UUID

from sqlalchemy.orm import Session

from app.llm.client import OpenRouterClient
from app.tools.fetch import WebsiteFetcher
from app.tools.search import SearchProvider


def run_lead(
    lead_id: UUID,
    session: Session,
    search: SearchProvider,
    fetcher: WebsiteFetcher,
    llm: OpenRouterClient,
    max_results: int = 5,
    tool_budget: int = 30,
) -> dict:
    """Execute one full pass and return {lead_id, state, outcome, fit, ...}."""
    raise NotImplementedError
