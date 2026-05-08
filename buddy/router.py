from __future__ import annotations

import json
import os
from typing import Any

import httpx

from buddy.config import load_environment


load_environment()

BUILD_ACTION_PREFIXES = (
    "add ",
    "build ",
    "code ",
    "create ",
    "fix ",
    "implement ",
    "make ",
    "scaffold ",
    "set up ",
    "setup ",
    "write ",
)

BUILD_ACTION_PHRASES = {
    "build me",
    "code me",
    "create a",
    "create an",
    "create me",
    "make a",
    "make an",
    "make me",
    "write code",
}

HARD_CODE_TERMS = {
    "architecture",
    "auth",
    "authentication",
    "database",
    "distributed",
    "migration",
    "multi-agent",
    "orchestrator",
    "payment",
    "payments",
    "production",
    "refactor",
    "security",
}

MEDIUM_RISK_TERMS = {
    "actual budget",
    "calendar",
    "email",
    "finance",
    "gmail",
    "invoice",
    "newsletter",
    "schedule",
}

HIGH_RISK_TERMS = {
    "bank",
    "buy stock",
    "commit",
    "delete",
    "deploy",
    "merge",
    "pay",
    "push",
    "sell stock",
    "send email",
    "trade",
    "transfer",
}

VALID_EXECUTORS = {"gpt_oss", "codex", "fallback"}
VALID_RISKS = {"low", "medium", "high"}
VALID_COMPLEXITIES = {"low", "standard", "hard"}

ROUTE_SCHEMA = {
    "type": "object",
    "additionalProperties": False,
    "properties": {
        "intent": {
            "type": "string",
            "enum": [
                "greeting",
                "question",
                "code_task",
                "restricted_action",
                "fallback",
            ],
        },
        "executor": {"type": "string", "enum": ["gpt_oss", "codex", "fallback"]},
        "risk": {"type": "string", "enum": ["low", "medium", "high"]},
        "needs_confirmation": {"type": "boolean"},
        "complexity": {"type": "string", "enum": ["low", "standard", "hard"]},
        "reason": {"type": "string"},
    },
    "required": [
        "intent",
        "executor",
        "risk",
        "needs_confirmation",
        "complexity",
        "reason",
    ],
}

SYSTEM_PROMPT = """
You are Buddy Orchestrator's router. Return only strict JSON matching the supplied schema.

Routing policy:
- Code/build/file-modifying work must be intent=code_task, executor=codex, risk=medium,
  needs_confirmation=true, and complexity=standard or hard.
- Normal questions and greetings go to executor=gpt_oss with risk=low and needs_confirmation=false.
- Email, calendar, finance, deploy, commit, push, trading, payment, or destructive requests must
  require confirmation and use executor=fallback until those tools exist.
- The router classifies only. It never executes work.
""".strip()


class MockRouter:
    """Deterministic first-pass router."""

    def classify(self, text: str) -> dict[str, Any]:
        normalized = _normalize(text)
        risk = _risk(normalized)
        is_build_request = _matches_build_request(normalized)

        if is_build_request:
            route = {
                "intent": "code_task",
                "executor": "codex",
                "risk": "medium",
                "needs_confirmation": True,
                "complexity": _code_complexity(normalized),
                "reason": (
                    "Code/build tasks may modify files, so they require confirmation before execution."
                ),
            }
        elif normalized in {"hello", "hi", "hey"}:
            route = {
                "intent": "greeting",
                "executor": "gpt_oss",
                "risk": "low",
                "needs_confirmation": False,
                "complexity": "low",
                "reason": "Simple conversational message for the local brain.",
            }
        elif risk != "low":
            route = {
                "intent": "restricted_action",
                "executor": "fallback",
                "risk": risk,
                "needs_confirmation": True,
                "complexity": "standard",
                "reason": (
                    "Potentially sensitive external action requires confirmation and future tooling."
                ),
            }
        else:
            route = {
                "intent": "question",
                "executor": "gpt_oss",
                "risk": "low",
                "needs_confirmation": False,
                "complexity": "low",
                "reason": "General question or chat should go to the local gpt-oss brain.",
            }

        return _validated_route(route, text)


