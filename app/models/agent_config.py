from __future__ import annotations
from datetime import datetime
from sqlalchemy import Column, Integer, String, DateTime, Text, Boolean, Float
from .database import Base


class AgentConfig(Base):
    """Configuration de l'agent IA vocal."""
    __tablename__ = "agent_configs"

    id           = Column(Integer, primary_key=True, index=True)
    name         = Column(String(100), default="Sophie")
    company_name = Column(String(200), default="AssurancePro")
    language     = Column(String(10), default="fr")
    voice        = Column(String(50), default="nova")      # nova, alloy, echo, fable, onyx, shimmer
    temperature  = Column(Float, default=0.7)
    system_prompt = Column(Text, nullable=True)
    greeting_text = Column(Text, nullable=True)
    is_default   = Column(Boolean, default=True)
    created_at   = Column(DateTime, default=datetime.utcnow)
    updated_at   = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
