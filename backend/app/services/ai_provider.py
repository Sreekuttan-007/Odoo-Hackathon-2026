"""The single pluggable LLM provider for Payloom's optional AI layer —
the PayTrace narrator (Phase 7B) and the Payloom Intelligence brief
(Phase 10) both call through here.

One provider at a time, chosen by `AI_PROVIDER` (`"gemini"` |
`"anthropic"`). Every failure — no key, timeout, rate limit, 4xx/5xx,
unreadable body — is raised as a `ProviderError` carrying a stable
`reason` string; callers turn that into `available: False`. Nothing here
ever computes payroll or interprets the model's content — it only moves
text in and out.
"""
from __future__ import annotations

import logging

import httpx

from app.core.config import settings

logger = logging.getLogger("payloom.ai")

TIMEOUT_SECONDS = 15.0

ANTHROPIC_URL = "https://api.anthropic.com/v1/messages"
ANTHROPIC_MODEL = "claude-haiku-4-5-20251001"

GEMINI_MODEL = "gemini-2.5-flash"
GEMINI_URL = f"https://generativelanguage.googleapis.com/v1beta/models/{GEMINI_MODEL}:generateContent"


class ProviderError(Exception):
    """reason ∈ NOT_CONFIGURED | TIMEOUT | RATE_LIMITED | PROVIDER_ERROR | MALFORMED_RESPONSE"""

    def __init__(self, reason: str):
        self.reason = reason
        super().__init__(reason)


def _provider() -> str:
    return (settings.AI_PROVIDER or "anthropic").strip().lower()


def _active_key() -> str | None:
    return settings.GEMINI_API_KEY if _provider() == "gemini" else settings.ANTHROPIC_API_KEY


def is_configured() -> bool:
    return bool(_active_key())


def active_provider_name() -> str | None:
    return _provider() if is_configured() else None


def complete_json(system: str, user: str, *, max_tokens: int = 1200) -> str:
    """Send a system + user prompt, return the model's raw text response
    (the caller expects JSON and parses/validates it). Raises
    ProviderError on any failure; never returns None, never raises
    anything else."""
    if not _active_key():
        raise ProviderError("NOT_CONFIGURED")
    try:
        if _provider() == "gemini":
            return _call_gemini(system, user, max_tokens)
        return _call_anthropic(system, user, max_tokens)
    except httpx.TimeoutException:
        raise ProviderError("TIMEOUT")
    except httpx.HTTPStatusError as exc:
        code = exc.response.status_code
        raise ProviderError("RATE_LIMITED" if code == 429 else "PROVIDER_ERROR")
    except (httpx.HTTPError, KeyError, IndexError, ValueError, TypeError):
        raise ProviderError("MALFORMED_RESPONSE")


def _call_gemini(system: str, user: str, max_tokens: int) -> str:
    response = httpx.post(
        GEMINI_URL,
        params={"key": settings.GEMINI_API_KEY},
        headers={"content-type": "application/json"},
        json={
            "system_instruction": {"parts": [{"text": system}]},
            "contents": [{"role": "user", "parts": [{"text": user}]}],
            "generationConfig": {
                "maxOutputTokens": max_tokens,
                "temperature": 0.2,
                "responseMimeType": "application/json",
            },
        },
        timeout=TIMEOUT_SECONDS,
    )
    response.raise_for_status()
    payload = response.json()
    parts = payload["candidates"][0]["content"]["parts"]
    return "".join(p.get("text", "") for p in parts)


def _call_anthropic(system: str, user: str, max_tokens: int) -> str:
    response = httpx.post(
        ANTHROPIC_URL,
        headers={
            "x-api-key": settings.ANTHROPIC_API_KEY,
            "anthropic-version": "2023-06-01",
            "content-type": "application/json",
        },
        json={
            "model": ANTHROPIC_MODEL,
            "max_tokens": max_tokens,
            "system": system,
            "messages": [{"role": "user", "content": user}],
        },
        timeout=TIMEOUT_SECONDS,
    )
    response.raise_for_status()
    payload = response.json()
    return payload["content"][0]["text"]
