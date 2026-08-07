RISK_WEIGHTS = {
    "directory_scan": 10,
    "file_enumeration": 10,
    "decoy_file_access": 20,
    "credential_read": 25,
    "credential_auth_attempt": 30,
    "cloud_bucket_enumeration": 20,
    "sensitive_decoy_access": 25,
    "bulk_export_attempt": 40,
    "source_secret_access": 25,
    "database_credential_access": 25,
    "financial_document_access": 20,
    "fake_service_probe": 15,
}


def risk_delta(action: str) -> int:
    return RISK_WEIGHTS.get(action, 5)


def severity(score: int) -> str:
    if score >= 75:
        return "CRITICAL"
    if score >= 50:
        return "HIGH"
    if score >= 25:
        return "MEDIUM"
    return "LOW"
