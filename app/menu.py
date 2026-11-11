"""IVR DTMF menu mirrored from Wakilibot web CHAT_INTENTS.

Keep labels in sync with Wakilibot-agent/utils/intent_catalog.py.
Language-specific spoken prompts live in app.languages.
"""

from __future__ import annotations

from typing import Dict, List, Optional, TypedDict

from app import languages as _languages


class MenuItem(TypedDict):
    key: str
    intent: str
    label: str
    prompt: str


# Same activity set the web topic menu exposes (excluding "Chat freely" as key 0).
IVR_MENU: List[MenuItem] = [
    {
        "key": "1",
        "intent": "submit_complaint",
        "label": "File a complaint",
        "prompt": "Please briefly describe your complaint after the beep. Press hash when done.",
    },
    {
        "key": "2",
        "intent": "fraud_alert",
        "label": "Report fraud",
        "prompt": "Please describe the fraud or scam after the beep. Press hash when done.",
    },
    {
        "key": "3",
        "intent": "check_status",
        "label": "Check complaint status",
        "prompt": "Please say your complaint I D after the beep. Press hash when done.",
    },
    {
        "key": "4",
        "intent": "consumer_rights",
        "label": "Know my rights",
        "prompt": "Please ask your rights question after the beep. Press hash when done.",
    },
    {
        "key": "5",
        "intent": "general_inquiry",
        "label": "Ask about CTDRU",
        "prompt": "Please ask your question about CTDRU after the beep. Press hash when done.",
    },
]

FREE_SPEECH_KEY = "0"
REPEAT_KEY = "9"
CHANGE_LANGUAGE_KEY = _languages.CHANGE_LANGUAGE_KEY


def menu_by_key(key: str) -> Optional[MenuItem]:
    for item in IVR_MENU:
        if item["key"] == key:
            return item
    return None


def spoken_menu_script(language: str = "en") -> str:
    """Localized main-menu prompt for AT <Say> / TTS."""
    return _languages.spoken_menu_script(language)


def intent_for_digit(digit: str) -> Optional[str]:
    if digit == FREE_SPEECH_KEY:
        return "auto"
    item = menu_by_key(digit)
    return item["intent"] if item else None


def prompts_by_intent() -> Dict[str, str]:
    return {item["intent"]: item["prompt"] for item in IVR_MENU}
