"""B2: OpenRouter client guardrails. All network I/O mocked — no API key needed."""

import json
import os

import httpx
import pytest

from app.llm import (
    LLMBudgetExceededError,
    LLMConfigError,
    LLMRateLimitError,
    LLMResponseError,
    LLMTimeoutError,
    LLMValidationError,
    OpenRouterClient,
)
from app.schemas.qualification import QualificationResult

MESSAGES = [{"role": "user", "content": "Qualify Acme."}]

GOOD_CONTENT = json.dumps(
    {
        "operational_pain": 2,
        "automation_plausibility": 2,
        "relevance": 2,
        "evidence_quality": 2,
        "supporting_evidence_ids": ["a", "b"],
        "summary": "Support automation plausible.",
    }
)


def _envelope(content: str, total_tokens: int = 100) -> dict:
    return {
        "choices": [{"message": {"content": content, "finish_reason": "stop"}}],
        "usage": {"prompt_tokens": 80, "completion_tokens": 20, "total_tokens": total_tokens},
    }


def _client(handler, **kwargs) -> OpenRouterClient:
    http = httpx.Client(transport=httpx.MockTransport(handler))
    return OpenRouterClient(api_key="test-key", model="test-model", **kwargs, http_client=http)


def test_success_returns_validated_model():
    def handler(request: httpx.Request) -> httpx.Response:
        assert request.headers["authorization"] == "Bearer test-key"
        return httpx.Response(200, json=_envelope(GOOD_CONTENT))

    result, usage = _client(handler).complete_json(MESSAGES, QualificationResult)

    assert isinstance(result, QualificationResult)
    assert result.evidence_quality == 2
    assert usage["total_tokens"] == 100


def test_retries_429_then_succeeds():
    calls = []

    def handler(request: httpx.Request) -> httpx.Response:
        calls.append(1)
        if len(calls) == 1:
            return httpx.Response(429, json={"error": "throttled"})
        return httpx.Response(200, json=_envelope(GOOD_CONTENT))

    result, _ = _client(handler).complete_json(MESSAGES, QualificationResult)

    assert result.operational_pain == 2
    assert len(calls) == 2


def test_rate_limit_exhausted():
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(429, json={"error": "throttled"})

    with pytest.raises(LLMRateLimitError):
        _client(handler, max_retries=1).complete_json(MESSAGES, QualificationResult)


def test_no_retry_on_400():
    calls = []

    def handler(request: httpx.Request) -> httpx.Response:
        calls.append(1)
        return httpx.Response(400, json={"error": "bad request"})

    with pytest.raises(LLMResponseError):
        _client(handler).complete_json(MESSAGES, QualificationResult)
    assert len(calls) == 1


def test_invented_score_field_rejected():
    bad = json.dumps(
        {
            "operational_pain": 2,
            "automation_plausibility": 2,
            "relevance": 2,
            "evidence_quality": 2,
            "supporting_evidence_ids": [],
            "summary": "x",
            "fit_score_100": 84,
        }
    )

    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json=_envelope(bad))

    with pytest.raises(LLMValidationError):
        _client(handler).complete_json(MESSAGES, QualificationResult)


def test_out_of_range_dimension_rejected():
    bad = GOOD_CONTENT.replace('"evidence_quality": 2', '"evidence_quality": 9')

    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json=_envelope(bad))

    with pytest.raises(LLMValidationError):
        _client(handler).complete_json(MESSAGES, QualificationResult)


def test_missing_api_key():
    with pytest.raises(LLMConfigError):
        OpenRouterClient(api_key="", model="m")


def test_timeout_surfaces_typed_error():
    def handler(request: httpx.Request) -> httpx.Response:
        raise httpx.TimeoutException("slow", request=request)

    with pytest.raises(LLMTimeoutError):
        _client(handler, max_retries=0).complete_json(MESSAGES, QualificationResult)


def test_budget_exceeded():
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json=_envelope(GOOD_CONTENT, total_tokens=9999))

    with pytest.raises(LLMBudgetExceededError):
        _client(handler, max_total_tokens=100).complete_json(MESSAGES, QualificationResult)


@pytest.mark.skipif(
    not os.environ.get("OPENROUTER_API_KEY"), reason="needs OPENROUTER_API_KEY (live check)"
)
def test_live_pinned_model_structured_output():
    """Validates the pinned model honors JSON-schema output. Run manually with a key."""
    from app.config import settings

    live = OpenRouterClient(api_key=settings.openrouter_api_key, model=settings.llm_model)
    result, usage = live.complete_json(MESSAGES, QualificationResult, schema_name="qualification")

    assert all(0 <= v <= 3 for v in (result.operational_pain, result.automation_plausibility))
    assert usage.get("total_tokens", 0) > 0
