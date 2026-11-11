"""Wakilibot-agent readiness — require GET {agent}/health → HTTP 200.

Used by IVR startup, /health/agent, and ops probes. Separate from IVR liveness
so Render can keep the IVR service up while the agent is cold or rate-limited.
"""

from __future__ import annotations

import asyncio
import logging
import time
from typing import Any, Dict, Optional

import httpx

from app.agent_client import get_client
from app.config import settings

logger = logging.getLogger(__name__)

# Last successful / last attempted check (in-process).
_last: Dict[str, Any] = {
    "checked_at": None,
    "http_200": False,
    "status_code": None,
    "agent_url": None,
    "error": None,
    "latency_ms": None,
}


def last_check() -> Dict[str, Any]:
    return dict(_last)


async def check_wakilibot_agent(*, timeout_sec: float = 8.0) -> Dict[str, Any]:
    """Hit wakilibot-agent /health and report whether the status code is exactly 200."""
    cfg = settings()
    agent_url = cfg["agent_url"]
    url = f"{agent_url}/health"
    started = time.monotonic()
    result: Dict[str, Any] = {
        "agent_url": agent_url,
        "health_url": url,
        "http_200": False,
        "status_code": None,
        "ok": False,
        "error": None,
        "latency_ms": None,
        "checked_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
    }
    try:
        resp = await get_client().get(
            url,
            timeout=httpx.Timeout(timeout_sec, connect=min(3.0, timeout_sec)),
        )
        latency_ms = int((time.monotonic() - started) * 1000)
        code = resp.status_code
        result["status_code"] = code
        result["latency_ms"] = latency_ms
        result["http_200"] = code == 200
        result["ok"] = code == 200
        if code == 429:
            result["error"] = "rate_limited"
            result["note"] = "Agent returned 429; wait and retry — not a healthy 200"
        elif code != 200:
            result["error"] = f"unexpected_status_{code}"
    except Exception as exc:
        result["latency_ms"] = int((time.monotonic() - started) * 1000)
        result["error"] = f"{exc.__class__.__name__}: {exc}"

    _last.update(
        {
            "checked_at": result["checked_at"],
            "http_200": result["http_200"],
            "status_code": result["status_code"],
            "agent_url": agent_url,
            "error": result.get("error"),
            "latency_ms": result.get("latency_ms"),
        }
    )
    return result


async def wait_for_agent_http_200(
    *,
    attempts: int = 6,
    delay_sec: float = 5.0,
    timeout_sec: float = 8.0,
) -> Dict[str, Any]:
    """Poll until agent /health returns 200, or exhaust attempts."""
    last: Optional[Dict[str, Any]] = None
    for i in range(1, attempts + 1):
        last = await check_wakilibot_agent(timeout_sec=timeout_sec)
        if last.get("http_200"):
            logger.info(
                "Wakilibot-agent healthy (HTTP 200) on attempt %s/%s (%sms)",
                i,
                attempts,
                last.get("latency_ms"),
            )
            return last
        logger.warning(
            "Wakilibot-agent not HTTP 200 yet (attempt %s/%s): status=%s error=%s",
            i,
            attempts,
            last.get("status_code"),
            last.get("error"),
        )
        if i < attempts:
            await asyncio.sleep(delay_sec)
    assert last is not None
    return last
