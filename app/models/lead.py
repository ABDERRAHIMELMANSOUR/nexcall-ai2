from __future__ import annotations
from datetime import datetime
from sqlalchemy import Column, Integer, String, DateTime, Text, Boolean, Float
from .database import Base


class Lead(Base):
    __tablename__ = "leads"

    id                  = Column(Integer, primary_key=True, index=True)
    call_id             = Column(String(120), index=True, nullable=True)
    campaign_id         = Column(Integer, nullable=True, index=True)
    phone_number        = Column(String(30), index=True)
    name                = Column(String(100), nullable=True)
    email               = Column(String(200), nullable=True)
    service_interest    = Column(String(200), nullable=True)  # assurance auto, santé...
    intent              = Column(String(50), nullable=True)
    qualification_score = Column(Float, default=0.0)
    is_hot              = Column(Boolean, default=False)
    contacted           = Column(Boolean, default=False)
    notes               = Column(Text, nullable=True)
    ivr_responses       = Column(Text, nullable=True)  # JSON des réponses IVR
    created_at          = Column(DateTime, default=datetime.utcnow)
    contacted_at        = Column(DateTime, nullable=True)
