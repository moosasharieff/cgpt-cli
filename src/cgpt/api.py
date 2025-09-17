from __future__ import annotations

import json
from typing import Dict, Optional, Iterator

import requests

DEFAULT_BASE_URL: str = "https://api.openai.com/v1"
DEFAULT_TIMEOUT: int = 300


def endpoint_for(mode: str, base_url: Optional[str]) -> str:
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


def _extract_chat_text(data: dict) -> Optional[str]:
    """Best-effort text extraction for Chat Completions (non-streaming)."""
    choices = data.get("choices")
    if isinstance(choices, list) and choices:
        top = choices[0]
        if isinstance(top, dict):
            msg = top.get("message") or {}
            content = msg.get("content")
            if isinstance(content, str):
                return content
    return None


def _extract_responses_text(event: dict) -> Optional[str]:
    """Best-effort delta extraction for streaming events.

    Handles:
      - Responses stream: {"type":"...output_text.delta","delta":"..."}
      - Chat stream: {"choices":[{"delta":{"content":"..."}}]}
      - Fallback: {"output_text":"..."} (accumulated)
    """
    etype = event.get("type")
    if isinstance(etype, str) and etype.endswith("output_text.delta"):
        delta = event.get("delta")
        if isinstance(delta, str):
            return delta

    choices = event.get("choices")
    if isinstance(choices, list) and choices:
        delta = (choices[0].get("delta") or {}).get("content")
        if isinstance(delta, str):
            return delta

    out_text = event.get("output.text")
    if isinstance(out_text, str):
        return out_text

    return None


def _extract_stream_delta(event: dict) -> Optional[str]:
    """Best-effort delta extraction for streaming events.

    Handles:
      - Responses stream: {"type":"...output_text.delta","delta":"..."}
      - Chat stream: {"choices":[{"delta":{"content":"..."}}]}
      - Fallback: {"output_text":"..."} (accumulated)
    """
    etype = event.get("type")
    if isinstance(etype, str) and etype.endswith("output_text.delta"):
        delta = event.get("delta")
        if isinstance(delta, str):
            return delta

    choices = event.get("choices")
    if isinstance(choices, list) and choices:
        delta = (choices[0].get("delta") or {}).get("content")
        if isinstance(delta, str):
            return delta

    out_text = event.get("output_text")
    if isinstance(out_text, str):
        return out_text

    return None


def ask_once(
    *,
    api_key: str,
    prompt: str,
    model: str,
    mode: str = "responses",
    base_url: Optional[str] = None,
    timeout: int = DEFAULT_TIMEOUT,
) -> str:
    """Call the API without streaming and return the full text.

    Args:
        api_key: Bearer token.
        prompt: User input (single turn).
        model: Model id, e.g. "gpt-4o", "gpt-4o-mini".
        mode: "responses" (default) or "chat".
        base_url: Optional API base URL override.
        timeout: HTTP timeout in seconds.

    Returns:
        Extracted text, or the full JSON (pretty) if extraction fails.

    Raises:
        requests.HTTPError / requests.RequestException on HTTP/transport errors.
    """
    url = endpoint_for(mode, base_url)
    if mode.lower() == "chat":
        payload = {"model": model, "messages": [{"role": "user", "content": prompt}]}
    else:
        payload = {"model": model, "input": prompt}

    resp = requests.post(
        url, headers=auth_headers(api_key), data=json.dumps(payload), timeout=timeout
    )
    resp.raise_for_status()
    data = resp.json()

    text = (
        _extract_chat_text(data) if model == "chat" else _extract_responses_text(data)
    )
    return text if text is not None else json.dumps(data, ensure_ascii=False)


def ask_stream(
    *,
    api_key: str,
    prompt: str,
    model: str,
    mode: str = "responses",
    base_url: Optional[str] = None,
    timeout: int = DEFAULT_TIMEOUT,
) -> Iterator[str]:
    """
    Call the API with streaming enabled and yield text fragments.

    This function enables real-time streaming of model output using
    Server-Sent Events (SSE) or chunked responses. It normalizes common
    event formats from both the Responses and Chat APIs, so the caller
    can iterate over plain text fragments without handling protocol details.

    Args:
        api_key: Bearer token for API authentication.
        prompt: User input prompt (single-turn).
        model: Model identifier (e.g., "gpt-4o", "gpt-4o-mini").
        mode: Which API surface to call: "responses" (default) or "chat".
        base_url: Optional override for the API base URL. Falls back to
            DEFAULT_BASE_URL ("https://api.openai.com/v1").
        timeout: HTTP timeout in seconds (default: 300).

    Yields:
        str: Text fragments as soon as they are available. The caller is
        expected to print them incrementally (with `nl=False`) and add a
        final newline after the stream ends.

    Raises:
        requests.HTTPError: If the server responds with an error status.
        requests.RequestException: On transport-level errors or timeouts.
    """
    url = endpoint_for(mode, base_url)
    if mode.lower() == "chat":
        payload = {
            "model": model,
            "messages": [{"role": "user", "content": prompt}],
            "stream": True,
        }
    else:
        payload = {"model": model, "input": prompt, "stream": True}

    with requests.post(
        url,
        headers=auth_headers(api_key),
        data=json.dumps(payload),
        stream=True,
        timeout=timeout,
    ) as resp:
        resp.raise_for_status()

        for raw in resp.iter_lines(decode_unicode=True):
            if not raw:
                continue
            line = raw[5:].strip() if raw.startswith("data:") else raw.strip()
            if line == "[DONE]":
                break

            try:
                event = json.loads(line)
            except Exception:
                # unknown chunk shape data is emitted for use to see
                yield line
                continue

            delta = _extract_stream_delta(event)
            if delta is not None:
                yield delta
