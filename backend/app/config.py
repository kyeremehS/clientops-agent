"""Environment-only config stub. No secrets, no logic."""

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    app_name: str = "clientops-agent"
    database_url: str = "postgresql://postgres:postgres@localhost:5432/clientops"
    llm_provider: str = "openrouter"
    llm_model: str = "qwen/qwen3.8-27b:free"
    openrouter_api_key: str = ""
    llm_timeout_s: float = 30.0
    llm_max_retries: int = 3
    llm_max_tokens: int = 2000

    model_config = {"env_prefix": "", "env_file": ".env", "extra": "ignore"}


settings = Settings()
