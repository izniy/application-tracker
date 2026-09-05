"""Thin wrapper around the Anthropic API. Every LLM call in Orbit goes through here
so the model, retries and JSON parsing live in one place."""
import json
import logging
import re

from anthropic import Anthropic

from ..config import settings

log = logging.getLogger(__name__)

_client: Anthropic | None = None


def client() -> Anthropic:
    global _client
    if _client is None:
        if not settings.anthropic_api_key:
            raise RuntimeError("ANTHROPIC_API_KEY is not set")
        _client = Anthropic(api_key=settings.anthropic_api_key)
    return _client


def complete(system: str, user: str, max_tokens: int = 1024) -> str:
    resp = client().messages.create(
        model=settings.anthropic_model,
        max_tokens=max_tokens,
        system=system,
        messages=[{"role": "user", "content": user}],
    )
    return "".join(block.text for block in resp.content if block.type == "text")


def complete_json(system: str, user: str, max_tokens: int = 1024) -> dict:
    """Ask for JSON only; strip code fences; return {} on failure so callers degrade gracefully."""
    text = complete(system + "\n\nRespond with a single JSON object and nothing else.", user, max_tokens)
    text = re.sub(r"^```(?:json)?|```$", "", text.strip(), flags=re.M).strip()
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        log.warning("LLM returned non-JSON: %s", text[:300])
        return {}
