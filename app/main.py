"""Africa's Talking Voice callback app for Looyawange / Wakilibot IVR.

Quality bar: fast callback XML, robust STT/TTS, same agent knowledge as web.
Language select is the first gate on every new call.
"""

from __future__ import annotations

import json
import logging
import re
from contextlib import asynccontextmanager
from typing import Optional

from fastapi import FastAPI, Form, Request
from fastapi.responses import Response
from fastapi.staticfiles import StaticFiles

from app import agent_client, agent_ready, at_voice, languages, menu, sessions
from app.config import ROOT, settings

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("looyawange-ivr")


@asynccontextmanager
async def lifespan(_app: FastAPI):
    # Warm shared HTTP pool; pre-cache language picker + default menu via agent TTS.
    cfg = settings()
    logger.info(
        "IVR starting agent=%s public=%s (knowledge+ASR+TTS = wakilibot-agent)",
        cfg["agent_url"],
        cfg["public_base"],
    )
    agent_client.get_client()
    default_lang = cfg["default_language"]
    # Require wakilibot-agent GET /health == 200 before TTS pre-cache.
    ready = await agent_ready.wait_for_agent_http_200(attempts=5, delay_sec=4.0)
    if not ready.get("http_200"):
        logger.warning(
            "Wakilibot-agent not HTTP 200 at %s (last=%s) — TTS pre-cache skipped; "
            "IVR stays up and will retry on /health/agent",
            cfg["agent_url"],
            ready,
        )
    else:
        try:
            await agent_client.synthesize_to_file(
                languages.spoken_language_prompt(),
                language=default_lang,
                cacheable=True,
            )
            await agent_client.synthesize_to_file(
                menu.spoken_menu_script(default_lang),
                language=default_lang,
                cacheable=True,
            )
        except Exception:
            logger.warning("TTS pre-cache skipped after agent 200 (TTS endpoint issue)")
    yield
    await agent_client.close_client()


app = FastAPI(title="Looyawange IVR", version="0.3.3", lifespan=lifespan)
app.mount("/static", StaticFiles(directory=str(ROOT / "static")), name="static")


def xml_response(body: str) -> Response:
    return Response(content=body, media_type="application/xml")


def _digits(raw: Optional[str]) -> str:
    return re.sub(r"\D", "", raw or "")


def _user_id(caller: str) -> str:
    return f"ivr:{caller or 'unknown'}"


def _session_language(state: dict) -> str:
    if sessions.has_language(state):
        return languages.normalize_language(state.get("language"))
    return languages.normalize_language(settings()["default_language"])


async def _prompt_audio(text: str, language: str, *, cacheable: bool = False):
    """Prefer cached/agent TTS; fall back to AT <Say> for reliability."""
    _, play_url = await agent_client.synthesize_to_file(
        text, language=language, cacheable=cacheable
    )
    if play_url:
        return at_voice.play(play_url)
    return at_voice.say(text)


async def _language_select_xml(callback: str) -> str:
    """First-ring language picker (DTMF 1–6). Spoken in English names + native cues."""
    prompt = await _prompt_audio(
        languages.spoken_language_prompt(),
        languages.DEFAULT_LANGUAGE,
        cacheable=True,
    )
    gather = at_voice.get_digits(
        num_digits=1,
        timeout=15,
        finish_on_key="#",
        callback_url=callback,
        prompt=prompt,
    )
    return at_voice.build_response([gather])


async def _welcome_xml(callback: str, language: str) -> str:
    prompt = await _prompt_audio(
        menu.spoken_menu_script(language), language, cacheable=True
    )
    gather = at_voice.get_digits(
        num_digits=1,
        timeout=12,
        finish_on_key="#",
        callback_url=callback,
        prompt=prompt,
    )
    return at_voice.build_response([gather])


async def _record_xml(prompt_text: str, callback: str, language: str) -> str:
    prompt = await _prompt_audio(prompt_text, language, cacheable=False)
    rec = at_voice.record(
        max_length=45,
        timeout=8,
        finish_on_key="#",
        play_beep=True,
        callback_url=callback,
        prompt=prompt,
    )
    return at_voice.build_response([rec])


