"""
NexCall AI — Router Campagnes
"""
from datetime import datetime
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models.campaign import Campaign, CampaignStatus

router = APIRouter(prefix="/api/campaigns", tags=["campaigns"])


class CampaignCreate(BaseModel):
    name:             str
    description:      Optional[str] = None
    type:             str = "inbound"
    target_interest:  Optional[str] = None
    target_region:    Optional[str] = None
    ai_system_prompt: Optional[str] = None
    ivr_message:      Optional[str] = None


class CampaignUpdate(BaseModel):
    name:             Optional[str] = None
    description:      Optional[str] = None
    status:           Optional[str] = None
    target_interest:  Optional[str] = None
    target_region:    Optional[str] = None
    ai_system_prompt: Optional[str] = None
    ivr_message:      Optional[str] = None


@router.get("")
async def list_campaigns(db: AsyncSession = Depends(get_db)):
    result = await db.execute(
        select(Campaign).order_by(Campaign.created_at.desc())
    )
    return [c.to_dict() for c in result.scalars().all()]


@router.post("", status_code=201)
async def create_campaign(body: CampaignCreate, db: AsyncSession = Depends(get_db)):
    campaign = Campaign(
        name             = body.name,
        description      = body.description,
        type             = body.type,
        target_interest  = body.target_interest,
        target_region    = body.target_region,
        ai_system_prompt = body.ai_system_prompt,
        ivr_message      = body.ivr_message,
        status           = CampaignStatus.DRAFT.value,
    )
    db.add(campaign)
    await db.flush()
    return campaign.to_dict()


@router.get("/{campaign_id}")
async def get_campaign(campaign_id: int, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Campaign).where(Campaign.id == campaign_id))
    c = result.scalar_one_or_none()
    if not c:
        raise HTTPException(404, "Campagne non trouvée")
    return c.to_dict()


@router.put("/{campaign_id}")
async def update_campaign(
    campaign_id: int, body: CampaignUpdate, db: AsyncSession = Depends(get_db)
):
    result = await db.execute(select(Campaign).where(Campaign.id == campaign_id))
    c = result.scalar_one_or_none()
    if not c:
        raise HTTPException(404, "Campagne non trouvée")
    for field, value in body.model_dump(exclude_none=True).items():
        setattr(c, field, value)
    c.updated_at = datetime.utcnow()
    return c.to_dict()


@router.post("/{campaign_id}/activate")
async def activate(campaign_id: int, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Campaign).where(Campaign.id == campaign_id))
    c = result.scalar_one_or_none()
    if not c:
        raise HTTPException(404, "Campagne non trouvée")
    c.status     = CampaignStatus.ACTIVE.value
    c.is_active  = True
    c.started_at = c.started_at or datetime.utcnow()
    return {"success": True, "status": c.status}


@router.post("/{campaign_id}/pause")
async def pause(campaign_id: int, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Campaign).where(Campaign.id == campaign_id))
    c = result.scalar_one_or_none()
    if not c:
        raise HTTPException(404, "Campagne non trouvée")
    c.status    = CampaignStatus.PAUSED.value
    c.is_active = False
    return {"success": True, "status": c.status}


@router.post("/{campaign_id}/complete")
async def complete(campaign_id: int, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Campaign).where(Campaign.id == campaign_id))
    c = result.scalar_one_or_none()
    if not c:
        raise HTTPException(404, "Campagne non trouvée")
    c.status    = CampaignStatus.COMPLETED.value
    c.is_active = False
    c.ended_at  = datetime.utcnow()
    return {"success": True, "status": c.status}


@router.delete("/{campaign_id}")
async def delete_campaign(campaign_id: int, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Campaign).where(Campaign.id == campaign_id))
    c = result.scalar_one_or_none()
    if not c:
        raise HTTPException(404, "Campagne non trouvée")
    await db.delete(c)
    return {"success": True}
