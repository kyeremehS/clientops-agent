"""B1: audit event chain + approval expiry. SQLite in-memory, no live DB needed."""

from datetime import timedelta

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from app.db import (
    append_audit_event,
    approval_expiry,
    is_approval_expired,
    sha256_hex,
    utcnow,
)
from app.db.base import Base
from app.db.models import Approval, Lead, ResearchArtifact


@pytest.fixture
def session() -> Session:
    engine = create_engine("sqlite:///:memory:", future=True)
    Base.metadata.create_all(engine)
    with Session(engine) as s:
        yield s


def _lead(session: Session) -> Lead:
    lead = Lead(company="Acme Logistics", website="https://acme.test", contact="a@acme.test")
    session.add(lead)
    session.flush()
    return lead


def test_event_chain_links_previous(session: Session):
    lead = _lead(session)
    e1 = append_audit_event(session, lead.id, "run.created")
    e2 = append_audit_event(session, lead.id, "research.completed")
    e3 = append_audit_event(session, lead.id, "decision.made")

    assert e1.previous_event_id is None
    assert e2.previous_event_id == e1.event_id
    assert e3.previous_event_id == e2.event_id
    assert e3.run_id == str(lead.id)


def test_artifact_content_hash(session: Session):
    lead = _lead(session)
    body = "Acme runs 40 trucks"
    artifact = ResearchArtifact(
        lead_id=lead.id,
        source_url="https://acme.test/about",
        content=body,
        content_hash=sha256_hex(body),
    )
    session.add(artifact)
    session.flush()

    assert artifact.content_hash == sha256_hex(body)
    assert len(artifact.content_hash) == 64


def test_approval_expiry_is_24h():
    requested = utcnow()
    assert approval_expiry(requested) == requested + timedelta(hours=24)


def test_expired_approval_blocks_action(session: Session):
    lead = _lead(session)
    requested = utcnow() - timedelta(hours=25)
    approval = Approval(
        lead_id=lead.id,
        status="pending",
        requested_at=requested,
        expires_at=approval_expiry(requested),
    )
    session.add(approval)
    session.flush()

    assert is_approval_expired(approval.expires_at) is True


def test_fresh_approval_not_expired(session: Session):
    lead = _lead(session)
    requested = utcnow()
    approval = Approval(
        lead_id=lead.id,
        status="pending",
        requested_at=requested,
        expires_at=approval_expiry(requested),
    )
    session.add(approval)
    session.flush()

    assert is_approval_expired(approval.expires_at) is False
