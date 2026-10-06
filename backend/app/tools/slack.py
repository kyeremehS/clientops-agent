"""Slack tool. Only this module posts to Slack.

Guardrails (same doctrine as the LLM client):
- per-request timeout, retry with backoff on 429 / 5xx / timeouts and
  `ok:false rate_limited`. Auth/config errors fail immediately.
- message text is never logged (lead PII); channel, ts, and lengths are.
- idempotency lives one layer up: the execute worker keys the Action row
  per approval, so a retry after an ambiguous timeout never double-sends.
"""

import logging
import time

import httpx

logger = logging.getLogger(__name__)

SLACK_POST_URL = "https://slack.com/api/chat.postMessage"
_BACKOFF_S = (0.5, 1.0, 2.0)


class SlackError(Exception):
    """Base class for Slack tool failures."""


class SlackConfigError(SlackError):
    """Missing bot token."""


class SlackRateLimitError(SlackError):
    """Throttled and retries were exhausted."""


class SlackResponseError(SlackError):
    """Non-retryable Slack failure (bad channel, auth, malformed reply)."""


def format_qualification_message(
    company: str, website: str, contact: str, message: str, fit_score: float | None = None
) -> str:
    """Deterministic message body. No LLM output inside — code-composed only."""
    lines = [f"*New qualified lead: {company}*"]
    if fit_score is not None:
        lines.append(f"Fit: {fit_score:.0f}/100")
    if website:
        lines.append(f"Website: {website}")
    if contact:
        lines.append(f"Contact: {contact}")
    if message:
        lines.append(f"Inbound message: {message}")
    lines.append("Recommended next step: contact for discovery")
    return "\n".join(lines)


class SlackSender:
    def __init__(
        self,
        bot_token: str,
        timeout_s: float = 15.0,
        max_retries: int = 3,
        http_client: httpx.Client | None = None,
    ) -> None:
        if not bot_token:
            raise SlackConfigError("SLACK_BOT_TOKEN is not set")
        self._bot_token = bot_token
        self._max_retries = max_retries
        self._http = http_client or httpx.Client(timeout=timeout_s)

    def post_message(self, channel_id: str, text: str) -> dict:
        """Post once. Returns {"ts": ..., "channel": ...}. Raises SlackError."""
        if not channel_id:
            raise SlackConfigError("channel_id is required")
        headers = {"Authorization": f"Bearer {self._bot_token}", "Content-Type": "application/json"}
        body = {"channel": channel_id, "text": text}
        last_error: Exception | None = None
        for attempt in range(self._max_retries + 1):
            start = time.monotonic()
            try:
                response = self._http.post(SLACK_POST_URL, headers=headers, json=body)
            except httpx.TimeoutException as exc:
                last_error = exc
                self._sleep(attempt)
                continue
            except httpx.TransportError as exc:
                raise SlackResponseError(f"transport failure: {exc}")
            latency_ms = int((time.monotonic() - start) * 1000)
            if response.status_code == 429 or response.status_code >= 500:
                last_error = Exception(f"HTTP {response.status_code}: {response.text[:200]}")
                self._sleep(attempt)
                continue
            if response.status_code >= 400:
                raise SlackResponseError(f"HTTP {response.status_code}: {response.text[:200]}")
            try:
                payload = response.json()
            except ValueError as exc:
                raise SlackResponseError(f"non-JSON reply: {exc}")
            if not payload.get("ok"):
                error = str(payload.get("error", "unknown_error"))
                if error == "rate_limited":
                    last_error = Exception("rate_limited")
                    self._sleep(attempt)
                    continue
                raise SlackResponseError(f"slack API error: {error}")
            ts = payload.get("ts", "")
            logger.info(
                "slack.post channel=%s ts=%s latency_ms=%d text_chars=%d",
                channel_id,
                ts,
                latency_ms,
                len(text),
            )
            return {"ts": ts, "channel": payload.get("channel", channel_id)}
        if last_error is not None and "429" in str(last_error):
            raise SlackRateLimitError(f"rate limited after {self._max_retries + 1} attempts")
        raise SlackRateLimitError(f"no send after {self._max_retries + 1} attempts: {last_error}")

    def _sleep(self, attempt: int) -> None:
        time.sleep(_BACKOFF_S[min(attempt, len(_BACKOFF_S) - 1)])
