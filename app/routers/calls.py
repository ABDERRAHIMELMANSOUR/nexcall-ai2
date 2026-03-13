"""
NexCall AI — Router Appels
CRUD + statistiques + simulation + transfert
"""
import logging
from datetime import datetime
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models.call import Call, CallStatus
from app.services.ringover_service import ringover_service
from app.services.ai_agent import ai_agent
from app.services.ivr_service import ivr_service
from app.services.lead_service import lead_service
from app.config import settings

router = APIRouter(prefix="/api/calls", tags=["calls"])
logger = logging.getLogger(__name__)


# ── Schemas ──────────────────────────────────────────────────────────────────

class SimulateCallRequest(BaseModel):
    caller_number: str = "+33600000000"
    ivr_digit: str = "1"
    message: str = "Bonjour, je cherche une assurance auto pour mon véhicule."
    campaign_prompt: Optional[str] = None


# ── Endpoints ────────────────────────────────────────────────────────────────

@router.get("")
async def list_calls(
    limit:  int            = Query(50, ge=1, le=500),
    offset: int            = Query(0, ge=0),
    status: Optional[str]  = None,
    db: AsyncSession = Depends(get_db),
):
    q = select(Call).order_by(Call.created_at.desc()).limit(limit).offset(offset)
    if status:
        q = q.where(Call.status == status)
    result = await db.execute(q)
    return [c.to_dict() for c in result.scalars().all()]


@router.get("/stats")
async def get_stats(db: AsyncSession = Depends(get_db)):
    total      = await db.scalar(select(func.count(Call.id))) or 0
    completed  = await db.scalar(select(func.count(Call.id)).where(Call.status == CallStatus.COMPLETED.value)) or 0
    missed     = await db.scalar(select(func.count(Call.id)).where(Call.status == CallStatus.MISSED.value)) or 0
    transferred= await db.scalar(select(func.count(Call.id)).where(Call.status == CallStatus.TRANSFERRED.value)) or 0
    in_progress= await db.scalar(select(func.count(Call.id)).where(Call.status == CallStatus.IN_PROGRESS.value)) or 0
    avg_dur    = await db.scalar(select(func.avg(Call.duration)).where(Call.status == CallStatus.COMPLETED.value)) or 0
    return {
        "total":       total,
        "completed":   completed,
        "missed":      missed,
        "transferred": transferred,
        "in_progress": in_progress,
        "avg_duration": round(avg_dur, 1),
    }


@router.get("/{call_id}")
async def get_call(call_id: int, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Call).where(Call.id == call_id))
    call = result.scalar_one_or_none()
    if not call:
        raise HTTPException(404, "Appel non trouvé")
    return call.to_dict()


@router.post("/{call_id}/transfer")
async def transfer_call(call_id: int, db: AsyncSession = Depends(get_db)):
    """Transfère un appel actif vers l'agent humain configuré"""
    result = await db.execute(select(Call).where(Call.id == call_id))
    call = result.scalar_one_or_none()
    if not call:
        raise HTTPException(404, "Appel non trouvé")

    transfer_number = settings.RINGOVER_TRANSFER_NUMBER
    if not transfer_number:
        raise HTTPException(400, "Numéro de transfert non configuré")

    if call.ringover_call_id:
        res = await ringover_service.transfer_call(call.ringover_call_id, transfer_number)
        if not res.get("success"):
            raise HTTPException(502, f"Ringover transfer failed: {res.get('error')}")

    call.status       = CallStatus.TRANSFERRED.value
    call.transfer_to  = transfer_number
    call.transferred_at = datetime.utcnow()

    return {"success": True, "transfer_to": transfer_number}


@router.post("/simulate")
async def simulate_call(body: SimulateCallRequest, db: AsyncSession = Depends(get_db)):
    """
    Simule un appel complet sans Ringover.
    Utile pour tester l'agent IA et le pipeline de qualification.
    """
    fake_id = f"sim_{int(datetime.utcnow().timestamp() * 1000)}"

    # 1. Créer l'enregistrement d'appel
    call = Call(
        ringover_call_id = fake_id,
        caller_number    = body.caller_number,
        called_number    = settings.RINGOVER_PHONE_NUMBER or "+33000000000",
        status           = CallStatus.IN_PROGRESS.value,
        direction        = "inbound",
        started_at       = datetime.utcnow(),
    )

    # 2. Traitement IVR
    ivr_result = ivr_service.process_dtmf(body.ivr_digit)
    call.ivr_choice = ivr_result.get("intent")

    # 3. Conversation IA
    ai_session = ai_agent.create_session(
        fake_id,
        ivr_choice      = call.ivr_choice,
        campaign_prompt = body.campaign_prompt,
    )

    ai_response = await ai_agent.chat(
        call_id       = fake_id,
        user_message  = body.message,
        ivr_choice    = call.ivr_choice,
    )

    # 4. Finalisation de l'appel
    call.transcript = f"Client : {body.message}\nIA : {ai_response['text']}"
    call.status     = CallStatus.COMPLETED.value
    call.duration   = 45
    call.ended_at   = datetime.utcnow()
    call.answered_at = call.started_at

    # 5. Résumé IA
    call.ai_summary = await ai_agent.summarize_call(call.transcript)

    db.add(call)
    await db.flush()

    # 6. Création/mise à jour du lead
    lead_data = ai_response.get("lead_data")
    if lead_data:
        lead = await lead_service.upsert_from_call(db, body.caller_number, lead_data)
        call.lead_id = lead.id
        await db.flush()

    # Nettoyage session
    ai_agent.end_session(fake_id)

    return {
        "call_id":    call.id,
        "call_status": call.status,
        "ivr_choice": call.ivr_choice,
        "ai_greeting": ivr_result.get("message"),
        "ai_response": ai_response["text"],
        "ai_summary":  call.ai_summary,
        "lead_data":   lead_data,
        "transcript":  call.transcript,
    }


@router.delete("/{call_id}")
async def delete_call(call_id: int, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Call).where(Call.id == call_id))
    call = result.scalar_one_or_none()
    if not call:
        raise HTTPException(404, "Appel non trouvé")
    await db.delete(call)
    return {"success": True}
