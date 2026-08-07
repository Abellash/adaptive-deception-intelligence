from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field


class TelemetryEventIn(BaseModel):
    session_id: str = Field(min_length=1, max_length=64)
    source: str = "canary"
    source_ip: str = "127.0.0.1"
    asset_id: str | None = None
    asset_type: str = "file"
    action: str
    details: dict[str, Any] = Field(default_factory=dict)
    timestamp: datetime | None = None


class EventOut(BaseModel):
    event_id: str
    timestamp: datetime
    session_id: str
    source: str
    source_ip: str
    asset_id: str | None
    asset_type: str
    action: str
    details: dict[str, Any]
    risk_delta: int
    risk_score: int
    severity: str
    intent: str
    intent_confidence: float
    intent_probabilities: dict[str, float] = Field(default_factory=dict)
    behavior: str = ""
    threat_percent: int = 0
    next_paths: list[dict[str, str | float]] = Field(default_factory=list)
    session_status: str = "OBSERVING"
    containment_action: str | None = None
    mitre_tactic: str
    mitre_technique: str
    orchestrator_action: str
    policy_allowed: bool


class DemoTrigger(BaseModel):
    session_id: str = "demo-attacker-01"
    source_ip: str = "172.20.0.10"


class HoneytokenCreate(BaseModel):
    name: str = Field(min_length=3, max_length=120)
    token_type: str
    environment: str = "NovaPay lab"
    risk_weight: int = Field(default=20, ge=1, le=100)
