"""First-party website fetch. No vendor, no key — httpx plus stdlib parsing.

Guards (untrusted-input doctrine: the lead supplies the URL):
- http(s) only. file://, ftp://, and friends are rejected, never fetched.
- SSRF block: hostnames resolving to private / loopback / link-local /
  multicast / reserved addresses are refused before any byte is sent.
- byte cap (streamed, truncated with a flag) and timeout on every request.
- text/* responses only; binaries fail fast with a typed error.
"""

import hashlib
import ipaddress
import logging
import re
import socket
import time
from html.parser import HTMLParser
from urllib.parse import urlsplit

import httpx
from pydantic import BaseModel

logger = logging.getLogger(__name__)

_SKIP_TAGS = {"script", "style", "noscript", "template"}
_BREAK_TAGS = {
    "p", "br", "div", "section", "article", "li", "tr",
    "h1", "h2", "h3", "h4", "h5", "h6", "header", "footer",
}


class FetchResult(BaseModel):
    url: str
    final_url: str = ""
    text: str = ""
    content_hash: str = ""
    truncated: bool = False


class FetchError(Exception):
    """Base class for fetch failures."""


class FetchBlockedError(FetchError):
    """Refused before sending: bad scheme or unsafe destination."""


class FetchResponseError(FetchError):
    """Non-retryable fetch failure (DNS, status, content type, timeout exhausted)."""


class _TextExtractor(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self._parts: list[str] = []
        self._skip_depth = 0

    def handle_starttag(self, tag: str, attrs: list) -> None:
        if tag in _SKIP_TAGS:
            self._skip_depth += 1
        elif tag in _BREAK_TAGS:
            self._parts.append("\n")

    def handle_endtag(self, tag: str) -> None:
        if tag in _SKIP_TAGS and self._skip_depth:
            self._skip_depth -= 1
        elif tag in _BREAK_TAGS:
            self._parts.append("\n")

    def handle_data(self, data: str) -> None:
        if not self._skip_depth:
            self._parts.append(data)

    def text(self, char_cap: int) -> tuple[str, bool]:
        collapsed = re.sub(r"[ \t]+", " ", "".join(self._parts))
        collapsed = re.sub(r"\n\s*\n+", "\n\n", collapsed).strip()
        if len(collapsed) > char_cap:
            return collapsed[:char_cap], True
        return collapsed, False


def _is_unsafe_host(host: str) -> bool:
    """True when the hostname resolves to an address that must never be fetched."""
    infos = socket.getaddrinfo(host, None)
    for info in infos:
        try:
            ip = ipaddress.ip_address(info[4][0])
        except ValueError:
            return True
        if ip.is_private or ip.is_loopback or ip.is_link_local or ip.is_multicast or ip.is_reserved:
            return True
    return False


class WebsiteFetcher:
    def __init__(
        self,
        timeout_s: float = 15.0,
        max_bytes: int = 1_000_000,
        max_chars: int = 20_000,
        user_agent: str = "clientops-agent/1.0 research",
        http_client: httpx.Client | None = None,
    ) -> None:
        self._timeout_s = timeout_s
        self._max_bytes = max_bytes
        self._max_chars = max_chars
        self._http = http_client or httpx.Client(
            timeout=timeout_s, follow_redirects=True, max_redirects=5, headers={"User-Agent": user_agent}
        )

    def fetch(self, url: str) -> FetchResult:
        scheme = urlsplit(url).scheme.lower()
        if scheme not in ("http", "https"):
            raise FetchBlockedError(f"refused scheme: {scheme or '(none)'}")
        host = urlsplit(url).hostname or ""
        try:
            unsafe = _is_unsafe_host(host)
        except socket.gaierror as exc:
            raise FetchResponseError(f"unresolvable host {host}: {exc}")
        if unsafe:
            raise FetchBlockedError(f"refused destination: {host}")
        start = time.monotonic()
        try:
            with self._http.stream("GET", url) as response:
                if response.status_code >= 400:
                    raise FetchResponseError(f"HTTP {response.status_code} for {url}")
                content_type = response.headers.get("content-type", "")
                if "text" not in content_type and "html" not in content_type:
                    raise FetchResponseError(f"non-text content ({content_type}) for {url}")
                chunks: list[bytes] = []
                size = 0
                truncated = False
                for chunk in response.iter_bytes(chunk_size=65536):
                    size += len(chunk)
                    if size > self._max_bytes:
                        truncated = True
                        break
                    chunks.append(chunk)
                body = b"".join(chunks).decode(response.encoding or "utf-8", errors="replace")
        except httpx.TimeoutException as exc:
            raise FetchResponseError(f"timeout fetching {url}: {exc}")
        except httpx.TransportError as exc:
            raise FetchResponseError(f"transport failure for {url}: {exc}")
        extractor = _TextExtractor()
        extractor.feed(body)
        text, over_chars = extractor.text(self._max_chars)
        final_url = str(response.url)
        digest = hashlib.sha256(f"{final_url}\n{text}".encode("utf-8")).hexdigest()
        logger.info(
            "fetch.ok url=%s final=%s chars=%d truncated=%s latency_ms=%d",
            url,
            final_url,
            len(text),
            truncated or over_chars,
            int((time.monotonic() - start) * 1000),
        )
        return FetchResult(
            url=url,
            final_url=final_url,
            text=text,
            content_hash=digest,
            truncated=truncated or over_chars,
        )
