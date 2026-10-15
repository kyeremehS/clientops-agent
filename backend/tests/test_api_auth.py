"""C5: API key gate. Missing/wrong key → 401; /health stays open; empty key = dev-open."""

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.api.deps import get_session
from app.config import settings
from app.main import app


@pytest.fixture
def keyed_client(tmp_path, monkeypatch):
    url = f"sqlite:///{tmp_path}/auth.db"
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
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()


def test_missing_key_is_401(keyed_client):
    """No credentials at all → 401, never a hint about the route."""
    assert keyed_client.post("/leads", json={"company": "Acme"}).status_code == 401


def test_wrong_key_is_401(keyed_client):
    """A wrong secret gets the same 401 — no oracle for guessing."""
    response = keyed_client.post(
        "/leads", json={"company": "Acme"}, headers={"Authorization": "Bearer wrong"}
    )
    assert response.status_code == 401


def test_correct_key_passes(keyed_client):
    """Right key → normal behavior."""
    response = keyed_client.post(
        "/leads", json={"company": "Acme"}, headers={"Authorization": "Bearer test-key"}
    )
    assert response.status_code == 201


def test_health_needs_no_key(keyed_client):
    """Liveness probe stays open for orchestrators and load balancers."""
    assert keyed_client.get("/health").status_code == 200


def test_empty_key_means_dev_open(tmp_path, monkeypatch):
    """Unset API_KEY leaves local dev working; production sets it."""
    url = f"sqlite:///{tmp_path}/open.db"
    monkeypatch.setattr(settings, "database_url", url)
    monkeypatch.setattr(settings, "api_key", "")
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
    with TestClient(app) as test_client:
        assert test_client.post("/leads", json={"company": "Acme"}).status_code == 201
    app.dependency_overrides.clear()
