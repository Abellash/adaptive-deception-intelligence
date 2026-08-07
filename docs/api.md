# API

## `POST /api/v1/telemetry`

Accepts standardized telemetry including `session_id`, `source_ip`, `asset_id`, `asset_type`, `action`, and `details`. The supported initial actions are `directory_scan`, `decoy_file_access`, `credential_read`, `credential_auth_attempt`, `cloud_bucket_enumeration`, `sensitive_decoy_access`, and `bulk_export_attempt`.

The response adds `risk_delta`, session `risk_score`, severity, intent/confidence, deterministic ATT&CK mapping, and the policy-approved orchestration action.

## `WS /ws/events`

Broadcasts `{ "type": "telemetry", "data": EventOut }` after ingestion.
