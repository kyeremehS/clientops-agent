"""Research runner. Fixed query plan in code; LLM synthesizes claims only."""

from sqlalchemy.orm import Session

from app.llm.client import OpenRouterClient
from app.schemas.leads import LeadCreate
from app.schemas.research import ResearchResult
from app.tools.fetch import WebsiteFetcher
from app.tools.search import SearchProvider


def run_research(
    lead: LeadCreate,
    search: SearchProvider,
    fetcher: WebsiteFetcher,
    llm: OpenRouterClient,
    session: Session,
    max_results: int = 5,
) -> ResearchResult:
    """Run the fixed plan, persist artifacts, return synthesized claims."""
    raise NotImplementedError
