"""IVR language catalog — subset of Wakilibot web / agent codes.

Supported on IVR: en, sw, lg, nyn, at, ac
(English, Swahili, Luganda, Runyankole, Ateso, Acholi).
"""

from __future__ import annotations

from typing import Dict, List, Optional, TypedDict


class LanguageOption(TypedDict):
    digit: str
    code: str
    name: str
    native_name: str


# DTMF 1–6 — order requested for voice: EN, SW, LG, Runyankole, Ateso, Acholi.
IVR_LANGUAGES: List[LanguageOption] = [
    {"digit": "1", "code": "en", "name": "English", "native_name": "English"},
    {"digit": "2", "code": "sw", "name": "Swahili", "native_name": "Kiswahili"},
    {"digit": "3", "code": "lg", "name": "Luganda", "native_name": "Oluganda"},
    {"digit": "4", "code": "nyn", "name": "Runyankole", "native_name": "Orunyankole"},
    {"digit": "5", "code": "at", "name": "Ateso", "native_name": "Ateso"},
    {"digit": "6", "code": "ac", "name": "Acholi", "native_name": "Leb Acholi"},
]

SUPPORTED_CODES = frozenset(item["code"] for item in IVR_LANGUAGES)
DEFAULT_LANGUAGE = "en"
CHANGE_LANGUAGE_KEY = "8"

# Aliases the agent / web also accept (only for supported IVR languages).
_ALIASES: Dict[str, str] = {
    "english": "en",
    "eng": "en",
    "en": "en",
    "swahili": "sw",
    "swa": "sw",
    "sw": "sw",
    "luganda": "lg",
    "lug": "lg",
    "lg": "lg",
    "runyankole": "nyn",
    "runyakore": "nyn",
    "nyn": "nyn",
    "ateso": "at",
    "teo": "at",
    "at": "at",
    "acholi": "ac",
    "ach": "ac",
    "ac": "ac",
}


def normalize_language(code: Optional[str]) -> str:
    """Map aliases to a supported IVR/agent code; unknown → English."""
    if not code:
        return DEFAULT_LANGUAGE
    key = str(code).strip().lower()
    mapped = _ALIASES.get(key, key)
    return mapped if mapped in SUPPORTED_CODES else DEFAULT_LANGUAGE


def language_by_digit(digit: str) -> Optional[LanguageOption]:
    for item in IVR_LANGUAGES:
        if item["digit"] == digit:
            return item
    return None


def code_for_digit(digit: str) -> Optional[str]:
    item = language_by_digit(digit)
    return item["code"] if item else None


def language_by_code(code: str) -> Optional[LanguageOption]:
    normalized = normalize_language(code)
    for item in IVR_LANGUAGES:
        if item["code"] == normalized:
            return item
    return None


def spoken_language_prompt() -> str:
    """First-ring language picker. Each option named so the caller hears their language."""
    lines = [
        "Welcome to CTDRU Wakilibot.",
        "For English, press 1.",
        "Kwa Kiswahili, bonyeza 2.",
        "Oluganda, nyiga 3.",
        "Orunyankole, siba 4.",
        "Iteso, iyai 5.",
        "Pi Leb Acholi, diyo 6.",
    ]
    return " ".join(lines)


def spoken_invalid_language() -> str:
    return "Invalid language option. " + spoken_language_prompt()


