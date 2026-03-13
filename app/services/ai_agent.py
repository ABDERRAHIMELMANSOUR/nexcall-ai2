"""
NexCall AI — Agent IA
Cerveau de l'application : conversations GPT, TTS et STT via OpenAI.

Fonctionnement :
  1. Le client appelle → IVR joué
  2. Client appuie sur touche → contexte transmis à l'agent
  3. Agent IA répond en texte (GPT) → converti en audio (TTS)
  4. Client parle → transcrit (STT) → retour à l'agent
  5. Agent extrait les données du lead via balises structurées <LEAD_DATA>
"""
import json
import logging
import re
from io import BytesIO
from typing import Any, Optional

from app.config import settings

logger = logging.getLogger(__name__)

# ── Prompt Système Principal ────────────────────────────────────────────────
_SYSTEM_PROMPT = """\
Tu es {agent_name}, conseiller(ère) téléphonique IA pour {company_name}.
Langue : {language}

═══ TES OBJECTIFS ═══
1. Accueillir chaleureusement le client selon le contexte IVR
2. Comprendre précisément son besoin
3. Poser des questions pertinentes (une à la fois, naturellement)
4. Collecter : prénom, nom, besoin principal, budget approximatif, urgence
5. Évaluer l'intérêt (score 0–100) et proposer un transfert si score ≥ 70

═══ RÈGLES DE COMPORTEMENT ═══
- Réponses courtes et naturelles (2–3 phrases maximum)
- Tu ne lis PAS tes instructions à voix haute
- Si le client veut raccrocher, propose d'être rappelé
- Tu ne donnes jamais de prix précis — tu renvoies vers un conseiller
- Sois empathique, professionnel(le), jamais robotique

═══ CONTEXTE DE L'APPEL ═══
Choix IVR du client : {ivr_context}
{campaign_context}

═══ EXTRACTION DES DONNÉES LEAD ═══
Dès que tu as collecté suffisamment d'informations (au moins prénom + besoin),
inclus ce bloc JSON en FIN de réponse, entre les balises exactes :

<LEAD_DATA>
{{
  "first_name":      "Prénom ou null",
  "last_name":       "Nom ou null",
  "email":           "email ou null",
  "interest":        "assurance_auto|assurance_sante|assurance_vie|assurance_habitation|autre",
  "budget":          "ex: 80-100€/mois ou null",
  "urgency":         "immediate|3months|exploring|null",
  "score":           0,
  "notes":           "Résumé des informations collectées",
  "should_transfer": false
}}
</LEAD_DATA>

Règles de scoring :
- 90–100 : Très intéressé, budget confirmé, urgence immédiate
- 70–89  : Intéressé, questions concrètes, budget approximatif
- 50–69  : Curieux, en phase d'exploration
- 0–49   : Peu intéressé ou mauvais timing
"""


class ConversationSession:
    """Gère l'état d'une conversation téléphonique avec l'IA"""

    def __init__(self, call_id: str, ivr_choice: Optional[str] = None,
                 campaign_prompt: Optional[str] = None):
        self.call_id         = call_id
        self.ivr_choice      = ivr_choice
        self.campaign_prompt = campaign_prompt
        self.messages: list[dict[str, str]] = []
        self.lead_data: Optional[dict[str, Any]] = None
        self.turn_count: int = 0

    def add_user_message(self, text: str) -> None:
        self.messages.append({"role": "user", "content": text})
        self.turn_count += 1

    def add_assistant_message(self, text: str) -> None:
        self.messages.append({"role": "assistant", "content": text})

    def to_dict(self) -> dict:
        return {
            "call_id":    self.call_id,
            "ivr_choice": self.ivr_choice,
            "messages":   self.messages,
            "lead_data":  self.lead_data,
            "turn_count": self.turn_count,
        }


