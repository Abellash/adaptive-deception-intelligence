from contextlib import asynccontextmanager
from datetime import datetime, timezone
import os

from fastapi import Depends, FastAPI, HTTPException, WebSocket, WebSocketDisconnect
from fastapi.responses import HTMLResponse
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import select
from sqlalchemy.orm import Session

from .database import Base, engine, get_db
from .models import Asset, AttackerSession, BehaviorMemory, Honeytoken, Incident, SecurityEvent
from .schemas import DemoTrigger, EventOut, HoneytokenCreate, TelemetryEventIn
from .services.honeytokens import TOKEN_REFERENCE, write_first_honeytoken
from .services.intent import behavior_label, infer_intent, infer_intent_probabilities, next_path_probabilities
from .services.mapping import map_event
from .services.orchestrator import decide
from .services.risk import risk_delta, severity
from .websocket import ConnectionManager

manager = ConnectionManager()


def seed_first_honeytoken(db: Session) -> Asset:
    asset = db.scalar(select(Asset).where(Asset.name == ".env.production"))
    if asset:
        return asset
    asset = Asset(name=".env.production", type="config_file", environment="NovaPay / payment-service")
    db.add(asset)
    db.flush()
    db.add(Honeytoken(token_type="fake_aws_credential", asset_id=asset.id, reference=TOKEN_REFERENCE, risk_weight=25))
    db.commit()
    write_first_honeytoken()
    return asset


@asynccontextmanager
async def lifespan(app: FastAPI):
    Base.metadata.create_all(bind=engine)
    with next(get_db()) as db:
        seed_first_honeytoken(db)
    yield


app = FastAPI(title="PikaTrap", version="0.1.0", lifespan=lifespan)
cors_origins = [origin.strip() for origin in os.getenv("BACKEND_CORS_ORIGINS", "http://localhost:5173,http://localhost:8081").split(",") if origin.strip()]
app.add_middleware(CORSMiddleware, allow_origins=cors_origins, allow_credentials=True, allow_methods=["*"], allow_headers=["*"])


@app.get("/health")
def health():
    return {"status": "ok", "service": "pikatrap-api"}


@app.post("/api/v1/honeytokens", status_code=201)
def create_honeytoken(payload: HoneytokenCreate, db: Session = Depends(get_db)):
    """Create a safe, metadata-only lab token; no real credential is generated."""
    from uuid import uuid4
    asset = Asset(name=payload.name, type=payload.token_type, environment=payload.environment, metadata_json={"generated_by": "PikaTrap Honeytoken Factory", "safe": True})
    db.add(asset)
    db.flush()
    token = Honeytoken(token_type=payload.token_type, asset_id=asset.id, reference=f"ptk-{uuid4().hex[:12]}", risk_weight=payload.risk_weight)
    db.add(token)
    db.commit()
    return {"asset_id": asset.id, "token_id": token.id, "name": asset.name, "token_type": token.token_type, "reference": token.reference, "message": "Safe honeytoken created in the NovaPay lab inventory."}


@app.post("/api/v1/telemetry", response_model=EventOut, status_code=201)
async def ingest_telemetry(payload: TelemetryEventIn, db: Session = Depends(get_db)):
    asset = db.get(Asset, payload.asset_id) if payload.asset_id else db.scalar(select(Asset).where(Asset.name == ".env.production"))
    session = db.get(AttackerSession, payload.session_id)
    if not session:
        session = AttackerSession(id=payload.session_id, source_ip=payload.source_ip)
        db.add(session)
        db.flush()
    if session.status == "CONTAINED":
        raise HTTPException(status_code=423, detail="Sandbox session is quarantined; fake credentials are revoked for this simulation.")
    delta = risk_delta(payload.action)
    session.risk_score = min(100, session.risk_score + delta)
    session.last_seen = datetime.now(timezone.utc)
    actions = list(db.scalars(select(SecurityEvent.event_type).where(SecurityEvent.session_id == session.id).order_by(SecurityEvent.timestamp))) + [payload.action]
    intent, confidence, evidence = infer_intent(actions)
    probabilities = infer_intent_probabilities(actions)
    behavior = behavior_label(actions)
    next_paths = next_path_probabilities(actions)
    session.current_intent = intent
    tactic, technique = map_event(payload.action)
    memory = db.get(BehaviorMemory, payload.action)
    prior_observations = memory.observations if memory and memory.observations is not None else 0
    if not memory:
        memory = BehaviorMemory(action=payload.action, observations=0)
        db.add(memory)
    memory.observations = (memory.observations or 0) + 1
    memory.last_seen = datetime.now(timezone.utc)
    action, reason, policy_allowed = decide(session.risk_score, intent, confidence)
    if prior_observations:
        reason += f" Adaptive memory has seen this behavior {prior_observations} time(s) in prior lab interactions."
    containment_action = None
    if action == "RECOMMEND_CONTAINMENT":
        containment_action = "Sandbox session isolated; fake credentials revoked for this attacker session."
        session.status = "CONTAINED"
        db.add(Incident(session_id=session.id, severity=severity(session.risk_score), status="CONTAINED", summary=f"Policy threshold met. {reason}", containment_action=containment_action))
        reason += " Policy executor completed local sandbox containment."
    event = SecurityEvent(session_id=session.id, asset_id=asset.id if asset else None, event_type=payload.action, timestamp=payload.timestamp or datetime.now(timezone.utc), details={**payload.details, "source": payload.source, "evidence": evidence, "decision_reason": reason, "behavior": behavior, "intent_probabilities": probabilities, "next_paths": next_paths, "threat_percent": session.risk_score, "session_status": session.status, "containment_action": containment_action, "fake_credential_revoked": bool(containment_action)}, risk_delta=delta, mitre_tactic=tactic, mitre_technique=technique)
    db.add(event)
    db.commit()
    db.refresh(event)
    output = EventOut(event_id=event.id, timestamp=event.timestamp, session_id=session.id, source=payload.source, source_ip=session.source_ip, asset_id=event.asset_id, asset_type=payload.asset_type, action=payload.action, details=event.details, risk_delta=delta, risk_score=session.risk_score, severity=severity(session.risk_score), intent=intent, intent_confidence=confidence, intent_probabilities=probabilities, behavior=behavior, threat_percent=session.risk_score, next_paths=next_paths, session_status=session.status, containment_action=containment_action, mitre_tactic=tactic, mitre_technique=technique, orchestrator_action=action, policy_allowed=policy_allowed)
    await manager.broadcast({"type": "telemetry", "data": output.model_dump(mode="json")})
    return output