async def _speak_reply(text: str, language: str, then_menu: bool = False) -> str:
    """Speak agent knowledge reply via TTS; fall back to AT <Say>."""
    clean = re.sub(r"[*_#`]+", "", text or "").strip()
    if len(clean) > 450:
        clean = clean[:447] + "..."

    actions = [
        await _prompt_audio(
            clean or "Sorry, I could not generate a reply.", language
        )
    ]

    if then_menu:
        cfg = settings()
        callback = f"{cfg['public_base']}/ivr/voice"
        follow = await _prompt_audio(
            languages.after_reply_prompt(language),
            language,
            cacheable=True,
        )
        actions.append(
            at_voice.get_digits(
                num_digits=1,
                timeout=12,
                callback_url=callback,
                prompt=follow,
            )
        )
    return at_voice.build_response(actions)


async def _apply_language_choice(
    sid: str, caller: str, digit: str, callback: str
) -> Optional[str]:
    """Handle DTMF on the language step. Returns XML or None if digit invalid."""
    code = languages.code_for_digit(digit)
    if not code:
        bad = await _prompt_audio(
            languages.spoken_invalid_language(),
            languages.DEFAULT_LANGUAGE,
            cacheable=True,
        )
        gather = at_voice.get_digits(
            num_digits=1,
            timeout=15,
            finish_on_key="#",
            callback_url=callback,
            prompt=bad,
        )
        return at_voice.build_response([gather])

    sessions.update_session(sid, caller, language=code, step="menu", intent=None)
    confirm = await _prompt_audio(
        languages.language_confirmed_prompt(code),
        code,
        cacheable=True,
    )
    menu_prompt = await _prompt_audio(
        menu.spoken_menu_script(code), code, cacheable=True
    )
    return at_voice.build_response(
        [
            confirm,
            at_voice.get_digits(
                num_digits=1,
                timeout=12,
                finish_on_key="#",
                callback_url=callback,
                prompt=menu_prompt,
            ),
        ]
    )


@app.api_route("/", methods=["GET", "HEAD"])
@app.api_route("/health", methods=["GET", "HEAD"])
async def health():
    """IVR liveness for Render. Includes last agent 200-check (cached)."""
    cfg = settings()
    agent = await agent_client.agent_health()
    last = agent_ready.last_check()
    # IVR itself is live even if agent is cold/rate-limited — do not fail Render probes.
    return {
        "status": "ok",
        "service": "looyawange-ivr",
        "agent_http_200": bool(agent.get("http_200")),
        "agent_status": (
            "ok"
            if agent.get("http_200")
            else ("rate_limited" if agent.get("rate_limited") else "degraded")
        ),
        "at_env": cfg["at_env"],
        "agent_url": cfg["agent_url"],
        "agent": agent,
        "agent_last_check": last,
        "knowledge_source": "wakilibot-agent (/agents/conversations — same LLM + legal knowledge as web)",
        "asr": "wakilibot-agent /transcribe",
        "tts": "wakilibot-agent /tts",
        "public_base": cfg["public_base"],
        "voice_number_configured": bool(cfg["at_voice_number"]),
        "default_language": cfg["default_language"],
        "languages": [
            {"digit": L["digit"], "code": L["code"], "name": L["name"]}
            for L in languages.IVR_LANGUAGES
        ],
        "menu": [
            {"key": m["key"], "intent": m["intent"], "label": m["label"]}
            for m in menu.IVR_MENU
        ],
    }


@app.get("/health/agent")
async def health_agent():
    """Live check: wakilibot-agent /health must return HTTP 200.

    Response status:
      - 200 if agent health is 200
      - 503 otherwise (429, 5xx, timeout, connect error)
    """
    result = await agent_ready.check_wakilibot_agent()
    # Refresh cached probe used by /health (may still be 429).
    await agent_client.agent_health(force=True)
    status = 200 if result.get("http_200") else 503
    return Response(
        content=json.dumps(result),
        status_code=status,
        media_type="application/json",
    )


