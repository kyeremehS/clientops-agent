"""Web search behind a provider interface. Sync, typed, swappable.

One protocol, three live adapters (Parallel Fast default, Tavily, Serper)
plus a mock for tests/eval. Agents depend on SearchProvider only — switching
vendors is a config change, never a code change.
"""

import logging
import time
from typing import Protocol

import httpx
from pydantic import BaseModel

logger = logging.getLogger(__name__)

_BACKOFF_S = (0.5, 1.0, 2.0)


class SearchResult(BaseModel):
    title: str = ""
    url: str = ""
    excerpt: str = ""


class SearchProvider(Protocol):
    def search(self, objective: str, max_results: int = 5) -> list[SearchResult]:
        """Run one research query. Returns up to max_results, possibly fewer."""
        ...


class SearchError(Exception):
    """Base class for search failures."""


class SearchConfigError(SearchError):
    """Missing API key or unsupported provider name."""


class SearchRateLimitError(SearchError):
    """Throttled / quota exhausted and retries were exhausted."""


class SearchResponseError(SearchError):
    """Non-retryable provider failure (auth, plan limits, malformed reply)."""


def _post_json(
    http: httpx.Client,
    url: str,
    headers: dict,
    body: dict,
    max_retries: int,
    provider: str,
) -> dict:
    """POST with backoff on 429/5xx/timeout. Returns the decoded envelope."""
    last_error: Exception | None = None
    for attempt in range(max_retries + 1):
        try:
            response = http.post(url, headers=headers, json=body)
        except httpx.TimeoutException as exc:
            last_error = exc
            time.sleep(_BACKOFF_S[min(attempt, len(_BACKOFF_S) - 1)])
            continue
        except httpx.TransportError as exc:
            raise SearchResponseError(f"{provider}: transport failure: {exc}")
        if response.status_code == 429 or response.status_code >= 500:
            last_error = Exception(f"HTTP {response.status_code}: {response.text[:200]}")
            time.sleep(_BACKOFF_S[min(attempt, len(_BACKOFF_S) - 1)])
            continue
        if response.status_code >= 400:
            raise SearchResponseError(f"{provider}: HTTP {response.status_code}: {response.text[:200]}")
        try:
            envelope = response.json()
        except ValueError as exc:
            raise SearchResponseError(f"{provider}: non-JSON reply: {exc}")
        if not isinstance(envelope, dict):
            raise SearchResponseError(f"{provider}: malformed envelope")
        return envelope
    raise SearchRateLimitError(f"{provider}: no response after {max_retries + 1} attempts: {last_error}")


class ParallelSearchProvider:
    """Parallel Search API, Fast mode. Objective in, excerpts out."""

    URL = "https://api.parallel.ai/v1/search"

    def __init__(
        self,
        api_key: str,
        mode: str = "fast",
        timeout_s: float = 20.0,
        max_retries: int = 3,
        http_client: httpx.Client | None = None,
    ) -> None:
        if not api_key:
            raise SearchConfigError("PARALLEL_API_KEY is not set")
        self._api_key = api_key
        self._mode = mode
        self._max_retries = max_retries
        self._http = http_client or httpx.Client(timeout=timeout_s)

    def search(self, objective: str, max_results: int = 5) -> list[SearchResult]:
        start = time.monotonic()
        query = (objective or "").strip()[:200]
        if not query:
            raise SearchConfigError("parallel: objective must not be empty")
        envelope = _post_json(
            self._http,
            self.URL,
            {"Content-Type": "application/json", "x-api-key": self._api_key},
            {
                "objective": objective,
                "search_queries": [query],
                "mode": self._mode,
                "advanced_settings": {"max_results": max_results},
            },
            self._max_retries,
            "parallel",
        )
        results = [
            SearchResult(
                title=str(item.get("title", "")),
                url=str(item.get("url", "")),
                excerpt="\n".join(str(e) for e in item.get("excerpts", []) or []),
            )
            for item in envelope.get("results", [])
            if item.get("url")
        ][:max_results]
        logger.info(
            "search.parallel objective_chars=%d results=%d latency_ms=%d",
            len(objective),
            len(results),
            int((time.monotonic() - start) * 1000),
        )
        return results


