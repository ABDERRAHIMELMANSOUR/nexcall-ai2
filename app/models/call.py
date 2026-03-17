from __future__ import annotations
import enum
from datetime import datetime
from sqlalchemy import Column, Integer, String, DateTime, Text, Boolean, Float, Enum as SAEnum
from .database import Base


class CallStatus(str, enum.Enum):
    RINGING   = "ringing"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    TRANSFERRED = "transferred"
    FAILED    = "failed"
    NO_ANSWER = "no_answer"


class Call(Base):
    __tablename__ = "calls"

    id               = Column(Integer, primary_key=True, index=True)
    call_id          = Column(String(120), unique=True, index=True, nullable=True)
    campaign_id      = Column(Integer, nullable=True, index=True)
    phone_number     = Column(String(30), index=True)
    direction        = Column(String(10), default="inbound")   # inbound | outbound
    call_type        = Column(String(20), default="ai_agent")  # ai_agent | ivr
    status           = Column(String(20), default=CallStatus.RINGING)
    intent           = Column(String(50), nullable=True)
    duration_seconds = Column(Integer, default=0)
    transcript       = Column(Text, nullable=True)
    ai_summary       = Column(Text, nullable=True)
    recording_url    = Column(String(500), nullable=True)
    transferred      = Column(Boolean, default=False)
    transferred_to   = Column(String(30), nullable=True)
    ivr_path         = Column(String(200), nullable=True)  # trace du chemin IVR
    started_at       = Column(DateTime, default=datetime.utcnow)
    ended_at         = Column(DateTime, nullable=True)
    created_at       = Column(DateTime, default=datetime.utcnow)
