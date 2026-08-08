# PikaTrap

> **Adaptive deception. Intelligent defense.**

PikaTrap is a working cyber-deception platform built by **Team Pikachu** for the Neurobots National Level Hackathon 2026.

It creates a safe, defender-owned environment where fictional attackers interact with realistic decoys such as fake credentials, customer exports, source-code secrets, cloud-storage routes, and services. PikaTrap collects those interactions as telemetry, analyzes the observed behavior, maps it to MITRE ATT&CK, calculates risk per action, adaptively chooses the next deception response, and produces an incident report.

> **Safety first:** PikaTrap is a controlled simulation. It does not scan, access, modify, or attack any external or real-world system. All credentials, files, identities, and services used in the demo are fictional.

---

## Team

| Item | Details |
|---|---|
| Team name | Team Pikachu |
| Members | Abellash, Antony |
| Domain | Defensive Cybersecurity |
| College | Sahrdaya College |
| Project | PikaTrap — Adaptive Deception Intelligence Platform |

---

## Problem statement

Security teams often discover credential theft, data collection, source-code discovery, or cloud reconnaissance only after an attacker reaches valuable assets.

Traditional alerts can also be noisy: one event alone does not explain what an attacker is trying to achieve.

PikaTrap addresses this problem by using safe decoys to observe attacker-like behavior early and convert the interaction sequence into understandable evidence:

- What was accessed?
- What is the likely attacker intent?
- Which MITRE ATT&CK technique matches the behavior?
- How risky is this specific action?
- Should the defender observe, deploy another decoy, or contain the session?

---

## Proposed solution

PikaTrap is a defender-owned adaptive deception platform.

Instead of exposing real assets, it uses realistic fictional decoys inside the NovaPay target lab. When a user chooses simulated attacker actions, PikaTrap records telemetry and adapts its next decision based on the observed path.

### Core flow

```mermaid
flowchart LR
    A[Defender-owned NovaPay target lab] --> B[Honeytoken interaction]
    B --> C[Telemetry collector]
    C --> D[Behavior and intent analysis]
    D --> E[Risk score + MITRE ATT&CK mapping]
    E --> F[Adaptive Decoy Policy Engine]

    F --> G[SWEEP: multiple safe decoys]
    F --> H[SEEK: targeted safe decoy]
    F --> I[CONTAIN: simulated quarantine]

    G --> J[Live dashboard and deception graph]
    H --> J
    I --> J

    J --> K[Session history and incident report]
