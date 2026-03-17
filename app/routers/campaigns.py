from __future__ import annotations
import json
import asyncio
from datetime import datetime
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, desc
from pydantic import BaseModel
from app.models.database import get_db
from app.models.campaign import Campaign, CampaignStatus, CampaignType
from app.services.ringover import ringover
from app.services.ai_service import ai_service
import logging

log    = logging.getLogger("campaigns")
router = APIRouter(prefix="/api/campaigns", tags=["campaigns"])


class CampaignCreate(BaseModel):
    name: str
    description: Optional[str] = None
    campaign_type: str = "ai_agent"
    offer_type: Optional[str] = None
    offer_script: Optional[str] = None
    contacts: list[str] = []
    delay_between_calls: int = 5


class CampaignUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    offer_type: Optional[str] = None
    offer_script: Optional[str] = None
    contacts: Optional[list[str]] = None


@router.get("/")
async def list_campaigns(db: AsyncSession = Depends(get_db)):
    r = await db.execute(select(Campaign).order_by(desc(Campaign.created_at)))
    camps = r.scalars().all()
    return [_camp_out(c) for c in camps]


@router.post("/", status_code=201)
async def create_campaign(body: CampaignCreate, db: AsyncSession = Depends(get_db)):
    camp = Campaign(
        name=body.name,
        description=body.description,
        campaign_type=body.campaign_type,
        offer_type=body.offer_type,
        offer_script=body.offer_script,
        contacts_json=json.dumps(body.contacts),
        total_contacts=len(body.contacts),
        delay_between_calls=body.delay_between_calls,
    )
    db.add(camp)
    await db.commit()
    await db.refresh(camp)
    return _camp_out(camp)


@router.get("/{camp_id}")
async def get_campaign(camp_id: int, db: AsyncSession = Depends(get_db)):
    camp = await _get_or_404(camp_id, db)
    return _camp_out(camp)


@router.put("/{camp_id}")
async def update_campaign(camp_id: int, body: CampaignUpdate, db: AsyncSession = Depends(get_db)):
    camp = await _get_or_404(camp_id, db)
    if body.name        is not None: camp.name        = body.name
    if body.description is not None: camp.description = body.description
    if body.offer_type  is not None: camp.offer_type  = body.offer_type
    if body.offer_script is not None: camp.offer_script = body.offer_script
    if body.contacts    is not None:
        camp.contacts_json  = json.dumps(body.contacts)
        camp.total_contacts = len(body.contacts)
    await db.commit()
    await db.refresh(camp)
    return _camp_out(camp)


@router.delete("/{camp_id}")
async def delete_campaign(camp_id: int, db: AsyncSession = Depends(get_db)):
    camp = await _get_or_404(camp_id, db)
    await db.delete(camp)
    await db.commit()
    return {"deleted": camp_id}


@router.post("/{camp_id}/launch")
async def launch_campaign(camp_id: int, db: AsyncSession = Depends(get_db)):
    camp = await _get_or_404(camp_id, db)
    if camp.status == CampaignStatus.ACTIVE:
        raise HTTPException(400, "Campagne déjà active")
    contacts = json.loads(camp.contacts_json or "[]")
    if not contacts:
        raise HTTPException(400, "Aucun contact dans la campagne")
    camp.status     = CampaignStatus.ACTIVE
    camp.started_at = datetime.utcnow()
    await db.commit()
    asyncio.create_task(_run_dialer(camp_id, contacts, camp.campaign_type,
                                    camp.offer_type, camp.delay_between_calls))
    return {"status": "active", "contacts": len(contacts)}


@router.post("/{camp_id}/pause")
async def pause_campaign(camp_id: int, db: AsyncSession = Depends(get_db)):
    camp = await _get_or_404(camp_id, db)
    camp.status = CampaignStatus.PAUSED
    await db.commit()
    return {"status": "paused"}


@router.post("/{camp_id}/resume")
async def resume_campaign(camp_id: int, db: AsyncSession = Depends(get_db)):
    camp = await _get_or_404(camp_id, db)
    camp.status = CampaignStatus.ACTIVE
    await db.commit()
    return {"status": "active"}


async def _run_dialer(camp_id: int, contacts: list[str], camp_type: str,
                      offer_type: str | None, delay: int):
    from app.models.database import AsyncSessionLocal
    for number in contacts:
        async with AsyncSessionLocal() as db:
            r = await db.execute(select(Campaign).where(Campaign.id == camp_id))
            camp = r.scalar_one_or_none()
            if not camp or camp.status != CampaignStatus.ACTIVE:
                break
            try:
                await ringover.make_call(number)
                camp.calls_made += 1
                await db.commit()
            except Exception as e:
                log.error(f"Dialer error {number}: {e}")
        await asyncio.sleep(max(delay, 3))

    async with AsyncSessionLocal() as db:
        r = await db.execute(select(Campaign).where(Campaign.id == camp_id))
        camp = r.scalar_one_or_none()
        if camp and camp.status == CampaignStatus.ACTIVE:
            camp.status       = CampaignStatus.COMPLETED
            camp.completed_at = datetime.utcnow()
            await db.commit()


async def _get_or_404(camp_id: int, db: AsyncSession) -> Campaign:
    r = await db.execute(select(Campaign).where(Campaign.id == camp_id))
    camp = r.scalar_one_or_none()
    if not camp:
        raise HTTPException(404, "Campagne introuvable")
    return camp


def _camp_out(c: Campaign) -> dict:
    contacts = json.loads(c.contacts_json or "[]")
    return {
        "id": c.id, "name": c.name, "description": c.description,
        "campaign_type": c.campaign_type, "status": c.status,
        "offer_type": c.offer_type, "offer_script": c.offer_script,
        "total_contacts": c.total_contacts, "calls_made": c.calls_made,
        "calls_answered": c.calls_answered, "leads_generated": c.leads_generated,
        "contacts": contacts,
        "progress_pct": round(c.calls_made / c.total_contacts * 100, 1) if c.total_contacts else 0,
        "created_at":   c.created_at.isoformat()   if c.created_at   else None,
        "started_at":   c.started_at.isoformat()   if c.started_at   else None,
        "completed_at": c.completed_at.isoformat() if c.completed_at else None,
    }
