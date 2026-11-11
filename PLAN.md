# Looyawange IVR Plan (Africa’s Talking Voice)

**Goal:** A **fast, world-class, robust, reliable** phone channel for CTDR-U. Callers use the same activity menu as Wakilibot web, speak naturally (ASR/STT), and hear answers grounded in the **same agent / LLM / legal knowledge** as the web platform (TTS out).

**Principle:** IVR is a thin, hardened adapter. **All information spoken to the caller comes from Wakilibot-agent** — the same `/agents/conversations` pipeline the web uses (flows, LLM phrasing, legal knowledge retrieval, case filing). STT/TTS reuse agent `/transcribe` and `/tts`. Do not fork knowledge or complaint logic inside IVR.

**Stack:** Python + FastAPI (matches agent/USSD/SMS). Reliability comes from shared HTTP pools, timeouts, retries, TTS caching for static prompts, and graceful `<Say>` fallbacks — not from rewriting in Rust for v1.

---

## Quality bar (world-class IVR)

| Pillar | How we hit it |
|--------|----------------|
| **Fast** | Persistent `httpx` connection pool; tight timeouts; pre-cache menu TTS at startup; short spoken replies (~450 chars) |
| **Correct knowledge** | Every substantive answer = agent chat (same LLM + knowledge as web). IVR never invents legal content |
| **Robust ASR/TTS** | Agent Ateker STT + Spark TTS; one retry; if TTS fails → Africa’s Talking `<Say>` so the call continues |
| **Reliable calls** | Clear DTMF menu; re-prompt on empty transcript; safe goodbye on hangup; health checks agent dependency |
| **Same product** | Menu keys map 1:1 to web `CHAT_INTENTS` / `GET /intents` |

---

## 1. Architecture

```
Caller phone
    │
    ▼
Africa’s Talking Voice gateway
    │  POST form fields (sessionId, callerNumber, dtmfDigits, recordingUrl, …)
    ▼
Looyawange-ivr  (this service)
    │  XML: <Say> / <GetDigits> / <Record> / <Play>
    ├─► Wakilibot-agent  POST /agents/conversations   (text dialogue)
    ├─► Wakilibot-agent  POST /transcribe             (ASR / STT)
    └─► Wakilibot-agent  POST /tts                    (TTS WAV → public <Play> URL)
```

| Layer | Responsibility |
|--------|----------------|
| Africa’s Talking | Inbound/outbound voice, DTMF, Record → `recordingUrl` |
| Looyawange-ivr | AT Voice XML callbacks, menu, session glue, audio fetch/host |
| Wakilibot-agent | Intent/flows, legal knowledge, case filing, STT, TTS |
| Case Backend | Complaints/incidents (unchanged) |

---

## 2. Web menu → IVR mapping

Source of truth: `Wakilibot-agent/utils/intent_catalog.py` → `CHAT_INTENTS` / `GET /intents`.

| Key | Activity (web label) | Intent id |
|-----|----------------------|-----------|
| 1 | File a complaint | `submit_complaint` |
| 2 | Report fraud | `fraud_alert` |
| 3 | Check complaint status | `check_status` |
| 4 | Know my rights | `consumer_rights` |
| 5 | Ask about CTDRU | `general_inquiry` |
| 0 | Speak freely (record → STT) | `auto` |
| 9 | Repeat menu | — |
| * | Hang up / goodbye | — |

Phase 1 uses **DTMF** for menu + short answers. Phase 2 adds **Record → STT** for free speech after menu choice (or option 0).

---

## 3. Africa’s Talking Voice contract