@app.post("/ivr/voice")
async def voice_callback(
    request: Request,
    isActive: str = Form(default="1"),
    sessionId: str = Form(default=""),
    callerNumber: str = Form(default=""),
    destinationNumber: str = Form(default=""),
    dtmfDigits: str = Form(default=""),
    recordingUrl: str = Form(default=""),
    direction: str = Form(default=""),
    durationInSeconds: str = Form(default=""),
):
    """Africa's Talking Voice notification callback."""
    cfg = settings()
    callback = f"{cfg['public_base']}/ivr/voice"
    caller = callerNumber or "unknown"
    sid = sessionId or "nosession"
    digit = _digits(dtmfDigits)

    logger.info(
        "IVR hit active=%s session=%s caller=%s digit=%r recording=%s",
        isActive,
        sid,
        caller,
        digit,
        bool(recordingUrl),
    )

    # Call ended
    if str(isActive) == "0":
        state = sessions.get_session(sid, caller)
        lang = _session_language(state)
        sessions.clear_session(sid, caller)
        return xml_response(
            at_voice.build_response([at_voice.say(languages.goodbye_prompt(lang))])
        )

    state = sessions.get_session(sid, caller)
    needs_language = (
        state.get("step") == "language" or not sessions.has_language(state)
    )

    # --- Language gate (before menu / collect) ---
    if needs_language and not recordingUrl:
        if not digit:
            sessions.update_session(sid, caller, step="language", language=None)
            return xml_response(await _language_select_xml(callback))

        xml = await _apply_language_choice(sid, caller, digit, callback)
        return xml_response(xml)

    language = _session_language(state)

    # Recording finished → STT → agent → TTS (uses chosen language)
    if recordingUrl:
        try:
            audio = await agent_client.download_url(recordingUrl)
            transcript = await agent_client.transcribe_bytes(audio, language=language)
            if not transcript:
                return xml_response(
                    await _record_xml(
                        languages.retry_listen_prompt(language),
                        callback,
                        language,
                    )
                )

            intent = state.get("intent") or "auto"
            result = await agent_client.chat(
                user_id=_user_id(caller),
                query=transcript,
                conversation_id=state.get("conversation_id"),
                intent=None if intent == "auto" else intent,
                language=language,
            )
            reply = (
                result.get("message")
                or result.get("response")
                or "Thank you. We have recorded your request."
            )
            conv_id = result.get("conversation_id") or state.get("conversation_id")
            sessions.update_session(sid, caller, conversation_id=conv_id, step="collect")
            return xml_response(await _speak_reply(reply, language, then_menu=True))
        except Exception:
            logger.exception("IVR recording handling failed")
            return xml_response(
                at_voice.build_response(
                    [
                        at_voice.say(
                            "Sorry, something went wrong processing your voice. "
                            "Please try again later."
                        )
                    ]
                )
            )

    # Change language mid-call
    if digit == menu.CHANGE_LANGUAGE_KEY:
        sessions.update_session(
            sid, caller, step="language", language=None, intent=None
        )
        return xml_response(await _language_select_xml(callback))

    # First ring after language / empty digits → menu
    if not digit:
        sessions.update_session(sid, caller, step="menu", intent=None)
        return xml_response(await _welcome_xml(callback, language))

    if digit == menu.REPEAT_KEY:
        sessions.update_session(sid, caller, step="menu", intent=None)
        return xml_response(await _welcome_xml(callback, language))

    # Free speech
    if digit == menu.FREE_SPEECH_KEY:
        sessions.update_session(sid, caller, intent="auto", step="collect")
        return xml_response(
            await _record_xml(
                languages.free_speech_prompt(language),
                callback,
                language,
            )
        )

    item = menu.menu_by_key(digit)
    if item:
        sessions.update_session(sid, caller, intent=item["intent"], step="collect")
        try:
            seed = f"I want to {item['label'].lower()}"
            result = await agent_client.chat(
                user_id=_user_id(caller),
                query=seed,
                conversation_id=state.get("conversation_id"),
                intent=item["intent"],
                language=language,
            )
            conv_id = result.get("conversation_id")
            if conv_id:
                sessions.update_session(sid, caller, conversation_id=conv_id)
            agent_prompt = result.get("message") or item["prompt"]
        except Exception:
            logger.exception("IVR menu seed chat failed")
            agent_prompt = item["prompt"]

        return xml_response(await _record_xml(agent_prompt, callback, language))

    # Invalid key — still try TTS menu, fall back inside helper
    bad = await _prompt_audio(
        languages.invalid_option_prompt(language), language, cacheable=True
    )
    menu_prompt = await _prompt_audio(
        menu.spoken_menu_script(language), language, cacheable=True
    )
    return xml_response(
        at_voice.build_response(
            [
                bad,
                at_voice.get_digits(
                    num_digits=1,
                    timeout=12,
                    callback_url=callback,
                    prompt=menu_prompt,
                ),
            ]
        )
    )


@app.post("/ivr/events")
async def voice_events(request: Request):
    """Optional AT voice events webhook — acknowledge only."""
    form = await request.form()
    logger.info("IVR event: %s", dict(form))
    return {"ok": True}
