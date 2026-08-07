# Architecture

```text
Safe .env honeytoken / demo canary
             ↓
 FastAPI telemetry API → PostgreSQL SecurityEvent
             ↓                  ↓
 deterministic risk + intent + validated ATT&CK mapping
             ↓
 policy-gated Deception Orchestrator recommendation
             ↓
 WebSocket → React dashboard
```

The current prototype uses deterministic rules for risk, intent, MITRE mappings, and containment policy. It now persists an explainable behavior-memory count for previously observed lab actions; this lets explanations adapt based on prior demonstrations, but it is explicitly not model training or an LLM. An LLM interface may later explain or recommend among fixed actions; it never receives shell execution authority. PostgreSQL persists production-style data in Docker; SQLite makes the backend independently runnable for local testing. Redis is provisioned as the real-time state service for the next phase but not yet used by the initial vertical slice.

The containment action is only a recommendation. Future execution must be restricted to the Docker lab and require policy validation/human approval as appropriate.
