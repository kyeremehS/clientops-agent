"""API dependencies: request-scoped DB sessions."""

from collections.abc import Iterator

from sqlalchemy.orm import Session

from app.config import settings
from app.db.base import get_session_factory

_factory = None


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
