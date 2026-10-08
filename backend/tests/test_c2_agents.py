"""C2 agent behavior. LLM/search/fetch all mocked — no keys, no network."""

import json
from uuid import UUID

import httpx
import pytest
from sqlalchemy import create_engine, select
from sqlalchemy.orm import sessionmaker

from app.agents.qualification.runner import run_qualification
from app.agents.research.prompts import build_claim_queries
from app.agents.research.runner import run_research
from app.db.base import Base
from app.db.models import Lead, Qualification, ResearchArtifact
from app.llm.client import OpenRouterClient
from app.schemas.leads import LeadCreate
from app.tools.fetch import WebsiteFetcher
from app.tools.search import MockSearchProvider, SearchResult

HTML = "<html><body><p>Acme runs 40 trucks.</p></body></html>"


@pytest.fixture
def session(tmp_path):
    engine = create_engine(f"sqlite:///{tmp_path}/c2.db", future=True)
    Base.metadata.create_all(engine)
    factory = sessionmaker(bind=engine, expire_on_commit=False, future=True)
    db = factory()
    lead = Lead(company="Acme", website="https://acme.test", message="Hi")
    db.add(lead)
    db.commit()
    yield db, lead.id
    db.close()


def _lead() -> LeadCreate:
    return LeadCreate(company="Acme", website="https://acme.test", message="Hi")


def _mock_llm(payload: dict) -> OpenRouterClient:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(
            200,
            json={
                "choices": [{"message": {"content": json.dumps(payload)}, "finish_reason": "stop"}],
                "usage": {},
            },
        )

    return OpenRouterClient(
        api_key="k", model="m", http_client=httpx.Client(transport=httpx.MockTransport(handler))
    )


class _NeverCalledLLM:
    def complete_json(self, *args, **kwargs):
        raise AssertionError("llm must not be called")


def _mock_search() -> MockSearchProvider:
    return MockSearchProvider(
        results=[
            SearchResult(title="Acme", url="http://93.184.216.34/", excerpt="Runs trucks.")
        ]
    )


def _mock_fetcher(status: int = 200) -> WebsiteFetcher:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(status, headers={"content-type": "text/html"}, text=HTML)

    return WebsiteFetcher(
        http_client=httpx.Client(transport=httpx.MockTransport(handler))
    )


def test_claim_queries_fixed_three_angles():
    """Query plan is fixed data: profile, pain, news for the named company."""
    queries = build_claim_queries("Acme")
    assert len(queries) == 3
    assert all("Acme" in q for q in queries)
    with pytest.raises(ValueError):
        build_claim_queries("  ")


def test_research_writes_artifacts_and_maps_claims(session):
    """Happy path: 3 queries × 1 result → 3 hashed artifacts + sourced claim."""
    db, lead_id = session
    llm = _mock_llm(
        {
            "claims": [
                {
                    "claim": "Runs 40 trucks.",
                    "evidence_refs": ["art-1"],
                    "source_urls": ["http://93.184.216.34/"],
                }
            ],
            "inconclusive": False,
            "note": "",
        }
    )
    result = run_research(lead_id, _lead(), _mock_search(), _mock_fetcher(), llm, db)

    assert result.inconclusive is False
    assert result.claims[0].claim == "Runs 40 trucks."
    rows = db.scalars(select(ResearchArtifact)).all()
    assert len(rows) == 3
    assert all(len(r.content_hash) == 64 and "40 trucks" in r.content for r in rows)


def test_research_drops_unsourced_claims(session):
    """Claims without source_urls are discarded; none left → inconclusive."""
    db, lead_id = session
    llm = _mock_llm({"claims": [{"claim": "Hunch.", "evidence_refs": [], "source_urls": []}]})
    result = run_research(lead_id, _lead(), _mock_search(), _mock_fetcher(), llm, db)

    assert result.inconclusive is True and result.claims == []


def test_research_skips_failed_fetches(session):
    """HTTP 500 on every fetch → zero artifacts → inconclusive, model untouched."""
    db, lead_id = session
    result = run_research(
        lead_id, _lead(), _mock_search(), _mock_fetcher(status=500), _NeverCalledLLM(), db
    )

    assert result.inconclusive is True
    assert db.scalars(select(ResearchArtifact)).all() == []


def test_research_empty_search_is_inconclusive(session):
    """No search hits at all → inconclusive without calling the model."""
    db, lead_id = session
    result = run_research(
        lead_id, _lead(), MockSearchProvider(results=[]), _mock_fetcher(), _NeverCalledLLM(), db
    )

    assert result.inconclusive is True


def _seed_artifact(db, lead_id: UUID) -> str:
    row = ResearchArtifact(
        lead_id=lead_id,
        source_url="https://acme.test/",
        content="Acme runs 40 trucks.",
        content_hash="h" * 64,
    )
    db.add(row)
    db.commit()
    return str(row.id)


def test_qualification_persists_row_and_fit(session):
    """Dims + real supporting id → Qualification row with code-computed fit."""
    db, lead_id = session
    art_id = _seed_artifact(db, lead_id)
    llm = _mock_llm(
        {
            "operational_pain": 2,
            "automation_plausibility": 2,
            "relevance": 2,
            "evidence_quality": 2,
            "supporting_evidence_ids": [art_id],
            "summary": "Fleet ops look automatable.",
        }
    )
    result, fit = run_qualification(lead_id, _lead(), llm, db)

    assert fit == pytest.approx(66.67, abs=0.01)
    assert result.supporting_evidence_ids == [art_id]
    rows = db.scalars(select(Qualification)).all()
    assert len(rows) == 1 and rows[0].score == pytest.approx(66.67, abs=0.01)


def test_qualification_drops_invented_ids_and_caps_evidence(session):
    """supporting ids must name stored artifacts; invented → dropped, eq capped at 1."""
    db, lead_id = session
    _seed_artifact(db, lead_id)
    llm = _mock_llm(
        {
            "operational_pain": 3,
            "automation_plausibility": 3,
            "relevance": 3,
            "evidence_quality": 3,
            "supporting_evidence_ids": ["art-does-not-exist"],
            "summary": "Amazing.",
        }
    )
    result, _ = run_qualification(lead_id, _lead(), llm, db)

    assert result.supporting_evidence_ids == []
    assert result.evidence_quality == 1


def test_qualification_empty_evidence_skips_model(session):
    """No artifacts → all-zero dims with the fixed sentence, model never called."""
    db, lead_id = session
    result, fit = run_qualification(lead_id, _lead(), _NeverCalledLLM(), db)

    assert fit == 0.0
    assert result.summary == "no sufficiently supported automation opportunity found"
    assert db.scalars(select(Qualification)).all() != []
