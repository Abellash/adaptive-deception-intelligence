"""Safe, local decoy placement for the defender-owned NovaPay sandbox."""

from sqlalchemy import select
from sqlalchemy.orm import Session

from ..models import Asset, DecoyFeedback, Honeytoken


def _feedback_score(db: Session, label: str, token_type: str) -> int:
    outcomes = db.scalars(select(DecoyFeedback.outcome).where(DecoyFeedback.decoy_label == label, DecoyFeedback.token_type == token_type))
    weights = {"ENGAGED_AND_PROGRESSED": 3, "ENGAGED": 2, "IGNORED": -1}
    return sum(weights.get(outcome, 0) for outcome in outcomes)


def _deploy(db: Session, session_id: str, mode: str, label: str, token_type: str, risk_weight: int, feedback_score: int = 0) -> dict:
    slug = label.lower().replace(" ", "-").replace("/", "-")
    asset_name = f"sandbox-{session_id[-10:]}-{slug}"
    asset = db.scalar(select(Asset).where(Asset.name == asset_name))
    created = False
    if not asset:
        asset = Asset(name=asset_name, type=token_type, environment="NovaPay defender-owned sandbox", metadata_json={"safe": True, "placement_mode": mode, "session_id": session_id, "label": label, "feedback_score": feedback_score})
        db.add(asset)
        db.flush()
        db.add(Honeytoken(token_type=token_type, asset_id=asset.id, reference=f"ptk-{session_id[-8:]}-{slug}", risk_weight=risk_weight))
        created = True
    return {"name": label, "asset_id": asset.id, "created": created, "token_type": token_type, "feedback_score": feedback_score}


def _select_preferred(db: Session, choices: list[tuple[str, str, int]]) -> tuple[tuple[str, str, int], int]:
    scored = [(choice, _feedback_score(db, choice[0], choice[1])) for choice in choices]
    return max(scored, key=lambda item: item[1])


def place_safe_decoys(db: Session, session_id: str, observed_action: str, intent: str, risk_score: int) -> dict:
    """Place metadata-only decoys. This never scans or modifies external systems."""
    if risk_score >= 75 and intent == "Collection":
        return {"mode": "CONTAIN", "rationale": "Collection risk is already high; preserve evidence and contain the sandbox session rather than exposing more decoys.", "decoys": []}

    if observed_action in {"directory_scan", "file_enumeration", "cloud_bucket_enumeration"}:
        choices = [("Customer export lure", "fake_document", 25), ("AWS billing honeycredential", "cloud_credential", 30), ("CI deploy-key lure", "source_secret", 30)]
        scored_choices = [(choice, _feedback_score(db, choice[0], choice[1])) for choice in choices]
        scored_choices.sort(key=lambda item: item[1], reverse=True)
        return {"mode": "SWEEP", "rationale": "Broad discovery was observed, so the sandbox expanded several diverse decoy surfaces to measure attacker preference. Prior controlled-lab engagement outcomes influence display and placement order.", "decoys": [_deploy(db, session_id, "SWEEP", *choice, feedback_score=score) for choice, score in scored_choices]}

    candidates = [("Customer export lure", "fake_document", 30), ("Finance archive lure", "fake_document", 25)]
    if observed_action in {"credential_read", "credential_auth_attempt", "database_credential_access"}:
        candidates = [("Cloud storage honeycredential", "cloud_credential", 35), ("AWS billing honeycredential", "cloud_credential", 30)]
    elif observed_action in {"source_secret_access", "fake_service_probe"}:
        candidates = [("Release artifact archive", "source_secret", 35), ("CI deploy-key lure", "source_secret", 30)]
    target, score = _select_preferred(db, candidates)
    return {"mode": "SEEK", "rationale": f"{intent} behavior was observed, so the sandbox placed one targeted decoy to validate the attacker's likely objective. The candidate is selected using prior controlled-lab feedback where available.", "decoys": [_deploy(db, session_id, "SEEK", *target, feedback_score=score)]}
