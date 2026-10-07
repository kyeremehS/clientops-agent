"""C1: research tools. All network I/O mocked — no provider keys needed."""

import httpx
import pytest

from app.tools import (
    FetchBlockedError,
    FetchResponseError,
    MockSearchProvider,
    ParallelSearchProvider,
    SearchConfigError,
    SearchRateLimitError,
    SearchResponseError,
    SearchResult,
    SerperSearchProvider,
    TavilySearchProvider,
    WebsiteFetcher,
    create_search_provider,
)


def _mocked(provider_cls, handler, **kwargs):
    http = httpx.Client(transport=httpx.MockTransport(handler))
    return provider_cls(api_key="test-key", http_client=http, **kwargs)


def test_parallel_maps_excerpts_and_skips_url_less():
    def handler(request: httpx.Request) -> httpx.Response:
        assert request.headers["x-api-key"] == "test-key"
        assert request.url.path == "/v1/search"
        return httpx.Response(
            200,
            json={
                "results": [
                    {"title": "A", "url": "https://a.test", "excerpts": ["one", "two"]},
                    {"title": "NoUrl", "excerpts": ["x"]},
                ]
            },
        )

    results = _mocked(ParallelSearchProvider, handler).search("acme logistics", max_results=5)

    assert len(results) == 1
    assert results[0].excerpt == "one\ntwo"
    assert results[0].url == "https://a.test"


def test_tavily_maps_content():
    def handler(request: httpx.Request) -> httpx.Response:
        assert request.headers["authorization"] == "Bearer test-key"
        return httpx.Response(
            200, json={"results": [{"title": "B", "url": "https://b.test", "content": "chunk"}]}
        )

    results = _mocked(TavilySearchProvider, handler).search("acme", max_results=5)

    assert results[0] == SearchResult(title="B", url="https://b.test", excerpt="chunk")


def test_serper_maps_organic():
    def handler(request: httpx.Request) -> httpx.Response:
        assert request.headers["x-api-key"] == "test-key"
        return httpx.Response(
            200,
            json={"organic": [{"title": "C", "link": "https://c.test", "snippet": "blurb"}]},
        )

    results = _mocked(SerperSearchProvider, handler).search("acme", max_results=5)

    assert results[0] == SearchResult(title="C", url="https://c.test", excerpt="blurb")


def test_search_retries_429_then_succeeds():
    calls = []

    def handler(request: httpx.Request) -> httpx.Response:
        calls.append(1)
        if len(calls) == 1:
            return httpx.Response(429, json={"error": "throttled"})
        return httpx.Response(200, json={"results": []})

    _mocked(ParallelSearchProvider, handler).search("acme")
    assert len(calls) == 2


def test_search_rate_limit_exhausted():
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(429, json={"error": "throttled"})

    provider = _mocked(ParallelSearchProvider, handler, max_retries=1)
    with pytest.raises(SearchRateLimitError):
        provider.search("acme")


def test_search_auth_failure_fails_fast():
    calls = []

    def handler(request: httpx.Request) -> httpx.Response:
        calls.append(1)
        return httpx.Response(401, json={"error": "bad key"})

    provider = _mocked(TavilySearchProvider, handler)
    with pytest.raises(SearchResponseError):
        provider.search("acme")
    assert len(calls) == 1


def test_missing_keys_and_unknown_provider():
    with pytest.raises(SearchConfigError):
        ParallelSearchProvider(api_key="")
    with pytest.raises(SearchConfigError):
        TavilySearchProvider(api_key="")
    with pytest.raises(SearchConfigError):
        SerperSearchProvider(api_key="")
    with pytest.raises(SearchConfigError):
        create_search_provider("altavista")


def test_mock_records_queries_and_caps():
    mock = MockSearchProvider(
        results=[SearchResult(title=f"T{i}", url=f"https://t{i}.test") for i in range(4)]
    )
    assert len(mock.search("objective", max_results=2)) == 2
    assert mock.queries == [("objective", 2)]
    assert create_search_provider("mock").search("x")


HTML = """<html><head><title>Acme</title><style>.x{}</style></head>
<body><script>evil()</script><h1>Acme Logistics</h1><p>Runs 40 trucks.</p></body></html>"""


def _fetcher(handler, **kwargs) -> WebsiteFetcher:
    return WebsiteFetcher(http_client=httpx.Client(transport=httpx.MockTransport(handler)), **kwargs)


def test_fetch_extracts_text_skips_scripts():
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, headers={"content-type": "text/html"}, text=HTML)

    result = _fetcher(handler).fetch("http://93.184.216.34/")

    assert "Acme Logistics" in result.text and "Runs 40 trucks." in result.text
    assert "evil()" not in result.text and ".x{}" not in result.text
    assert len(result.content_hash) == 64 and result.truncated is False


def test_fetch_rejects_schemes():
    fetcher = WebsiteFetcher()
    for url in ("ftp://x.test/f", "file:///etc/passwd", "notaurl"):
        with pytest.raises(FetchBlockedError):
            fetcher.fetch(url)


def test_fetch_blocks_ssrf_targets():
    fetcher = WebsiteFetcher()
    for url in ("http://127.0.0.1/", "http://10.0.0.1/", "http://169.254.169.254/latest/"):
        with pytest.raises(FetchBlockedError):
            fetcher.fetch(url)


def test_fetch_rejects_non_text():
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, headers={"content-type": "application/pdf"}, content=b"%PDF")

    with pytest.raises(FetchResponseError):
        _fetcher(handler).fetch("http://93.184.216.34/doc.pdf")


def test_fetch_truncates_over_cap():
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, headers={"content-type": "text/html"}, text=HTML * 50)

    result = _fetcher(handler, max_bytes=200, max_chars=100).fetch("http://93.184.216.34/")

    assert result.truncated is True
