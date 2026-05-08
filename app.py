from __future__ import annotations

import json
import time
from contextlib import asynccontextmanager
from typing import Any

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field

from buddy.audit import (
    create_pending_confirmation,
    get_confirmation,
    init_db,
    log_audit,
    recent_audit_rows,
    recent_confirmations,
    update_confirmation_status,
)
from buddy.config import load_environment
from buddy.executors import codex, fallback, gpt_oss
from buddy.github import status as github_status
from buddy.planning import load_context, load_projects
from buddy.router import classify


load_environment()


@asynccontextmanager
async def lifespan(_: FastAPI):
    init_db()
    yield


app = FastAPI(
    title="Buddy Orchestrator",
    description="Private local agent-control server for OpenClaw.",
    version="0.4.0",
    lifespan=lifespan,
)


class TextRequest(BaseModel):
    text: str = Field(..., min_length=1)


class MessageResponse(BaseModel):
    ok: bool
    confirmation_required: bool
    executor: str
    route: dict[str, Any]
    output_text: str
    latency_ms: int
    confirmation_id: str | None = None
    data: dict[str, Any] | None = None


class RouteResponse(BaseModel):
    route: dict[str, Any]


class AuditResponse(BaseModel):
    rows: list[dict[str, Any]]


class OpenClawMessageRequest(BaseModel):
    text: str = Field(..., min_length=1)
    channel: str = "telegram"
    user_id: str | None = None
    chat_id: str | None = None


class OpenClawCommandRequest(BaseModel):
    command: str = Field(..., min_length=1)
    chat_id: str | None = None
    user_id: str | None = None


class OpenClawResponse(BaseModel):
    reply_text: str
    confirmation_required: bool
    confirmation_id: str | None = None
    commands: list[str] = Field(default_factory=list)


class OpenClawCommandResponse(BaseModel):
    reply_text: str


class ConfirmRequest(BaseModel):
    confirmation_id: str = Field(..., min_length=1)
    approved: bool


class ConfirmResponse(BaseModel):
    ok: bool
    confirmation_id: str
    status: str
    executor: str
    route: dict[str, Any]
    output_text: str
    latency_ms: int
    data: dict[str, Any] | None = None


class ConfirmationsResponse(BaseModel):
    rows: list[dict[str, Any]]


class GitHubStatusResponse(BaseModel):
    configured: bool
    authenticated: bool
    login: str | None = None
    account_type: str | None = None
    owner: str | None = None
    default_repo: str | None = None
    api_url: str
    message: str


class ProjectsResponse(BaseModel):
    source: str
    configured: bool
    authenticated: bool
    login: str | None = None
    owner: str | None = None
    default_repo: str | None = None
    api_url: str
    repositories: list[dict[str, Any]]
    repository_count: int
    message: str


class PlanningContextResponse(BaseModel):
    source: str
    registry: dict[str, Any]
    operating_model: dict[str, Any]
    message: str


def _latency_ms(start: float) -> int:
    return round((time.perf_counter() - start) * 1000)


def _dispatch(text: str, route: dict[str, Any]) -> dict[str, Any]:
    executor = route.get("executor", "fallback")

    if executor == "gpt_oss":
        return gpt_oss.run(text)

    if executor == "codex":
        return codex.run(text, route)

    return fallback.run(text, route)


@app.get("/health")
def health() -> dict[str, Any]:
    start = time.perf_counter()
    output = {
        "ok": True,
        "service": "buddy-orchestrator",
        "private": True,
        "host": "127.0.0.1",
    }
    log_audit(
        input_text="GET /health",
        route={
            "intent": "health_check",
            "executor": "health",
            "risk": "low",
            "needs_confirmation": False,
            "complexity": "low",
            "reason": "Local health check.",
        },
        executor="health",
        output_text=json.dumps(output, sort_keys=True),
        latency_ms=_latency_ms(start),
    )
    return output


@app.post("/route", response_model=RouteResponse)
def route_message(request: TextRequest) -> RouteResponse:
    start = time.perf_counter()
    route = classify(request.text)
    latency_ms = _latency_ms(start)

    log_audit(
        input_text=request.text,
        route=route,
        executor="router",
        output_text=json.dumps(route, sort_keys=True),
        latency_ms=latency_ms,
    )

    return RouteResponse(route=route)


@app.get("/audit", response_model=AuditResponse)
def audit() -> AuditResponse:
    start = time.perf_counter()
    route = {
        "intent": "audit_query",
        "executor": "audit",
        "risk": "low",
        "needs_confirmation": False,
        "complexity": "low",
        "reason": "Local audit_log query.",
    }
    log_audit(
        input_text="GET /audit",
        route=route,
        executor="audit",
        output_text="Returned last 10 audit_log rows.",
        latency_ms=_latency_ms(start),
    )
    return AuditResponse(rows=recent_audit_rows(limit=10))


