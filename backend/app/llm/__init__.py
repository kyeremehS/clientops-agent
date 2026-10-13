"""LLM abstraction. Only this package calls the model."""

from app.llm.client import OpenRouterClient, client_from_settings
from app.llm.errors import (
    LLMBudgetExceededError,
    LLMConfigError,
    LLMError,
    LLMRateLimitError,
    LLMResponseError,
    LLMTimeoutError,
    LLMValidationError,
)
from app.llm.groq import GroqClient, groq_client_from_settings

__all__ = [
    "GroqClient",
    "LLMBudgetExceededError",
    "LLMConfigError",
    "LLMError",
    "LLMRateLimitError",
    "LLMResponseError",
    "LLMTimeoutError",
    "LLMValidationError",
    "OpenRouterClient",
    "client_from_settings",
    "groq_client_from_settings",
    "llm_client_from_settings",
]


def llm_client_from_settings(settings) -> OpenRouterClient | GroqClient:
    """Build the configured provider client. Unknown providers fail closed."""
    provider = getattr(settings, "llm_provider", "openrouter")
    if provider == "groq":
        return groq_client_from_settings(
            api_key=settings.groq_api_key,
            model=settings.llm_model,
            timeout_s=settings.llm_timeout_s,
            max_retries=settings.llm_max_retries,
            max_tokens=settings.llm_max_tokens,
        )
    if provider == "openrouter":
        return client_from_settings(
            api_key=settings.openrouter_api_key,
            model=settings.llm_model,
            timeout_s=settings.llm_timeout_s,
            max_retries=settings.llm_max_retries,
            max_tokens=settings.llm_max_tokens,
        )
    raise LLMConfigError(f"unknown LLM_PROVIDER: {provider!r} (openrouter|groq)")
