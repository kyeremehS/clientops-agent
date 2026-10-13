"""Groq client: same contract, Groq endpoint. Mocked — no API key needed."""

import json

import httpx
import pytest

from app.llm import GroqClient, OpenRouterClient, llm_client_from_settings
from app.llm.errors import LLMConfigError
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


def _envelope(content: str) -> dict:
    return {
        "choices": [{"message": {"content": content, "finish_reason": "stop"}}],
        "usage": {"prompt_tokens": 80, "completion_tokens": 20, "total_tokens": 100},
    }


def test_groq_hits_groq_endpoint():
    def handler(request: httpx.Request) -> httpx.Response:
        assert str(request.url).startswith("https://api.groq.com/openai/v1/")
        assert request.headers["authorization"] == "Bearer test-key"
        return httpx.Response(200, json=_envelope(GOOD_CONTENT))

    http = httpx.Client(transport=httpx.MockTransport(handler))
    result, _ = GroqClient(api_key="test-key", model="m", http_client=http).complete_json(
        MESSAGES, QualificationResult
    )

    assert result.evidence_quality == 2


def test_groq_missing_key_names_groq():
    """The missing-key error must name GROQ_API_KEY, not OpenRouter's."""
    with pytest.raises(LLMConfigError, match="GROQ_API_KEY"):
        GroqClient(api_key="", model="m")


def test_factory_selects_provider_and_rejects_unknown():
    class Base:
        llm_model = "m"
        openrouter_api_key = "ok"
        groq_api_key = "gk"
        llm_timeout_s = 5.0
        llm_max_retries = 1
        llm_max_tokens = 50

    class OpenRouterSettings(Base):
        llm_provider = "openrouter"

    class GroqSettings(Base):
        llm_provider = "groq"

    class BadSettings(Base):
        llm_provider = "altavista"

    assert isinstance(llm_client_from_settings(OpenRouterSettings()), OpenRouterClient)
    groq = llm_client_from_settings(GroqSettings())
    assert isinstance(groq, GroqClient) and groq._model == "m"
    with pytest.raises(LLMConfigError, match="unknown LLM_PROVIDER"):
        llm_client_from_settings(BadSettings())
