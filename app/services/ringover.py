"""
Client API Ringover — appels entrants/sortants, TTS, transfert
"""
from __future__ import annotations
import httpx
from datetime import datetime
from app.config import settings


class RingoverClient:
    def __init__(self):
        self._base = settings.RINGOVER_API_URL
        self._headers = {
            "Authorization": settings.RINGOVER_API_KEY,
            "Content-Type": "application/json",
        }

    async def _request(self, method: str, path: str, body: dict | None = None) -> dict | None:
        if not settings.RINGOVER_API_KEY:
            return {"simulated": True, "call_id": f"SIM_{int(datetime.utcnow().timestamp())}"}
        try:
            async with httpx.AsyncClient(timeout=15) as c:
                r = await getattr(c, method.lower())(
                    f"{self._base}{path}", headers=self._headers, json=body
                )
                r.raise_for_status()
                return r.json()
        except Exception as e:
            import logging
            logging.getLogger("ringover").error(f"API error {path}: {e}")
            return None

    async def test_connection(self) -> dict:
        r = await self._request("GET", "/account")
        return {
            "connected": bool(r and not r.get("error") and not r.get("simulated")),
            "simulated": bool((r or {}).get("simulated")),
        }

    async def make_call(self, to: str, from_number: str | None = None) -> dict | None:
        frm = from_number or settings.RINGOVER_PHONE_NUMBER
        return await self._request("POST", "/calls", {"from_number": frm, "to_number": to})

    async def hangup(self, call_id: str) -> None:
        await self._request("POST", f"/calls/{call_id}/hangup", {})

    async def transfer(self, call_id: str, to: str) -> dict | None:
        return await self._request("POST", f"/calls/{call_id}/transfer", {"number": to})

    async def tts(self, call_id: str, text: str, lang: str = "fr-FR") -> None:
        await self._request("POST", f"/calls/{call_id}/tts", {"text": text, "language": lang})

    async def get_numbers(self) -> list:
        r = await self._request("GET", "/numbers")
        return (r or {}).get("numbers") or []

    async def get_users(self) -> list:
        r = await self._request("GET", "/users")
        return (r or {}).get("users") or []


ringover = RingoverClient()
