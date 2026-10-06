"""B4: approvals API. Each test gets an isolated SQLite file; no live DB needed."""

from datetime import timedelta
from uuid import UUID

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.api.deps import get_session
from app.config import settings
from app.db.base import Base
from app.db.events import utcnow
from app.db.models import Approval
from app.main import app


@pytest.fixture
def client(tmp_path, monkeypatch):
    url = f"sqlite:///{tmp_path}/test.db"
    monkeypatch.setattr(settings, "database_url", url)
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

    app.dependency_overrides[get_session] = override
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()


def _create_lead(client: TestClient) -> dict:
    response = client.post(
        "/leads",
        json={"company": "Acme Logistics", "website": "https://acme.test", "message": "Hi"},
    )
    assert response.status_code == 201
    return response.json()


def _request_approval(client: TestClient, lead_id: str) -> dict:
    response = client.post(f"/leads/{lead_id}/approvals")
    assert response.status_code == 201
    return response.json()


def test_create_and_get_lead(client: TestClient):
    lead = _create_lead(client)
    assert lead["company"] == "Acme Logistics"

    fetched = client.get(f"/leads/{lead['id']}")
    assert fetched.status_code == 200
    assert fetched.json()["id"] == lead["id"]


def test_get_missing_lead_404(client: TestClient):
    response = client.get("/leads/00000000-0000-0000-0000-000000000000")
    assert response.status_code == 404
    assert response.json()["detail"] == "lead_not_found"


def test_approve_happy_path(client: TestClient):
    lead = _create_lead(client)
    approval = _request_approval(client, lead["id"])

    response = client.post(f"/approvals/{approval['id']}/approve")
    assert response.status_code == 200
    assert response.json()["status"] == "approved"

    pending = client.get("/approvals/pending").json()
    assert all(a["id"] != approval["id"] for a in pending)


def test_reject_happy_path(client: TestClient):
    lead = _create_lead(client)
    approval = _request_approval(client, lead["id"])

    response = client.post(f"/approvals/{approval['id']}/reject")
    assert response.status_code == 200
    assert response.json()["status"] == "rejected"


def test_double_approve_is_409(client: TestClient):
    lead = _create_lead(client)
    approval = _request_approval(client, lead["id"])
    client.post(f"/approvals/{approval['id']}/approve")

    response = client.post(f"/approvals/{approval['id']}/approve")
    assert response.status_code == 409
    assert response.json()["detail"] == "wrong_state"


def test_second_approval_request_while_pending_is_409(client: TestClient):
    lead = _create_lead(client)
    _request_approval(client, lead["id"])

    response = client.post(f"/leads/{lead['id']}/approvals")
    assert response.status_code == 409
    assert response.json()["detail"] == "wrong_state"


def test_approve_unknown_404(client: TestClient):
    response = client.post("/approvals/00000000-0000-0000-0000-000000000000/approve")
    assert response.status_code == 404


def test_cors_allows_queue_origin(client: TestClient):
    for origin in ("http://localhost:3000", "http://localhost:3001"):
        response = client.options(
            "/approvals/pending",
            headers={"Origin": origin, "Access-Control-Request-Method": "GET"},
        )
        assert response.status_code == 200
        assert response.headers["access-control-allow-origin"] == origin


def test_late_approve_is_409_and_marks_expired(client: TestClient, tmp_path):
    # Backdate expires_at directly in the DB to simulate a 25h-old approval.
    url = f"sqlite:///{tmp_path}/test.db"
    engine = create_engine(url, future=True)
    backdate = utcnow() - timedelta(hours=1)

    lead = _create_lead(client)
    approval = _request_approval(client, lead["id"])

    from sqlalchemy.orm import Session

    with Session(engine) as session:
        row = session.get(Approval, UUID(approval["id"]))
        row.expires_at = backdate
        session.commit()

    response = client.post(f"/approvals/{approval['id']}/approve")
    assert response.status_code == 409
    assert response.json()["detail"] == "approval_expired"

    with Session(engine) as session:
        assert session.get(Approval, UUID(approval["id"])).status == "expired"
