from __future__ import annotations

from typing import Any

from buddy.github import repository_registry


def load_projects() -> dict[str, Any]:
    return repository_registry()


def load_context() -> dict[str, Any]:
    registry = load_projects()
    return {
        "source": "github",
        "registry": registry,
        "operating_model": {
            "project_registry": "GitHub repositories visible to Buddy's token.",
            "work_items": "Use GitHub Issues for project-scoped tasks.",
            "code_review": "Use branches and pull requests for proposed code changes.",
            "roadmaps": "Use repo README files, GitHub Issues, and GitHub Projects for longer-horizon planning.",
            "local_private_state": "Keep .env, audit.db, logs, and runtime state local and out of GitHub.",
        },
        "message": (
            "GitHub is Buddy's cross-repo registry. Buddy should plan against the "
            "repositories, issues, and pull requests its token can access."
        ),
    }