# Localized main-menu + common IVR prompts (agent still owns knowledge answers).
_MENU_SCRIPTS: Dict[str, str] = {
    "en": (
        "Welcome to CTDRU Wakilibot. "
        "Press 1 to file a complaint. "
        "Press 2 to report fraud. "
        "Press 3 to check complaint status. "
        "Press 4 to know your rights. "
        "Press 5 to ask about CTDRU. "
        "Press 0 to speak freely. "
        "Press 8 to change language. "
        "Press 9 to hear this menu again."
    ),
    "sw": (
        "Karibu CTDRU Wakilibot. "
        "Bonyeza 1 kuwasilisha malalamiko. "
        "Bonyeza 2 kuripoti udanganyifu. "
        "Bonyeza 3 kuangalia hali ya malalamiko. "
        "Bonyeza 4 kujua haki zako. "
        "Bonyeza 5 kuuliza kuhusu CTDRU. "
        "Bonyeza 0 kuzungumza kwa uhuru. "
        "Bonyeza 8 kubadilisha lugha. "
        "Bonyeza 9 kusikia menyu tena."
    ),
    "lg": (
        "Tukusanyukidde ku CTDRU Wakilibot. "
        "Nyiga 1 okuteeka okwemulugunya. "
        "Nyiga 2 okutegeeza obulimba. "
        "Nyiga 3 okukebera embeera y'okwemulugunya. "
        "Nyiga 4 okumanya eddembe lyo. "
        "Nyiga 5 okubuuza ku CTDRU. "
        "Nyiga 0 okwogera bulungi. "
        "Nyiga 8 okukyusa olulimi. "
        "Nyiga 9 okuwulira menyu nate."
    ),
}

_FREE_SPEECH: Dict[str, str] = {
    "en": "Please tell us how we can help after the beep. Press hash when you are finished.",
    "sw": "Tafadhali tuambie jinsi tunaweza kusaidia baada ya bipi. Bonyeza hash ukimaliza.",
    "lg": "Tukubegireko nga twasobola okuyamba oluvannyuma lw'omulanga. Nyiga hash nga omalirizza.",
}

_AFTER_REPLY: Dict[str, str] = {
    "en": "Press 9 for the main menu, or hang up to end the call.",
    "sw": "Bonyeza 9 kwa menyu kuu, au weka simu kumaliza.",
    "lg": "Nyiga 9 ku menyu enkulu, oba teeka essimu okukomya.",
}

_INVALID_OPTION: Dict[str, str] = {
    "en": "Invalid option.",
    "sw": "Chaguo si sahihi.",
    "lg": "Ekyo tekiri kirungi.",
}

_RETRY_LISTEN: Dict[str, str] = {
    "en": "Sorry, I did not catch that. Please speak again after the beep.",
    "sw": "Samahani, sikukusikia. Tafadhali ongea tena baada ya bipi.",
    "lg": "Tusonyiwe, tetuwulidde. Yogera nate oluvannyuma lw'omulanga.",
}

_GOODBYE: Dict[str, str] = {
    "en": "Thank you for calling CTDRU. Goodbye.",
    "sw": "Asante kwa kupiga CTDRU. Kwaheri.",
    "lg": "Webale okukuba CTDRU. Weraba.",
}

_LANGUAGE_CONFIRMED: Dict[str, str] = {
    "en": "English selected.",
    "sw": "Kiswahili kimechaguliwa.",
    "lg": "Oluganda lulondeddwa.",
    "nyn": "Orunyankole ruhashire.",
    "at": "Ateso eyalai.",
    "ac": "Leb Acholi kiyero.",
}


def _pick(table: Dict[str, str], language: str) -> str:
    code = normalize_language(language)
    return table.get(code) or table[DEFAULT_LANGUAGE]


def spoken_menu_script(language: str = DEFAULT_LANGUAGE) -> str:
    return _pick(_MENU_SCRIPTS, language)


def free_speech_prompt(language: str = DEFAULT_LANGUAGE) -> str:
    return _pick(_FREE_SPEECH, language)


def after_reply_prompt(language: str = DEFAULT_LANGUAGE) -> str:
    return _pick(_AFTER_REPLY, language)


def invalid_option_prompt(language: str = DEFAULT_LANGUAGE) -> str:
    return _pick(_INVALID_OPTION, language)


def retry_listen_prompt(language: str = DEFAULT_LANGUAGE) -> str:
    return _pick(_RETRY_LISTEN, language)


def goodbye_prompt(language: str = DEFAULT_LANGUAGE) -> str:
    return _pick(_GOODBYE, language)


def language_confirmed_prompt(language: str) -> str:
    code = normalize_language(language)
    return _LANGUAGE_CONFIRMED.get(code) or f"{code} selected."
