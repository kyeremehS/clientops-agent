"""Research runner. Fixed query plan in code; LLM synthesizes claims only."""

from collections.abc import Callable
from uuid import UUID

from sqlalchemy.orm import Session

from app.agents.research.prompts import build_claim_queries, build_research_prompt
from app.db.models import ResearchArtifact
from app.llm import GroqClient, OpenRouterClient
from app.policy.safety import GuardBlockedError
from app.schemas.leads import LeadCreate
from app.schemas.research import ResearchResult
from app.tools.fetch import FetchError, WebsiteFetcher
from app.tools.search import SearchError, SearchProvider


def run_research(
    lead_id: UUID,
    lead: LeadCreate,
    search: SearchProvider,
    fetcher: WebsiteFetcher,
    llm: OpenRouterClient | GroqClient,
    session: Session,
    max_results: int = 5,
    guard: Callable[[str, dict], str | None] | None = None,
) -> ResearchResult:
    """Run the fixed plan, persist artifacts, return synthesized claims.

    Fetch/search failures are skipped per source (recorded nowhere — an
    unfetched URL simply yields no artifact). Claims without cited sources
    are dropped; with zero usable claims the result is inconclusive.
    When guard is set, every search/fetch passes through it first and
    denied calls are skipped like failures.
    """
    artifacts: list[ResearchArtifact] = []
    for query in build_claim_queries(lead.company):
        if not _allowed(guard, "web_search", {"query": query, "max_results": max_results}):
            continue
        try:
            results = search.search(query, max_results=max_results)
        except SearchError:
            continue
        for item in results:
            if not item.url:
                continue
            if not _allowed(guard, "website_fetch", {"url": item.url}):
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
        return ResearchResult(claims=[], inconclusive=True, note="no fetchable evidence found")

    parsed, _ = llm.complete_json(
        [{"role": "user", "content": build_research_prompt(lead, evidence)}],
        ResearchResult,
        "research",
    )
    claims = [c for c in parsed.claims if c.source_urls]
    if not claims:
        return ResearchResult(
            claims=[], inconclusive=True, note="no sourced claims synthesized"
        )
    # Claims may only cite pages we actually fetched. A model citing a URL it
    # remembers from training is hallucinated grounding — drop it, exactly as
    # the qualification runner drops invented evidence ids.
    fetched = {a.source_url for a in artifacts}
    grounded = [c for c in claims if set(c.source_urls) <= fetched]
    if not grounded:
        return ResearchResult(
            claims=[],
            inconclusive=True,
            note=f"{len(claims)} claims dropped: cited URLs outside fetched evidence",
        )
    return ResearchResult(claims=grounded, inconclusive=False, note=parsed.note)


def _allowed(
    guard: Callable[[str, dict], str | None] | None, tool_name: str, args: dict
) -> bool:
    """Run one call through the safety guard. Denied calls are skipped."""
    if guard is None:
        return True
    try:
        guard(tool_name, args)
    except GuardBlockedError:
        return False
    return True
