from functools import lru_cache

from urllib.parse import urlsplit

from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_name: str = "Agent Lens"
    database_url: str = "sqlite:///./agent_lens.db"
    evaluator_backend: str = "mock"
    openai_api_key: str | None = None
    openai_evaluator_model: str = "gpt-4.1-mini"
    deepseek_api_key: str | None = None
    deepseek_base_url: str = "https://api.deepseek.com"
    deepseek_evaluator_model: str = "deepseek-v4-flash"
    cors_origins: str = "http://localhost:5173,http://127.0.0.1:5173"

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    @field_validator("cors_origins")
    @classmethod
    def local_origins_only(cls, value: str) -> str:
        for origin in value.split(","):
            parsed = urlsplit(origin.strip())
            if parsed.scheme not in {"http", "https"} or parsed.hostname not in {"localhost", "127.0.0.1", "::1"} or parsed.path or parsed.query or parsed.fragment or parsed.username:
                raise ValueError("CORS origins must be explicit loopback origins without paths")
        return value

    @field_validator("evaluator_backend")
    @classmethod
    def supported_evaluator(cls, value: str) -> str:
        if value not in {"mock", "openai", "deepseek"}:
            raise ValueError("EVALUATOR_BACKEND must be mock, openai, or deepseek")
        return value

    @property
    def cors_origin_list(self) -> list[str]:
        return [origin.strip() for origin in self.cors_origins.split(",") if origin.strip()]


@lru_cache
def get_settings() -> Settings:
    return Settings()
