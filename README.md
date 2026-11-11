# Looyawange IVR

Africa’s Talking **Voice** adapter for CTDR-U Wakilibot — built for **speed, robustness, and reliability**.

Callers get the **same activity menu as the web platform**, then talk or press keys.

| Capability | Source (same as web) |
|------------|----------------------|
| What to say (knowledge / LLM / flows) | Agent `POST /agents/conversations` |
| ASR / STT | Agent `POST /transcribe` |
| TTS | Agent `POST /tts` (with AT `<Say>` fallback) |

IVR does **not** invent answers — it speaks what the agent (web brain) returns.

See **[PLAN.md](./PLAN.md)** for architecture, quality bar, and phases.

## Quick start

```bash
cd Looyawange-ivr
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env   # fill AT_* and WAKILIBOT_AGENT_URL
uvicorn app.main:app --reload --port 8088
```

Health:

- `GET /health` — IVR liveness (always 200 when the service is up)
- `GET /health/agent` — **live** Wakilibot-agent check; **200 only if agent `/health` is 200**, else **503**

## Docker (`bateesa/looyawange-ivr`)

```bash
cd Looyawange-ivr
docker build -t bateesa/looyawange-ivr:latest .
docker run --rm -p 8088:8088 --env-file .env bateesa/looyawange-ivr:latest
```

Push (optional, for registry / Render image deploy):

```bash
docker push bateesa/looyawange-ivr:latest
```

Secrets stay in env / Render dashboard — **do not** bake `.env` into the image.

## Deploy on Render (yes — supported)

Render can run this Dockerfile as a **Web Service**.

1. **New → Web Service** → connect the repo (or use Docker image `bateesa/looyawange-ivr`)
2. Root directory: `Looyawange-ivr` (if monorepo) · Runtime: **Docker**
3. Set env vars (required on Render):

| Variable | Value |
|----------|--------|
| `WAKILIBOT_AGENT_URL` | `https://wakilibot-agent-0wm0.onrender.com` (web knowledge + `/transcribe` + `/tts`) |
| `IVR_PUBLIC_BASE_URL` | `https://looyawange-ivr.onrender.com` |
| `AT_ENV` / `AT_USERNAME` / `AT_API_KEY` | Sandbox first |
| `AT_VOICE_NUMBER` | When you have the Voice number |
| `IVR_DEFAULT_LANGUAGE` | `en` |

If `WAKILIBOT_AGENT_URL` is missing, older images defaulted to `localhost:8000` and TTS pre-cache logged `ConnectError`. Current image defaults to the Render agent URL.

4. Health check path: `/health` (also serves `/`)
5. Point Africa’s Talking Voice callback to: `https://looyawange-ivr.onrender.com/ivr/voice`

Prefer a **Starter** (or always-on) plan for voice — free-tier cold starts are too slow for AT call timeouts. Keep the **agent** service warm too, or STT/TTS fall back / fail until it wakes.

Blueprint file: [`render.yaml`](./render.yaml).

## Africa’s Talking Voice callback

Point the Voice number callback to:

```text
https://<your-public-host>/ivr/voice
```

Local tunnel example:

```bash
ngrok http 8088
# callback = https://xxxx.ngrok.io/ivr/voice
# set IVR_PUBLIC_BASE_URL to that https origin
```

## Local test (no phone)

Unit tests:

```bash
cd Looyawange-ivr && source .venv/bin/activate
pytest tests/ -q
```

Simulate Africa’s Talking callbacks (server must be on `:8088`):

```bash
./scripts/smoke_ivr_local.sh
```

## Language select (first ring)

| Key | Language |
|-----|----------|
| 1 | English |
| 2 | Swahili |
| 3 | Luganda |
| 4 | Runyankole |
| 5 | Ateso |
| 6 | Acholi |
| 8 | Change language (from main menu) |

## Main menu (matches web `GET /intents`)

| Key | Action |
|-----|--------|
| 1 | File a complaint |
| 2 | Report fraud |
| 3 | Check complaint status |
| 4 | Know my rights |
| 5 | Ask about CTDRU |
| 0 | Speak freely (record → STT) |
| 9 | Repeat menu |

## Related services

| Service | Role |
|---------|------|
| `Wakilibot-agent` | Dialogue, STT, TTS |
| `Wakilibot-backend` | Cases (via agent) |
| Existing `POST /ussd`, `POST /sms` | Sibling channel adapters |
