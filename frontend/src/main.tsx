import React, { useEffect, useState } from "react";
import { createRoot } from "react-dom/client";
import "./style.css";

type Event = { event_id: string; timestamp: string; session_id: string; action: string; risk_delta: number; risk_score: number; severity: string; intent: string; intent_confidence: number; intent_probabilities: Record<string, number>; behavior: string; threat_percent: number; next_paths: { path: string; probability: number }[]; session_status: string; containment_action: string | null; mitre_technique: string; orchestrator_action: string; details: Record<string, unknown> };
type Incident = { id: string; session_id: string; severity: string; status: string; summary: string; containment_action: string; created_at: string };
type Effectiveness = { decoys_evaluated: number; engaged: number; ignored: number; progressed: number; engagement_rate_percent: number; sessions_evaluated: number };
type AnalystDecision = { id: string; analyst: string; action: string; note: string; recommendation: string; created_at: string };
const API = import.meta.env.VITE_API_URL || "http://localhost:8000";
const LAB_URL = import.meta.env.VITE_LAB_URL || "http://localhost:8081";
const title = (value: string) => value.replaceAll("_", " ");
const eventLabels: Record<string, string> = {
  directory_scan: "Portal discovery", file_enumeration: "Workspace enumeration", decoy_file_access: "Decoy file access",
  credential_read: ".env.production read", credential_auth_attempt: "Fake credential use", cloud_bucket_enumeration: "Storage bucket discovery",
  sensitive_decoy_access: "Sensitive decoy accessed", bulk_export_attempt: "Decoy export attempt",
};
const tokenChoices = [
  [".env production config", "fake_config", 25], ["AWS-style honeycredential", "cloud_credential", 30],
  ["Database backup credentials", "database_credential", 25], ["Customer export document", "fake_document", 25],
  ["Source repository deploy key", "source_secret", 30],
] as const;

function AttackGraph({ events, activeSession, heading = "Live deception graph" }: { events: Event[]; activeSession: string | null; heading?: string }) {
  const sessionEvents = activeSession ? events.filter(event => event.session_id === activeSession) : [];
  const latest = sessionEvents[0];
  const path = [...sessionEvents].reverse();
  return <section className="graph-section">
    <div className="section-title"><div><p className="eyebrow">ADAPTIVE DECEPTION GRAPH</p><h2>{heading}</h2></div><span>{activeSession ? `Session ${activeSession}` : "Awaiting a session"}</span></div>
    {path.length ? <div className="attack-graph" aria-label="Observed live attacker path">{path.map((event, index) => <React.Fragment key={event.event_id}>
      <div className={`graph-node seen ${index === path.length - 1 ? "current" : ""}`}><span>{String(index + 1).padStart(2, "0")}</span><strong>{eventLabels[event.action] || title(event.action)}</strong><small>{event.intent}</small><em>Threat {event.threat_percent}%</em></div>
      {index < path.length - 1 && <div className="graph-edge lit">-&gt;</div>}
    </React.Fragment>)}</div> : <div className="empty">No path is shown until a real NovaPay lab interaction occurs.</div>}
    {latest && <div className="behavior-panel"><div><small>OBSERVED BEHAVIOR</small><p>{latest.behavior || "Observed lab interaction"}</p></div><div><small>EVOLVING INTENT</small><p>{Object.entries(latest.intent_probabilities || {}).sort((a,b) => b[1] - a[1]).slice(0, 3).map(([intent, probability]) => `${intent} ${probability}%`).join(" · ") || latest.intent}</p></div><div><small>LIKELY NEXT ROUTES</small><p>{(latest.next_paths || []).map(item => `${item.path} ${item.probability}%`).join(" · ") || "Observe for more evidence"}</p></div></div>}
    {latest && (() => { const placement = latest.details.placement as { mode?: string; rationale?: string; decoys?: { name: string; created: boolean }[] } | undefined; return placement ? <div className={`placement ${placement.mode?.toLowerCase()}`}><strong>{placement.mode} DECISION</strong><p>{placement.rationale}</p>{placement.decoys?.length ? <small>Safe sandbox decoys: {placement.decoys.map(decoy => `${decoy.name}${decoy.created ? " (deployed)" : " (already active)"}`).join(" · ")}</small> : <small>No further decoys deployed; evidence preservation and containment take priority.</small>}</div> : null; })()}
    {latest && (() => { const recommendation = latest.details.agent_recommendation as { recommended_action?: string; reason?: string; evidence?: { event_count?: number; risk_score?: number; intent_confidence?: number } } | undefined; const gate = latest.details.agentic_decision as { approved_action?: string; gate_status?: string; gate_reason?: string } | undefined; return recommendation && gate ? <div className="agentic-decision"><div><small>BOUNDED AGENT RECOMMENDATION</small><strong>{recommendation.recommended_action || "OBSERVE"}</strong></div><div><small>SAFETY-GATED ACTION</small><strong>{gate.approved_action || "OBSERVE"} / {gate.gate_status || "PENDING"}</strong></div><p>{recommendation.reason}</p><p className="agentic-meta">Session evidence: {recommendation.evidence?.event_count ?? 0} events / risk {recommendation.evidence?.risk_score ?? 0} / confidence {Math.round((recommendation.evidence?.intent_confidence ?? 0) * 100)}%</p><small className="agentic-gate">Safety gate: {gate.gate_reason}</small></div> : null; })()}
    <p className="graph-caption">Only actions the attacker has already taken are displayed. The likely-route percentages are transparent estimates from the observed sequence and change after each interaction.</p>
  </section>;
}

