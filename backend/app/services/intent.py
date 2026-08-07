from collections import Counter


def infer_intent_probabilities(actions: list[str]) -> dict[str, float]:
    """Explainable evolving probabilities, derived only from observed actions."""
    scores = {"Reconnaissance": 8, "Discovery": 8, "Credential Access": 8, "Cloud Discovery": 8, "Collection": 8, "Exfiltration Attempt": 4}
    signals = {
        "directory_scan": {"Reconnaissance": 35, "Discovery": 25}, "file_enumeration": {"Discovery": 35},
        "decoy_file_access": {"Discovery": 20}, "credential_read": {"Credential Access": 45, "Discovery": 10},
        "source_secret_access": {"Credential Access": 45}, "database_credential_access": {"Credential Access": 45},
        "credential_auth_attempt": {"Credential Access": 35, "Cloud Discovery": 25}, "cloud_bucket_enumeration": {"Cloud Discovery": 45, "Collection": 10},
        "sensitive_decoy_access": {"Collection": 45}, "financial_document_access": {"Collection": 40},
        "bulk_export_attempt": {"Collection": 25, "Exfiltration Attempt": 55}, "fake_service_probe": {"Discovery": 25},
    }
    for action in actions:
        for intent, weight in signals.get(action, {}).items(): scores[intent] += weight
    total = sum(scores.values())
    return {intent: round(value * 100 / total, 1) for intent, value in scores.items()}


def behavior_label(actions: list[str]) -> str:
    observed = set(actions)
    if "bulk_export_attempt" in observed: return "High-risk collection and simulated exfiltration behavior"
    if "sensitive_decoy_access" in observed: return "Sensitive data collection behavior"
    if "cloud_bucket_enumeration" in observed: return "Cloud-resource discovery and collection pivot"
    if "credential_auth_attempt" in observed: return "Credential validation and lateral-pivot behavior"
    if observed & {"credential_read", "source_secret_access", "database_credential_access"}: return "Credential harvesting behavior"
    if observed & {"directory_scan", "file_enumeration", "fake_service_probe"}: return "Reconnaissance and environment discovery"
    return "Insufficient correlated behavior"


def next_path_probabilities(actions: list[str]) -> list[dict[str, float | str]]:
    last = actions[-1] if actions else ""
    paths = {
        "directory_scan": [("Enumerate operational files", 46), ("Inspect finance documents", 30), ("Probe source-control artifacts", 24)],
        "file_enumeration": [("Read a credential-bearing configuration", 52), ("Open a sensitive document", 28), ("Probe a fake internal service", 20)],
        "credential_read": [("Try fake cloud authentication", 56), ("Try source-control authentication", 27), ("Continue local discovery", 17)],
        "source_secret_access": [("Try source-control authentication", 58), ("Inspect linked cloud configuration", 27), ("Continue discovery", 15)],
        "database_credential_access": [("Attempt database access", 55), ("Search finance data", 30), ("Continue discovery", 15)],
        "credential_auth_attempt": [("Enumerate fake cloud buckets", 60), ("Inspect sensitive export", 25), ("Probe another service", 15)],
        "cloud_bucket_enumeration": [("Access customer export decoy", 63), ("Inspect financial archive", 22), ("Inspect engineering secrets", 15)],
        "sensitive_decoy_access": [("Attempt bulk export", 70), ("Access another sensitive decoy", 18), ("Return to discovery", 12)],
        "financial_document_access": [("Attempt bulk export", 62), ("Access related document", 23), ("Return to discovery", 15)],
        "bulk_export_attempt": [("Sandbox containment recommendation", 100)],
    }
    return [{"path": name, "probability": probability} for name, probability in paths.get(last, [("Observe for more evidence", 100)])]


def infer_intent(actions: list[str]) -> tuple[str, float, list[str]]:
    observed = set(actions)
    if {"sensitive_decoy_access", "bulk_export_attempt"} <= observed:
        return "Collection", 0.94, ["sensitive dataset access", "bulk export attempt"]
    if {"credential_auth_attempt", "cloud_bucket_enumeration"} <= observed:
        return "Cloud Discovery", 0.88, ["honeycredential use", "bucket enumeration"]
    if "credential_read" in observed or "decoy_file_access" in observed:
        confidence = 0.84 if "credential_read" in observed else 0.62
        return "Credential Access", confidence, ["deceptive configuration accessed"]
    if Counter(actions)["directory_scan"] or "file_enumeration" in observed:
        return "Discovery", 0.70, ["filesystem enumeration"]
    probabilities = infer_intent_probabilities(actions)
    intent, probability = max(probabilities.items(), key=lambda item: item[1])
    if probability < 35:
        return "Uncertain", probability / 100, ["conflicting or limited behavioral evidence"]
    return intent, probability / 100, ["behavioral probability estimate"]
