import json
from pathlib import Path

from evaluation.run_evaluation import build_report, run_scenario
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.database import Base


SCENARIOS_PATH = Path(__file__).resolve().parents[1] / "evaluation" / "scenarios.json"


def test_evaluation_catalog_has_diverse_reproducible_scenarios():
    scenarios = json.loads(SCENARIOS_PATH.read_text(encoding="utf-8"))
    assert 20 <= len(scenarios) <= 50
    assert {scenario["expected_placement"] for scenario in scenarios} == {"SWEEP", "SEEK", "CONTAIN"}
    assert any(scenario["expected_containment"] for scenario in scenarios)
    assert any(not scenario["expected_containment"] for scenario in scenarios)


def test_evaluation_runs_against_an_isolated_database():
    scenarios = json.loads(SCENARIOS_PATH.read_text(encoding="utf-8"))
    engine = create_engine("sqlite+pysqlite:///:memory:")
    Base.metadata.create_all(engine)
    with sessionmaker(bind=engine)() as db:
        results = [run_scenario(db, scenario) for scenario in scenarios]
    report = build_report(results)
    assert report["scenario_count"] == 24
    assert report["real_assets_reached_percent"] == 0.0
    assert report["average_dwell_time"].startswith("N/A")
