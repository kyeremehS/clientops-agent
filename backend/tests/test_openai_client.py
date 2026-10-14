"""OpenAI client: same contract, reasoning-model token key. Mocked, no key needed."""

import json

import httpx
import pytest

from app.llm import OpenAIClient, llm_client_from_settings
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


def _client(handler) -> OpenAIClient:
    http = httpx.Client(transport=httpx.MockTransport(handler))
    return OpenAIClient(api_key="test-key", model="m", http_client=http)


def test_cap_sent_as_max_completion_tokens():
    def handler(request: httpx.Request) -> httpx.Response:
        assert str(request.url).startswith("https://api.openai.com/v1/")
        assert request.headers["authorization"] == "Bearer test-key"
        body = json.loads(request.content)
        assert "max_completion_tokens" in body and "max_tokens" not in body
        return httpx.Response(200, json=_envelope(GOOD_CONTENT))

    result, usage = _client(handler).complete_json(MESSAGES, QualificationResult)

    assert result.evidence_quality == 2
    assert usage["total_tokens"] == 100


def test_openai_missing_key_names_openai():
    with pytest.raises(LLMConfigError, match="OPENAI_API_KEY"):
        OpenAIClient(api_key="", model="m")


def test_factory_selects_openai():
    class Settings:
        llm_provider = "openai"
        llm_model = "gpt-5-mini"
        openrouter_api_key = "ok"
        openai_api_key = "ak"
        groq_api_key = "gk"
        llm_timeout_s = 5.0
        llm_max_retries = 1
        llm_max_tokens = 50

    class BadSettings(Settings):
        llm_provider = "openllama"

    client = llm_client_from_settings(Settings())
    assert isinstance(client, OpenAIClient) and client._model == "gpt-5-mini"
    with pytest.raises(LLMConfigError, match="unknown LLM_PROVIDER"):
        llm_client_from_settings(BadSettings())
