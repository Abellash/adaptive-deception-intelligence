from datetime import datetime, timezone
from uuid import uuid4

from sqlalchemy import Boolean, DateTime, Float, ForeignKey, Integer, JSON, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from .database import Base


def now() -> datetime:
    return datetime.now(timezone.utc)


class Asset(Base):
    __tablename__ = "assets"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    name: Mapped[str] = mapped_column(String(255))
    type: Mapped[str] = mapped_column(String(80))
    environment: Mapped[str] = mapped_column(String(80), default="NovaPay production")
    is_decoy: Mapped[bool] = mapped_column(Boolean, default=True)
    metadata_json: Mapped[dict] = mapped_column("metadata", JSON, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)


class Honeytoken(Base):
    __tablename__ = "honeytokens"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    token_type: Mapped[str] = mapped_column(String(80))
    asset_id: Mapped[str] = mapped_column(ForeignKey("assets.id"))
    reference: Mapped[str] = mapped_column(String(255), unique=True)
    trigger_type: Mapped[str] = mapped_column(String(80), default="http_callback")
    risk_weight: Mapped[int] = mapped_column(Integer, default=20)
    active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)


class AttackerSession(Base):
    __tablename__ = "attacker_sessions"
    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    source_ip: Mapped[str] = mapped_column(String(64))
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)
    last_seen: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)
    risk_score: Mapped[int] = mapped_column(Integer, default=0)
    status: Mapped[str] = mapped_column(String(40), default="OBSERVING")
    current_intent: Mapped[str] = mapped_column(String(80), default="Uncertain")


class SecurityEvent(Base):
    __tablename__ = "security_events"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    session_id: Mapped[str] = mapped_column(ForeignKey("attacker_sessions.id"))
    asset_id: Mapped[str | None] = mapped_column(ForeignKey("assets.id"), nullable=True)
    event_type: Mapped[str] = mapped_column(String(80))
    timestamp: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)
    details: Mapped[dict] = mapped_column(JSON, default=dict)
    risk_delta: Mapped[int] = mapped_column(Integer, default=0)
    mitre_tactic: Mapped[str] = mapped_column(String(80), default="")
    mitre_technique: Mapped[str] = mapped_column(String(80), default="")


class Incident(Base):
    __tablename__ = "incidents"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    session_id: Mapped[str] = mapped_column(ForeignKey("attacker_sessions.id"))
    severity: Mapped[str] = mapped_column(String(20))
    status: Mapped[str] = mapped_column(String(40), default="OPEN")
    summary: Mapped[str] = mapped_column(Text)
    containment_action: Mapped[str | None] = mapped_column(String(120), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)


class BehaviorMemory(Base):
    """Small, explainable policy memory; this is not a trained ML model."""
    __tablename__ = "behavior_memory"
    action: Mapped[str] = mapped_column(String(80), primary_key=True)
    observations: Mapped[int] = mapped_column(Integer, default=0)
    last_seen: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)
