"""
NexCall AI — Webhooks Ringover
Endpoints appelés par Ringover lors des événements téléphoniques.

Configuration dans Ringover :
  - Appel entrant  : POST /webhooks/ringover/incoming
  - DTMF           : POST /webhooks/ringover/dtmf
  - Parole         : POST /webhooks/ringover/speech
  - Statut         : POST /webhooks/ringover/status
  - Fin d'appel    : POST /webhooks/ringover/hangup
"""
import json
import logging
from datetime import datetime
from typing import Any

from fastapi import APIRouter, Depends, Request, Response
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models.call import Call, CallStatus
from app.services.ai_agent import ai_agent
from app.services.ivr_service import ivr_service
from app.services.lead_service import lead_service
from app.services.ringover_service import ringover_service
from app.config import settings

router = APIRouter(prefix="/webhooks/ringover", tags=["webhooks"])
logger = logging.getLogger(__name__)

# ──────────────────────────────────────────────────────────────────────────────
# Helpers
# ──────────────────────────────────────────────────────────────────────────────

def _map_ringover_status(raw: str) -> str:
    return {
        "ringing":    CallStatus.RINGING.value,
        "answered":   CallStatus.ANSWERED.value,
        "in_progress": CallStatus.IN_PROGRESS.value,
        "transferred": CallStatus.TRANSFERRED.value,
        "ended":      CallStatus.COMPLETED.value,
        "completed":  CallStatus.COMPLETED.value,
        "hangup":     CallStatus.COMPLETED.value,
        "no_answer":  CallStatus.MISSED.value,
        "busy":       CallStatus.MISSED.value,
        "failed":     CallStatus.FAILED.value,
    }.get(raw.lower(), raw)


async def _get_or_create_call(
    db: AsyncSession,
    call_id: str,
    caller: str,
    called: str = "",
) -> Call:
    result = await db.execute(select(Call).where(Call.ringover_call_id == call_id))
    call = result.scalar_one_or_none()
    if not call:
        call = Call(
            ringover_call_id = call_id,
            caller_number    = caller,
            called_number    = called or settings.RINGOVER_PHONE_NUMBER or "",
            status           = CallStatus.INCOMING.value,
            direction        = "inbound",
            started_at       = datetime.utcnow(),
        )
        db.add(call)
        await db.flush()
    return call


# ──────────────────────────────────────────────────────────────────────────────
# 1. Appel entrant
# ──────────────────────────────────────────────────────────────────────────────
@router.post("/incoming")
async def webhook_incoming(request: Request, db: AsyncSession = Depends(get_db)):
    """Déclenché dès qu'un appel entrant est reçu"""
    body: dict[str, Any] = {}
    try:
        body = await request.json()
    except Exception:
        pass

    call_id = body.get("call_uuid") or body.get("call_id") or f"rng_{int(datetime.utcnow().timestamp()*1000)}"
    caller  = body.get("from_number") or body.get("caller") or body.get("from", "Inconnu")
    called  = body.get("to_number")   or body.get("callee") or ""

    logger.info(f"[WEBHOOK] ☎  Incoming call: {caller} → {called} (id={call_id})")

    call = await _get_or_create_call(db, call_id, caller, called)

    # Créer la session IA
    ai_agent.create_session(call_id)

    greeting = ivr_service.get_greeting()

    return {
        "status":  "ok",
        "call_id": call_id,
        "action":  "play_ivr",
        "message": greeting,
    }


# ──────────────────────────────────────────────────────────────────────────────
# 2. Touche DTMF pressée
# ──────────────────────────────────────────────────────────────────────────────
@router.post("/dtmf")
async def webhook_dtmf(request: Request, db: AsyncSession = Depends(get_db)):
    """Déclenché quand le client appuie sur une touche"""
    body: dict[str, Any] = {}
    try:
        body = await request.json()
    except Exception:
        pass

    call_id = body.get("call_uuid") or body.get("call_id", "")
    digit   = str(body.get("digit") or body.get("dtmf", ""))

    logger.info(f"[WEBHOOK] 🔢 DTMF: call={call_id} digit={digit}")

    ivr_result = ivr_service.process_dtmf(digit)

    # Mise à jour en BDD
    if call_id:
        result = await db.execute(select(Call).where(Call.ringover_call_id == call_id))
        call = result.scalar_one_or_none()
        if call:
            call.ivr_choice  = ivr_result.get("intent")
            call.status      = CallStatus.IN_PROGRESS.value
            call.answered_at = call.answered_at or datetime.utcnow()
            await db.flush()

    # Mise à jour de la session IA
    session = ai_agent.get_session(call_id)
    if session:
        session.ivr_choice = ivr_result.get("intent")

    # Transfert immédiat si touche 3
    if ivr_result.get("is_transfer"):
        transfer_number = settings.RINGOVER_TRANSFER_NUMBER
        if transfer_number and call_id:
            await ringover_service.transfer_call(call_id, transfer_number)
        return {
            "status":  "ok",
            "action":  "transfer",
            "to":      transfer_number,
            "message": ivr_result["message"],
        }

    return {
        "status":  "ok",
        "action":  "connect_ai" if ivr_result["valid"] else "replay_ivr",
        "intent":  ivr_result.get("intent"),
        "message": ivr_result["message"],
    }


