from __future__ import annotations
from datetime import datetime
from sqlalchemy import Column, Integer, String, DateTime, Text, Boolean, ForeignKey
from .database import Base


class IVRMenu(Base):
    """Arbre IVR complet associé à une campagne."""
    __tablename__ = "ivr_menus"

    id           = Column(Integer, primary_key=True, index=True)
    campaign_id  = Column(Integer, ForeignKey("campaigns.id", ondelete="CASCADE"), index=True)
    name         = Column(String(200), nullable=False)
    welcome_text = Column(Text, nullable=False,
                          default="Bienvenue. Veuillez choisir parmi les options suivantes.")
    timeout_seconds = Column(Integer, default=10)
    max_retries  = Column(Integer, default=3)
    created_at   = Column(DateTime, default=datetime.utcnow)


class IVROption(Base):
    """Option d'un menu IVR (touche → action)."""
    __tablename__ = "ivr_options"

    id           = Column(Integer, primary_key=True, index=True)
    menu_id      = Column(Integer, ForeignKey("ivr_menus.id", ondelete="CASCADE"), index=True)
    key_press    = Column(String(5), nullable=False)   # "1", "2", "#", "*"
    label        = Column(String(200), nullable=False)  # "Assurance Auto"
    action       = Column(String(30), nullable=False)   # info | transfer | submenu | ai_agent | hangup
    action_value = Column(String(500), nullable=True)   # n° de transfert, texte info, etc.
    position     = Column(Integer, default=0)
    is_active    = Column(Boolean, default=True)
