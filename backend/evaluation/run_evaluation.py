"""Run deterministic, safe regression scenarios against PikaTrap services.

This is a synthetic evaluation harness for the defender-owned NovaPay lab.
It measures consistency against reviewed scenario labels; it is not a claim of
real-world attacker detection accuracy.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys
from typing import Any

from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

# Support both `python evaluation/run_evaluation.py` and pytest execution.
BACKEND_ROOT = Path(__file__).resolve().parents[1]
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

from app.database import Base
from app.services.intent import infer_intent
from app.services.mapping import map_event
from app.services.orchestrator import decide
from app.services.placement import place_safe_decoys
from app.services.risk import risk_delta


ROOT = Path(__file__).resolve().parent
SCENARIOS_PATH = ROOT / "scenarios.json"


def percent(numerator: int, denominator: int) -> float:
    return round(100 * numerator / denominator, 1) if denominator else 0.0


def first_correct_intent_step(actions: list[str], expected_intent: str) -> int | None:
    for step in range(1, len(actions) + 1):
        predicted, _, _ = infer_intent(actions[:step])
        if predicted == expected_intent:
            return step
    return None


def run_scenario(db: Session, scenario: dict[str, Any]) -> dict[str, Any]:
    actions = scenario["actions"]
    risk_score = min(100, sum(risk_delta(action) for action in actions))
    intent, confidence, _ = infer_intent(actions)
    _, technique = map_event(actions[-1])
    orchestrator_action, _, _ = decide(risk_score, intent, confidence)
    placement = place_safe_decoys(db, f"eval-{scenario['id']}", actions[-1], intent, risk_score)
    contained = orchestrator_action == "RECOMMEND_CONTAINMENT"
    detection_step = first_correct_intent_step(actions, scenario["expected_intent"])
    return {
        "id": scenario["id"],
        "actions": actions,
        "expected_intent": scenario["expected_intent"],
        "predicted_intent": intent,
        "intent_correct": intent == scenario["expected_intent"],
        "expected_mitre": scenario["expected_mitre"],
        "predicted_mitre": technique,
        "mitre_correct": technique == scenario["expected_mitre"],
        "risk_score": risk_score,
        "expected_placement": scenario["expected_placement"],
        "placement": placement["mode"],
        "placement_correct": placement["mode"] == scenario["expected_placement"],
        "expected_containment": scenario["expected_containment"],
        "contained": contained,
        "containment_correct": contained == scenario["expected_containment"],
        "false_positive_containment": contained and not scenario["expected_containment"],
        "engaged": scenario["engaged"],
        "detection_latency_events": detection_step,
    }


def build_report(results: list[dict[str, Any]]) -> dict[str, Any]:
    total = len(results)
    expected_negative = [row for row in results if not row["expected_containment"]]
    expected_positive = [row for row in results if row["expected_containment"]]
    contained_positive = [row for row in expected_positive if row["contained"]]
    false_positives = [row for row in expected_negative if row["contained"]]
    latency_values = [row["detection_latency_events"] for row in results if row["detection_latency_events"] is not None]
    engaged = [row for row in results if row["engaged"]]
    return {
        "evaluation_scope": "Synthetic, deterministic NovaPay sandbox scenarios. Metrics are regression checks against reviewed labels, not claims of production detection performance.",
        "scenario_count": total,
        "intent_classification_accuracy_percent": percent(sum(row["intent_correct"] for row in results), total),
        "mitre_mapping_accuracy_percent": percent(sum(row["mitre_correct"] for row in results), total),
        "sweep_seek_contain_decision_accuracy_percent": percent(sum(row["placement_correct"] for row in results), total),
        "containment_accuracy_percent": percent(sum(row["containment_correct"] for row in results), total),
        "containment_recall_percent": percent(len(contained_positive), len(expected_positive)),
        "containment_false_positive_rate_percent": percent(len(false_positives), len(expected_negative)),
        "average_detection_latency_events": round(sum(latency_values) / len(latency_values), 2) if latency_values else None,
        "decoy_engagement_rate_percent": percent(len(engaged), total),
        "average_dwell_time": "N/A — synthetic scenarios do not model elapsed attacker dwell time.",
        "real_assets_reached_percent": 0.0,
        "scenario_results": results,
    }


def write_markdown(report: dict[str, Any], destination: Path) -> None:
    lines = [
        "# PikaTrap Synthetic Evaluation Report",
        "",
        report["evaluation_scope"],
        "",
        "## Metrics",
        "",
        "| Metric | Result |",
        "|---|---:|",
    ]
    for label, key in [
        ("Scenario count", "scenario_count"),
        ("Intent classification accuracy", "intent_classification_accuracy_percent"),
        ("MITRE mapping accuracy", "mitre_mapping_accuracy_percent"),
        ("SWEEP / SEEK / CONTAIN decision accuracy", "sweep_seek_contain_decision_accuracy_percent"),
        ("Containment accuracy", "containment_accuracy_percent"),
        ("Containment recall", "containment_recall_percent"),
        ("Containment false-positive rate", "containment_false_positive_rate_percent"),
        ("Average detection latency", "average_detection_latency_events"),
        ("Decoy engagement rate", "decoy_engagement_rate_percent"),
        ("Average dwell time", "average_dwell_time"),
        ("Real assets reached", "real_assets_reached_percent"),
    ]:
        value = report[key]
        suffix = "%" if "percent" in key else " events" if key == "average_detection_latency_events" else ""
        lines.append(f"| {label} | {value}{suffix} |")
    lines.extend(["", "## Scenario results", "", "| Scenario | Intent | MITRE | Placement | Containment |", "|---|---|---|---|---|"])
    for row in report["scenario_results"]:
        lines.append(f"| {row['id']} | {'PASS' if row['intent_correct'] else 'FAIL'} | {'PASS' if row['mitre_correct'] else 'FAIL'} | {'PASS' if row['placement_correct'] else 'FAIL'} | {'PASS' if row['containment_correct'] else 'FAIL'} |")
    destination.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser(description="Run PikaTrap safe synthetic evaluation scenarios.")
    parser.add_argument("--output-dir", default=str(ROOT / "results"), help="Directory for JSON and Markdown reports.")
    args = parser.parse_args()

    scenarios = json.loads(SCENARIOS_PATH.read_text(encoding="utf-8"))
    engine = create_engine("sqlite+pysqlite:///:memory:")
    Base.metadata.create_all(engine)
    session_factory = sessionmaker(bind=engine)
    with session_factory() as db:
        results = [run_scenario(db, scenario) for scenario in scenarios]
        db.commit()

    report = build_report(results)
    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    (output_dir / "evaluation-report.json").write_text(json.dumps(report, indent=2), encoding="utf-8")
    write_markdown(report, output_dir / "evaluation-report.md")
    print(json.dumps({key: value for key, value in report.items() if key != "scenario_results"}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