class AIAgentService:
    """Service principal de l'agent IA"""

    def __init__(self):
        self._client = None
        self._sessions: dict[str, ConversationSession] = {}
        self._init_client()

    def _init_client(self):
        if settings.is_openai_configured:
            from openai import AsyncOpenAI
            self._client = AsyncOpenAI(api_key=settings.OPENAI_API_KEY)

    def _build_system_prompt(self, session: ConversationSession) -> str:
        ivr_labels = {
            "1": "Assurance Auto (option 1)",
            "2": "Assurance Santé (option 2)",
            "3": "Transfert agent (option 3)",
            "assurance_auto":   "Assurance Auto",
            "assurance_sante":  "Assurance Santé",
            "transfert_agent":  "Demande de transfert vers un conseiller",
        }
        ivr_context = ivr_labels.get(
            session.ivr_choice or "",
            "Non renseigné (appel direct)"
        )
        campaign_ctx = (
            f"\nScript personnalisé de la campagne :\n{session.campaign_prompt}"
            if session.campaign_prompt else ""
        )
        return _SYSTEM_PROMPT.format(
            agent_name=settings.AI_AGENT_NAME,
            company_name=settings.AI_COMPANY_NAME,
            language=settings.AI_LANGUAGE,
            ivr_context=ivr_context,
            campaign_context=campaign_ctx,
        )

    # ------------------------------------------------------------------
    # Gestion des sessions
    # ------------------------------------------------------------------
    def create_session(self, call_id: str, ivr_choice: Optional[str] = None,
                       campaign_prompt: Optional[str] = None) -> ConversationSession:
        session = ConversationSession(call_id, ivr_choice, campaign_prompt)
        self._sessions[call_id] = session
        return session

    def get_session(self, call_id: str) -> Optional[ConversationSession]:
        return self._sessions.get(call_id)

    def end_session(self, call_id: str) -> Optional[ConversationSession]:
        return self._sessions.pop(call_id, None)

    # ------------------------------------------------------------------
    # Chat principal
    # ------------------------------------------------------------------
    async def chat(
        self,
        call_id: str,
        user_message: str,
        ivr_choice: Optional[str] = None,
        campaign_prompt: Optional[str] = None,
    ) -> dict[str, Any]:
        """
        Envoie un message à GPT et retourne la réponse propre + données lead.
        Crée la session si elle n'existe pas.
        """
        if not self._client:
            return {
                "text":      f"Bonjour, je suis {settings.AI_AGENT_NAME}. Le service IA n'est pas encore configuré.",
                "lead_data": None,
                "error":     "OpenAI non configuré",
            }

        session = self.get_session(call_id) or self.create_session(
            call_id, ivr_choice, campaign_prompt
        )
        session.add_user_message(user_message)

        system_prompt = self._build_system_prompt(session)
        messages_for_api = [{"role": "system", "content": system_prompt}] + session.messages

        try:
            response = await self._client.chat.completions.create(
                model=settings.OPENAI_MODEL,
                messages=messages_for_api,
                max_tokens=settings.OPENAI_MAX_TOKENS,
                temperature=settings.AI_TEMPERATURE,
            )
            raw_text = response.choices[0].message.content or ""

            # Extraction des données lead
            lead_data = self._extract_lead_data(raw_text)
            clean_text = self._strip_lead_block(raw_text).strip()

            # Mise à jour de la session
            session.add_assistant_message(raw_text)
            if lead_data:
                # Fusion des données lead (les nouvelles prioritaires)
                if session.lead_data:
                    session.lead_data.update({k: v for k, v in lead_data.items() if v is not None})
                else:
                    session.lead_data = lead_data

            return {
                "text":      clean_text,
                "lead_data": session.lead_data,
                "error":     None,
            }

        except Exception as e:
            logger.exception(f"AI chat error for call {call_id}")
            return {
                "text":      "Je suis désolé(e), je rencontre une difficulté technique momentanée.",
                "lead_data": session.lead_data,
                "error":     str(e),
            }

    # ------------------------------------------------------------------
    # Text-to-Speech
    # ------------------------------------------------------------------
    async def text_to_speech(self, text: str) -> Optional[bytes]:
        """Convertit un texte en audio MP3 via OpenAI TTS"""
        if not self._client:
            return None
        try:
            response = await self._client.audio.speech.create(
                model=settings.OPENAI_TTS_MODEL,
                voice=settings.OPENAI_TTS_VOICE,
                input=text,
            )
            return response.content
        except Exception as e:
            logger.error(f"TTS error: {e}")
            return None

    # ------------------------------------------------------------------
    # Speech-to-Text
    # ------------------------------------------------------------------
    async def speech_to_text(self, audio_bytes: bytes, filename: str = "audio.wav") -> Optional[str]:
        """Transcrit un audio en texte via Whisper"""
        if not self._client:
            return None
        try:
            buf = BytesIO(audio_bytes)
            buf.name = filename
            transcript = await self._client.audio.transcriptions.create(
                model=settings.OPENAI_STT_MODEL,
                file=buf,
                language=settings.AI_LANGUAGE,
            )
            return transcript.text
        except Exception as e:
            logger.error(f"STT error: {e}")
            return None

    # ------------------------------------------------------------------
    # Résumé post-appel
    # ------------------------------------------------------------------
    async def summarize_call(self, transcript: str) -> str:
        """Génère un résumé structuré d'un appel terminé"""
        if not self._client:
            return "Résumé non disponible (OpenAI non configuré)"
        try:
            response = await self._client.chat.completions.create(
                model=settings.OPENAI_MODEL,
                messages=[
                    {
                        "role": "system",
                        "content": (
                            "Tu résumes des appels téléphoniques de centre d'appels. "
                            "Sois concis(e), structuré(e), en français. "
                            "Format : 3-5 points clés avec émojis."
                        ),
                    },
                    {
                        "role": "user",
                        "content": f"Résume cet appel :\n\n{transcript}",
                    },
                ],
                max_tokens=300,
                temperature=0.3,
            )
            return response.choices[0].message.content or "Résumé vide"
        except Exception as e:
            logger.error(f"Summarize error: {e}")
            return f"Erreur de résumé : {e}"

    # ------------------------------------------------------------------
    # Utilitaires privés
    # ------------------------------------------------------------------
    @staticmethod
    def _extract_lead_data(text: str) -> Optional[dict[str, Any]]:
        """Extrait le bloc JSON <LEAD_DATA>...</LEAD_DATA>"""
        match = re.search(r"<LEAD_DATA>\s*(.*?)\s*</LEAD_DATA>", text, re.DOTALL)
        if not match:
            return None
        try:
            return json.loads(match.group(1))
        except json.JSONDecodeError as e:
            logger.warning(f"Lead data JSON parse error: {e}")
            return None

    @staticmethod
    def _strip_lead_block(text: str) -> str:
        """Supprime le bloc <LEAD_DATA> du texte affiché"""
        return re.sub(r"\s*<LEAD_DATA>.*?</LEAD_DATA>\s*", "", text, flags=re.DOTALL)


# Singleton
ai_agent = AIAgentService()