@app.get("/confirmations", response_model=ConfirmationsResponse)
def confirmations() -> ConfirmationsResponse:
    start = time.perf_counter()
    route = {
        "intent": "confirmations_query",
        "executor": "confirmation",
        "risk": "low",
        "needs_confirmation": False,
        "complexity": "low",
        "reason": "Local pending_confirmations query.",
    }
    log_audit(
        input_text="GET /confirmations",
        route=route,
        executor="confirmation",
        output_text="Returned last 10 pending/recent confirmations.",
        latency_ms=_latency_ms(start),
    )
    return ConfirmationsResponse(rows=recent_confirmations(limit=10))


@app.get("/github/status", response_model=GitHubStatusResponse)
def github_status_endpoint() -> GitHubStatusResponse:
    start = time.perf_counter()
    output = github_status()
    log_audit(
        input_text="GET /github/status",
        route={
            "intent": "github_status",
            "executor": "github",
            "risk": "low",
            "needs_confirmation": False,
            "complexity": "low",
            "reason": "Local GitHub credential status check.",
        },
        executor="github",
        output_text=json.dumps(output, sort_keys=True),
        latency_ms=_latency_ms(start),
    )
    return GitHubStatusResponse(**output)


@app.get("/projects", response_model=ProjectsResponse)
def projects() -> ProjectsResponse:
    start = time.perf_counter()
    output = load_projects()
    log_audit(
        input_text="GET /projects",
        route={
            "intent": "project_registry",
            "executor": "planning",
            "risk": "low",
            "needs_confirmation": False,
            "complexity": "low",
            "reason": "GitHub-backed cross-repo project registry.",
        },
        executor="planning",
        output_text=json.dumps(
            {
                "source": output.get("source"),
                "repository_count": output.get("repository_count"),
                "message": output.get("message"),
            },
            sort_keys=True,
        ),
        latency_ms=_latency_ms(start),
    )
    return ProjectsResponse(**output)


@app.get("/planning/context", response_model=PlanningContextResponse)
def planning_context() -> PlanningContextResponse:
    start = time.perf_counter()
    output = load_context()
    log_audit(
        input_text="GET /planning/context",
        route={
            "intent": "planning_context",
            "executor": "planning",
            "risk": "low",
            "needs_confirmation": False,
            "complexity": "low",
            "reason": "Cross-repo planning context built from GitHub registry.",
        },
        executor="planning",
        output_text=json.dumps(
            {
                "source": output.get("source"),
                "repository_count": output.get("registry", {}).get("repository_count"),
                "message": output.get("message"),
            },
            sort_keys=True,
        ),
        latency_ms=_latency_ms(start),
    )
    return PlanningContextResponse(**output)


@app.post("/message", response_model=MessageResponse)
def message(request: TextRequest) -> MessageResponse:
    return _handle_message_text(request.text)


@app.post("/openclaw/message", response_model=OpenClawResponse)
def openclaw_message(request: OpenClawMessageRequest) -> OpenClawResponse:
    message_response = _handle_message_text(request.text)
    return _openclaw_response_from_message(message_response)


@app.post("/openclaw/command", response_model=OpenClawCommandResponse)
def openclaw_command(request: OpenClawCommandRequest) -> OpenClawCommandResponse:
    parsed = _parse_openclaw_command(request.command)
    if parsed is None:
        reply_text = "Unsupported command. Use /approve <id> or /reject <id>."
        log_audit(
            input_text=request.command,
            route={
                "intent": "openclaw_command",
                "executor": "confirmation",
                "risk": "low",
                "needs_confirmation": False,
                "complexity": "low",
                "reason": "Unsupported OpenClaw command.",
            },
            executor="confirmation",
            output_text=reply_text,
            latency_ms=0,
        )
        return OpenClawCommandResponse(reply_text=reply_text)

    confirmation_id, approved = parsed
    try:
        confirmation_response = _handle_confirmation_decision(
            confirmation_id=confirmation_id,
            approved=approved,
        )
    except HTTPException as exc:
        return OpenClawCommandResponse(reply_text=str(exc.detail))

    return OpenClawCommandResponse(reply_text=confirmation_response.output_text)


def _handle_message_text(text: str) -> MessageResponse:
    start = time.perf_counter()
    route = classify(text)
    executor = route.get("executor", "fallback")

    if route.get("needs_confirmation") or route.get("risk") in {"medium", "high"}:
        confirmation_id = create_pending_confirmation(
            input_text=text,
            route=route,
            executor=executor,
        )
        output_text = "Confirmation required before Buddy executes this request."
        latency_ms = _latency_ms(start)
        log_audit(
            input_text=text,
            route=route,
            executor=executor,
            output_text=f"{output_text} confirmation_id={confirmation_id}",
            latency_ms=latency_ms,
        )
        return MessageResponse(
            ok=True,
            confirmation_required=True,
            executor=executor,
            route=route,
            output_text=output_text,
            latency_ms=latency_ms,
            confirmation_id=confirmation_id,
            data=None,
        )

    result = _dispatch(text, route)
    output_text = result.get("output_text", "")
    data = result.get("data")
    latency_ms = _latency_ms(start)

    log_audit(
        input_text=text,
        route=route,
        executor=executor,
        output_text=output_text,
        latency_ms=latency_ms,
    )

    return MessageResponse(
        ok=True,
        confirmation_required=False,
        executor=executor,
        route=route,
        output_text=output_text,
        latency_ms=latency_ms,
        confirmation_id=None,
        data=data,
    )


