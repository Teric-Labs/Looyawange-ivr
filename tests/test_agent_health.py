import asyncio
from unittest.mock import AsyncMock, MagicMock, patch

from app import agent_client


def _reset_cache():
    agent_client._health_cache = None
    agent_client._health_cache_at = 0.0


def test_agent_health_http_200():
    _reset_cache()
    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_client = MagicMock()
    mock_client.get = AsyncMock(return_value=mock_resp)

    with patch.object(agent_client, "get_client", return_value=mock_client):
        result = asyncio.run(agent_client.agent_health(force=True))

    assert result["ok"] is True
    assert result["http_200"] is True
    assert result["status_code"] == 200
    _reset_cache()


def test_agent_health_429_is_not_http_200():
    _reset_cache()
    mock_resp = MagicMock()
    mock_resp.status_code = 429
    mock_client = MagicMock()
    mock_client.get = AsyncMock(return_value=mock_resp)

    with patch.object(agent_client, "get_client", return_value=mock_client):
        result = asyncio.run(agent_client.agent_health(force=True))

    assert result["http_200"] is False
    assert result["ok"] is False
    assert result["rate_limited"] is True
    assert result["status_code"] == 429
    _reset_cache()


def test_agent_health_is_cached():
    _reset_cache()
    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_client = MagicMock()
    mock_client.get = AsyncMock(return_value=mock_resp)

    async def _both():
        first = await agent_client.agent_health(force=True)
        second = await agent_client.agent_health()
        return first, second

    with patch.object(agent_client, "get_client", return_value=mock_client):
        first, second = asyncio.run(_both())

    assert first["http_200"] is True
    assert second["http_200"] is True
    assert mock_client.get.await_count == 1
    _reset_cache()
