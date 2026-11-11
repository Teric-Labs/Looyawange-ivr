from app import at_voice


def test_build_menu_xml_contains_get_digits_and_say():
    prompt = at_voice.say("Press 1 for complaints.")
    xml = at_voice.build_response(
        [at_voice.get_digits(num_digits=1, callback_url="https://example.com/ivr/voice", prompt=prompt)]
    )
    assert xml.startswith("<?xml")
    assert "<Response>" in xml
    assert "<Say>" in xml
    assert "<GetDigits" in xml
    assert "https://example.com/ivr/voice" in xml


def test_record_xml():
    xml = at_voice.build_response(
        [at_voice.record(prompt=at_voice.say("Speak after the beep"))]
    )
    assert "<Record" in xml
    assert "playBeep=\"true\"" in xml
