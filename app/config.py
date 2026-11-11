"""Environment for Looyawange IVR."""

from __future__ import annotations

import os
from functools import lru_cache
from pathlib import Path

from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parents[1]
load_dotenv(ROOT / ".env")

# Same agent the web uses for knowledge + ASR + TTS (Render).
DEFAULT_AGENT_URL = "https://wakilibot-agent-0wm0.onrender.com"


def _public_base() -> str:
    """Prefer explicit IVR_PUBLIC_BASE_URL; on Render use RENDER_EXTERNAL_URL."""
    explicit = (os.getenv("IVR_PUBLIC_BASE_URL") or "").strip()
    if explicit:
        return explicit.rstrip("/")
    render = (os.getenv("RENDER_EXTERNAL_URL") or "").strip()
    if render:
        return render.rstrip("/")
    return "http://localhost:8088"


@lru_cache(maxsize=1)
def settings() -> dict:
    return {
        "at_env": (os.getenv("AT_ENV") or "sandbox").strip().lower(),
        "at_username": (os.getenv("AT_USERNAME") or "sandbox").strip(),
        "at_api_key": (os.getenv("AT_API_KEY") or "").strip(),
        "at_voice_number": (os.getenv("AT_VOICE_NUMBER") or "").strip(),
        "public_base": _public_base(),
        "agent_url": (
            os.getenv("WAKILIBOT_AGENT_URL") or DEFAULT_AGENT_URL
        ).strip().rstrip("/"),
        "default_language": (os.getenv("IVR_DEFAULT_LANGUAGE") or "en").strip(),
        "audio_dir": ROOT / "static" / "audio",
    }
