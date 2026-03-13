"""
NexCall AI — Configuration centralisee
Compatible Render (PORT injecte, pas de .env sur le serveur).
"""
import os
from functools import lru_cache
from pathlib import Path
from typing import List, Optional

from pydantic_settings import BaseSettings, SettingsConfigDict

# Chemin absolu vers la racine du projet
BASE_DIR = Path(__file__).resolve().parent.parent

# Creer le dossier data si necessaire (AVANT que SQLite essaye d'y ecrire)
(BASE_DIR / "data").mkdir(exist_ok=True)


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        # Sur Render il n'y a pas de .env, les vars sont injectees directement
        # En local le .env est lu normalement
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # ── Application ───────────────────────────────────────────────
    APP_NAME: str = "NexCall AI"
    APP_HOST: str = "0.0.0.0"
    APP_PORT: int = 10000  # Render utilise le port 10000 par defaut
    DEBUG: bool = False
    SECRET_KEY: str = "nexcall-change-this-in-production"

    # ── Base de donnees ───────────────────────────────────────────
    # Chemin ABSOLU pour SQLite (evite les problemes de working directory)
    DATABASE_URL: str = f"sqlite+aiosqlite:///{BASE_DIR / 'data' / 'nexcall.db'}"

    # ── Ringover ──────────────────────────────────────────────────
    RINGOVER_API_KEY: Optional[str] = None
    RINGOVER_API_URL: str = "https://public-api.ringover.com/v2"
    RINGOVER_WEBHOOK_SECRET: Optional[str] = None
    RINGOVER_PHONE_NUMBER: Optional[str] = None
    RINGOVER_TRANSFER_NUMBER: Optional[str] = None

    # ── OpenAI ────────────────────────────────────────────────────
    OPENAI_API_KEY: Optional[str] = None
    OPENAI_MODEL: str = "gpt-4o"
    OPENAI_TTS_MODEL: str = "tts-1"
    OPENAI_TTS_VOICE: str = "nova"
    OPENAI_STT_MODEL: str = "whisper-1"
    OPENAI_MAX_TOKENS: int = 600

    # ── Agent IA ──────────────────────────────────────────────────
    AI_AGENT_NAME: str = "Sophie"
    AI_COMPANY_NAME: str = "AssurancePro"
    AI_LANGUAGE: str = "fr"
    AI_TEMPERATURE: float = 0.7

    # ── IVR ───────────────────────────────────────────────────────
    IVR_GREETING: str = (
        "Bonjour et bienvenue. "
        "Pour l'assurance auto, tapez 1. "
        "Pour l'assurance sante, tapez 2. "
        "Pour parler a un conseiller, tapez 3."
    )

    # ── Leads ─────────────────────────────────────────────────────
    LEAD_SCORE_THRESHOLD: int = 70

    # ── Render ────────────────────────────────────────────────────
    RENDER_EXTERNAL_URL: Optional[str] = None
    CORS_ORIGINS: List[str] = ["*"]

    @property
    def is_ringover_configured(self) -> bool:
        return bool(self.RINGOVER_API_KEY and self.RINGOVER_API_KEY != "votre_cle_api_ringover")

    @property
    def is_openai_configured(self) -> bool:
        return bool(self.OPENAI_API_KEY and self.OPENAI_API_KEY != "sk-votre_cle_openai")

    @property
    def public_url(self) -> str:
        """URL publique pour les webhooks. Render injecte RENDER_EXTERNAL_URL."""
        if self.RENDER_EXTERNAL_URL:
            return self.RENDER_EXTERNAL_URL.rstrip("/")
        return f"http://{self.APP_HOST}:{self.APP_PORT}"


@lru_cache()
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
