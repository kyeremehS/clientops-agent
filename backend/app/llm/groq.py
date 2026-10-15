"""Groq client: same chat-completions contract, Groq's OpenAI-compatible endpoint.

Inherits every guardrail from OpenRouterClient (timeout, retry policy,
budgets, logging, validation). Only the endpoint and the missing-key
message differ — verified live before pinning any model.
"""

from app.llm.client import OpenRouterClient
from app.llm.errors import LLMConfigError

GROQ_URL = "https://api.groq.com/openai/v1/chat/completions"


class GroqClient(OpenRouterClient):
    def __init__(self, api_key: str, model: str, **kwargs) -> None:
        if not api_key:
            raise LLMConfigError("GROQ_API_KEY is not set")
        super().__init__(api_key=api_key, model=model, base_url=GROQ_URL, **kwargs)


def groq_client_from_settings(
    api_key: str,
    model: str,
    timeout_s: float,
    max_retries: int,
    max_tokens: int,
    max_total_tokens: int | None = None,
) -> GroqClient:
    return GroqClient(
        api_key=api_key,
        model=model,
        timeout_s=timeout_s,
        max_retries=max_retries,
        max_tokens=max_tokens,
        max_total_tokens=max_total_tokens,
    )
