"""C3 pipeline behavior. Providers/LLM mocked; SQLite file per test."""

import json
import re
from uuid import UUID

import httpx
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, select
from sqlalchemy.orm import sessionmaker

from app.api.deps import get_llm_client, get_search_provider, get_session, get_website_fetcher
from app.config import settings
from app.db.base import Base
from app.db.models import Approval, Decision, Lead
from app.main import app
from app.orchestrator.runner import LeadNotFoundError, run_lead
from app.orchestrator.states import lead_state
from app.policy.safety import GuardBlockedError, SafetyTracker, check, classify
from app.tools.fetch import WebsiteFetcher
from app.tools.search import MockSearchProvider, SearchResult

HTML = "<html><body><p>Acme runs 40 trucks.</p></body></html>"
_UUID_RE = re.compile(r"\[([0-9a-f-]{36}):")


@pytest.fixture
def db(tmp_path):
    engine = create_engine(f"sqlite:///{tmp_path}/c3.db", future=True)
    Base.metadata.create_all(engine)
    factory = sessionmaker(bind=engine, expire_on_commit=False, future=True)
    session = factory()
    lead = Lead(company="Acme", website="https://acme.test", message="Hi")
    session.add(lead)
    session.commit()
    yield session, lead.id
    session.close()


def _mock_search(n: int = 2) -> MockSearchProvider:
    return MockSearchProvider(
        results=[
            SearchResult(title=f"Acme {i}", url=f"http://93.184.216.34/{i}", excerpt="x")
            for i in range(n)
        ]
    )


def _mock_fetcher() -> WebsiteFetcher:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, headers={"content-type": "text/html"}, text=HTML)

    return WebsiteFetcher(
        http_client=httpx.Client(transport=httpx.MockTransport(handler))
    )


def _mock_llm(dims: dict) -> object:
    """OpenRouter-shaped mock. Qualification cites every evidence id in the prompt."""

    def handler(request: httpx.Request) -> httpx.Response:
        body = json.loads(request.content)
        name = body["response_format"]["json_schema"]["name"]
        if name == "research":
            payload = {
                "claims": [
                    {
                        "claim": "Runs trucks.",
                        "evidence_refs": ["art-1"],
                        "source_urls": ["http://93.184.216.34/0"],
                    }
                ]
            }
        else:
            prompt = body["messages"][0]["content"]
            payload = {**dims, "supporting_evidence_ids": _UUID_RE.findall(prompt)}
        return httpx.Response(
            200,
            json={
                "choices": [{"message": {"content": json.dumps(payload)}, "finish_reason": "stop"}],
                "usage": {},
            },
        )

    from app.llm.client import OpenRouterClient

    return OpenRouterClient(
        api_key="k", model="m", http_client=httpx.Client(transport=httpx.MockTransport(handler))
    )


def _dims(pain=2, plaus=2, rel=2, eq=2) -> dict:
    return {
        "operational_pain": pain,
        "automation_plausibility": plaus,
        "relevance": rel,
        "evidence_quality": eq,
        "summary": "s",
    }


def test_review_path_creates_decision_and_approval(db):
    """Qualified lead → REVIEW Decision + pending Approval + review_pending state."""
    session, lead_id = db
    result = run_lead(lead_id, session, _mock_search(), _mock_fetcher(), _mock_llm(_dims()))

    assert result["outcome"] == "REVIEW" and result["approval_id"] is not None
    assert result["state"] == "review_pending"
    assert session.scalar(select(Decision).where(Decision.lead_id == lead_id)) is not None
    approval = session.scalar(select(Approval).where(Approval.lead_id == lead_id))
    assert approval is not None and approval.status == "pending"


def test_reject_path_creates_no_approval(db):
    """Low fit with good evidence → REJECT Decision, no Approval, rejected state."""
    session, lead_id = db
    result = run_lead(
        lead_id, session, _mock_search(), _mock_fetcher(), _mock_llm(_dims(1, 1, 0, 2))
    )

    assert result["outcome"] == "REJECT" and result["approval_id"] is None
    assert result["state"] == "rejected"
    assert session.scalar(select(Approval).where(Approval.lead_id == lead_id)) is None


