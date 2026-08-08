# PikaTrap Safe Synthetic Evaluation

This folder contains a deterministic regression evaluation for the defender-owned NovaPay lab. It is intentionally limited to fictional attack sequences and does not execute network scans, credential use, or actions against external systems.

## What is measured

- Final intent agreement with a reviewed scenario label
- Terminal-event MITRE mapping agreement with a reviewed scenario label
- SWEEP / SEEK / CONTAIN placement agreement
- Containment accuracy, recall, and false-positive rate
- Detection latency measured as number of events until the expected intent first appears
- Decoy engagement rate from labelled simulated scenarios
- Real assets reached: always `0%` by design

Synthetic scenarios do not model real elapsed attacker dwell time, so that metric is reported as `N/A`. These results are regression metrics for the current deterministic policy, not a claim of production attack-detection accuracy.

## Run

From the `backend` directory, after installing `requirements.txt`:

```powershell
python evaluation/run_evaluation.py
```

The command runs 24 scenarios from `scenarios.json` in an isolated in-memory SQLite database. It writes JSON and Markdown reports into `evaluation/results/`, which is excluded from Git.

## Adding a scenario

Add one JSON object to `scenarios.json` with:

- `id`
- `actions`
- `expected_intent`
- `expected_mitre`
- `expected_placement`
- `expected_containment`
- `engaged`

Run the harness after changing a rule or mapping. A changed metric is a signal to review the deterministic policy or the reviewed scenario label.
