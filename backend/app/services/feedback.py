"""Explainable feedback loop for safe PikaTrap decoy placement."""

from __future__ import annotations

from collections import Counter

from sqlalchemy import select
from sqlalchemy.orm import Session

from ..models import Asset, DecoyFeedback, SecurityEvent


ENGAGEMENT_ACTIONS = {
    "fake_document": {"sensitive_decoy_access", "financial_document_access", "bulk_export_attempt"},
    "cloud_credential": {"credential_auth_attempt", "cloud_bucket_enumeration"},
    "source_secret": {"source_secret_access", "fake_service_probe"},
}
PROGRESSION_ACTIONS = {"credential_auth_attempt", "cloud_bucket_enumeration", "sensitive_decoy_access", "financial_document_access", "bulk_export_attempt"}


def record_session_feedback(db: Session, session_id: str) -> dict:
    """Persist one outcome per dynamically placed decoy after containment.

    Engagement is derived from controlled-lab event semantics. Dwell is measured
    in later event count, not elapsed wall-clock time.
    """
    existing = list(db.scalars(select(DecoyFeedback).where(DecoyFeedback.session_id == session_id)))
    if existing:
        return summarize_feedback(existing)

    events = list(db.scalars(select(SecurityEvent).where(SecurityEvent.session_id == session_id).order_by(SecurityEvent.timestamp)))
    actions = [event.event_type for event in events]
    assets = [asset for asset in db.scalars(select(Asset)) if (asset.metadata_json or {}).get("session_id") == session_id]
    feedback_rows: list[DecoyFeedback] = []

    for asset in assets:
        metadata = asset.metadata_json or {}
        relevant_actions = ENGAGEMENT_ACTIONS.get(asset.type, set())
        interaction_steps = [index + 1 for index, action in enumerate(actions) if action in relevant_actions]
        first_step = interaction_steps[0] if interaction_steps else None
        later_actions = actions[first_step:] if first_step else []
        progression = sum(action in PROGRESSION_ACTIONS for action in later_actions)
        outcome = "IGNORED"
        if interaction_steps:
            outcome = "ENGAGED_AND_PROGRESSED" if progression else "ENGAGED"
        row = DecoyFeedback(
            session_id=session_id,
            asset_id=asset.id,
            decoy_label=str(metadata.get("label", asset.name)),
            token_type=asset.type,
            placement_mode=str(metadata.get("placement_mode", "SEEK")),
            outcome=outcome,
            interaction_count=len(interaction_steps),
            first_interaction_step=first_step,
            progression_event_count=progression,
        )
        db.add(row)
        feedback_rows.append(row)
    db.flush()
    return summarize_feedback(feedback_rows)


def summarize_feedback(rows: list[DecoyFeedback]) -> dict:
    outcomes = Counter(row.outcome for row in rows)
    engaged = outcomes["ENGAGED"] + outcomes["ENGAGED_AND_PROGRESSED"]
    progressed = outcomes["ENGAGED_AND_PROGRESSED"]
    total = len(rows)
    return {
        "decoys_evaluated": total,
        "engaged": engaged,
        "ignored": outcomes["IGNORED"],
        "progressed": progressed,
        "engagement_rate_percent": round(100 * engaged / total, 1) if total else 0.0,
        "outcomes": dict(outcomes),
        "measurement": "Controlled-lab outcome derived from event sequences; dwell is measured in later event count.",
    }


def effectiveness_snapshot(db: Session) -> dict:
    rows = list(db.scalars(select(DecoyFeedback)))
    summary = summarize_feedback(rows)
    summary["sessions_evaluated"] = len({row.session_id for row in rows})
    summary["strategy_outcomes"] = {
        mode: dict(Counter(row.outcome for row in rows if row.placement_mode == mode))
        for mode in {"SWEEP", "SEEK"}
    }
    return summary