class OpenAIRouter:
    """OpenAI-backed router using strict JSON Structured Outputs."""

    def __init__(
        self,
        *,
        api_key: str,
        model: str,
        fallback: MockRouter | None = None,
    ) -> None:
        self.api_key = api_key
        self.model = model
        self.fallback = fallback or MockRouter()

    def classify(self, text: str) -> dict[str, Any]:
        try:
            route = self._classify_with_api(text)
            return _validated_route(route, text)
        except Exception:
            return self.fallback.classify(text)

    def _classify_with_api(self, text: str) -> dict[str, Any]:
        with httpx.Client(timeout=10) as client:
            response = client.post(
                "https://api.openai.com/v1/responses",
                headers={
                    "Authorization": f"Bearer {self.api_key}",
                    "Content-Type": "application/json",
                },
                json={
                    "model": self.model,
                    "input": [
                        {"role": "system", "content": SYSTEM_PROMPT},
                        {"role": "user", "content": text},
                    ],
                    "max_output_tokens": 250,
                    "text": {
                        "format": {
                            "type": "json_schema",
                            "name": "buddy_route",
                            "strict": True,
                            "schema": ROUTE_SCHEMA,
                        }
                    },
                },
            )
            response.raise_for_status()

        output_text = _extract_output_text(response.json())
        payload = json.loads(output_text)
        if not isinstance(payload, dict):
            raise ValueError("OpenAI router returned non-object JSON.")
        return payload


def get_router() -> MockRouter | OpenAIRouter:
    provider = os.getenv("ROUTER_PROVIDER", "mock").strip().lower()
    if provider != "openai":
        return MockRouter()

    api_key = os.getenv("OPENAI_API_KEY", "").strip()
    if not api_key:
        return MockRouter()

    model = os.getenv("OPENAI_ROUTER_MODEL", "gpt-4o-mini").strip() or "gpt-4o-mini"
    return OpenAIRouter(api_key=api_key, model=model)


def classify(text: str) -> dict[str, Any]:
    return get_router().classify(text)


def _extract_output_text(payload: dict[str, Any]) -> str:
    if isinstance(payload.get("output_text"), str):
        return payload["output_text"]

    for item in payload.get("output", []):
        for content in item.get("content", []):
            if content.get("type") == "refusal":
                raise ValueError(content.get("refusal", "OpenAI router refused."))
            if content.get("type") in {"output_text", "text"} and isinstance(
                content.get("text"),
                str,
            ):
                return content["text"]

    raise ValueError("OpenAI router response did not include output text.")


def _validated_route(route: dict[str, Any], text: str) -> dict[str, Any]:
    normalized = _normalize(text)
    safe_route = dict(route)

    safe_route["intent"] = str(safe_route.get("intent", "fallback"))
    safe_route["executor"] = str(safe_route.get("executor", "fallback"))
    safe_route["risk"] = str(safe_route.get("risk", "low"))
    safe_route["complexity"] = str(safe_route.get("complexity", "standard"))
    safe_route["reason"] = str(safe_route.get("reason", "Classified by Buddy router."))

    is_code_task = (
        _matches_build_request(normalized)
        or safe_route["intent"] == "code_task"
        or safe_route["executor"] == "codex"
    )
    if is_code_task:
        safe_route["intent"] = "code_task"
        safe_route["executor"] = "codex"
        safe_route["risk"] = "medium"
        if safe_route["complexity"] not in {"standard", "hard"}:
            safe_route["complexity"] = _code_complexity(normalized)
        safe_route["needs_confirmation"] = True
        safe_route["reason"] = (
            "Code/build tasks may modify files, so they require confirmation before execution."
        )
        return safe_route

    if safe_route["executor"] not in VALID_EXECUTORS:
        safe_route["executor"] = "fallback"
    if safe_route["risk"] not in VALID_RISKS:
        safe_route["risk"] = "low"
    if safe_route["complexity"] not in VALID_COMPLEXITIES:
        safe_route["complexity"] = "standard"

    safe_route["needs_confirmation"] = safe_route["risk"] in {"medium", "high"}
    return safe_route


def _normalize(text: str) -> str:
    return " ".join(text.lower().split())


def _matches_build_request(normalized: str) -> bool:
    if any(phrase in normalized for phrase in BUILD_ACTION_PHRASES):
        return True
    return normalized.startswith(BUILD_ACTION_PREFIXES)


def _risk(normalized: str) -> str:
    if any(term in normalized for term in HIGH_RISK_TERMS):
        return "high"
    if any(term in normalized for term in MEDIUM_RISK_TERMS):
        return "medium"
    return "low"


def _code_complexity(normalized: str) -> str:
    if any(term in normalized for term in HARD_CODE_TERMS):
        return "hard"
    return "standard"
