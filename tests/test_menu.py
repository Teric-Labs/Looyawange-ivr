from app.languages import CHANGE_LANGUAGE_KEY
from app.menu import (
    IVR_MENU,
    FREE_SPEECH_KEY,
    REPEAT_KEY,
    intent_for_digit,
    menu_by_key,
    spoken_menu_script,
)


def test_menu_covers_web_activity_intents():
    intents = {item["intent"] for item in IVR_MENU}
    assert intents == {
        "submit_complaint",
        "fraud_alert",
        "check_status",
        "consumer_rights",
        "general_inquiry",
    }


def test_digit_routing():
    assert intent_for_digit("1") == "submit_complaint"
    assert intent_for_digit("0") == "auto"
    assert intent_for_digit("8") is None
    assert menu_by_key("2")["label"] == "Report fraud"


def test_control_keys_do_not_collide_with_menu():
    menu_keys = {item["key"] for item in IVR_MENU}
    assert FREE_SPEECH_KEY not in menu_keys
    assert REPEAT_KEY not in menu_keys
    assert CHANGE_LANGUAGE_KEY not in menu_keys
    assert CHANGE_LANGUAGE_KEY == "8"


def test_spoken_menu_mentions_keys():
    script = spoken_menu_script("en")
    for key in ("1", "2", "3", "4", "5", "0", "9", "8"):
        assert key in script


def test_spoken_menu_accepts_language():
    assert "Karibu" in spoken_menu_script("sw")
    assert "Nyiga" in spoken_menu_script("lg") or "nyiga" in spoken_menu_script("lg")
