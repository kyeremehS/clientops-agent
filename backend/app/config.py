"""Environment-only config stub. No secrets, no logic."""

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    app_name: str = "clientops-agent"
    database_url: str = "postgresql://postgres:postgres@localhost:5432/clientops"

    model_config = {"env_prefix": "", "env_file": ".env", "extra": "ignore"}


settings = Settings()
