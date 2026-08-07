# PikaTrap

Adaptive deception. Intelligent defense. PikaTrap is a safe, local-first hackathon prototype for Team Pikachu. It uses intelligent honeytokens, adaptive deception, attacker behavior analysis, threat intelligence, and automated containment.

## Hackathon project

Built for the **Autonomous Deception Intelligence Platform Using Honeytokens & Active Defense** challenge.

### Team

- Abellash
- Antony

## Working vertical slice

`deception/fake_source/payment-service/.env.production` is a deliberately fake, non-functional honeytoken. The demo canary reports access to the API, where PikaTrap persists the event, scores it, infers intent from the event sequence, maps ATT&CK, selects an allowed action, and broadcasts it to the dashboard over WebSocket.

No real credentials, cloud infrastructure, external scanning, or counter-hacking are included.

## Run with Docker

```bash
copy .env.example .env
docker compose up --build
```

Open `http://localhost:5173`, then choose **Open NovaPay target lab**. API health is at `http://localhost:8000/health`.

For the richer safe demo, use the linked NovaPay lab. Choose Engineering (fake `.env.production` -> fake cloud console -> storage bucket -> fictional customer export), Finance (forecast/payroll decoys), or Source Control (fake deployment key -> local authentication decoy). Each local interaction sends a different standardized telemetry event to PikaTrap. This is defender-owned simulation only; it does not interact with external websites.

## Run backend locally

```bash
cd backend
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
uvicorn app.main:app --reload
```

The local backend defaults to `backend/data/pikatrap.db`. Trigger the safe canary with:

```bash
python deception/scripts/trigger_env_canary.py
```

## Endpoints

- `GET /health`
- `POST /api/v1/telemetry` - standardized event ingestion
- `POST /api/v1/demo/trigger` - safe first-honeytoken demo
- `GET /api/v1/events`
- `GET /api/v1/incidents`
- `GET /api/v1/reports/{session_id}.html`
- `WS /ws/events`

See [architecture](docs/architecture.md), [API notes](docs/api.md), and the [repeatable demo](docs/demo-scenario.md).
