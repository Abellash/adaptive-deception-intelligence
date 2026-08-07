def decide(risk_score: int, intent: str, confidence: float) -> tuple[str, str, bool]:
    if risk_score >= 75 and intent == "Collection" and confidence >= 0.8:
        return "RECOMMEND_CONTAINMENT", "Multi-step collection behavior crossed the sandbox containment threshold.", True
    if risk_score >= 50 and intent in {"Credential Access", "Cloud Discovery"}:
        return "EXPAND_DECEPTION", "Credential-related behavior warrants a linked cloud decoy.", True
    if intent == "Credential Access":
        return "DEPLOY_DECOY", "Configuration access suggests credential harvesting; deploy a linked honeycredential.", True
    return "OBSERVE", "More correlated behavior is required before escalation.", True
