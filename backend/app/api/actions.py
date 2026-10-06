"""Execute endpoint: send the approved Slack message exactly once.

Guards: approval must exist (404) and be approved (409 otherwise).
Idempotency: the Action row is keyed per approval. If it exists, return it
without re-sending — a retry after an ambiguous timeout can never double-send.
"""

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.deps import get_session, get_slack_sender
from app.config import settings
from app.db.events import append_audit_event
from app.db.models import Action, Approval, Lead
from app.schemas.actions import ActionRead
from app.tools.slack import SlackError, SlackSender, format_qualification_message

router = APIRouter()


def _idempotency_key(approval_id: UUID) -> str:
    return f"approval:{approval_id}"


@router.post("/approvals/{approval_id}/execute", response_model=ActionRead)
def execute_approval(
    approval_id: UUID,
    session: Session = Depends(get_session),
    sender: SlackSender = Depends(get_slack_sender),
) -> Action:
    approval = session.get(Approval, approval_id)
    if approval is None:
        raise HTTPException(status_code=404, detail="approval_not_found")
    if approval.status != "approved":
        raise HTTPException(status_code=409, detail="wrong_state")

    key = _idempotency_key(approval.id)
    existing = session.scalar(select(Action).where(Action.idempotency_key == key))
    if existing is not None:
        return existing

    lead = session.get(Lead, approval.lead_id)
    if lead is None:  # pragma: no cover — defensive; lead outlives approvals
        raise HTTPException(status_code=404, detail="lead_not_found")
    text = format_qualification_message(lead.company, lead.website, lead.contact, lead.message)

    append_audit_event(session, lead.id, "action.started", payload={"channel": "slack"})
    try:
        sent = sender.post_message(settings.slack_channel_id, text)
    except SlackError as exc:
        append_audit_event(
            session, lead.id, "action.failed", payload={"error": type(exc).__name__}
        )
        session.commit()
        raise HTTPException(status_code=502, detail="slack_failed")
    action = Action(
        lead_id=lead.id,
        approval_id=approval.id,
        idempotency_key=key,
        channel_id=sent.get("channel", settings.slack_channel_id),
        text=text,
        result=f"ok ts={sent.get('ts', '')}",
    )
    session.add(action)
    session.flush()
    append_audit_event(
        session, lead.id, "action.succeeded", payload={"ts": sent.get("ts", "")}
    )
    session.commit()
    session.refresh(action)
    return action
