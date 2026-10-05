"""Typed LLM errors. Callers match on type, never on message text."""


class LLMError(Exception):
    """Base class for all LLM client failures."""


class LLMConfigError(LLMError):
    """Missing or invalid client configuration (e.g. no API key)."""


class LLMTimeoutError(LLMError):
    """Provider did not respond within the configured timeout."""


class LLMRateLimitError(LLMError):
    """Provider throttled us (HTTP 429) and retries were exhausted."""


class LLMResponseError(LLMError):
    """Provider returned an error status or malformed envelope after retries."""


class LLMValidationError(LLMError):
    """Provider output failed Pydantic validation against the declared schema."""


class LLMBudgetExceededError(LLMError):
    """Response token usage exceeded the configured budget."""
