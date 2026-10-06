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

__all__ = [
    "LLMBudgetExceededError",
    "LLMConfigError",
    "LLMError",
    "LLMRateLimitError",
    "LLMResponseError",
    "LLMTimeoutError",
    "LLMValidationError",
    "OpenRouterClient",
    "client_from_settings",
]
