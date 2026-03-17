"""
Service IA — Conversations vocales intelligentes via OpenAI GPT-4o
"""
from __future__ import annotations
import json
import logging
from typing import Any
from app.config import settings

log = logging.getLogger("ai_service")

SYSTEM_PROMPT_TEMPLATE = """Tu es {agent_name}, conseiller(ère) commercial(e) expert(e) chez {company_name}.
Tu réponds UNIQUEMENT en français, de manière chaleureuse, professionnelle et concise (1-3 phrases max).
Tu aides les appelants à obtenir des informations sur : {services}.

RÈGLES ABSOLUES:
- Réponses courtes et naturelles (conversation téléphonique)
- Ne jamais inventer de prix ou de garanties
- Si demande de devis → collecter: nom, téléphone, service souhaité, puis confirmer un rappel
- Si réclamation complexe → transférer à un conseiller humain

Réponds TOUJOURS en JSON:
{{
  "message": "ta réponse vocale",
  "intent": "information|devis|reclamation|transfert|fin|inconnu",
  "should_transfer": false,
  "should_end": false,
  "extracted": {{"nom": null, "telephone": null, "service": null}},
  "lead_score": 0
}}
"""

SERVICES_MAP = {
    "assurance_auto": "l'assurance auto",
    "assurance_sante": "l'assurance santé",
    "mutuelle": "la mutuelle",
    "immobilier": "l'immobilier",
    "credit": "le crédit",
}


class AIConversationService:
    def __init__(self):
        self._history: dict[str, list] = {}  # call_id → messages

    def _get_system_prompt(self, offer_type: str | None = None) -> str:
        services = ", ".join(SERVICES_MAP.values()) if not offer_type else SERVICES_MAP.get(offer_type, offer_type)
        return SYSTEM_PROMPT_TEMPLATE.format(
            agent_name=settings.AI_AGENT_NAME,
            company_name=settings.AI_COMPANY_NAME,
            services=services,
        )

    async def process(self, call_id: str, user_text: str, offer_type: str | None = None) -> dict[str, Any]:
        if not settings.OPENAI_API_KEY:
            return self._fallback(user_text)

        try:
            from openai import AsyncOpenAI
            client = AsyncOpenAI(api_key=settings.OPENAI_API_KEY)

            history = self._history.setdefault(call_id, [])
            history.append({"role": "user", "content": user_text})

            resp = await client.chat.completions.create(
                model=settings.OPENAI_MODEL,
                messages=[
                    {"role": "system", "content": self._get_system_prompt(offer_type)},
                    *history[-12:],  # garde les 6 derniers échanges
                ],
                temperature=settings.AI_TEMPERATURE,
                max_tokens=300,
                response_format={"type": "json_object"},
            )

            raw = resp.choices[0].message.content
            result = json.loads(raw)
            result = self._validate(result)
            history.append({"role": "assistant", "content": result["message"]})

            log.info(f"[{call_id}] intent={result['intent']} score={result['lead_score']}")
            return result

        except Exception as e:
            log.error(f"OpenAI error: {e}")
            return self._fallback(user_text)

    def get_greeting(self, offer_type: str | None = None) -> str:
        services = SERVICES_MAP.get(offer_type or "", "nos services")
        return (
            f"Bonjour, je suis {settings.AI_AGENT_NAME} de {settings.AI_COMPANY_NAME}. "
            f"Je vous appelle au sujet de {services}. "
            f"Avez-vous quelques minutes pour en discuter ?"
        )

    def get_transcript(self, call_id: str) -> list[dict]:
        return self._history.get(call_id, [])

    def clear(self, call_id: str) -> None:
        self._history.pop(call_id, None)

    async def generate_summary(self, call_id: str) -> str:
        history = self._history.get(call_id, [])
        if not history or not settings.OPENAI_API_KEY:
            return "Aucun résumé disponible."
        try:
            from openai import AsyncOpenAI
            client = AsyncOpenAI(api_key=settings.OPENAI_API_KEY)
            conv_text = "\n".join(f"{m['role'].upper()}: {m['content']}" for m in history)
            resp = await client.chat.completions.create(
                model=settings.OPENAI_MODEL,
                messages=[{
                    "role": "user",
                    "content": f"Résume cette conversation téléphonique en 2-3 phrases concises pour un CRM:\n\n{conv_text}",
                }],
                max_tokens=150,
            )
            return resp.choices[0].message.content or "Résumé indisponible."
        except Exception as e:
            log.error(f"Summary error: {e}")
            return "Erreur génération résumé."

    def _validate(self, r: dict) -> dict:
        defaults = {
            "message": "Comment puis-je vous aider ?",
            "intent": "inconnu",
            "should_transfer": False,
            "should_end": False,
            "extracted": {"nom": None, "telephone": None, "service": None},
            "lead_score": 0,
        }
        for k, v in defaults.items():
            if k not in r:
                r[k] = v
        return r

    def _fallback(self, text: str) -> dict:
        return {
            "message": f"Bonjour, je suis {settings.AI_AGENT_NAME}. Comment puis-je vous aider aujourd'hui ?",
            "intent": "inconnu",
            "should_transfer": False,
            "should_end": False,
            "extracted": {"nom": None, "telephone": None, "service": None},
            "lead_score": 0,
        }


ai_service = AIConversationService()
