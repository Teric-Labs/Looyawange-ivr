"""HTTP client to Wakilibot-agent (dialogue, STT, TTS).

Single shared AsyncClient for connection reuse — IVR call paths must stay
fast and reliable under Africa's Talking callback timeouts.
"""

from __future__ import annotations

import hashlib
import logging
import time
import uuid
from pathlib import Path
from typing import Any, Dict, Optional, Tuple

import httpx

from app.config import settings

logger = logging.getLogger(__name__)

# Tight budgets: AT Voice expects an XML reply promptly.
_TIMEOUT_CHAT = httpx.Timeout(25.0, connect=5.0)
_TIMEOUT_STT = httpx.Timeout(35.0, connect=5.0)
_TIMEOUT_TTS = httpx.Timeout(35.0, connect=5.0)
_TIMEOUT_DOWNLOAD = httpx.Timeout(20.0, connect=5.0)

# Avoid hammering agent /health from Render probes (was causing 429 storms).
_HEALTH_TTL_SEC = 90.0
_health_cache_at: float = 0.0
_health_cache: Optional[Dict[str, Any]] = None

_client: Optional[httpx.AsyncClient] = None


def get_client() -> httpx.AsyncClient:
    global _client
    if _client is None or _client.is_closed:
        _client = httpx.AsyncClient(
            limits=httpx.Limits(max_connections=40, max_keepalive_connections=20),
            follow_redirects=True,
        )
    return _client


async def close_client() -> None:
    global _client
    if _client is not None and not _client.is_closed:
        await _client.aclose()
    _client = None


async def chat(
    *,
    user_id: str,
    query: str,
    conversation_id: Optional[str] = None,
    intent: Optional[str] = None,
    language: str = "en",
) -> Dict[str, Any]:
    """Same knowledge path as web: agent LLM + legal retrieval + flows."""
    cfg = settings()
    data = {
        "query": query,
        "user_id": user_id,
        "language": language,
    }
    if conversation_id:
        data["conversation_id"] = conversation_id
    if intent and intent != "auto":
        data["intent"] = intent

    url = f"{cfg['agent_url']}/agents/conversations"
    last_err: Optional[Exception] = None
    for attempt in range(2):
        try:
            resp = await get_client().post(url, data=data, timeout=_TIMEOUT_CHAT)
            resp.raise_for_status()
            return resp.json()
        except Exception as exc:
            last_err = exc
            logger.warning("agent chat attempt %s failed: %s", attempt + 1, exc)
    raise RuntimeError(f"agent chat failed: {last_err}")


async def transcribe_bytes(audio: bytes, filename: str = "call.mp3", language: str = "en") -> str:
    """ASR/STT via the same agent endpoint the web voice UI uses."""
    cfg = settings()
    url = f"{cfg['agent_url']}/transcribe"
    files = {"audio_file": (filename, audio, "audio/mpeg")}
    data = {"language": language}
    last_err: Optional[Exception] = None
    for attempt in range(2):
        try:
            resp = await get_client().post(url, data=data, files=files, timeout=_TIMEOUT_STT)
            resp.raise_for_status()
            payload = resp.json()
            return (payload.get("text") or "").strip()
        except Exception as exc:
            last_err = exc
            logger.warning("STT attempt %s failed: %s", attempt + 1, exc)
    raise RuntimeError(f"STT failed: {last_err}")


async def synthesize_to_file(
    text: str,
    language: str = "en",
    *,
    cacheable: bool = False,
) -> Tuple[Optional[Path], Optional[str]]:
    """TTS via agent /tts. Static prompts can be cacheable for speed."""
    cfg = settings()
    url = f"{cfg['agent_url']}/tts"
    clipped = text[:4000]
    audio_dir: Path = cfg["audio_dir"]
    audio_dir.mkdir(parents=True, exist_ok=True)

    if cacheable:
        digest = hashlib.sha256(f"{language}:{clipped}".encode("utf-8")).hexdigest()[:24]
        name = f"cache_{digest}.wav"
    else:
        name = f"{uuid.uuid4().hex}.wav"
    path = audio_dir / name
    public = f"{cfg['public_base']}/static/audio/{name}"

    if cacheable and path.exists() and path.stat().st_size > 0:
        return path, public

    data = {"text": clipped, "language": language}
    try:
        resp = await get_client().post(url, data=data, timeout=_TIMEOUT_TTS)
        resp.raise_for_status()
        path.write_bytes(resp.content)
        return path, public
    except Exception as exc:
        # Connect/timeouts are expected when agent is cold — fall back to AT <Say>.
        logger.warning(
            "TTS unavailable at %s (%s). Falling back to <Say>.",
            url,
            exc.__class__.__name__,
        )
        if path.exists() and not cacheable:
            path.unlink(missing_ok=True)
        return None, None


async def download_url(url: str) -> bytes:
    resp = await get_client().get(url, timeout=_TIMEOUT_DOWNLOAD)
    resp.raise_for_status()
    return resp.content


async def agent_health(*, force: bool = False) -> Dict[str, Any]:
    """Probe wakilibot-agent. Cached so IVR /health probes do not 429 the agent."""
    global _health_cache_at, _health_cache
    now = time.monotonic()
    if (
        not force
        and _health_cache is not None
        and (now - _health_cache_at) < _HEALTH_TTL_SEC
    ):
        return dict(_health_cache)

    cfg = settings()
    try:
        resp = await get_client().get(
            f"{cfg['agent_url']}/health",
            timeout=httpx.Timeout(8.0, connect=3.0),
        )
        code = resp.status_code
        if code == 200:
            result = {
                "ok": True,
                "http_200": True,
                "status_code": 200,
                "rate_limited": False,
            }
        elif code == 429:
            result = {
                "ok": False,
                "http_200": False,
                "status_code": 429,
                "rate_limited": True,
                "note": "Agent rate-limited health checks; not HTTP 200",
            }
        else:
            result = {
                "ok": False,
                "http_200": False,
                "status_code": code,
                "rate_limited": False,
            }
    except Exception as exc:
        result = {"ok": False, "http_200": False, "error": str(exc)}

    _health_cache = result
    _health_cache_at = now
    return dict(result)