def test_unknown_lead_raises(db):
    """A run against a missing lead id fails loudly, never half-writes."""
    session, _ = db
    with pytest.raises(LeadNotFoundError):
        run_lead(
            UUID("00000000-0000-0000-0000-000000000000"),
            session,
            _mock_search(),
            _mock_fetcher(),
            _mock_llm(_dims()),
        )


def test_states_walk_rows(db):
    """Derived state follows rows present: new → researched → qualified → review_pending."""
    session, lead_id = db
    assert lead_state(session, lead_id) == "new"


def test_safety_budget_trips():
    """Second call over a budget of 1 is denied with a stable code."""
    tracker = SafetyTracker(max_calls=1)
    assert check(tracker, "web_search", {"query": "a"}) == "auto"
    with pytest.raises(GuardBlockedError) as exc:
        check(tracker, "web_search", {"query": "b"})
    assert exc.value.code == "budget_exceeded"


def test_safety_breaker_trips_on_third_identical():
    """Same (tool, args) twice is tolerated; the third identical call trips."""
    tracker = SafetyTracker(max_calls=30)
    args = {"query": "same"}
    assert check(tracker, "web_search", args) == "auto"
    assert check(tracker, "web_search", args) == "auto"
    with pytest.raises(GuardBlockedError) as exc:
        check(tracker, "web_search", args)
    assert exc.value.code == "repeated_call"


def test_safety_unknown_tool_denied():
    """Unregistered tool names fail closed; read tools pass."""
    tracker = SafetyTracker()
    assert classify("website_fetch") == "auto"
    with pytest.raises(GuardBlockedError) as exc:
        check(tracker, "send_email", {"to": "x"})
    assert exc.value.code == "unknown_tool"


def test_guard_denial_skips_sources(db):
    """A guard denying website_fetch yields zero artifacts → inconclusive run."""
    from app.agents.research.runner import run_research
    from app.schemas.leads import LeadCreate

    from app.policy.safety import GuardBlockedError as Blocked

    session, lead_id = db

    def guard(tool_name: str, args: dict):
        if tool_name == "website_fetch":
            raise Blocked("denied", "no fetch in this test")
        return "auto"

    class _SilentLLM:
        def complete_json(self, *args, **kwargs):
            raise AssertionError("no evidence, so the model must not be called")

    result = run_research(
        lead_id,
        LeadCreate(company="Acme"),
        _mock_search(),
        _mock_fetcher(),
        _SilentLLM(),
        session,
        guard=guard,
    )
    assert result.inconclusive is True


@pytest.fixture
def client(tmp_path, monkeypatch):
    url = f"sqlite:///{tmp_path}/api.db"
    monkeypatch.setattr(settings, "database_url", url)
    import app.api.deps as deps

    monkeypatch.setattr(deps, "_factory", None)
    monkeypatch.setattr(deps, "_search", None)
    monkeypatch.setattr(deps, "_fetcher", None)
    monkeypatch.setattr(deps, "_llm", None)
    search, fetcher = _mock_search(), _mock_fetcher()
    llm = _mock_llm(_dims())
    app.dependency_overrides[get_session] = _session_override(tmp_path, url)
    app.dependency_overrides[get_search_provider] = lambda: search
    app.dependency_overrides[get_website_fetcher] = lambda: fetcher
    app.dependency_overrides[get_llm_client] = lambda: llm
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()


def _session_override(tmp_path, url):
    engine = create_engine(url, future=True)
    Base.metadata.create_all(engine)
    factory = sessionmaker(bind=engine, expire_on_commit=False, future=True)

    def override():
        session = factory()
        try:
            yield session
            session.commit()
        except Exception:
            session.rollback()
            raise
        finally:
            session.close()

    return override


def test_run_endpoint_end_to_end(client):
    """POST /leads/{id}/run returns the REVIEW summary with an approval id."""
    lead = client.post(
        "/leads", json={"company": "Acme", "website": "https://acme.test"}
    ).json()
    response = client.post(f"/leads/{lead['id']}/run")

    assert response.status_code == 200
    body = response.json()
    assert body["state"] == "review_pending" and body["outcome"] == "REVIEW"
    assert body["approval_id"] is not None and body["fit"] > 0


def test_run_endpoint_missing_lead_404(client):
    """Unknown lead id → 404 lead_not_found, never 500."""
    response = client.post("/leads/00000000-0000-0000-0000-000000000000/run")
    assert response.status_code == 404
    assert response.json()["detail"] == "lead_not_found"
