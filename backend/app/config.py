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
    slack_bot_token: str = ""
    slack_channel_id: str = ""
    slack_timeout_s: float = 15.0
    slack_max_retries: int = 3
    search_provider: str = "mock"
    parallel_api_key: str = ""
    tavily_api_key: str = ""
    serper_api_key: str = ""
    search_timeout_s: float = 20.0
    search_max_retries: int = 3
    search_max_results: int = 5
    fetch_timeout_s: float = 15.0
    fetch_max_bytes: int = 1_000_000
    fetch_max_chars: int = 20_000

    model_config = {"env_prefix": "", "env_file": ".env", "extra": "ignore"}


settings = Settings()
