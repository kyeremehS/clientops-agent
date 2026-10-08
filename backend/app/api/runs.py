"""Run endpoint: execute the full pipeline synchronously for one lead."""

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.api.deps import get_llm_client, get_search_provider, get_session, get_website_fetcher
from app.config import settings
from app.llm.client import OpenRouterClient
from app.orchestrator.runner import LeadNotFoundError, run_lead
from app.schemas.runs import RunRead
from app.tools.fetch import WebsiteFetcher
from app.tools.search import SearchProvider

router = APIRouter()


@router.post("/leads/{lead_id}/run", response_model=RunRead)
def run_lead_endpoint(
    lead_id: UUID,
    session: Session = Depends(get_session),
    search: SearchProvider = Depends(get_search_provider),
    fetcher: WebsiteFetcher = Depends(get_website_fetcher),
    llm: OpenRouterClient = Depends(get_llm_client),
) -> dict:
    try:
        return run_lead(
            lead_id,
            session,
            search,
            fetcher,
            llm,
            max_results=settings.search_max_results,
        )
    except LeadNotFoundError:
        raise HTTPException(status_code=404, detail="lead_not_found")
