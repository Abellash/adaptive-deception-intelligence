"""Bounded, explainable recommendation layer for the PikaTrap sandbox.

This is deliberately not an autonomous execution agent. It can recommend only
approved deception actions, and the deterministic policy remains the final
safety gate before the application changes a simulated session.
"""

from __future__ import annotations

from collections import Counter


ALLOWED_ACTIONS = {
    "OBSERVE",
    "SWEEP",
    "SEEK",
    "DEPLOY_DECOY",
    "ESCALATE",
    "RECOMMEND_CONTAINMENT",
}

BROAD_DISCOVERY_ACTIONS = {"directory_scan", "file_enumeration", "cloud_bucket_enumeration"}
FOCUSED_ACTIONS = {
    "credential_read",
    "credential_auth_attempt",
    "database_credential_access",
    "source_secret_access",
    "fake_service_probe",
}
HIGH_VALUE_ACTIONS = {"sensitive_decoy_access", "financial_document_access", "bulk_export_attempt"}


def recommend(actions: list[str], risk_score: int, intent: str, confidence: float) -> dict:
    """Recommend a bounded action using only the current sandbox session history."""
    history = Counter(actions)
    last_action = actions[-1] if actions else ""
    evidence = {
        "event_count": len(actions),
        "last_action": last_action or "none",
        "risk_score": risk_score,
        "intent": intent,
        "intent_confidence": round(confidence, 2),
        "credential_signals": sum(history[action] for action in FOCUSED_ACTIONS),
        "discovery_signals": sum(history[action] for action in BROAD_DISCOVERY_ACTIONS),
        "high_value_signals": sum(history[action] for action in HIGH_VALUE_ACTIONS),
    }

    if risk_score >= 75 and intent == "Collection" and confidence >= 0.8:
        return {
            "recommended_action": "RECOMMEND_CONTAINMENT",
            "reason": "High-confidence collection behavior crossed the bounded containment recommendation threshold.",
            "evidence": evidence,
        }
    if last_action in BROAD_DISCOVERY_ACTIONS:
        return {
            "recommended_action": "SWEEP",
            "reason": "Broad discovery is the latest behavior; expand several safe metadata-only decoys to measure preference.",
            "evidence": evidence,
        }
    if last_action in FOCUSED_ACTIONS:
        return {
            "recommended_action": "SEEK",
            "reason": "Focused credential, source, database, or service behavior warrants one targeted safe decoy.",
            "evidence": evidence,
        }
    if last_action in HIGH_VALUE_ACTIONS and risk_score >= 50:
        return {
            "recommended_action": "ESCALATE",
            "reason": "High-value asset interest is increasing; preserve evidence and elevate monitoring before containment criteria are met.",
            "evidence": evidence,
        }
    if last_action:
        return {
            "recommended_action": "DEPLOY_DECOY",
            "reason": "A safe interaction occurred; deploy or retain a relevant decoy while collecting more evidence.",
            "evidence": evidence,
        }
    return {
        "recommended_action": "OBSERVE",
        "reason": "No attacker action has been observed yet.",
        "evidence": evidence,
    }


def apply_safety_gate(recommendation: dict, deterministic_action: str, placement_mode: str) -> dict:
    """Turn a recommendation into an explainable, bounded allowed action.

    The recommendation cannot execute external activity. The safety gate can
    override it with containment or normalize it to the placement service's
    safe local mode.
    """
    requested = recommendation["recommended_action"]
    if requested not in ALLOWED_ACTIONS:
        requested = "OBSERVE"

    if deterministic_action == "RECOMMEND_CONTAINMENT":
        return {
            "requested_action": requested,
            "approved_action": "RECOMMEND_CONTAINMENT",
            "gate_status": "OVERRIDDEN_BY_SAFETY_POLICY" if requested != "RECOMMEND_CONTAINMENT" else "APPROVED",
            "gate_reason": "Deterministic containment threshold was met; simulated session isolation takes priority.",
        }

    if requested == "RECOMMEND_CONTAINMENT":
        return {
            "requested_action": requested,
            "approved_action": "OBSERVE",
            "gate_status": "BLOCKED",
            "gate_reason": "Containment was not approved because the deterministic containment threshold was not met.",
        }

    approved = placement_mode if placement_mode in {"SWEEP", "SEEK"} else "OBSERVE"
    status = "APPROVED" if requested == approved else "NORMALIZED_TO_SAFE_PLACEMENT"
    return {
        "requested_action": requested,
        "approved_action": approved,
        "gate_status": status,
        "gate_reason": "Only metadata-only decoys inside the defender-owned sandbox are permitted.",
    }
