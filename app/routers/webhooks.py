"""
Webhooks Ringover — Réception de tous les événements d'appels
"""
from __future__ import annotations
import json
import asyncio
import logging
from datetime import datetime
from fastapi import APIRouter, Depends, Request
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.models.database import get_db
from app.models.call import Call
from app.models.lead import Lead
from app.models.campaign import Campaign
from app.services.ai_service import ai_service
from app.services.ivr_service import ivr_engine
from app.services.ringover import ringover

log    = logging.getLogger("webhooks")
router = APIRouter(prefix="/webhooks", tags=["webhooks"])

# Normalisation des types d'événements Ringover
_RINGING  = {"RINGING","CALL_CREATED","CALL.CREATED","CALL_INITIATED","INBOUND"}
_ANSWERED = {"ANSWERED","CALL_ANSWERED","CALL.ANSWERED","CALL_PICKED_UP"}
_DTMF     = {"DTMF","DTMF_RECEIVED","DIGIT_PRESSED","KEYPRESS"}
_SPEECH   = {"SPEECH","TRANSCRIPTION","STT","SPEECH_RESULT"}
_HANGUP   = {"HANGUP","CALL_ENDED","CALL.ENDED","CALL_COMPLETED","CALL_HUNG_UP"}


@router.post("/ringover")
async def ringover_webhook(request: Request, db: AsyncSession = Depends(get_db)):
    try:
        payload = await request.json()
    except Exception:
        return {"ok": False}

    evt     = (payload.get("event_type") or payload.get("type") or payload.get("event") or "").upper()
    call_id = str(payload.get("call_id") or payload.get("id") or "")
    from_n  = payload.get("from_number") or payload.get("from") or "unknown"
    to_n    = payload.get("to_number")   or payload.get("to")   or ""
    direct  = (payload.get("direction") or "inbound").lower()
    digit   = str(payload.get("digit")  or payload.get("dtmf") or payload.get("key") or "")
    speech  = payload.get("speech_text") or payload.get("transcription") or ""
    dur     = int(payload.get("duration") or payload.get("call_duration") or 0)
    rec     = payload.get("recording_url")

    log.info(f"Webhook: {evt} | call={call_id} | from={from_n}")

    if evt in _RINGING:
        await _on_ringing(call_id, from_n, to_n, direct, db)
    elif evt in _ANSWERED:
        await _on_answered(call_id, db)
    elif evt in _DTMF:
        await _on_dtmf(call_id, digit, db)
    elif evt in _SPEECH:
        await _on_speech(call_id, speech, db)
    elif evt in _HANGUP:
        await _on_hangup(call_id, dur, rec, db)

    return {"ok": True}


async def _on_ringing(call_id: str, from_n: str, to_n: str, direction: str, db: AsyncSession):
    r = await db.execute(select(Call).where(Call.call_id == call_id))
    if not r.scalar_one_or_none():
        db.add(Call(call_id=call_id, phone_number=from_n, direction=direction, status="ringing"))
        await db.commit()
    if direction == "inbound":
        asyncio.create_task(ringover.tts(call_id,
            "Bienvenue. Appuyez sur 1 pour Assurance Auto, 2 pour Assurance Santé, "
            "3 pour Immobilier, 4 pour parler à un conseiller."))


async def _on_answered(call_id: str, db: AsyncSession):
    r = await db.execute(select(Call).where(Call.call_id == call_id))
    call = r.scalar_one_or_none()
    if call:
        call.status = "in_progress"
        await db.commit()
        if call.call_type == "ai_agent":
            greeting = ai_service.get_greeting(getattr(call, "offer_type", None))
            asyncio.create_task(ringover.tts(call_id, greeting))


async def _on_dtmf(call_id: str, digit: str, db: AsyncSession):
    r = await db.execute(select(Call).where(Call.call_id == call_id))
    call = r.scalar_one_or_none()
    if not call or not digit:
        return

    # Si pas encore de menu IVR démarré, utiliser le menu par défaut
    # action basique intégrée
    _BASIC_IVR = {
        "1": ("ai_agent", "assurance_auto",  "Assurance Auto"),
        "2": ("ai_agent", "assurance_sante", "Assurance Santé"),
        "3": ("ai_agent", "immobilier",      "Immobilier"),
        "4": ("transfer", None,              "Conseiller"),
    }
    if digit in _BASIC_IVR:
        action, offer, label = _BASIC_IVR[digit]
        call.ivr_path = (call.ivr_path or "") + f"→{digit}:{label}"
        await db.commit()
        if action == "transfer":
            msg = "Je vous transfère vers un conseiller. Merci de patienter."
            asyncio.create_task(ringover.tts(call_id, msg))
        else:
            # Switch to AI agent mode for this offer
            call.call_type = "ai_agent"
            await db.commit()
            greeting = ai_service.get_greeting(offer)
            asyncio.create_task(ringover.tts(call_id, greeting))
    else:
        asyncio.create_task(ringover.tts(call_id,
            "Touche non reconnue. Appuyez sur 1, 2, 3 ou 4."))


async def _on_speech(call_id: str, speech_text: str, db: AsyncSession):
    if not speech_text:
        return
    r = await db.execute(select(Call).where(Call.call_id == call_id))
    call = r.scalar_one_or_none()
    if not call or call.call_type != "ai_agent":
        return

    result = await ai_service.process(call_id, speech_text)
    response_text = result.get("message", "")

    if result.get("should_transfer"):
        asyncio.create_task(_do_transfer(call_id, response_text))
    elif result.get("should_end"):
        asyncio.create_task(_do_end(call_id, response_text))
    else:
        asyncio.create_task(ringover.tts(call_id, response_text))

    # Update lead score
    if result.get("lead_score", 0) > 0:
        extracted = result.get("extracted", {})
        r2 = await db.execute(select(Lead).where(Lead.call_id == call_id))
        lead = r2.scalar_one_or_none()
        if not lead:
            lead = Lead(call_id=call_id, phone_number=call.phone_number)
            db.add(lead)
            await db.flush()
        lead.qualification_score = max(lead.qualification_score, result["lead_score"])
        lead.is_hot = lead.qualification_score >= 70
        if extracted.get("nom"):      lead.name             = extracted["nom"]
        if extracted.get("service"):  lead.service_interest = extracted["service"]
        call.intent = result.get("intent")
        await db.commit()


async def _on_hangup(call_id: str, duration: int, recording_url: str | None, db: AsyncSession):
    r = await db.execute(select(Call).where(Call.call_id == call_id))
    call = r.scalar_one_or_none()
    if call:
        call.status          = "completed"
        call.duration_seconds = duration
        call.ended_at        = datetime.utcnow()
        if recording_url:
            call.recording_url = recording_url
        # Save transcript
        transcript = ai_service.get_transcript(call_id)
        if transcript:
            call.transcript = json.dumps(transcript, ensure_ascii=False)
            call.ai_summary = await ai_service.generate_summary(call_id)
        ai_service.clear(call_id)
        await db.commit()


async def _do_transfer(call_id: str, message: str):
    from app.config import settings
    if message:
        await ringover.tts(call_id, message)
    import asyncio; await asyncio.sleep(2)
    if settings.RINGOVER_TRANSFER_NUMBER:
        await ringover.transfer(call_id, settings.RINGOVER_TRANSFER_NUMBER)

async def _do_end(call_id: str, message: str):
    if message:
        await ringover.tts(call_id, message)
    import asyncio; await asyncio.sleep(3)
    await ringover.hangup(call_id)