@app.post("/api/v1/demo/trigger", response_model=EventOut)
async def trigger_first_honeytoken(payload: DemoTrigger, db: Session = Depends(get_db)):
    asset = seed_first_honeytoken(db)
    event = TelemetryEventIn(session_id=payload.session_id, source_ip=payload.source_ip, source="file_canary", asset_id=asset.id, asset_type="config_file", action="credential_read", details={"path": "/opt/payment-service/.env.production", "canary_id": TOKEN_REFERENCE, "message": "Safe demo trigger: fake credential file accessed."})
    return await ingest_telemetry(event, db)


@app.get("/api/v1/events", response_model=list[EventOut])
def list_events(db: Session = Depends(get_db)):
    events = list(db.scalars(select(SecurityEvent).order_by(SecurityEvent.timestamp.desc()).limit(50)))
    result = []
    for event in events:
        session = db.get(AttackerSession, event.session_id)
        actions = list(db.scalars(select(SecurityEvent.event_type).where(SecurityEvent.session_id == event.session_id).order_by(SecurityEvent.timestamp)))
        intent, confidence, _ = infer_intent(actions)
        probabilities = event.details.get("intent_probabilities", infer_intent_probabilities(actions))
        behavior = event.details.get("behavior", behavior_label(actions))
        next_paths = event.details.get("next_paths", next_path_probabilities(actions))
        action, _, allowed = decide(session.risk_score, intent, confidence)
        result.append(EventOut(event_id=event.id, timestamp=event.timestamp, session_id=event.session_id, source=event.details.get("source", "canary"), source_ip=session.source_ip, asset_id=event.asset_id, asset_type="config_file", action=event.event_type, details=event.details, risk_delta=event.risk_delta, risk_score=event.details.get("threat_percent", session.risk_score), severity=severity(event.details.get("threat_percent", session.risk_score)), intent=intent, intent_confidence=confidence, intent_probabilities=probabilities, behavior=behavior, threat_percent=event.details.get("threat_percent", session.risk_score), next_paths=next_paths, session_status=event.details.get("session_status", session.status), containment_action=event.details.get("containment_action"), mitre_tactic=event.mitre_tactic, mitre_technique=event.mitre_technique, orchestrator_action=action, policy_allowed=allowed))
    return result


@app.get("/api/v1/incidents")
def list_incidents(db: Session = Depends(get_db)):
    incidents = list(db.scalars(select(Incident).order_by(Incident.created_at.desc()).limit(30)))
    return [{
        "id": incident.id,
        "session_id": incident.session_id,
        "severity": incident.severity,
        "status": incident.status,
        "summary": incident.summary,
        "containment_action": incident.containment_action,
        "created_at": incident.created_at,
    } for incident in incidents]


