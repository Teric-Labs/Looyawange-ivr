"""Voice callback language-gate tests (agent TTS mocked → AT <Say>)."""

from __future__ import annotations

from unittest.mock import AsyncMock, patch

import pytest
from fastapi.testclient import TestClient

from app import sessions
from app.main import app


@pytest.fixture
def client():
    with patch("app.main.agent_client.get_client"), patch(
        "app.main.agent_client.close_client", new_callable=AsyncMock
    ), patch(
        "app.main.agent_client.synthesize_to_file",
        new_callable=AsyncMock,
        return_value=(None, None),
    ), patch(
        "app.main.agent_ready.wait_for_agent_http_200",
        new_callable=AsyncMock,
        return_value={"http_200": True, "status_code": 200, "ok": True},
    ):
        with TestClient(app) as c:
            yield c


def _post(client: TestClient, **fields):
    payload = {
        "isActive": "1",
        "sessionId": "sess-1",
        "callerNumber": "+256700111222",
        "dtmfDigits": "",
        "recordingUrl": "",
    }
    payload.update(fields)
    return client.post("/ivr/voice", data=payload)


def test_first_ring_prompts_language_select(client):
    res = _post(client)
    assert res.status_code == 200
    body = res.text
    assert "<GetDigits" in body
    assert "Press 1" in body or "press 1" in body.lower()
    assert "Kiswahili" in body or "Oluganda" in body
    state = sessions.get_session("sess-1", "+256700111222")
    assert state["step"] == "language"
    assert state["language"] is None


def test_select_luganda_then_hears_menu(client):
    _post(client)  # first ring
    res = _post(client, dtmfDigits="3")
    assert res.status_code == 200
    body = res.text
    assert "Oluganda" in body or "lulondeddwa" in body
    assert "<GetDigits" in body
    # Main menu should mention change-language (8) in Luganda script
    assert "8" in body
    state = sessions.get_session("sess-1", "+256700111222")
    assert state["language"] == "lg"
    assert state["step"] == "menu"


def test_select_swahili(client):
    _post(client)
    res = _post(client, dtmfDigits="2")
    assert "Kiswahili" in res.text
    assert sessions.get_session("sess-1", "+256700111222")["language"] == "sw"


def test_invalid_language_digit_reprompts(client):
    _post(client)
    res = _post(client, dtmfDigits="9")
    assert "Invalid" in res.text
    state = sessions.get_session("sess-1", "+256700111222")
    assert state["language"] is None
    assert state["step"] == "language"


def test_press_8_returns_to_language_select(client):
    _post(client)
    _post(client, dtmfDigits="1")  # English
    assert sessions.get_session("sess-1", "+256700111222")["language"] == "en"

    res = _post(client, dtmfDigits="8")
    assert "Press 1" in res.text or "English" in res.text
    state = sessions.get_session("sess-1", "+256700111222")
    assert state["step"] == "language"
    assert state["language"] is None


def test_after_language_menu_digit_uses_session_language(client):
    _post(client)
    _post(client, dtmfDigits="1")

    with patch(
        "app.main.agent_client.chat",
        new_callable=AsyncMock,
        return_value={"message": "Please describe your complaint.", "conversation_id": "c1"},
    ):
        res = _post(client, dtmfDigits="1")

    assert res.status_code == 200
    assert "<Record" in res.text
    state = sessions.get_session("sess-1", "+256700111222")
    assert state["language"] == "en"
    assert state["intent"] == "submit_complaint"
    assert state["conversation_id"] == "c1"


def test_hangup_clears_session(client):
    _post(client)
    _post(client, dtmfDigits="3")
    res = _post(client, isActive="0")
    assert res.status_code == 200
    assert "CTDRU" in res.text or "Goodbye" in res.text or "Weraba" in res.text
    # Fresh session after clear
    state = sessions.get_session("sess-1", "+256700111222")
    assert state["language"] is None
    assert state["step"] == "language"


def test_health_lists_languages(client):
    with patch(
        "app.main.agent_client.agent_health",
        new_callable=AsyncMock,
        return_value={"ok": True, "http_200": True, "status_code": 200},
    ):
        res = client.get("/health")
    assert res.status_code == 200
    data = res.json()
    assert data["status"] == "ok"
    assert data["agent_status"] == "ok"
    assert data["agent_http_200"] is True
    codes = {L["code"] for L in data["languages"]}
    assert codes == {"en", "sw", "lg", "nyn", "at", "ac"}
    assert [L["code"] for L in data["languages"]] == [
        "en",
        "sw",
        "lg",
        "nyn",
        "at",
        "ac",
    ]
    assert data["languages"][0]["digit"] == "1"


def test_health_rate_limited_agent_still_ok(client):
    with patch(
        "app.main.agent_client.agent_health",
        new_callable=AsyncMock,
        return_value={
            "ok": False,
            "http_200": False,
            "status_code": 429,
            "rate_limited": True,
        },
    ):
        res = client.get("/health")
    assert res.status_code == 200
    data = res.json()
    assert data["status"] == "ok"  # IVR liveness
    assert data["agent_status"] == "rate_limited"
    assert data["agent_http_200"] is False


def test_health_agent_endpoint_requires_200(client):
    with patch(
        "app.main.agent_ready.check_wakilibot_agent",
        new_callable=AsyncMock,
        return_value={
            "http_200": True,
            "ok": True,
            "status_code": 200,
            "agent_url": "https://example.com",
        },
    ), patch(
        "app.main.agent_client.agent_health",
        new_callable=AsyncMock,
        return_value={"ok": True, "http_200": True, "status_code": 200},
    ):
        res = client.get("/health/agent")
    assert res.status_code == 200
    assert res.json()["http_200"] is True


def test_health_agent_endpoint_503_when_not_200(client):
    with patch(
        "app.main.agent_ready.check_wakilibot_agent",
        new_callable=AsyncMock,
        return_value={
            "http_200": False,
            "ok": False,
            "status_code": 429,
            "error": "rate_limited",
        },
    ), patch(
        "app.main.agent_client.agent_health",
        new_callable=AsyncMock,
        return_value={"ok": False, "http_200": False, "status_code": 429},
    ):
        res = client.get("/health/agent")
    assert res.status_code == 503
    assert res.json()["http_200"] is False
