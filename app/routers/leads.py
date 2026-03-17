from __future__ import annotations
from datetime import datetime
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, desc
from app.models.database import get_db
from app.models.lead import Lead
import csv, io

router = APIRouter(prefix="/api/leads", tags=["leads"])


@router.get("/")
async def list_leads(
    page: int = Query(1, ge=1),
    limit: int = Query(20, ge=1, le=100),
    contacted: Optional[bool] = None,
    is_hot: Optional[bool] = None,
    min_score: Optional[float] = None,
    db: AsyncSession = Depends(get_db),
):
    q = select(Lead).order_by(desc(Lead.qualification_score), desc(Lead.created_at))
    if contacted is not None: q = q.where(Lead.contacted == contacted)
    if is_hot is not None:    q = q.where(Lead.is_hot == is_hot)
    if min_score is not None: q = q.where(Lead.qualification_score >= min_score)

    total_r = await db.execute(select(func.count()).select_from(q.subquery()))
    total   = total_r.scalar() or 0
    rows    = await db.execute(q.offset((page - 1) * limit).limit(limit))
    leads   = rows.scalars().all()

    return {"total": total, "page": page, "limit": limit,
            "leads": [_lead_out(l) for l in leads]}


@router.patch("/{lead_id}/contacted")
async def mark_contacted(lead_id: int, db: AsyncSession = Depends(get_db)):
    r = await db.execute(select(Lead).where(Lead.id == lead_id))
    lead = r.scalar_one_or_none()
    if not lead:
        raise HTTPException(404, "Lead introuvable")
    lead.contacted    = True
    lead.contacted_at = datetime.utcnow()
    await db.commit()
    return {"success": True}


@router.delete("/{lead_id}")
async def delete_lead(lead_id: int, db: AsyncSession = Depends(get_db)):
    r = await db.execute(select(Lead).where(Lead.id == lead_id))
    lead = r.scalar_one_or_none()
    if not lead:
        raise HTTPException(404, "Lead introuvable")
    await db.delete(lead)
    await db.commit()
    return {"deleted": lead_id}


@router.get("/export/csv")
async def export_csv(db: AsyncSession = Depends(get_db)):
    rows = await db.execute(select(Lead).order_by(desc(Lead.created_at)))
    leads = rows.scalars().all()

    buf = io.StringIO()
    w   = csv.writer(buf)
    w.writerow(["ID", "Téléphone", "Nom", "Service", "Intent", "Score", "Chaud", "Contacté", "Date"])
    for l in leads:
        w.writerow([l.id, l.phone_number, l.name or "", l.service_interest or "",
                    l.intent or "", l.qualification_score,
                    "Oui" if l.is_hot else "Non",
                    "Oui" if l.contacted else "Non",
                    l.created_at.strftime("%d/%m/%Y %H:%M") if l.created_at else ""])
    buf.seek(0)
    return StreamingResponse(iter([buf.getvalue()]), media_type="text/csv",
                              headers={"Content-Disposition": "attachment; filename=leads.csv"})


def _lead_out(l: Lead) -> dict:
    return {
        "id": l.id, "call_id": l.call_id, "phone_number": l.phone_number,
        "name": l.name, "email": l.email, "service_interest": l.service_interest,
        "intent": l.intent, "qualification_score": l.qualification_score,
        "is_hot": l.is_hot, "contacted": l.contacted, "notes": l.notes,
        "created_at": l.created_at.isoformat() if l.created_at else None,
    }
