from __future__ import annotations

from typing import Any


def run(text: str, route: dict[str, Any]) -> dict[str, Any]:
    return {
        "output_text": (
            "Buddy does not have an executor for that yet. "
            "The request was classified and logged, but no external action was taken."
        ),
        "data": {
            "executor": "fallback",
            "input_text": text,
            "route": route,
        },
    }

