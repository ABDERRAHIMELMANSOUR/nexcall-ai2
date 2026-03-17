"""
Moteur IVR — Gestion des menus vocaux DTMF
"""
from __future__ import annotations
import logging
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.models.ivr import IVRMenu, IVROption
from app.services.ringover import ringover

log = logging.getLogger("ivr")


class IVREngine:
    async def get_menu(self, menu_id: int, db: AsyncSession) -> IVRMenu | None:
        r = await db.execute(select(IVRMenu).where(IVRMenu.id == menu_id))
        return r.scalar_one_or_none()

    async def get_options(self, menu_id: int, db: AsyncSession) -> list[IVROption]:
        r = await db.execute(
            select(IVROption)
            .where(IVROption.menu_id == menu_id, IVROption.is_active == True)
            .order_by(IVROption.position)
        )
        return list(r.scalars().all())

    def build_announcement(self, menu: IVRMenu, options: list[IVROption]) -> str:
        """Construit le texte d'annonce du menu IVR."""
        text = menu.welcome_text + " "
        for opt in options:
            text += f"Tapez {opt.key_press} pour {opt.label}. "
        return text.strip()

    async def process_keypress(
        self,
        call_id: str,
        key: str,
        menu_id: int,
        db: AsyncSession,
    ) -> dict:
        """Traite la touche pressée et retourne l'action à effectuer."""
        options = await self.get_options(menu_id, db)
        opt = next((o for o in options if o.key_press == key), None)

        if not opt:
            return {"action": "retry", "message": f"Touche non reconnue. Veuillez réessayer."}

        log.info(f"[{call_id}] IVR key={key} action={opt.action} label={opt.label}")

        if opt.action == "info":
            return {"action": "info", "message": opt.action_value or opt.label}
        elif opt.action == "transfer":
            return {"action": "transfer", "number": opt.action_value, "label": opt.label}
        elif opt.action == "ai_agent":
            return {"action": "ai_agent", "offer_type": opt.action_value}
        elif opt.action == "hangup":
            return {"action": "hangup", "message": opt.action_value or "Au revoir, bonne journée !"}
        elif opt.action == "submenu":
            return {"action": "submenu", "menu_id": int(opt.action_value or 0)}
        else:
            return {"action": "info", "message": opt.label}

    async def create_default_menu(self, campaign_id: int, db: AsyncSession) -> IVRMenu:
        """Crée un menu IVR par défaut pour une campagne."""
        menu = IVRMenu(
            campaign_id=campaign_id,
            name="Menu Principal",
            welcome_text="Bienvenue chez AssurancePro. Pour vous orienter, veuillez choisir parmi les options suivantes.",
        )
        db.add(menu)
        await db.flush()

        default_options = [
            IVROption(menu_id=menu.id, key_press="1", label="Assurance Auto",    action="ai_agent", action_value="assurance_auto",   position=0),
            IVROption(menu_id=menu.id, key_press="2", label="Assurance Santé",   action="ai_agent", action_value="assurance_sante",  position=1),
            IVROption(menu_id=menu.id, key_press="3", label="Immobilier",        action="ai_agent", action_value="immobilier",       position=2),
            IVROption(menu_id=menu.id, key_press="4", label="parler à un conseiller", action="transfer", action_value="",           position=3),
        ]
        for opt in default_options:
            db.add(opt)

        await db.commit()
        return menu


ivr_engine = IVREngine()
