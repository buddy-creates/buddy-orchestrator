from __future__ import annotations

from typing import Any

from buddy.github import (
    create_issue as github_create_issue,
    default_repository,
    list_issues,
    parse_repository,
    repository_registry,
)


def load_projects() -> dict[str, Any]:
    return repository_registry()


def load_repository_context(
    repository: str | None = None,
    *,
    state: str = "open",
    issue_limit: int = 10,
) -> dict[str, Any]:
    owner, repo = _resolve_repository(repository)
    issues = list_issues(owner=owner, repo=repo, state=state, limit=issue_limit)
    return {
        "source": "github",
        "repository": f"{owner}/{repo}",
        "issues": issues["issues"],
        "issue_count": issues["issue_count"],
        "state": state,
        "message": "Loaded repository planning context from GitHub Issues.",
    }


def create_planning_task(
    *,
    repository: str | None = None,
    title: str,
    body: str = "",
    labels: list[str] | None = None,
    assignees: list[str] | None = None,
) -> dict[str, Any]:
    owner, repo = _resolve_repository(repository)
    issue = github_create_issue(
        owner=owner,
        repo=repo,
        title=title,
        body=body,
        labels=labels,
        assignees=assignees,
    )
    return {
        "source": "github",
        "repository": f"{owner}/{repo}",
        "issue": issue,
        "message": "Created GitHub Issue planning task.",
    }


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
        "actions": {
            "list_projects": "GET /projects",
            "list_issues": "GET /projects/{owner}/{repo}/issues",
            "create_task": "POST /planning/task",
            "propose_code_change": "POST /github/pull-request",
        },
        "message": (
            "GitHub is Buddy's cross-repo registry. Buddy should plan against the "
            "repositories, issues, and pull requests its token can access."
        ),
    }


def _resolve_repository(repository: str | None) -> tuple[str, str]:
    if repository:
        return parse_repository(repository)

    default = default_repository()
    if default is None:
        raise ValueError(
            "Provide repository as owner/name or set BUDDY_GITHUB_DEFAULT_REPO."
        )
    return default
