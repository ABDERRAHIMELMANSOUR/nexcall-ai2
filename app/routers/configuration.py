"""
NexCall AI — Router Configuration
"""
from typing import Dict
from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from datetime import datetime

from app.database import get_db
from app.models.configuration import Configuration
from app.services.ringover_service import ringover_service
from app.config import settings

router = APIRouter(prefix="/api/config", tags=["configuration"])

SECRET_KEYS = {"ringover_api_key", "openai_api_key", "webhook_secret"}

CATEGORY_MAP = {
    "ringover":     {"ringover_api_key", "ringover_phone", "ringover_transfer", "webhook_secret"},
    "openai":       {"openai_api_key", "openai_model", "tts_voice", "stt_model"},
    "agent":        {"agent_name", "company_name", "language", "temperature"},
    "ivr":          {"ivr_greeting"},
    "leads":        {"lead_score_threshold"},
}


def _get_category(key: str) -> str:
    for category, keys in CATEGORY_MAP.items():
        if key in keys:
            return category
    return "general"


class ConfigSaveRequest(BaseModel):
    configs: Dict[str, str]


@router.get("")
async def get_configuration(db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Configuration))
    configs = result.scalars().all()
    return {c.key: c.to_dict() for c in configs}


@router.post("")
async def save_configuration(body: ConfigSaveRequest, db: AsyncSession = Depends(get_db)):
    saved = []
    for key, value in body.configs.items():
        if not key or not isinstance(value, str):
            continue

        result = await db.execute(select(Configuration).where(Configuration.key == key))
        existing = result.scalar_one_or_none()

        if existing:
            if existing.is_secret and value == "***":
                continue
            existing.value = value
            existing.updated_at = datetime.utcnow()
        else:
            cfg = Configuration(
                key=key,
                value=value,
                category=_get_category(key),
                is_secret=key in SECRET_KEYS,
            )
            db.add(cfg)
        saved.append(key)

    await db.flush()
    return {"success": True, "saved": saved, "message": "Configuration sauvegardee"}


@router.get("/status")
async def get_status():
    """Statut de toutes les integrations."""
    ringover_connected = False
    if settings.is_ringover_configured:
        test = await ringover_service.test_connection()
        ringover_connected = test.get("connected", False)

    return {
        "ringover": {
            "configured":      settings.is_ringover_configured,
            "connected":       ringover_connected,
            "phone_number":    settings.RINGOVER_PHONE_NUMBER,
            "transfer_number": settings.RINGOVER_TRANSFER_NUMBER,
            "api_url":         settings.RINGOVER_API_URL,
        },
        "openai": {
            "configured": settings.is_openai_configured,
            "model":      settings.OPENAI_MODEL,
            "tts_model":  settings.OPENAI_TTS_MODEL,
            "tts_voice":  settings.OPENAI_TTS_VOICE,
            "stt_model":  settings.OPENAI_STT_MODEL,
        },
        "agent": {
            "name":        settings.AI_AGENT_NAME,
            "company":     settings.AI_COMPANY_NAME,
            "language":    settings.AI_LANGUAGE,
            "temperature": settings.AI_TEMPERATURE,
        },
        "app": {
            "name":    settings.APP_NAME,
            "debug":   settings.DEBUG,
            "version": "2.0.0",
        },
    }


@router.post("/test-ringover")
async def test_ringover():
    return await ringover_service.test_connection()


@router.get("/webhook-urls")
async def get_webhook_urls():
    """URLs des webhooks a configurer dans Ringover."""
    # Utilise l'URL publique Render au lieu de localhost
    base = settings.public_url
    return {
        "incoming": f"{base}/webhooks/ringover/incoming",
        "dtmf":     f"{base}/webhooks/ringover/dtmf",
        "speech":   f"{base}/webhooks/ringover/speech",
        "status":   f"{base}/webhooks/ringover/status",
        "hangup":   f"{base}/webhooks/ringover/hangup",
        "note":     "Sur Render, l'URL publique est automatiquement detectee.",
    }