class TavilySearchProvider:
    """Tavily Search API, basic depth (1 credit). Snippets per source."""

    URL = "https://api.tavily.com/search"

    def __init__(
        self,
        api_key: str,
        timeout_s: float = 20.0,
        max_retries: int = 3,
        http_client: httpx.Client | None = None,
    ) -> None:
        if not api_key:
            raise SearchConfigError("TAVILY_API_KEY is not set")
        self._api_key = api_key
        self._max_retries = max_retries
        self._http = http_client or httpx.Client(timeout=timeout_s)

    def search(self, objective: str, max_results: int = 5) -> list[SearchResult]:
        start = time.monotonic()
        envelope = _post_json(
            self._http,
            self.URL,
            {"Content-Type": "application/json", "Authorization": f"Bearer {self._api_key}"},
            {
                "query": objective,
                "search_depth": "basic",
                "max_results": max_results,
                "include_answer": False,
            },
            self._max_retries,
            "tavily",
        )
        results = [
            SearchResult(
                title=str(item.get("title", "")),
                url=str(item.get("url", "")),
                excerpt=str(item.get("content", "")),
            )
            for item in envelope.get("results", [])
            if item.get("url")
        ][:max_results]
        logger.info(
            "search.tavily objective_chars=%d results=%d latency_ms=%d",
            len(objective),
            len(results),
            int((time.monotonic() - start) * 1000),
        )
        return results


class SerperSearchProvider:
    """Serper Google SERP API. Thin snippets — pair with website_fetch."""

    URL = "https://google.serper.dev/search"

    def __init__(
        self,
        api_key: str,
        timeout_s: float = 20.0,
        max_retries: int = 3,
        http_client: httpx.Client | None = None,
    ) -> None:
        if not api_key:
            raise SearchConfigError("SERPER_API_KEY is not set")
        self._api_key = api_key
        self._max_retries = max_retries
        self._http = http_client or httpx.Client(timeout=timeout_s)

    def search(self, objective: str, max_results: int = 5) -> list[SearchResult]:
        start = time.monotonic()
        envelope = _post_json(
            self._http,
            self.URL,
            {"Content-Type": "application/json", "X-API-KEY": self._api_key},
            {"q": objective, "num": max_results},
            self._max_retries,
            "serper",
        )
        results = [
            SearchResult(
                title=str(item.get("title", "")),
                url=str(item.get("link", "")),
                excerpt=str(item.get("snippet", "")),
            )
            for item in envelope.get("organic", [])
            if item.get("link")
        ][:max_results]
        logger.info(
            "search.serper objective_chars=%d results=%d latency_ms=%d",
            len(objective),
            len(results),
            int((time.monotonic() - start) * 1000),
        )
        return results


class MockSearchProvider:
    """Canned results. Tests and offline eval — never touches the network."""

    def __init__(self, results: list[SearchResult] | None = None):
        self._results = results or [
            SearchResult(title="Mock Co", url="https://mock.test/", excerpt="Mock excerpt.")
        ]
        self.queries: list[tuple[str, int]] = []

    def search(self, objective: str, max_results: int = 5) -> list[SearchResult]:
        self.queries.append((objective, max_results))
        return self._results[:max_results]


def create_search_provider(
    name: str,
    parallel_key: str = "",
    tavily_key: str = "",
    serper_key: str = "",
    **kwargs,
) -> SearchProvider:
    providers = {
        "parallel": lambda: ParallelSearchProvider(api_key=parallel_key, **kwargs),
        "tavily": lambda: TavilySearchProvider(api_key=tavily_key, **kwargs),
        "serper": lambda: SerperSearchProvider(api_key=serper_key, **kwargs),
        "mock": lambda: MockSearchProvider(),
    }
    try:
        return providers[name]()
    except KeyError:
        raise SearchConfigError(f"unknown SEARCH_PROVIDER: {name!r}") from None
