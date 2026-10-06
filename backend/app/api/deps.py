"""API dependencies: request-scoped DB sessions."""

from collections.abc import Iterator

from sqlalchemy.orm import Session

from app.config import settings
from app.db.base import get_session_factory
from app.tools.slack import SlackSender

_factory = None
_sender: SlackSender | None = None


def get_session() -> Iterator[Session]:
    global _factory
    if _factory is None:
        _factory = get_session_factory(settings.database_url)
    session = _factory()
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()


def get_slack_sender() -> SlackSender:
    global _sender
    if _sender is None:
        _sender = SlackSender(
            bot_token=settings.slack_bot_token,
            timeout_s=settings.slack_timeout_s,
            max_retries=settings.slack_max_retries,
        )
    return _sender
