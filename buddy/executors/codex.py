from __future__ import annotations

import json
import re
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from buddy.executors import gpt_oss
from buddy.planning import load_context


TASK_DIR = Path("agent-workspace/tasks")


def run(text: str, route: dict[str, Any]) -> dict[str, Any]:
    TASK_DIR.mkdir(parents=True, exist_ok=True)

    task_id = str(uuid.uuid4())
    created_at = datetime.now(timezone.utc).isoformat()
    safe_route = _codex_route(route)
    task_spec = {
        "id": task_id,
        "status": "queued",
        "executor": "codex",
        "input_text": text,
        "route": safe_route,
        "created_at": created_at,
        "safety": {
            "requires_confirmation_for_medium_or_high_risk": True,
            "no_auto_email": True,
            "no_auto_finance_changes": True,
            "no_auto_deploy": True,
            "no_auto_commit": True,
        },
    }

    path = TASK_DIR / f"{_slug(text)}-{task_id[:8]}.json"
    path.write_text(json.dumps(task_spec, indent=2, sort_keys=True), encoding="utf-8")

    brief = gpt_oss.run(_build_execution_brief_prompt(text, safe_route, path))
    brief_text = str(brief.get("output_text", "")).strip()

    output_text = f"Created Codex task spec at {path}."
    if brief_text:
        output_text = f"{output_text}\n\nGPT-OSS execution brief:\n{brief_text}"

    return {
        "output_text": output_text,
        "data": {
            "task_id": task_id,
            "task_path": str(path),
            "task": task_spec,
            "gpt_oss": brief.get("data"),
        },
    }


def _codex_route(route: dict[str, Any]) -> dict[str, Any]:
    safe_route = dict(route)
    safe_route["intent"] = "code_task"
    safe_route["executor"] = "codex"
    safe_route["risk"] = "medium"
    safe_route["needs_confirmation"] = True
    if safe_route.get("complexity") not in {"standard", "hard"}:
        safe_route["complexity"] = "standard"
    safe_route.setdefault(
        "reason",
        "Code/build tasks may modify files, so they require confirmation before execution.",
    )
    return safe_route


def _slug(text: str) -> str:
    slug = re.sub(r"[^a-z0-9]+", "-", text.lower()).strip("-")
    return (slug[:48] or "task").strip("-")


def _build_execution_brief_prompt(text: str, route: dict[str, Any], path: Path) -> str:
    return (
        "Answer directly in the final response. A user approved this Buddy code/build "
        "request. Produce a concise execution brief for the Codex builder. Do not "
        "claim the work is already done. Start with 'Deliverable:' and include first "
        "implementation steps plus one safety check. Keep it under 90 words.\n\n"
        f"User request: {text}\n"
        f"Task spec path: {path}\n"
        f"Route: {json.dumps(route, sort_keys=True)}\n"
        f"GitHub planning context: {_planning_context_excerpt()}"
    )


def _planning_context_excerpt() -> str:
    try:
        context = load_context()
    except Exception as exc:
        return f"unavailable: {exc}"

    registry = context.get("registry", {})
    repositories = registry.get("repositories", [])
    repo_summaries = []
    for repo in repositories[:8]:
        if not isinstance(repo, dict):
            continue
        repo_summaries.append(
            {
                "full_name": repo.get("full_name"),
                "description": repo.get("description"),
                "default_branch": repo.get("default_branch"),
                "permissions": repo.get("permissions"),
            }
        )

    excerpt = {
        "source": context.get("source"),
        "repository_count": registry.get("repository_count"),
        "repositories": repo_summaries,
        "operating_model": context.get("operating_model"),
    }
    return json.dumps(excerpt, sort_keys=True)
