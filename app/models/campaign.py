from __future__ import annotations
import enum
from datetime import datetime
from sqlalchemy import Column, Integer, String, DateTime, Text, Boolean, Float
from .database import Base


class CampaignType(str, enum.Enum):
    AI_AGENT = "ai_agent"
    IVR      = "ivr"


class CampaignStatus(str, enum.Enum):
    DRAFT     = "draft"
    ACTIVE    = "active"
    PAUSED    = "paused"
    COMPLETED = "completed"


class Campaign(Base):
    __tablename__ = "campaigns"

    id              = Column(Integer, primary_key=True, index=True)
    name            = Column(String(200), nullable=False)
    description     = Column(Text, nullable=True)
    campaign_type   = Column(String(20), default=CampaignType.AI_AGENT)
    status          = Column(String(20), default=CampaignStatus.DRAFT)

    # Offre / service
    offer_type      = Column(String(50), nullable=True)  # assurance_auto, sante, mutuelle...
    offer_script    = Column(Text, nullable=True)         # Script vocal

    # Stats
    total_contacts  = Column(Integer, default=0)
    calls_made      = Column(Integer, default=0)
    calls_answered  = Column(Integer, default=0)
    leads_generated = Column(Integer, default=0)
    contacts_json   = Column(Text, default="[]")  # liste de numéros

    # Config délai
    delay_between_calls = Column(Integer, default=5)  # secondes

    created_at  = Column(DateTime, default=datetime.utcnow)
    started_at  = Column(DateTime, nullable=True)
    completed_at = Column(DateTime, nullable=True)
