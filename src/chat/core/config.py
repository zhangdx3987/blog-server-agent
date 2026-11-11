from functools import lru_cache
from typing import Literal

from pydantic import AnyHttpUrl, Field, SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="forbid",
        hide_input_in_errors=True,
    )

    app_name: str = "Blog Server Agent"
    app_env: Literal["development", "test", "production"] = "development"

    llm_provider: Literal["ollama", "qwen"] = "ollama"
    llm_base_url: AnyHttpUrl = AnyHttpUrl("http://localhost:11434/v1")
    llm_model: str = Field(min_length=1)
    llm_api_key: SecretStr | None = None
    llm_timeout_seconds: float = Field(default=60.0, gt=0)

@lru_cache
def get_settings() -> Settings:
    return Settings()