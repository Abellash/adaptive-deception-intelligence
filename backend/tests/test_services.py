from app.services.intent import infer_intent
from app.services.orchestrator import decide
from app.services.risk import risk_delta, severity


def test_risk_weights_and_thresholds():
    assert risk_delta("credential_read") == 25
    assert severity(24) == "LOW"
    assert severity(75) == "CRITICAL"


def test_intent_requires_correlated_evidence():
    intent, confidence, _ = infer_intent(["directory_scan"])
    assert intent == "Discovery"
    assert confidence < 0.8


def test_containment_requires_collection_and_high_risk():
    assert decide(90, "Collection", 0.94)[0] == "RECOMMEND_CONTAINMENT"
    assert decide(90, "Uncertain", 0.3)[0] != "RECOMMEND_CONTAINMENT"
