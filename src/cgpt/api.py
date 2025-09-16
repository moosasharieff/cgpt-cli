from __future__ import annotations

import json
from typing import Dict, Iterator, Optional

import requests

DEFAULT_BASE_URL: str = "https://api.openai.com/v1"
DEFAULT_TIMEOUT: int = 300


def endpoint_for(mode: str, base_url: str) -> str:
    """Return the full endpoint URL for a given API `mode`.

        mode == "responses" -> /v1/responses
        mode == "chat"      -> /v1/chat/completions

    Args:
        mode: Either "responses" (default) or "chat" (case-insensitive accepted by CLI).
        base_url: Optional base URL override; falls back to DEFAULT_BASE_URL.

    Returns:
        Fully-qualified URL string.

    """
    root = (base_url or DEFAULT_BASE_URL).rstrip("/")
    if mode.lower() == "chat":
        return f"{root}/chat/completions"
    return f"{root}/responses"


def auth_headers(api_key: str) -> Dict[str, str]:
    """Return HTTP headers for bearer auth and JSON payloads."""
    return {"Authorization": f"Bearer {api_key}", "Content-Type": "applications/json"}
