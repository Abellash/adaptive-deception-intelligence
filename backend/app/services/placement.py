"""Safe, local decoy placement for the defender-owned NovaPay sandbox."""

from sqlalchemy import select
from sqlalchemy.orm import Session

from ..models import Asset, Honeytoken


def _deploy(db: Session, session_id: str, mode: str, label: str, token_type: str, risk_weight: int) -> dict:
    slug = label.lower().replace(" ", "-").replace("/", "-")
    asset_name = f"sandbox-{session_id[-10:]}-{slug}"
    asset = db.scalar(select(Asset).where(Asset.name == asset_name))
    created = False
    if not asset:
        asset = Asset(name=asset_name, type=token_type, environment="NovaPay defender-owned sandbox", metadata_json={"safe": True, "placement_mode": mode, "session_id": session_id, "label": label})
        db.add(asset)
        db.flush()
        db.add(Honeytoken(token_type=token_type, asset_id=asset.id, reference=f"ptk-{session_id[-8:]}-{slug}", risk_weight=risk_weight))
        created = True
    return {"name": label, "asset_id": asset.id, "created": created, "token_type": token_type}


def place_safe_decoys(db: Session, session_id: str, observed_action: str, intent: str, risk_score: int) -> dict:
    """Place metadata-only decoys. This never scans or modifies external systems."""
    if risk_score >= 75 and intent == "Collection":
        return {"mode": "CONTAIN", "rationale": "Collection risk is already high; preserve evidence and contain the sandbox session rather than exposing more decoys.", "decoys": []}

    if observed_action in {"directory_scan", "file_enumeration", "cloud_bucket_enumeration"}:
        choices = [("Customer export lure", "fake_document", 25), ("AWS billing honeycredential", "cloud_credential", 30), ("CI deploy-key lure", "source_secret", 30)]
        return {"mode": "SWEEP", "rationale": "Broad discovery was observed, so the sandbox expanded several diverse decoy surfaces to measure attacker preference.", "decoys": [_deploy(db, session_id, "SWEEP", *choice) for choice in choices]}

    target = ("Customer export lure", "fake_document", 30)
    if observed_action in {"credential_read", "credential_auth_attempt", "database_credential_access"}:
        target = ("Cloud storage honeycredential", "cloud_credential", 35)
    elif observed_action in {"source_secret_access", "fake_service_probe"}:
        target = ("Release artifact archive", "source_secret", 35)
    return {"mode": "SEEK", "rationale": f"{intent} behavior was observed, so the sandbox placed one targeted decoy to validate the attacker's likely objective.", "decoys": [_deploy(db, session_id, "SEEK", *target)]}
