"""API dependencies: request-scoped DB sessions + shared external clients."""

from collections.abc import Iterator

from sqlalchemy.orm import Session

from app.config import settings
from app.db.base import get_session_factory
from app.llm.client import OpenRouterClient, client_from_settings
from app.tools.fetch import WebsiteFetcher
from app.tools.search import SearchProvider, create_search_provider
from app.tools.slack import SlackSender

_factory = None
_sender: SlackSender | None = None
_search: SearchProvider | None = None
_fetcher: WebsiteFetcher | None = None
_llm: OpenRouterClient | None = None


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


def get_search_provider() -> SearchProvider:
    global _search
    if _search is None:
        _search = create_search_provider(
            settings.search_provider,
            parallel_key=settings.parallel_api_key,
            tavily_key=settings.tavily_api_key,
            serper_key=settings.serper_api_key,
            timeout_s=settings.search_timeout_s,
            max_retries=settings.search_max_retries,
        )
    return _search


def get_website_fetcher() -> WebsiteFetcher:
    global _fetcher
    if _fetcher is None:
        _fetcher = WebsiteFetcher(
            timeout_s=settings.fetch_timeout_s,
            max_bytes=settings.fetch_max_bytes,
            max_chars=settings.fetch_max_chars,
        )
    return _fetcher


def get_llm_client() -> OpenRouterClient:
    global _llm
    if _llm is None:
        _llm = client_from_settings(
            api_key=settings.openrouter_api_key,
            model=settings.llm_model,
            timeout_s=settings.llm_timeout_s,
            max_retries=settings.llm_max_retries,
            max_tokens=settings.llm_max_tokens,
        )
    return _llm
