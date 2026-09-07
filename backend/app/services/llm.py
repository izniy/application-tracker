"""Thin wrapper around the LLM provider. Every LLM call in Orbit goes through here
so the model, retries and JSON parsing live in one place.

Provider is chosen from env: ANTHROPIC_API_KEY if set, else GEMINI_API_KEY."""
import json
import logging
import re
import time

import httpx
from anthropic import Anthropic

from ..config import settings

log = logging.getLogger(__name__)

_client: Anthropic | None = None

GEMINI_URL = "https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent"


def is_configured() -> bool:
    return bool(settings.anthropic_api_key or settings.gemini_api_key)


def client() -> Anthropic:
    global _client
    if _client is None:
        if not settings.anthropic_api_key:
            raise RuntimeError("ANTHROPIC_API_KEY is not set")
        _client = Anthropic(api_key=settings.anthropic_api_key)
    return _client


def _anthropic_complete(system: str, user: str, max_tokens: int, temperature: float) -> str:
    resp = client().messages.create(
        model=settings.anthropic_model,
        max_tokens=max_tokens,
        temperature=temperature,
        system=system,
        messages=[{"role": "user", "content": user}],
    )
    return "".join(block.text for block in resp.content if block.type == "text")


def _gemini_429(r: httpx.Response) -> tuple[float, bool]:
    """Extract (suggested retry delay, daily quota exhausted) from a 429 body."""
    try:
        details = r.json()["error"]["details"]
    except Exception:  # noqa: BLE001
        return 0.0, False
    daily = any("PerDay" in v.get("quotaId", "")
                for d in details if d.get("@type", "").endswith("QuotaFailure")
                for v in d.get("violations", []))
    delay = 0.0
    for d in details:
        if d.get("@type", "").endswith("RetryInfo"):
            m = re.match(r"([\d.]+)s", d.get("retryDelay", ""))
            if m:
                delay = float(m.group(1))
    return delay, daily


def _gemini_complete(system: str, user: str, max_tokens: int, temperature: float, json_mode: bool) -> str:
    """Gemini REST call. Thinking tokens share maxOutputTokens, so give generous headroom."""
    config: dict = {"temperature": temperature, "maxOutputTokens": max_tokens + 4096}
    if json_mode:
        config["responseMimeType"] = "application/json"
    body = {
        "system_instruction": {"parts": [{"text": system}]},
        "contents": [{"role": "user", "parts": [{"text": user}]}],
        "generationConfig": config,
    }
    url = GEMINI_URL.format(model=settings.gemini_model)
    tries = 5
    for attempt in range(tries):
        r = httpx.post(url, headers={"x-goog-api-key": settings.gemini_api_key}, json=body, timeout=120)
        if r.status_code in (429, 500, 503) and attempt < tries - 1:
            delay: float = 3 * 2 ** attempt
            if r.status_code == 429:
                suggested, daily = _gemini_429(r)
                if daily:
                    raise RuntimeError(
                        f"Gemini free-tier daily quota exhausted for {settings.gemini_model} — "
                        "resets at midnight Pacific, or switch GEMINI_MODEL"
                    )
                delay = min(max(delay, suggested + 1), 90)
            log.warning("Gemini API %s — retrying in %ss", r.status_code, delay)
            time.sleep(delay)
            continue
        r.raise_for_status()
        candidates = r.json().get("candidates") or []
        if not candidates:
            return ""
        parts = candidates[0].get("content", {}).get("parts", [])
        return "".join(p.get("text", "") for p in parts if not p.get("thought"))
    return ""


def complete(system: str, user: str, max_tokens: int = 1024, temperature: float = 0.0) -> str:
    if settings.anthropic_api_key:
        return _anthropic_complete(system, user, max_tokens, temperature)
    if settings.gemini_api_key:
        return _gemini_complete(system, user, max_tokens, temperature, json_mode=False)
    raise RuntimeError("No LLM configured — set ANTHROPIC_API_KEY or GEMINI_API_KEY")


def complete_json(system: str, user: str, max_tokens: int = 1024, temperature: float = 0.0) -> dict:
    """Ask for JSON only; strip code fences; return {} on failure so callers degrade gracefully."""
    system = system + "\n\nRespond with a single JSON object and nothing else."
    if settings.anthropic_api_key:
        text = _anthropic_complete(system, user, max_tokens, temperature)
    elif settings.gemini_api_key:
        text = _gemini_complete(system, user, max_tokens, temperature, json_mode=True)
    else:
        raise RuntimeError("No LLM configured — set ANTHROPIC_API_KEY or GEMINI_API_KEY")
    text = re.sub(r"^```(?:json)?|```$", "", text.strip(), flags=re.M).strip()
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        log.warning("LLM returned non-JSON: %s", text[:300])
        return {}
