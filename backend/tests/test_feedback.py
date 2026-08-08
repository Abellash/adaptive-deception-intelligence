from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.database import Base
from app.models import Asset, AttackerSession, DecoyFeedback, SecurityEvent
from app.services.feedback import effectiveness_snapshot, record_session_feedback
from app.services.placement import place_safe_decoys


def test_feedback_records_engagement_and_progression_for_a_contained_session():
    engine = create_engine("sqlite+pysqlite:///:memory:")
    Base.metadata.create_all(engine)
    with sessionmaker(bind=engine)() as db:
        db.add(AttackerSession(id="feedback-session", source_ip="127.0.0.1"))
        decoy = Asset(name="sandbox-feedback-customer-export", type="fake_document", environment="NovaPay defender-owned sandbox", metadata_json={"session_id": "feedback-session", "label": "Customer export lure", "placement_mode": "SEEK"})
        db.add(decoy)
        db.flush()
        db.add_all([
            SecurityEvent(session_id="feedback-session", asset_id=decoy.id, event_type="sensitive_decoy_access", details={}),
            SecurityEvent(session_id="feedback-session", asset_id=decoy.id, event_type="bulk_export_attempt", details={}),
        ])
        summary = record_session_feedback(db, "feedback-session")
        assert summary["decoys_evaluated"] == 1
        assert summary["engaged"] == 1
        assert summary["progressed"] == 1
        assert effectiveness_snapshot(db)["engagement_rate_percent"] == 100.0


def test_placement_prefers_a_previously_engaged_candidate():
    engine = create_engine("sqlite+pysqlite:///:memory:")
    Base.metadata.create_all(engine)
    with sessionmaker(bind=engine)() as db:
        db.add(AttackerSession(id="history-session", source_ip="127.0.0.1"))
        asset = Asset(name="historical-aws", type="cloud_credential", environment="NovaPay defender-owned sandbox")
        db.add(asset)
        db.flush()
        db.add(DecoyFeedback(session_id="history-session", asset_id=asset.id, decoy_label="AWS billing honeycredential", token_type="cloud_credential", placement_mode="SEEK", outcome="ENGAGED", interaction_count=1, progression_event_count=0))
        db.flush()
        result = place_safe_decoys(db, "new-session", "credential_read", "Credential Access", 25)
        assert result["decoys"][0]["name"] == "AWS billing honeycredential"
        assert result["decoys"][0]["feedback_score"] == 2
