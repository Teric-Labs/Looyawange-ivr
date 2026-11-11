import asyncio
from unittest.mock import AsyncMock, MagicMock, patch

from app import agent_ready


def test_check_wakilibot_agent_requires_http_200():
    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_client = MagicMock()
    mock_client.get = AsyncMock(return_value=mock_resp)

    with patch("app.agent_ready.get_client", return_value=mock_client):
        result = asyncio.run(agent_ready.check_wakilibot_agent())

    assert result["http_200"] is True
    assert result["ok"] is True
    assert result["status_code"] == 200
    assert agent_ready.last_check()["http_200"] is True


def test_check_wakilibot_agent_rejects_429():
    mock_resp = MagicMock()
    mock_resp.status_code = 429
    mock_client = MagicMock()
    mock_client.get = AsyncMock(return_value=mock_resp)

    with patch("app.agent_ready.get_client", return_value=mock_client):
        result = asyncio.run(agent_ready.check_wakilibot_agent())

    assert result["http_200"] is False
    assert result["ok"] is False
    assert result["status_code"] == 429
    assert result["error"] == "rate_limited"


def test_wait_for_agent_http_200_retries_then_succeeds():
    mock_fail = MagicMock()
    mock_fail.status_code = 429
    mock_ok = MagicMock()
    mock_ok.status_code = 200
    mock_client = MagicMock()
    mock_client.get = AsyncMock(side_effect=[mock_fail, mock_ok])

    with patch("app.agent_ready.get_client", return_value=mock_client), patch(
        "app.agent_ready.asyncio.sleep", new_callable=AsyncMock
    ):
        result = asyncio.run(
            agent_ready.wait_for_agent_http_200(attempts=3, delay_sec=0.01)
        )

    assert result["http_200"] is True
    assert mock_client.get.await_count == 2
