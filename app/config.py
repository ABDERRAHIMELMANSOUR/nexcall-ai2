"""
Configuration NexCall AI — pydantic-settings
Charge .env depuis le dossier racine du projet (chemin absolu).
"""
from __future__ import annotations
from pathlib import Path
from functools import lru_cache
from pydantic_settings import BaseSettings, SettingsConfigDict

_ENV_FILE = Path(__file__).resolve().parent.parent / ".env"


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=str(_ENV_FILE),
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # App
    APP_NAME: str = "NexCall AI"
    APP_HOST: str = "0.0.0.0"
    APP_PORT: int = 8000
    DEBUG: bool = False
    SECRET_KEY: str = "change-me-in-production-32chars!!"

    # DB
    DATABASE_URL: str = f"sqlite+aiosqlite:///{_ENV_FILE.parent}/data/nexcall.db"

    # Ringover
    RINGOVER_API_KEY: str = ""
    RINGOVER_API_URL: str = "https://public-api.ringover.com/v2"
    RINGOVER_WEBHOOK_SECRET: str = ""
    RINGOVER_PHONE_NUMBER: str = ""
    RINGOVER_TRANSFER_NUMBER: str = ""

    # OpenAI
    OPENAI_API_KEY: str = ""
    OPENAI_MODEL: str = "gpt-4o"
    OPENAI_TTS_VOICE: str = "nova"

    # Agent
    AI_AGENT_NAME: str = "Sophie"
    AI_COMPANY_NAME: str = "AssurancePro"
    AI_LANGUAGE: str = "fr"
    AI_TEMPERATURE: float = 0.7

    # Leads
    LEAD_SCORE_THRESHOLD: float = 70.0

    @property
    def is_ringover_configured(self) -> bool:
        return bool(self.RINGOVER_API_KEY)

    @property
    def is_openai_configured(self) -> bool:
        return bool(self.OPENAI_API_KEY)


@lru_cache(maxsize=None)
def get_settings() -> Settings:
    return Settings()


# Singleton accessible via import direct
settings = get_settings()
