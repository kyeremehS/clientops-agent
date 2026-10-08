"""OpenRouter chat client with JSON-schema structured output.

Production guardrails (per Agents Honestly: reliability is not a later phase):
- per-request timeout
- retry with backoff on 429 / 5xx / transport timeouts (never on 4xx or bad output)
- max_tokens cap on requests + optional total-token budget on responses
- structured logging: model, latency, token usage, finish reason.
  Prompt/response bodies are NOT logged (may contain lead PII).
- only place in the codebase that touches the network for the model.
"""

import json
import logging
import time

import httpx
from pydantic import BaseModel, TypeAdapter, ValidationError

from app.llm.errors import (
    LLMBudgetExceededError,
    LLMConfigError,
    LLMRateLimitError,
    LLMResponseError,
    LLMTimeoutError,
    LLMValidationError,
)

logger = logging.getLogger(__name__)

OPENROUTER_URL = "https://openrouter.ai/api/v1/chat/completions"
RETRYABLE_STATUS = {429, 500, 502, 503, 504}
_BACKOFF_S = (0.5, 1.0, 2.0)


class OpenRouterClient:
    def __init__(
        self,
        api_key: str,
        model: str,
        timeout_s: float = 30.0,
        max_retries: int = 3,
        max_tokens: int = 2000,
        max_total_tokens: int | None = None,
        http_client: httpx.Client | None = None,
    ) -> None:
        if not api_key:
            raise LLMConfigError("OPENROUTER_API_KEY is not set")
        if not model:
            raise LLMConfigError("LLM_MODEL is not set")
        self._api_key = api_key
        self._model = model
        self._timeout_s = timeout_s
        self._max_retries = max_retries
        self._max_tokens = max_tokens
        self._max_total_tokens = max_total_tokens
        self._http = http_client or httpx.Client(timeout=timeout_s)

    def complete_json(
        self, messages: list[dict], response_model: type[BaseModel], schema_name: str = "result"
    ) -> tuple[BaseModel, dict]:
        """Call the model and validate output. Returns (parsed_model, usage)."""
        schema = TypeAdapter(response_model).json_schema()
        body = {
            "model": self._model,
            "messages": messages,
            "max_tokens": self._max_tokens,
            "response_format": {
                "type": "json_schema",
                "json_schema": {"name": schema_name, "strict": True, "schema": schema},
            },
        }
        raw, usage, finish_reason, latency_ms = self._post_with_retry(body)
        if finish_reason == "length":
            raise LLMResponseError(
                f"output truncated by max_tokens={self._max_tokens}; "
                "raise the budget instead of retrying"
            )
        total = usage.get("total_tokens")
        if (
            self._max_total_tokens is not None
            and isinstance(total, int)
            and total > self._max_total_tokens
        ):
            raise LLMBudgetExceededError(f"used {total} tokens, budget is {self._max_total_tokens}")
        logger.info(
            "llm.complete model=%s latency_ms=%d prompt_tokens=%s "
            "completion_tokens=%s finish=%s messages=%d prompt_chars=%d",
            self._model,
            latency_ms,
            usage.get("prompt_tokens"),
            usage.get("completion_tokens"),
            finish_reason,
            len(messages),
            sum(len(str(m.get("content", ""))) for m in messages),
        )
        try:
            parsed = TypeAdapter(response_model).validate_python(json.loads(raw))
        except (json.JSONDecodeError, ValidationError) as exc:
            raise LLMValidationError(f"output failed {response_model.__name__} validation: {exc}")
        return parsed, usage

    def _post_with_retry(self, body: dict) -> tuple[str, dict, str | None, int]:
        headers = {"Authorization": f"Bearer {self._api_key}", "Content-Type": "application/json"}
        last_error: Exception | None = None
        for attempt in range(self._max_retries + 1):
            start = time.monotonic()
            try:
                response = self._http.post(OPENROUTER_URL, headers=headers, json=body)
            except httpx.TimeoutException as exc:
                last_error = exc
                self._backoff(attempt)
                continue
            except httpx.TransportError as exc:
                raise LLMResponseError(f"transport failure: {exc}")
            latency_ms = int((time.monotonic() - start) * 1000)
            if response.status_code == 429:
                last_error = Exception(f"HTTP 429: {response.text[:200]}")
                self._backoff(attempt)
                continue
            if response.status_code in RETRYABLE_STATUS:
                last_error = Exception(f"HTTP {response.status_code}: {response.text[:200]}")
                self._backoff(attempt)
                continue
            if response.status_code >= 400:
                raise LLMResponseError(f"HTTP {response.status_code}: {response.text[:500]}")
            try:
                envelope = response.json()
            except ValueError as exc:
                raise LLMResponseError(f"non-JSON envelope: {exc}")
            try:
                choice = envelope["choices"][0]["message"]
                usage = envelope.get("usage", {})
            except (KeyError, IndexError, TypeError) as exc:
                raise LLMResponseError(f"malformed envelope: {exc}")
            return str(choice.get("content", "")), dict(usage), choice.get("finish_reason"), latency_ms
        if last_error is not None and "429" in str(last_error):
            raise LLMRateLimitError(f"rate limited after {self._max_retries + 1} attempts")
        raise LLMTimeoutError(f"no response after {self._max_retries + 1} attempts: {last_error}")

    def _backoff(self, attempt: int) -> None:
        time.sleep(_BACKOFF_S[min(attempt, len(_BACKOFF_S) - 1)])


def client_from_settings(
    api_key: str, model: str, timeout_s: float, max_retries: int, max_tokens: int
) -> OpenRouterClient:
    return OpenRouterClient(
        api_key=api_key,
        model=model,
        timeout_s=timeout_s,
        max_retries=max_retries,
        max_tokens=max_tokens,
    )