function HoneytokenFactory() {
  const [message, setMessage] = useState("");
  const createToken = async (name: string, tokenType: string, riskWeight: number) => {
    setMessage("Creating safe lab honeytoken...");
    try {
      const response = await fetch(`${API}/api/v1/honeytokens`, { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ name, token_type: tokenType, risk_weight: riskWeight }) });
      const data = await response.json();
      setMessage(response.ok ? `${data.name} created: ${data.reference}` : data.detail || "Unable to create honeytoken.");
    } catch { setMessage("API unavailable. Ensure the backend is running."); }
  };
  return <section className="factory"><div className="section-title"><div><p className="eyebrow">HONEYTOKEN FACTORY</p><h2>Create safe decoys</h2></div><span>NovaPay lab inventory</span></div><div className="token-options">{tokenChoices.map(([name, type, risk]) => <button key={type} onClick={() => createToken(name, type, risk)}><strong>{name}</strong><small>{type.replace("_", " ")} / risk weight {risk}</small></button>)}</div>{message && <p className="factory-message">{message}</p>}</section>;
}

function DeceptionEffectiveness() {
  const [metrics, setMetrics] = useState<Effectiveness | null>(null);
  useEffect(() => {
    const load = () => fetch(`${API}/api/v1/deception-effectiveness`).then(response => response.json()).then(setMetrics).catch(() => {});
    load();
    const timer = window.setInterval(load, 3000);
    return () => window.clearInterval(timer);
  }, []);
  const values = metrics || { decoys_evaluated: 0, engaged: 0, ignored: 0, progressed: 0, engagement_rate_percent: 0, sessions_evaluated: 0 };
  return <section className="effectiveness"><div className="section-title"><div><p className="eyebrow">ADAPTIVE FEEDBACK LOOP</p><h2>Deception effectiveness</h2></div><span>{values.sessions_evaluated} completed session{values.sessions_evaluated === 1 ? "" : "s"}</span></div><div className="effectiveness-metrics"><div><small>DECOYS EVALUATED</small><strong>{values.decoys_evaluated}</strong></div><div><small>ENGAGED</small><strong>{values.engaged}</strong></div><div><small>ENGAGEMENT RATE</small><strong>{values.engagement_rate_percent}%</strong></div><div><small>IGNORED</small><strong>{values.ignored}</strong></div><div><small>PROGRESSED</small><strong>{values.progressed}</strong></div></div><p className="graph-caption">After containment, PikaTrap records whether controlled-lab decoys were engaged, ignored, or followed by further progression. Future SEEK choices prefer decoys with stronger prior engagement outcomes.</p></section>;
}