Docs: [Handle calls](https://developers.africastalking.com/docs/voice/handle_calls), [Record](https://developers.africastalking.com/docs/voice/actions/record).

1. Caller dials AT voice number (sandbox virtual number first).
2. AT POSTs to our callback (e.g. `https://<host>/ivr/voice`).
3. We respond with XML (`Content-Type: application/xml`):
   - `<Say>` — AT English TTS (fallback)
   - `<Play url="…">` — our TTS WAV (preferred for Luganda etc.)
   - `<GetDigits>` — menu / numeric input → next POST includes `dtmfDigits`
   - `<Record>` — utterance → later POST includes `recordingUrl`
4. Final POST has `isActive=0` (hangup / billing fields).

**Sandbox setup**
- Username: `sandbox`
- API key: same AT app key used for USSD/SMS (`AT_API_KEY`)
- Create / assign a **Voice** number in AT sandbox
- Callback URL: `https://<public-host>/ivr/voice`
- Optional events URL: `https://<public-host>/ivr/events`

**Live setup (later)**
- Provision Uganda/live voice number via AT
- Point callback to production IVR host
- Swap `AT_ENV=production` credentials

---

## 4. Speech + knowledge path (ASR / STT → Agent → TTS)

**Single source of truth for what the bot says:** Wakilibot-agent (web’s brain).

```
Caller speech
  → AT Record → recordingUrl
  → IVR download
  → AGENT /transcribe          (ASR — same as web voice)
  → AGENT /agents/conversations (LLM + knowledge + flows — same as web chat)
  → AGENT /tts                 (TTS — same Spark path as web)
  → IVR hosts WAV → AT <Play>
  → fallback AT <Say> if TTS down
```

### Inbound speech
1. IVR returns `<Record maxLength="45" playBeep="true" finishOnKey="#" …>`.
2. AT POSTs `recordingUrl` (mp3).
3. IVR downloads audio → `POST {AGENT}/transcribe` (Ateker ASR used by web voice).
4. Transcript + session `intent` → `POST {AGENT}/agents/conversations` (**knowledge / LLM**).
5. Truncate agent reply for speech (~450 chars) so turns stay snappy on the phone.

### Outbound speech
1. Prefer `POST {AGENT}/tts` → host WAV under `/static/audio/…` (public HTTPS).
2. Static prompts (main menu, “press 9…”) are **cacheable** for speed.
3. Respond with `<Play url="…"/>`.
4. Fallback: `<Say>` if TTS fails so the call never dead-airs.

---

## 5. Session model

Key by `sessionId` (AT) and `callerNumber`:

```text
ivr:{callerNumber}
  intent: submit_complaint | … | auto | null
  conversation_id: uuid
  step: menu | collect | done
  language: en | lg | …
```

Same agent user id pattern as USSD/SMS: `ivr:+256…` so flows survive across turns.

---

## 6. Phased work

### Phase A — Scaffold (this folder) ✅
- [x] Folder `Looyawange-ivr`
- [x] PLAN + README + env example
- [x] FastAPI `/ivr/voice` XML menu (web activities)
- [x] DTMF routing to intent ids
- [x] Client stubs to agent `/agents/conversations`, `/transcribe`, `/tts`

### Phase B — Sandbox voice
- [ ] AT Voice number + callback to public URL (ngrok or Render)
- [ ] Dial simulator / sandbox number; walk DTMF menu
- [ ] Wire one full complaint DTMF path through agent
- [ ] Log sessions for dashboard channel attribution (`IVR`)

### Phase C — STT / TTS on calls
- [ ] `<Record>` after menu choice or option 0
- [ ] Download `recordingUrl` → agent `/transcribe`
- [ ] Agent reply → `/tts` → `<Play>`
- [x] Language selection first (DTMF 1–6: en/sw/lg/nyn/at/ac); press 8 to change

### Phase D — Production
- [ ] Live AT voice number
- [ ] Auth / IP allowlist on callbacks
- [ ] Always-on host (AT call timeouts are short)
- [ ] Ops runbook + dashboard IVR metrics

---

## 7. Env vars

| Variable | Purpose |
|----------|---------|
| `AT_USERNAME` | `sandbox` or live username |
| `AT_API_KEY` | Africa’s Talking API key |
| `AT_ENV` | `sandbox` \| `production` |
| `AT_VOICE_NUMBER` | AT voice number (+…) |
| `IVR_PUBLIC_BASE_URL` | Public HTTPS base for callbacks + `<Play>` URLs |
| `WAKILIBOT_AGENT_URL` | e.g. `https://wakilibot-agent-0wm0.onrender.com` |
| `IVR_DEFAULT_LANGUAGE` | `en` default |

Reuse the same sandbox API key already used for USSD/SMS in `Wakilibot-agent/.env` (do not commit secrets).

---

## 8. Non-goals (for this adapter)
- No duplicate complaint extraction logic in IVR
- No replacing web/USSD/SMS
- No building a new case store — Case Backend only via agent

---

## 9. Success criteria
1. Caller hears the same five activities as the web topic menu.
2. Choosing 1–5 starts the matching agent intent/flow.
3. Option 0 (or post-menu record) uses STT → agent → TTS.
4. Filed cases appear on CTDRU Dashboard like web/USSD.
5. Web `/agents/conversations` contract unchanged.
