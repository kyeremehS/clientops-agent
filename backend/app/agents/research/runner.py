"""Research runner. Fixed query plan in code; LLM synthesizes claims only."""

from uuid import UUID

from sqlalchemy.orm import Session

from app.agents.research.prompts import build_claim_queries, build_research_prompt
from app.db.models import ResearchArtifact
from app.llm.client import OpenRouterClient
from app.schemas.leads import LeadCreate
from app.schemas.research import ResearchResult
from app.tools.fetch import FetchError, WebsiteFetcher
from app.tools.search import SearchError, SearchProvider


def run_research(
    lead_id: UUID,
    lead: LeadCreate,
    search: SearchProvider,
    fetcher: WebsiteFetcher,
    llm: OpenRouterClient,
    session: Session,
    max_results: int = 5,
) -> ResearchResult:
    """Run the fixed plan, persist artifacts, return synthesized claims.

    Fetch/search failures are skipped per source (recorded nowhere — an
    unfetched URL simply yields no artifact). Claims without cited sources
    are dropped; with zero usable claims the result is inconclusive.
    """
    artifacts: list[ResearchArtifact] = []
    for query in build_claim_queries(lead.company):
        try:
            results = search.search(query, max_results=max_results)
        except SearchError:
            continue
        for item in results:
            if not item.url:
                continue
            try:
                fetched = fetcher.fetch(item.url)
            except FetchError:
                continue
            artifacts.append(
                ResearchArtifact(
                    lead_id=lead_id,
                    source_url=fetched.final_url or fetched.url,
                    content=fetched.text,
                    content_hash=fetched.content_hash,
                )
            )
    session.add_all(artifacts)
    session.commit()

    evidence = [
        {"id": str(a.id), "url": a.source_url, "text": a.content} for a in artifacts
    ]
    if not evidence:
        return ResearchResult(inconclusive=True, note="no fetchable evidence found")

    parsed, _ = llm.complete_json(
        [{"role": "user", "content": build_research_prompt(lead, evidence)}],
        ResearchResult,
        "research",
    )
    claims = [c for c in parsed.claims if c.source_urls]
    if not claims:
        return ResearchResult(inconclusive=True, note="no sourced claims synthesized")
    return ResearchResult(claims=claims, inconclusive=False, note=parsed.note)
