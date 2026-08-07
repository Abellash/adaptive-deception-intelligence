MITRE_MAPPING = {
    "directory_scan": ("Discovery", "T1083: File and Directory Discovery"),
    "file_enumeration": ("Discovery", "T1083: File and Directory Discovery"),
    "decoy_file_access": ("Discovery", "T1083: File and Directory Discovery"),
    "credential_read": ("Credential Access", "T1552.001: Credentials In Files"),
    "credential_auth_attempt": ("Credential Access", "T1078: Valid Accounts"),
    "cloud_bucket_enumeration": ("Discovery", "T1526: Cloud Service Discovery"),
    "sensitive_decoy_access": ("Collection", "T1213: Data from Information Repositories"),
    "bulk_export_attempt": ("Exfiltration", "T1020: Automated Exfiltration"),
    "source_secret_access": ("Credential Access", "T1552.001: Credentials In Files"),
    "database_credential_access": ("Credential Access", "T1552.001: Credentials In Files"),
    "financial_document_access": ("Collection", "T1213: Data from Information Repositories"),
    "fake_service_probe": ("Discovery", "T1046: Network Service Discovery"),
}


def map_event(action: str) -> tuple[str, str]:
    return MITRE_MAPPING.get(action, ("", ""))