function AnalystControls({ sessionId }: { sessionId: string | null }) {
  const [decisions, setDecisions] = useState<AnalystDecision[]>([]);
  const [message, setMessage] = useState("");
  const [contained, setContained] = useState(false);
  const load = () => { if (!sessionId) { setDecisions([]); setContained(false); return; } fetch(`${API}/api/v1/sessions/${encodeURIComponent(sessionId)}/analyst-decisions`).then(response => response.json()).then(setDecisions).catch(() => {}); fetch(`${API}/api/v1/sessions/${encodeURIComponent(sessionId)}/containment`).then(response => response.json()).then(data => setContained(data.contained === true)).catch(() => {}); };
  useEffect(() => { load(); const timer = window.setInterval(load, 3000); return () => window.clearInterval(timer); }, [sessionId]);
  const submit = async (action: string) => {
    if (!sessionId) return;
    try { const response = await fetch(`${API}/api/v1/sessions/${encodeURIComponent(sessionId)}/analyst-action`, { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ action, note: `SOC analyst selected ${action} in the safe lab.`, analyst: "SOC Analyst" }) }); const data = await response.json(); setMessage(response.ok ? data.message : data.detail || "Unable to record decision."); setContained(data.session_status === "CONTAINED"); load(); } catch { setMessage("API unavailable."); }
  };
  return <section className="analyst-controls"><div className="section-title"><div><p className="eyebrow">HUMAN-IN-THE-LOOP SOC</p><h2>Analyst decision controls</h2></div><span>{contained ? "SESSION CONTAINED" : sessionId ? "Audit trail active" : "Awaiting session"}</span></div><p className="graph-caption">The agent recommends bounded actions; the analyst can approve, reject, override, or quarantine only the defender-owned sandbox session.</p><div className="analyst-buttons"><button onClick={() => submit("APPROVE")} disabled={!sessionId || contained}>Approve</button><button onClick={() => submit("REJECT")} disabled={!sessionId || contained}>Reject</button><button onClick={() => submit("OVERRIDE")} disabled={!sessionId || contained}>Override</button><button className="quarantine" onClick={() => submit("QUARANTINE")} disabled={!sessionId || contained}>Quarantine</button></div>{contained && <div className="analyst-contained">SESSION QUARANTINED — analyst-approved local sandbox isolation; fake credentials revoked.</div>}{message && <p className="factory-message">{message}</p>}{decisions[0] && <p className="audit-line">Latest decision: <b>{decisions[0].action}</b> by {decisions[0].analyst} / agent recommendation was {decisions[0].recommendation}</p>}</section>;
}

