from app.languages import (
    CHANGE_LANGUAGE_KEY,
    DEFAULT_LANGUAGE,
    IVR_LANGUAGES,
    SUPPORTED_CODES,
    code_for_digit,
    free_speech_prompt,
    language_by_digit,
    language_confirmed_prompt,
    normalize_language,
    spoken_invalid_language,
    spoken_language_prompt,
    spoken_menu_script,
)


def test_ivr_languages_match_requested_set():
    codes = {item["code"] for item in IVR_LANGUAGES}
    assert codes == {"en", "sw", "lg", "nyn", "at", "ac"}
    assert codes == SUPPORTED_CODES
    assert "xog" not in codes


def test_language_digits_are_unique_one_through_six():
    digits = [item["digit"] for item in IVR_LANGUAGES]
    assert digits == ["1", "2", "3", "4", "5", "6"]
    assert len(set(digits)) == 6


def test_code_for_digit_maps_requested_order():
    assert code_for_digit("1") == "en"
    assert code_for_digit("2") == "sw"
    assert code_for_digit("3") == "lg"
    assert code_for_digit("4") == "nyn"
    assert code_for_digit("5") == "at"
    assert code_for_digit("6") == "ac"
    assert code_for_digit("7") is None
    assert code_for_digit("0") is None


def test_language_by_digit_includes_native_name():
    luganda = language_by_digit("3")
    assert luganda is not None
    assert luganda["name"] == "Luganda"
    assert luganda["native_name"] == "Oluganda"

    runyankole = language_by_digit("4")
    assert runyankole is not None
    assert runyankole["code"] == "nyn"


def test_normalize_language_aliases():
    assert normalize_language("EN") == "en"
    assert normalize_language("luganda") == "lg"
    assert normalize_language("swahili") == "sw"
    assert normalize_language("runyakore") == "nyn"
    assert normalize_language("runyankole") == "nyn"
    assert normalize_language("acholi") == "ac"
    assert normalize_language("ateso") == "at"
    assert normalize_language(None) == DEFAULT_LANGUAGE
    assert normalize_language("") == DEFAULT_LANGUAGE
    assert normalize_language("zz") == DEFAULT_LANGUAGE
    # Lusoga not offered on IVR → fall back to English
    assert normalize_language("xog") == DEFAULT_LANGUAGE
    assert normalize_language("lusoga") == DEFAULT_LANGUAGE


def test_spoken_language_prompt_lists_all_digits():
    script = spoken_language_prompt()
    assert "CTDRU" in script or "Wakilibot" in script
    for digit in ("1", "2", "3", "4", "5", "6"):
        assert digit in script
    assert "press 7" not in script.lower()
    assert "nyiga 7" not in script.lower()
    assert "English" in script
    assert "Kiswahili" in script or "Swahili" in script
    assert "Oluganda" in script or "Luganda" in script
    assert "Orunyankole" in script or "Runyankole" in script
    assert "Iteso" in script or "Ateso" in script
    assert "Acholi" in script
    assert "Olusoga" not in script and "Lusoga" not in script


def test_spoken_invalid_language_reprompts():
    text = spoken_invalid_language()
    assert "Invalid" in text
    assert "press 1" in text.lower() or "Press 1" in text


def test_localized_menu_mentions_change_language_and_keys():
    for lang in ("en", "sw", "lg"):
        script = spoken_menu_script(lang)
        for key in ("1", "2", "3", "4", "5", "0", "9", CHANGE_LANGUAGE_KEY):
            assert key in script, f"missing key {key} in {lang} menu"


def test_unknown_menu_language_falls_back_to_english():
    assert spoken_menu_script("zz") == spoken_menu_script("en")


def test_language_confirmed_prompt_per_code():
    assert "English" in language_confirmed_prompt("en")
    assert "Kiswahili" in language_confirmed_prompt("sw")
    assert "Oluganda" in language_confirmed_prompt("lg")
    assert "Orunyankole" in language_confirmed_prompt("nyn")
    assert "Ateso" in language_confirmed_prompt("at")
    assert "Acholi" in language_confirmed_prompt("ac")


def test_free_speech_prompt_localized():
    assert "beep" in free_speech_prompt("en").lower()
    assert free_speech_prompt("sw") != free_speech_prompt("en")
    assert free_speech_prompt("unknown") == free_speech_prompt("en")
