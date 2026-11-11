# Looyawange IVR — Work board

Track implementation against [PLAN.md](./PLAN.md).

## Now (Phase A — done in repo)

- [x] Create `Looyawange-ivr` folder
- [x] Write PLAN.md + README.md (world-class / knowledge-via-agent bar)
- [x] Menu aligned to web activities
- [x] FastAPI AT Voice XML callback `/ivr/voice`
- [x] Agent client for chat (knowledge) / STT / TTS with pool, timeouts, retry
- [x] Menu TTS pre-cache + `<Say>` fallback for reliability
- [x] Sandbox AT API key wired via `.env` (gitignored pattern)
- [x] Language select first gate (DTMF 1–6 = en/sw/lg/nyn/at/ac)
- [x] Press 8 to change language mid-call; session stores language for STT/TTS/agent
- [x] Unit tests: languages, sessions, menu, voice language gate

## Next (Phase B — sandbox voice)

- [ ] Create / assign Africa’s Talking **Voice** sandbox number
- [ ] Set callback URL to public `…/ivr/voice` (`IVR_PUBLIC_BASE_URL`)
- [ ] Expose local app with ngrok **or** deploy IVR service
- [ ] Dial and verify DTMF menu 1–5 / 0 / 9
- [ ] Confirm complaint seed turn hits Wakilibot-agent

## Then (Phase C — STT/TTS on air)

- [ ] Record → download `recordingUrl` → `/transcribe` (verify live)
- [ ] Agent reply → `/tts` → public `<Play>` URL
- [ ] Truncation + silence / retry prompts
- [x] Language select (DTMF) using agent language codes (done in Phase A prework)

## Later (Phase D — production)

- [ ] Live AT voice number for Uganda
- [ ] Callback auth / allowlisting
- [ ] Always-on hosting
- [ ] Dashboard “IVR” channel metrics from conversations

## Owners / notes

| Item | Note |
|------|------|
| AT API token | Same sandbox app as USSD/SMS |
| Web menu source | `Wakilibot-agent` `CHAT_INTENTS` / `GET /intents` |
| STT / TTS | Agent `/transcribe` and `/tts` (Ateker / Spark) |
| Do not change | Web `/agents/conversations` contract |
