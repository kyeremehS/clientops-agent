"""C7: lead-detail read endpoint. Seeds rows directly — a read needs no pipeline."""

from datetime import datetime, timedelta, timezone
from uuid import UUID

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from app.api.deps import get_session
from app.config import settings
from app.db.models import Approval, Decision, Lead, Qualification, ResearchArtifact
from app.main import app


@pytest.fixture
def setup(tmp_path, monkeypatch):
    url = f"sqlite:///{tmp_path}/detail.db"
    monkeypatch.setattr(settings, "database_url", url)
    monkeypatch.setattr(settings, "api_key", "test-key")
    engine = create_engine(url, future=True)
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

    app.dependency_overrides[get_session] = override
    with TestClient(app, headers={"Authorization": "Bearer test-key"}) as test_client:
        yield test_client, engine
    app.dependency_overrides.clear()


def _seed_full(engine, lead_id: UUID) -> None:
    with Session(engine) as session:
        session.add(
            ResearchArtifact(
                lead_id=lead_id,
                source_url="https://acme.test/about",
                content="x" * 2000,
                content_hash="h" * 64,
            )
        )
        session.add(
            Qualification(
                lead_id=lead_id,
                operational_pain=2,
                automation_plausibility=2,
                relevance=2,
                evidence_quality=2,
                supporting_evidence_ids=[],
                summary="s",
                score=66.67,
            )
        )
        session.add(Decision(lead_id=lead_id, outcome="REVIEW", reasons=["r"]))
        session.add(
            Approval(
                lead_id=lead_id,
                status="pending",
                requested_at=datetime.now(timezone.utc),
                expires_at=datetime.now(timezone.utc) + timedelta(hours=24),
            )
        )
        session.commit()


def test_detail_empty_lead(setup):
    """A fresh lead: state new, every section empty but present."""
    client, _ = setup
    lead = client.post("/leads", json={"company": "Acme"}).json()

    body = client.get(f"/leads/{lead['id']}/detail").json()

    assert body["state"] == "new"
    assert body["artifacts"] == []
    assert body["qualification"] is None
    assert body["decision"] is None
    assert body["approval"] is None


def test_detail_full_story(setup):
    """Seeded rows assemble into one story: state, excerpt cap, score, verdict."""
    client, engine = setup
    lead = client.post("/leads", json={"company": "Acme"}).json()
    _seed_full(engine, UUID(lead["id"]))

    body = client.get(f"/leads/{lead['id']}/detail").json()

    assert body["state"] == "review_pending"
    assert len(body["artifacts"]) == 1
    assert len(body["artifacts"][0]["excerpt"]) == 500  # capped for display
    assert body["qualification"]["score"] == 66.67
    assert body["decision"]["outcome"] == "REVIEW"
    assert body["approval"]["status"] == "pending"


def test_detail_missing_lead_404(setup):
    """Unknown id → 404, same as the single-lead endpoint."""
    client, _ = setup
    response = client.get("/leads/00000000-0000-0000-0000-000000000000/detail")
    assert response.status_code == 404
