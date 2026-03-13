"""
Modèle Campaign — Représente une campagne d'appels
"""
from datetime import datetime
from sqlalchemy import Column, Integer, String, DateTime, Text, Boolean, Float
from sqlalchemy.orm import relationship
from app.database import Base
import enum


class CampaignStatus(str, enum.Enum):
    DRAFT     = "draft"
    ACTIVE    = "active"
    PAUSED    = "paused"
    COMPLETED = "completed"
    ARCHIVED  = "archived"


class CampaignType(str, enum.Enum):
    INBOUND  = "inbound"
    OUTBOUND = "outbound"


class Campaign(Base):
    __tablename__ = "campaigns"

    id              = Column(Integer, primary_key=True, index=True)
    name            = Column(String(128), nullable=False)
    description     = Column(Text, nullable=True)

    # Type & statut
    type            = Column(String(16), default=CampaignType.INBOUND.value, nullable=False)
    status          = Column(String(32), default=CampaignStatus.DRAFT.value, nullable=False, index=True)
    is_active       = Column(Boolean, default=False, nullable=False)

    # Ciblage
    target_interest = Column(String(64), nullable=True)
    target_region   = Column(String(64), nullable=True)

    # Script IA personnalisé pour cette campagne
    ai_system_prompt = Column(Text, nullable=True)
    ivr_message      = Column(Text, nullable=True)

    # Métriques (calculées automatiquement)
    total_calls      = Column(Integer, default=0, nullable=False)
    answered_calls   = Column(Integer, default=0, nullable=False)
    missed_calls     = Column(Integer, default=0, nullable=False)
    transferred_calls = Column(Integer, default=0, nullable=False)
    leads_generated  = Column(Integer, default=0, nullable=False)
    conversion_rate  = Column(Float, default=0.0, nullable=False)

    # Timestamps
    started_at      = Column(DateTime, nullable=True)
    ended_at        = Column(DateTime, nullable=True)
    created_at      = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at      = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    # Relationships
    calls           = relationship("Call", back_populates="campaign")

    def __repr__(self) -> str:
        return f"<Campaign #{self.id} '{self.name}' [{self.status}]>"

    @property
    def answer_rate(self) -> float:
        if self.total_calls == 0:
            return 0.0
        return round(self.answered_calls / self.total_calls * 100, 1)

    def to_dict(self) -> dict:
        return {
            "id":               self.id,
            "name":             self.name,
            "description":      self.description,
            "type":             self.type,
            "status":           self.status,
            "is_active":        self.is_active,
            "target_interest":  self.target_interest,
            "target_region":    self.target_region,
            "ai_system_prompt": self.ai_system_prompt,
            "ivr_message":      self.ivr_message,
            "total_calls":      self.total_calls,
            "answered_calls":   self.answered_calls,
            "missed_calls":     self.missed_calls,
            "transferred_calls": self.transferred_calls,
            "leads_generated":  self.leads_generated,
            "conversion_rate":  self.conversion_rate,
            "answer_rate":      self.answer_rate,
            "started_at":       self.started_at.isoformat() if self.started_at else None,
            "ended_at":         self.ended_at.isoformat() if self.ended_at else None,
            "created_at":       self.created_at.isoformat() if self.created_at else None,
        }