@app.get("/api/v1/sessions/{session_id}/containment")
def containment_status(session_id: str, db: Session = Depends(get_db)):
    session = db.get(AttackerSession, session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    incident = db.scalar(select(Incident).where(Incident.session_id == session_id).order_by(Incident.created_at.desc()))
    return {
        "session_id": session.id,
        "status": session.status,
        "contained": session.status == "CONTAINED",
        "containment_action": incident.containment_action if incident else None,
    }


@app.get("/api/v1/reports/{session_id}.html")
def download_incident_report(session_id: str, db: Session = Depends(get_db)):
    """Download a self-contained, defender-safe incident report after containment is recommended."""
    import html
    session = db.get(AttackerSession, session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    incident = db.scalar(select(Incident).where(Incident.session_id == session_id).order_by(Incident.created_at.desc()))
    if not incident:
        raise HTTPException(status_code=409, detail="A report is available after containment is recommended.")
    events = list(db.scalars(select(SecurityEvent).where(SecurityEvent.session_id == session_id).order_by(SecurityEvent.timestamp)))
    intent, confidence, _ = infer_intent([event.event_type for event in events])
    from zoneinfo import ZoneInfo
    india_time = ZoneInfo("Asia/Kolkata")
    rows = "".join(
        f"<tr><td>{html.escape(event.timestamp.astimezone(india_time).strftime('%d %b %Y, %I:%M:%S %p IST'))}</td><td>{html.escape(event.event_type.replace('_', ' ').title())}</td><td>{html.escape(str(event.details.get('path') or event.details.get('object') or 'Controlled lab interaction'))}</td><td>{html.escape(event.mitre_technique or '—')}</td><td>+{event.risk_delta}</td></tr>"
        for event in events
    )
    graph_parts: list[str] = []
    for index, event in enumerate(events):
        graph_parts.append(f"<div class='graph-node'><span>STEP {index + 1}</span><b>{html.escape(event.event_type.replace('_', ' ').title())}</b><small>{html.escape(str(event.details.get('behavior', event.mitre_tactic or 'Observed behavior')))}</small><em>Threat {event.details.get('threat_percent', 0)}%</em></div>")
        if index < len(events) - 1:
            graph_parts.append("<div class='graph-edge'>&rarr;</div>")
    attack_graph = "".join(graph_parts)
    def step_line(event: SecurityEvent) -> str:
        predicted = ", ".join(f"{item.get('path')} ({item.get('probability')}%)" for item in event.details.get("next_paths", [])) or "observe"
        return f"<li><b>{html.escape(event.event_type.replace('_', ' ').title())}</b> — threat {event.details.get('threat_percent', 0)}%; {html.escape(str(event.details.get('behavior', 'Observed behavior')))}. Likely next: {html.escape(predicted)}</li>"
    step_assessment = "".join(step_line(event) for event in events)
    document = f"""<!doctype html><html><head><meta charset='utf-8'><title>PikaTrap Incident Report</title><style>body{{font-family:Arial,sans-serif;color:#15241b;max-width:900px;margin:48px auto;padding:0 24px}}h1{{color:#165c35}}.tag{{color:#527563;font-size:12px;font-weight:bold;letter-spacing:1px}}.box{{background:#eef7f0;border-left:5px solid #298653;padding:18px;margin:22px 0}}table{{width:100%;border-collapse:collapse}}th,td{{text-align:left;padding:12px;border-bottom:1px solid #d8e4db;font-size:14px}}th{{background:#f3f7f4}}li{{margin:10px 0;line-height:1.5}}.graph{{display:flex;align-items:stretch;gap:8px;overflow-x:auto;padding:8px 0 18px}}.graph-node{{width:145px;min-height:130px;flex:0 0 145px;background:#10251b;color:#e1f3e5;border:1px solid #4b9664;padding:13px;border-radius:8px;display:flex;flex-direction:column;gap:8px}}.graph-node span,.graph-node small{{font-size:10px;color:#a8d9b4;line-height:1.35}}.graph-node em{{font-size:11px;color:#f5d65c;font-style:normal;margin-top:auto}}.graph-edge{{align-self:center;color:#287247;font-size:22px;flex:0 0 22px}}</style></head><body><p class='tag'>PIKATRAP / INCIDENT REPORT / DEFENDER-OWNED LAB</p><h1>NovaPay simulated attack report</h1><div class='box'><b>Session:</b> {html.escape(session.id)}<br><b>Source:</b> {html.escape(session.source_ip)}<br><b>Risk:</b> {session.risk_score}/100 ({html.escape(severity(session.risk_score))})<br><b>Inferred intent:</b> {html.escape(intent)} ({confidence:.0%})<br><b>Behavior assessment:</b> {html.escape(behavior_label([event.event_type for event in events]))}<br><b>Containment:</b> {html.escape(incident.containment_action or 'Recommended')}</div><h2>Completed Adaptive Deception Graph</h2><div class='graph'>{attack_graph}</div><h2>Per-step behavior and adaptive next-path estimates</h2><ol>{step_assessment}</ol><h2>Telemetry timeline (IST)</h2><table><thead><tr><th>Time</th><th>Observed action</th><th>Asset / location</th><th>MITRE ATT&amp;CK</th><th>Risk impact</th></tr></thead><tbody>{rows}</tbody></table><p>This report describes only controlled PikaTrap decoys. No external system was accessed or targeted.</p></body></html>"""
    return HTMLResponse(document, headers={"Content-Disposition": f'attachment; filename="pikatrap-incident-{session_id}.html"'})


@app.websocket("/ws/events")
async def websocket_events(websocket: WebSocket):
    await manager.connect(websocket)
    try:
        while True:
            await websocket.receive_text()
    except WebSocketDisconnect:
        manager.disconnect(websocket)
