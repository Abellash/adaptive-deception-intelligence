from app.services.agentic_orchestrator import apply_safety_gate, recommend


def test_agent_recommends_sweep_after_broad_discovery():
    result = recommend(["directory_scan", "file_enumeration"], 20, "Discovery", 0.7)
    assert result["recommended_action"] == "SWEEP"
    assert result["evidence"]["event_count"] == 2


def test_agent_recommends_seek_after_focused_credential_behavior():
    result = recommend(["directory_scan", "credential_read"], 35, "Credential Access", 0.84)
    assert result["recommended_action"] == "SEEK"
    assert result["evidence"]["credential_signals"] == 1


def test_agent_cannot_bypass_deterministic_containment_gate():
    recommendation = recommend(["bulk_export_attempt"], 40, "Exfiltration Attempt", 0.55)
    gated = apply_safety_gate(recommendation, "OBSERVE", "SEEK")
    assert gated["approved_action"] == "SEEK"

    containment_request = {"recommended_action": "RECOMMEND_CONTAINMENT"}
    blocked = apply_safety_gate(containment_request, "OBSERVE", "SEEK")
    assert blocked["gate_status"] == "BLOCKED"
    assert blocked["approved_action"] == "OBSERVE"


def test_safety_policy_overrides_agent_when_containment_threshold_is_met():
    recommendation = recommend(["credential_read"], 25, "Credential Access", 0.84)
    gated = apply_safety_gate(recommendation, "RECOMMEND_CONTAINMENT", "CONTAIN")
    assert gated["approved_action"] == "RECOMMEND_CONTAINMENT"
    assert gated["gate_status"] == "OVERRIDDEN_BY_SAFETY_POLICY"
