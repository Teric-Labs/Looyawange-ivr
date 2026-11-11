"""In-memory IVR session store (swap for Redis later if needed)."""

from __future__ import annotations

from threading import Lock
from typing import Any, Dict, Optional

_LOCK = Lock()
_SESSIONS: Dict[str, Dict[str, Any]] = {}


def session_key(session_id: str, caller: str) -> str:
    return f"{session_id}:{caller}"


def _blank(session_id: str, caller: str) -> Dict[str, Any]:
    return {
        "session_id": session_id,
        "caller": caller,
        "intent": None,
        "conversation_id": None,
        "step": "language",  # language select before main menu
        "language": None,
    }


def get_session(session_id: str, caller: str) -> Dict[str, Any]:
    key = session_key(session_id, caller)
    with _LOCK:
        if key not in _SESSIONS:
            _SESSIONS[key] = _blank(session_id, caller)
        return dict(_SESSIONS[key])


def update_session(session_id: str, caller: str, **fields: Any) -> Dict[str, Any]:
    key = session_key(session_id, caller)
    with _LOCK:
        current = _SESSIONS.get(key) or _blank(session_id, caller)
        for k, v in fields.items():
            # Allow explicit None for language reset; skip only missing kwargs.
            current[k] = v
        _SESSIONS[key] = current
        return dict(current)


def clear_session(session_id: str, caller: str) -> None:
    key = session_key(session_id, caller)
    with _LOCK:
        _SESSIONS.pop(key, None)


def clear_all_sessions() -> None:
    """Test helper — wipe in-memory store."""
    with _LOCK:
        _SESSIONS.clear()


def has_language(session: Dict[str, Any]) -> bool:
    return bool(session.get("language"))