@app.post("/confirm", response_model=ConfirmResponse)
def confirm(request: ConfirmRequest) -> ConfirmResponse:
    return _handle_confirmation_decision(
        confirmation_id=request.confirmation_id,
        approved=request.approved,
    )


def _handle_confirmation_decision(
    *,
    confirmation_id: str,
    approved: bool,
) -> ConfirmResponse:
    start = time.perf_counter()
    confirmation = get_confirmation(confirmation_id)
    if confirmation is None:
        log_audit(
            input_text=confirmation_id,
            route={
                "intent": "confirmation_decision",
                "executor": "confirmation",
                "risk": "low",
                "needs_confirmation": False,
                "complexity": "low",
                "reason": "Confirmation decision for an unknown confirmation_id.",
                "confirmation": {
                    "decision": "approved" if approved else "rejected",
                    "status": "not_found",
                },
            },
            executor="confirmation",
            output_text="Confirmation not found.",
            latency_ms=_latency_ms(start),
        )
        raise HTTPException(status_code=404, detail="Confirmation not found.")

    route = confirmation["route"]
    executor = confirmation["executor"]
    input_text = confirmation["input_text"]

    if confirmation["status"] != "pending":
        output_text = f"Confirmation is already {confirmation['status']}."
        log_audit(
            input_text=input_text,
            route=_confirmation_audit_route(route, "already_resolved", confirmation["status"]),
            executor=executor,
            output_text=output_text,
            latency_ms=_latency_ms(start),
        )
        raise HTTPException(status_code=409, detail=output_text)

    if not approved:
        update_confirmation_status(confirmation_id, "rejected")
        output_text = "Confirmation rejected; request cancelled."
        latency_ms = _latency_ms(start)
        log_audit(
            input_text=input_text,
            route=_confirmation_audit_route(route, "rejected", "rejected"),
            executor=executor,
            output_text=output_text,
            latency_ms=latency_ms,
        )
        return ConfirmResponse(
            ok=True,
            confirmation_id=confirmation_id,
            status="rejected",
            executor=executor,
            route=route,
            output_text=output_text,
            latency_ms=latency_ms,
            data={"cancelled": True},
        )

    update_confirmation_status(confirmation_id, "approved")
    log_audit(
        input_text=input_text,
        route=_confirmation_audit_route(route, "approved", "approved"),
        executor=executor,
        output_text="Confirmation approved; executing original request.",
        latency_ms=_latency_ms(start),
    )

    try:
        result = _dispatch(input_text, route)
        output_text = result.get("output_text", "")
        data = result.get("data")
    except Exception as exc:
        update_confirmation_status(confirmation_id, "failed")
        output_text = f"Confirmation approved, but execution failed: {exc}"
        latency_ms = _latency_ms(start)
        log_audit(
            input_text=input_text,
            route=_confirmation_audit_route(route, "failed", "failed"),
            executor=executor,
            output_text=output_text,
            latency_ms=latency_ms,
        )
        return ConfirmResponse(
            ok=False,
            confirmation_id=confirmation_id,
            status="failed",
            executor=executor,
            route=route,
            output_text=output_text,
            latency_ms=latency_ms,
            data={"error": str(exc)},
        )

    update_confirmation_status(confirmation_id, "executed")
    latency_ms = _latency_ms(start)
    log_audit(
        input_text=input_text,
        route=_confirmation_audit_route(route, "executed", "executed"),
        executor=executor,
        output_text=output_text,
        latency_ms=latency_ms,
    )
    return ConfirmResponse(
        ok=True,
        confirmation_id=confirmation_id,
        status="executed",
        executor=executor,
        route=route,
        output_text=output_text,
        latency_ms=latency_ms,
        data=data,
    )


def _openclaw_response_from_message(response: MessageResponse) -> OpenClawResponse:
    commands: list[str] = []
    reply_text = response.output_text

    if response.confirmation_required and response.confirmation_id:
        commands = [
            f"/approve {response.confirmation_id}",
            f"/reject {response.confirmation_id}",
        ]
        reply_text = (
            f"{response.output_text}\n"
            f"Confirmation ID: {response.confirmation_id}\n"
            f"Approve: {commands[0]}\n"
            f"Reject: {commands[1]}"
        )

    return OpenClawResponse(
        reply_text=reply_text,
        confirmation_required=response.confirmation_required,
        confirmation_id=response.confirmation_id,
        commands=commands,
    )


def _parse_openclaw_command(command: str) -> tuple[str, bool] | None:
    parts = command.strip().split()
    if len(parts) < 2:
        return None

    verb = parts[0].split("@", 1)[0].lower()
    confirmation_id = parts[1]

    if verb == "/approve":
        return confirmation_id, True
    if verb == "/reject":
        return confirmation_id, False
    return None


def _confirmation_audit_route(
    route: dict[str, Any],
    decision: str,
    status: str,
) -> dict[str, Any]:
    audit_route = dict(route)
    audit_route["confirmation"] = {
        "decision": decision,
        "status": status,
    }
    return audit_route
