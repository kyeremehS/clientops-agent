"""OpenAI client: same chat-completions contract, OpenAI's own endpoint.

Inherits every guardrail from OpenRouterClient (timeout, retry policy,
budgets, logging, validation). GPT-5 models are reasoning models: OpenAI
rejects `max_tokens` on them, so the cap is sent as `max_completion_tokens`.
"""

from app.llm.client import OpenRouterClient
from app.llm.errors import LLMConfigError

OPENAI_URL = "https://api.openai.com/v1/chat/completions"


class OpenAIClient(OpenRouterClient):
    def __init__(self, api_key: str, model: str, **kwargs) -> None:
        if not api_key:
            raise LLMConfigError("OPENAI_API_KEY is not set")
        super().__init__(api_key=api_key, model=model, base_url=OPENAI_URL, **kwargs)

    def _build_body(self, messages: list[dict], schema_name: str, schema: dict) -> dict:
        body = super()._build_body(messages, schema_name, schema)
        body["max_completion_tokens"] = body.pop("max_tokens")
        return body


def openai_client_from_settings(
    api_key: str,
    model: str,
    timeout_s: float,
    max_retries: int,
    max_tokens: int,
    max_total_tokens: int | None = None,
) -> OpenAIClient:
    return OpenAIClient(
        api_key=api_key,
        model=model,
        timeout_s=timeout_s,
        max_retries=max_retries,
        max_tokens=max_tokens,
        max_total_tokens=max_total_tokens,
    )
