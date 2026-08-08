# Bounded Agentic Orchestrator

PikaTrap uses a bounded, explainable recommendation layer for each simulated attacker session. It reads the complete ordered event history and can recommend only one action from this allow-list:

`OBSERVE`, `SWEEP`, `SEEK`, `DEPLOY_DECOY`, `ESCALATE`, or `RECOMMEND_CONTAINMENT`.

The recommendation is not an external-action executor. The deterministic policy engine remains the safety gate:

- Containment is approved only when the deterministic collection threshold is met.
- If containment is not approved, a containment recommendation is blocked.
- All other deployment recommendations are normalized to the placement service's `SWEEP` or `SEEK` metadata-only sandbox action.
- No action can scan, modify, or access external infrastructure.

For every event, PikaTrap stores the recommendation, its evidence summary, the safety-gated action, gate status, and gate reason inside the event details. The live dashboard and contained-session report expose this explanation.

This design makes the system agentic in its recommendation workflow while retaining deterministic, auditable, bounded execution.

## Feedback loop

When a sandbox session is contained, PikaTrap records a per-decoy outcome: `IGNORED`, `ENGAGED`, or `ENGAGED_AND_PROGRESSED`. The outcome is derived from controlled-lab event semantics and later event count, not external attacker activity or real elapsed dwell time. The placement service uses these outcomes as an explainable preference score when selecting among equivalent safe SEEK candidates and ordering SWEEP candidates.