function App() {
  const [events, setEvents] = useState<Event[]>([]);
  const [connected, setConnected] = useState(false);
  const [activeSession, setActiveSession] = useState<string | null>(() => `novapay-demo-${Date.now()}-${Math.random().toString(36).slice(2, 10)}`);
  const [reportMessage, setReportMessage] = useState("");
  const [incidents, setIncidents] = useState<Incident[]>([]);
  useEffect(() => {
    const socket = new WebSocket(API.replace("http", "ws") + "/ws/events");
    socket.onopen = () => { setConnected(true); socket.send("dashboard"); };
    socket.onmessage = event => { const data = JSON.parse(event.data).data as Event; setActiveSession(data.session_id); setEvents(previous => [data, ...previous]); };
    socket.onclose = () => setConnected(false);
    return () => socket.close();
  }, []);
  useEffect(() => {
    const loadHistory = () => fetch(`${API}/api/v1/incidents`).then(response => response.json()).then(setIncidents).catch(() => {});
    loadHistory();
    const timer = window.setInterval(loadHistory, 3000);
    return () => window.clearInterval(timer);
  }, []);
  useEffect(() => {
    if (!activeSession) return;
    const sync = async () => {
      try {
        const response = await fetch(`${API}/api/v1/events`);
        const incoming = (await response.json() as Event[]).filter(event => event.session_id === activeSession);
        if (!incoming.length) return;
        setEvents(incoming);
      } catch { /* WebSocket remains the primary live path. */ }
    };
    sync();
    const timer = window.setInterval(sync, 1500);
    return () => window.clearInterval(timer);
  }, [activeSession]);
  const latest = activeSession ? events.find(event => event.session_id === activeSession) : undefined;
  const reportReady = latest?.orchestrator_action === "RECOMMEND_CONTAINMENT";
  const labUrl = `${LAB_URL}/?session_id=${encodeURIComponent(activeSession || "")}`;
  const downloadReport = async (sessionId = latest?.session_id) => {
    if (!sessionId) return;
    setReportMessage("Preparing incident report...");
    try {
      const response = await fetch(`${API}/api/v1/reports/${encodeURIComponent(sessionId)}.html`);
      if (!response.ok) throw new Error("Report is not ready yet.");
      const file = await response.blob();
      const downloadUrl = URL.createObjectURL(file);
      const link = document.createElement("a");
      link.href = downloadUrl;
      link.download = `pikatrap-incident-${sessionId}.html`;
      link.click();
      URL.revokeObjectURL(downloadUrl);
      setReportMessage("Incident report downloaded.");
    } catch (error) { setReportMessage(error instanceof Error ? error.message : "Unable to download report."); }
  };
  return <main>
    <header><div><p className="eyebrow">TEAM PIKACHU / NOVAPAY LAB</p><h1>PIKA<span>TRAP</span></h1><p>Adaptive deception. Intelligent defense.</p></div><div><a className="new-demo" href={labUrl} target="_blank" rel="noreferrer">Open linked lab</a><span className={connected ? "status online" : "status"}>● {connected ? "LIVE TELEMETRY" : "CONNECTING"}</span></div></header>
    <section className="hero"><div><p className="eyebrow">DEFENDER-OWNED DECEPTION LAB</p><h2>{latest ? `${latest.intent} detected` : "Run a safe attack simulation"}</h2><p>{latest ? `The policy selected ${title(latest.orchestrator_action)} after correlating this session’s observed behavior.` : "This dashboard session is ready. Open the linked NovaPay lab and make an attacker choice."}</p><a className="lab-link" href={labUrl} target="_blank" rel="noreferrer">Open NovaPay target lab</a>{reportReady && <button className="report-link" onClick={() => downloadReport()}>Download incident report</button>}{latest?.session_status === "CONTAINED" && <div className="containment-banner">SESSION ISOLATED — {latest.containment_action}</div>}{reportMessage && <span className="report-message">{reportMessage}</span>}</div><div className="risk"><small>LATEST ATTACK IMPACT</small><strong>+{latest?.risk_delta ?? 0}</strong><b className={latest?.severity?.toLowerCase() || "low"}>{latest ? title(latest.action) : "WAITING"}</b></div></section>
    <HoneytokenFactory />
    <section className="grid"><article><p className="eyebrow">ADAPTIVE POLICY</p><h3>{latest ? title(latest.orchestrator_action) : "OBSERVE"}</h3><p className="muted">PikaTrap persists explainable behavior memory from prior lab sessions. It is not a trained LLM and it never executes external actions.</p></article><article><p className="eyebrow">CONTAINMENT</p><h3>{latest?.session_status === "CONTAINED" ? "SESSION ISOLATED" : reportReady ? "REPORT READY" : "POLICY-GATED"}</h3><p className="muted">At threshold, the local policy executor quarantines the simulated session and revokes its fake-credential access.</p></article></section>
    <AttackGraph events={events} activeSession={activeSession} />
    <AnalystControls sessionId={activeSession} />
    <DeceptionEffectiveness />
    <section className="history"><div className="section-title"><div><p className="eyebrow">COMPLETED ATTACK HISTORY</p><h2>Contained incidents</h2></div><a className="new-session" href="/">New attacker session</a></div>{incidents.length ? incidents.map(incident => <article className="history-row" key={incident.id}><div><h3>{incident.severity} / {incident.status}</h3><p>{incident.summary}</p></div><div className="history-actions"><button onClick={() => downloadReport(incident.session_id)}>Download report</button></div></article>) : <div className="empty">Contained attack cycles will appear here.</div>}</section>
    <section className="events"><div className="section-title"><div><p className="eyebrow">EVENT TIMELINE</p><h2>Telemetry feed</h2></div><span>{activeSession ? events.filter(event => event.session_id === activeSession).length : 0} event{events.filter(event => event.session_id === activeSession).length === 1 ? "" : "s"}</span></div>{activeSession ? events.filter(event => event.session_id === activeSession).map(event => <article className="event" key={event.event_id}><div className="dot"></div><div><h3>{title(event.action)}</h3><p>{String(event.details.path || event.details.object || "Controlled canary interaction")}</p></div><div><small>MITRE ATT&CK</small><p>{event.mitre_technique || "Pending mapping"}</p></div><div className="intent"><small>INTENT</small><p>{event.intent} / {Math.round(event.intent_confidence * 100)}%</p></div><div className="impact"><small>ATTACK IMPACT</small><p>+{event.risk_delta}</p></div><b className={event.severity.toLowerCase()}>{event.severity}</b></article>) : <div className="empty">No interactions yet. Choose Start new demo, then open the NovaPay lab.</div>}</section>
  </main>;
}

createRoot(document.getElementById("root")!).render(<App />);
