from __future__ import annotations

import os
from typing import Any

import httpx

from buddy.config import load_environment


load_environment()


def _ollama_host() -> str:
    return os.getenv("OLLAMA_HOST", "http://127.0.0.1:11434")


def _ollama_model() -> str:
    return os.getenv("OLLAMA_MODEL", "gpt-oss:20b")


def _ollama_timeout_seconds() -> float:
    return float(os.getenv("OLLAMA_TIMEOUT_SECONDS", "110"))


def _ollama_num_predict() -> int:
    return int(os.getenv("OLLAMA_NUM_PREDICT", "1024"))


def _ollama_system_prompt() -> str:
    return os.getenv(
        "OLLAMA_SYSTEM_PROMPT",
        (
            "You are Buddy, a private local assistant running on the user's Mac "
            "through Ollama with gpt-oss:20b. Be concise, practical, and honest "
            "about what you can and cannot do. Answer directly in the final response."
        ),
    )


def run(text: str) -> dict[str, Any]:
    host = _ollama_host()
    model = _ollama_model()
    try:
        with httpx.Client(timeout=_ollama_timeout_seconds()) as client:
            response = client.post(
                f"{host.rstrip('/')}/api/generate",
                json={
                    "model": model,
                    "prompt": text,
                    "system": _ollama_system_prompt(),
                    "stream": False,
                    "options": {
                        "num_predict": _ollama_num_predict(),
                    },
                },
            )
            response.raise_for_status()
            payload = response.json()
    except httpx.HTTPError as exc:
        return {
            "output_text": (
                f"Buddy routed this to local Ollama model {model}, "
                f"but Ollama was not reachable or returned an error: {exc}"
            ),
            "data": {
                "executor": "gpt_oss",
                "model": model,
                "ollama_host": host,
                "error": str(exc),
            },
        }

    output_text = str(payload.get("response", "")).strip()
    if not output_text:
        output_text = (
            f"Ollama returned an empty final response from {model}. "
            "Try a shorter prompt or increase OLLAMA_NUM_PREDICT."
        )

    return {
        "output_text": output_text,
        "data": {
            "executor": "gpt_oss",
            "model": model,
            "ollama_host": host,
            "done_reason": payload.get("done_reason"),
        },
    }
