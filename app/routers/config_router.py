from __future__ import annotations
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from pydantic import BaseModel
from typing import Optional
from app.models.database import get_db
from app.models.agent_config import AgentConfig
from app.services.ringover import ringover

router = APIRouter(prefix="/api/config", tags=["config"])


class AgentConfigIn(BaseModel):
    name: str
    company_name: str
    language: str = "fr"
    voice: str = "nova"
    temperature: float = 0.7
    system_prompt: Optional[str] = None
    greeting_text: Optional[str] = None


@router.get("/agent")
async def get_agent_config(db: AsyncSession = Depends(get_db)):
    r = await db.execute(select(AgentConfig).where(AgentConfig.is_default == True))
    cfg = r.scalar_one_or_none()
    if not cfg:
        cfg = AgentConfig()
        db.add(cfg)
        await db.commit()
        await db.refresh(cfg)
    return _cfg_out(cfg)


@router.put("/agent")
async def update_agent_config(body: AgentConfigIn, db: AsyncSession = Depends(get_db)):
    r = await db.execute(select(AgentConfig).where(AgentConfig.is_default == True))
    cfg = r.scalar_one_or_none()
    if not cfg:
        cfg = AgentConfig(is_default=True)
        db.add(cfg)

    cfg.name           = body.name
    cfg.company_name   = body.company_name
    cfg.language       = body.language
    cfg.voice          = body.voice
    cfg.temperature    = body.temperature
    cfg.system_prompt  = body.system_prompt
    cfg.greeting_text  = body.greeting_text
    await db.commit()
    await db.refresh(cfg)
    return _cfg_out(cfg)


@router.get("/ringover/test")
async def test_ringover():
    result = await ringover.test_connection()
    return result


@router.get("/ringover/numbers")
async def get_numbers():
    nums = await ringover.get_numbers()
    return {"numbers": nums}


@router.get("/ringover/users")
async def get_users():
    users = await ringover.get_users()
    return {"users": users}


@router.get("/system")
async def system_info():
    from app.config import settings
    from pathlib import Path
    env_path = Path(__file__).resolve().parent.parent.parent / ".env"
    return {
        "app":     settings.APP_NAME,
        "version": "2.0.0",
        "ringover_configured": settings.is_ringover_configured,
        "openai_configured":   settings.is_openai_configured,
        "agent_name":    settings.AI_AGENT_NAME,
        "company_name":  settings.AI_COMPANY_NAME,
        "env_file_found": env_path.exists(),
        "env_path": str(env_path),
    }


def _cfg_out(c: AgentConfig) -> dict:
    return {
        "id": c.id, "name": c.name, "company_name": c.company_name,
        "language": c.language, "voice": c.voice, "temperature": c.temperature,
        "system_prompt": c.system_prompt, "greeting_text": c.greeting_text,
    }
