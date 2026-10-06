"""B5: Slack action worker. Network mocked — no workspace or token needed."""

from uuid import UUID

import httpx
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session, sessionmaker

from app.api.deps import get_session, get_slack_sender
from app.config import settings
from app.db.base import Base
from app.db.models import Action, AuditEvent
from app.main import app
from app.tools.slack import SlackRateLimitError, SlackResponseError, SlackSender


class FakeSender:
    """Scriptable stand-in honoring the SlackSender interface."""

    def __init__(self, script: list = None):
        self.script = list(script or [{"ts": "1.0", "channel": "C-test"}])
        self.calls: list[tuple[str, str]] = []

    def post_message(self, channel_id: str, text: str) -> dict:
        self.calls.append((channel_id, text))
        outcome = self.script.pop(0) if len(self.script) > 1 else self.script[0]
        if isinstance(outcome, Exception):
            raise outcome
        return outcome


@pytest.fixture
def wired(tmp_path, monkeypatch):
    url = f"sqlite:///{tmp_path}/test.db"
    monkeypatch.setattr(settings, "database_url", url)
    monkeypatch.setattr(settings, "slack_channel_id", "C-test")
    engine = create_engine(url, future=True)
    Base.metadata.create_all(engine)
    factory = sessionmaker(bind=engine, expire_on_commit=False, future=True)

    def override_session():
        session = factory()
        try:
            yield session
            session.commit()
        except Exception:
            session.rollback()
            raise
        finally:
            session.close()

    sender = FakeSender()
    app.dependency_overrides[get_session] = override_session
    app.dependency_overrides[get_slack_sender] = lambda: sender
    with TestClient(app) as test_client:
        yield test_client, sender, engine
    app.dependency_overrides.clear()


def _approved(wired) -> tuple[TestClient, FakeSender, object, dict]:
    client, sender, engine = wired
    lead = client.post(
        "/leads", json={"company": "Acme Logistics", "message": "Hi"}
    ).json()
    approval = client.post(f"/leads/{lead['id']}/approvals").json()
    client.post(f"/approvals/{approval['id']}/approve")
    return client, sender, engine, approval


def _events(engine, lead_id: str) -> list[str]:
    with Session(engine) as session:
        rows = session.scalars(
            select(AuditEvent.event_type).where(AuditEvent.lead_id == UUID(lead_id))
        )
        return list(rows)


def test_execute_happy_path(wired):
    client, sender, engine, approval = _approved(wired)

    response = client.post(f"/approvals/{approval['id']}/execute")

    assert response.status_code == 200
    action = response.json()
    assert action["approval_id"] == approval["id"]
    assert action["idempotency_key"] == f"approval:{approval['id']}"
    assert len(sender.calls) == 1
    channel, text = sender.calls[0]
    assert channel == "C-test"
    assert "Acme Logistics" in text
    events = _events(engine, approval["lead_id"])
    assert "action.started" in events and "action.succeeded" in events


def test_execute_is_idempotent(wired):
    client, sender, engine, approval = _approved(wired)

    first = client.post(f"/approvals/{approval['id']}/execute").json()
    second = client.post(f"/approvals/{approval['id']}/execute").json()

    assert second["id"] == first["id"]
    assert len(sender.calls) == 1  # never re-sent


def test_execute_pending_is_409(wired):
    client, sender, _ = wired
    lead = client.post("/leads", json={"company": "Acme"}).json()
    approval = client.post(f"/leads/{lead['id']}/approvals").json()

    response = client.post(f"/approvals/{approval['id']}/execute")

    assert response.status_code == 409
    assert len(sender.calls) == 0


def test_execute_rejected_is_409(wired):
    client, sender, _ = wired
    lead = client.post("/leads", json={"company": "Acme"}).json()
    approval = client.post(f"/leads/{lead['id']}/approvals").json()
    client.post(f"/approvals/{approval['id']}/reject")

    response = client.post(f"/approvals/{approval['id']}/execute")

    assert response.status_code == 409
    assert len(sender.calls) == 0


def test_execute_unknown_404(wired):
    client, _, _ = wired
    response = client.post("/approvals/00000000-0000-0000-0000-000000000000/execute")
    assert response.status_code == 404


def test_slack_failure_leaves_no_action_and_stays_retryable(wired):
    client, sender, engine, approval = _approved(wired)
    sender.script = [SlackResponseError("slack API error: channel_not_found")]

    failed = client.post(f"/approvals/{approval['id']}/execute")

    assert failed.status_code == 502
    assert failed.json()["detail"] == "slack_failed"
    with Session(engine) as session:
        assert session.scalar(select(Action)) is None
    assert "action.failed" in _events(engine, approval["lead_id"])

    sender.script = [{"ts": "2.0", "channel": "C-test"}]
    retry = client.post(f"/approvals/{approval['id']}/execute")
    assert retry.status_code == 200


def test_sender_retries_429_then_succeeds():
    calls = []

    def handler(request: httpx.Request) -> httpx.Response:
        calls.append(1)
        if len(calls) == 1:
            return httpx.Response(429, json={"ok": False})
        return httpx.Response(200, json={"ok": True, "ts": "3.0", "channel": "C-x"})

    sender = SlackSender(
        bot_token="xoxb-test",
        http_client=httpx.Client(transport=httpx.MockTransport(handler)),
    )
    assert sender.post_message("C-x", "hi")["ts"] == "3.0"
    assert len(calls) == 2


def test_sender_rate_limit_exhausted():
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(429, json={"ok": False})

    sender = SlackSender(
        bot_token="xoxb-test",
        max_retries=1,
        http_client=httpx.Client(transport=httpx.MockTransport(handler)),
    )
    with pytest.raises(SlackRateLimitError):
        sender.post_message("C-x", "hi")


def test_sender_non_retryable_error_fails_fast():
    calls = []

    def handler(request: httpx.Request) -> httpx.Response:
        calls.append(1)
        return httpx.Response(200, json={"ok": False, "error": "channel_not_found"})

    sender = SlackSender(
        bot_token="xoxb-test",
        http_client=httpx.Client(transport=httpx.MockTransport(handler)),
    )
    with pytest.raises(SlackResponseError):
        sender.post_message("C-x", "hi")
    assert len(calls) == 1
