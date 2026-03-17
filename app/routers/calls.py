"""
Router /api/calls — Gestion des appels
"""
from __future__ import annotations
from datetime import datetime
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, desc
from app.models.database import get_db
from app.models.call import Call
from app.models.lead import Lead
from app.services.ringover import ringover
from app.services.ai_service import ai_service
from pydantic import BaseModel

router = APIRouter(prefix="/api/calls", tags=["calls"])


class OutboundCallIn(BaseModel):
    to_number: str
    campaign_id: Optional[int] = None
    offer_type: Optional[str] = None
    call_type: str = "ai_agent"


@router.get("/")
async def list_calls(
    page: int = Query(1, ge=1),
    limit: int = Query(20, ge=1, le=100),
    status: Optional[str] = None,
    direction: Optional[str] = None,
    db: AsyncSession = Depends(get_db),
):
    q = select(Call).order_by(desc(Call.started_at))
    if status:    q = q.where(Call.status == status)
    if direction: q = q.where(Call.direction == direction)

    total_r = await db.execute(select(func.count()).select_from(q.subquery()))
    total   = total_r.scalar() or 0
    rows    = await db.execute(q.offset((page - 1) * limit).limit(limit))
    calls   = rows.scalars().all()

    return {
        "total": total, "page": page, "limit": limit,
        "calls": [_call_out(c) for c in calls],
    }


@router.get("/stats")
async def get_stats(days: int = Query(7, ge=1, le=90), db: AsyncSession = Depends(get_db)):
    from datetime import timedelta
    since = datetime.utcnow() - timedelta(days=days)

    total_r = await db.execute(select(func.count(Call.id)).where(Call.started_at >= since))
    total   = total_r.scalar() or 0

    today_start = datetime.utcnow().replace(hour=0, minute=0, second=0)
    today_r = await db.execute(select(func.count(Call.id)).where(Call.started_at >= today_start))
    today   = today_r.scalar() or 0

    done_r = await db.execute(
        select(func.count(Call.id)).where(Call.started_at >= since, Call.status == "completed")
    )
    done = done_r.scalar() or 0

    avg_r = await db.execute(
        select(func.avg(Call.duration_seconds)).where(
            Call.started_at >= since, Call.duration_seconds > 0
        )
    )
    avg_dur = round(avg_r.scalar() or 0)

    leads_r = await db.execute(select(func.count(Lead.id)).where(Lead.created_at >= since))
    leads   = leads_r.scalar() or 0

    hot_r = await db.execute(
        select(func.count(Lead.id)).where(Lead.created_at >= since, Lead.is_hot == True)
    )
    hot_leads = hot_r.scalar() or 0

    # Daily calls for chart
    daily = []
    for i in range(days):
        d = datetime.utcnow() - timedelta(days=days - i - 1)
        ds = d.replace(hour=0, minute=0, second=0)
        de = d.replace(hour=23, minute=59, second=59)
        n_r = await db.execute(
            select(func.count(Call.id)).where(Call.started_at.between(ds, de))
        )
        daily.append({"date": d.strftime("%d/%m"), "calls": n_r.scalar() or 0})

    return {
        "total_calls":      total,
        "calls_today":      today,
        "completed_calls":  done,
        "success_rate":     round(done / total * 100, 1) if total else 0,
        "avg_duration_sec": avg_dur,
        "total_leads":      leads,
        "hot_leads":        hot_leads,
        "daily_calls":      daily,
    }


@router.get("/{call_id}/detail")
async def get_call_detail(call_id: str, db: AsyncSession = Depends(get_db)):
    r = await db.execute(select(Call).where(Call.call_id == call_id))
    call = r.scalar_one_or_none()
    if not call:
        raise HTTPException(404, "Appel introuvable")

    transcript = ai_service.get_transcript(call_id)

    return {
        **_call_out(call),
        "transcript": transcript,
        "ai_summary": call.ai_summary,
    }


@router.post("/outbound")
async def make_outbound_call(body: OutboundCallIn, db: AsyncSession = Depends(get_db)):
    result = await ringover.make_call(body.to_number)
    call_id = str((result or {}).get("call_id") or f"OUT_{int(datetime.utcnow().timestamp())}")

    call = Call(
        call_id=call_id,
        phone_number=body.to_number,
        direction="outbound",
        call_type=body.call_type,
        campaign_id=body.campaign_id,
        status="ringing",
    )
    db.add(call)
    await db.commit()

    return {"call_id": call_id, "status": "ringing", "to": body.to_number}


def _call_out(c: Call) -> dict:
    return {
        "id": c.id,
        "call_id": c.call_id,
        "phone_number": c.phone_number,
        "direction": c.direction,
        "call_type": c.call_type,
        "status": c.status,
        "intent": c.intent,
        "duration_seconds": c.duration_seconds,
        "transferred": c.transferred,
        "campaign_id": c.campaign_id,
        "started_at": c.started_at.isoformat() if c.started_at else None,
        "ended_at":   c.ended_at.isoformat()   if c.ended_at   else None,
    }
