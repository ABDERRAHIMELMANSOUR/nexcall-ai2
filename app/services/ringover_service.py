"""
NexCall AI — Service Ringover
Client HTTP async pour l'API Ringover v2
Documentation : https://developer.ringover.com/
"""
import logging
from typing import Any, Optional
import httpx
from app.config import settings

logger = logging.getLogger(__name__)

RINGOVER_TIMEOUT = httpx.Timeout(10.0, connect=5.0)


class RingoverService:
    """
    Client pour l'API REST Ringover.
    Toutes les méthodes retournent un dict avec au minimum :
      - success (bool)
      - data    (dict | list | None)
      - error   (str | None)
    """

    def __init__(self):
        self._api_key  = settings.RINGOVER_API_KEY
        self._base_url = settings.RINGOVER_API_URL.rstrip("/")

    def _headers(self) -> dict[str, str]:
        return {
            "Authorization": self._api_key or "",
            "Content-Type":  "application/json",
            "Accept":        "application/json",
        }

    def _is_ready(self) -> bool:
        return bool(self._api_key)

    # ------------------------------------------------------------------
    # Test de connexion
    # ------------------------------------------------------------------
    async def test_connection(self) -> dict[str, Any]:
        if not self._is_ready():
            return {"success": False, "connected": False, "error": "Clé API Ringover manquante"}
        async with httpx.AsyncClient(timeout=RINGOVER_TIMEOUT) as client:
            try:
                r = await client.get(f"{self._base_url}/users", headers=self._headers())
                if r.status_code == 200:
                    return {"success": True, "connected": True, "data": r.json()}
                return {
                    "success": False, "connected": False,
                    "error": f"HTTP {r.status_code}: {r.text[:200]}"
                }
            except httpx.ConnectError:
                return {"success": False, "connected": False, "error": "Impossible de joindre l'API Ringover"}
            except Exception as e:
                logger.exception("Ringover test_connection error")
                return {"success": False, "connected": False, "error": str(e)}

    # ------------------------------------------------------------------
    # Appels
    # ------------------------------------------------------------------
    async def get_calls(self, limit: int = 50, offset: int = 0) -> dict[str, Any]:
        if not self._is_ready():
            return {"success": False, "data": [], "error": "API non configurée"}
        async with httpx.AsyncClient(timeout=RINGOVER_TIMEOUT) as client:
            try:
                r = await client.get(
                    f"{self._base_url}/calls",
                    headers=self._headers(),
                    params={"limit_count": limit, "start_offset": offset},
                )
                r.raise_for_status()
                return {"success": True, "data": r.json()}
            except Exception as e:
                logger.error(f"Ringover get_calls: {e}")
                return {"success": False, "data": [], "error": str(e)}

    async def transfer_call(self, call_id: str, to_number: str) -> dict[str, Any]:
        if not self._is_ready():
            return {"success": False, "error": "API non configurée"}
        async with httpx.AsyncClient(timeout=RINGOVER_TIMEOUT) as client:
            try:
                r = await client.post(
                    f"{self._base_url}/calls/{call_id}/transfer",
                    headers=self._headers(),
                    json={"to": to_number},
                )
                r.raise_for_status()
                return {"success": True, "data": r.json()}
            except Exception as e:
                logger.error(f"Ringover transfer_call: {e}")
                return {"success": False, "error": str(e)}

    async def hangup_call(self, call_id: str) -> dict[str, Any]:
        if not self._is_ready():
            return {"success": False, "error": "API non configurée"}
        async with httpx.AsyncClient(timeout=RINGOVER_TIMEOUT) as client:
            try:
                r = await client.delete(
                    f"{self._base_url}/calls/{call_id}",
                    headers=self._headers(),
                )
                r.raise_for_status()
                return {"success": True}
            except Exception as e:
                logger.error(f"Ringover hangup: {e}")
                return {"success": False, "error": str(e)}

    # ------------------------------------------------------------------
    # Numéros & Utilisateurs
    # ------------------------------------------------------------------
    async def get_numbers(self) -> dict[str, Any]:
        if not self._is_ready():
            return {"success": False, "data": [], "error": "API non configurée"}
        async with httpx.AsyncClient(timeout=RINGOVER_TIMEOUT) as client:
            try:
                r = await client.get(f"{self._base_url}/numbers", headers=self._headers())
                r.raise_for_status()
                return {"success": True, "data": r.json()}
            except Exception as e:
                return {"success": False, "data": [], "error": str(e)}

    async def get_users(self) -> dict[str, Any]:
        if not self._is_ready():
            return {"success": False, "data": [], "error": "API non configurée"}
        async with httpx.AsyncClient(timeout=RINGOVER_TIMEOUT) as client:
            try:
                r = await client.get(f"{self._base_url}/users", headers=self._headers())
                r.raise_for_status()
                return {"success": True, "data": r.json()}
            except Exception as e:
                return {"success": False, "data": [], "error": str(e)}

    # ------------------------------------------------------------------
    # Validation du webhook secret
    # ------------------------------------------------------------------
    def validate_webhook_signature(self, payload: bytes, signature: str) -> bool:
        """Valide la signature HMAC d'un webhook Ringover"""
        import hmac, hashlib
        secret = settings.RINGOVER_WEBHOOK_SECRET
        if not secret:
            return True  # Pas de secret configuré → accepter tout en dev
        expected = hmac.new(
            secret.encode(), payload, hashlib.sha256
        ).hexdigest()
        return hmac.compare_digest(expected, signature)


# Singleton
ringover_service = RingoverService()