# ──────────────────────────────────────────────────────────────────────────────
# 3. Parole reconnue (STT externe ou transcription Ringover)
# ──────────────────────────────────────────────────────────────────────────────
@router.post("/speech")
async def webhook_speech(request: Request, db: AsyncSession = Depends(get_db)):
    """Déclenché quand la parole du client est transcrite"""
    body: dict[str, Any] = {}
    try:
        body = await request.json()
    except Exception:
        pass

    call_id    = body.get("call_uuid") or body.get("call_id", "")
    transcript = body.get("transcript") or body.get("text", "")

    logger.info(f"[WEBHOOK] 🎤 Speech: call={call_id} text='{transcript[:80]}'")

    session = ai_agent.get_session(call_id)
    ivr_choice      = session.ivr_choice if session else None
    campaign_prompt = session.campaign_prompt if session else None

    # Appel à l'agent IA
    ai_response = await ai_agent.chat(
        call_id        = call_id,
        user_message   = transcript,
        ivr_choice     = ivr_choice,
        campaign_prompt = campaign_prompt,
    )

    response_text = ai_response["text"]
    lead_data     = ai_response.get("lead_data")

    # Mise à jour du call en BDD
    if call_id:
        result = await db.execute(select(Call).where(Call.ringover_call_id == call_id))
        call = result.scalar_one_or_none()
        if call:
            existing = call.transcript or ""
            call.transcript = f"{existing}\nClient : {transcript}\nIA : {response_text}".strip()

            # Sauvegarde du lead si données suffisantes
            if lead_data and call.caller_number:
                try:
                    lead = await lead_service.upsert_from_call(
                        db, call.caller_number, lead_data
                    )
                    call.lead_id = lead.id
                    await db.flush()
                except Exception as e:
                    logger.error(f"Lead upsert error: {e}")

    # Décision de transfert
    should_transfer = bool(lead_data and lead_data.get("should_transfer"))
    action = "transfer_then_speak" if should_transfer else "speak"

    return {
        "status":          "ok",
        "action":          action,
        "message":         response_text,
        "should_transfer": should_transfer,
        "transfer_to":     settings.RINGOVER_TRANSFER_NUMBER if should_transfer else None,
    }


# ──────────────────────────────────────────────────────────────────────────────
# 4. Changement de statut
# ──────────────────────────────────────────────────────────────────────────────
@router.post("/status")
async def webhook_status(request: Request, db: AsyncSession = Depends(get_db)):
    """Déclenché lors d'un changement de statut de l'appel"""
    body: dict[str, Any] = {}
    try:
        body = await request.json()
    except Exception:
        pass

    call_id  = body.get("call_uuid") or body.get("call_id", "")
    status   = body.get("status", "")
    duration = body.get("duration") or body.get("call_duration", 0)

    logger.info(f"[WEBHOOK] 📊 Status: call={call_id} status={status} duration={duration}s")

    if not call_id:
        return {"status": "ok", "ignored": True}

    result = await db.execute(select(Call).where(Call.ringover_call_id == call_id))
    call = result.scalar_one_or_none()

    if call:
        call.status = _map_ringover_status(status)
        if duration:
            call.duration = int(duration)
        if status.lower() in ("ended", "completed", "hangup"):
            call.ended_at = datetime.utcnow()
            if not call.duration and call.started_at:
                delta = datetime.utcnow() - call.started_at
                call.duration = int(delta.total_seconds())
            # Génération du résumé IA
            if call.transcript:
                try:
                    call.ai_summary = await ai_agent.summarize_call(call.transcript)
                except Exception as e:
                    logger.warning(f"Summary generation failed: {e}")
            # Nettoyage de la session
            ai_agent.end_session(call_id)
        await db.flush()

    return {"status": "ok"}


# ──────────────────────────────────────────────────────────────────────────────
# 5. Fin d'appel (alias de /status avec status=ended)
# ──────────────────────────────────────────────────────────────────────────────
@router.post("/hangup")
async def webhook_hangup(request: Request, db: AsyncSession = Depends(get_db)):
    """Alias fin d'appel — délègue à /status"""
    body: dict[str, Any] = {}
    try:
        raw = await request.body()
        body = json.loads(raw) if raw else {}
    except Exception:
        pass

    body.setdefault("status", "ended")

    # On reconstruit un faux Request pour réutiliser webhook_status
    from starlette.datastructures import Headers
    from starlette.requests import Request as StarletteRequest
    import io

    new_body = json.dumps(body).encode()

    class FakeRequest:
        async def json(self):
            return body

    return await webhook_status(FakeRequest(), db)
