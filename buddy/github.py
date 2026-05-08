from __future__ import annotations

import os
from typing import Any

import httpx

from buddy.config import load_environment


load_environment()


def _api_url() -> str:
    return os.getenv("BUDDY_GITHUB_API_URL", "https://api.github.com").rstrip("/")


def _token() -> str:
    return os.getenv("BUDDY_GITHUB_TOKEN", "").strip()


def _owner() -> str | None:
    return os.getenv("BUDDY_GITHUB_OWNER", "").strip() or None


def _default_repo() -> str | None:
    return os.getenv("BUDDY_GITHUB_DEFAULT_REPO", "").strip() or None


def _headers(token: str) -> dict[str, str]:
    return {
        "Accept": "application/vnd.github+json",
        "Authorization": f"Bearer {token}",
        "X-GitHub-Api-Version": "2022-11-28",
    }


def status() -> dict[str, Any]:
    load_environment()
    api_url = _api_url()
    token = _token()
    base = {
        "configured": bool(token),
        "authenticated": False,
        "login": None,
        "account_type": None,
        "owner": _owner(),
        "default_repo": _default_repo(),
        "api_url": api_url,
    }

    if not token:
        return {
            **base,
            "message": "Set BUDDY_GITHUB_TOKEN in Buddy's private .env file.",
        }

    try:
        with httpx.Client(timeout=10) as client:
            response = client.get(
                f"{api_url}/user",
                headers=_headers(token),
            )
    except httpx.HTTPError as exc:
        return {
            **base,
            "message": f"Could not reach GitHub API: {exc}",
        }

    if response.status_code == 401:
        return {
            **base,
            "message": "GitHub rejected BUDDY_GITHUB_TOKEN.",
        }

    if response.status_code == 403:
        return {
            **base,
            "message": "GitHub token is configured but forbidden for /user.",
        }

    try:
        response.raise_for_status()
        payload = response.json()
    except (httpx.HTTPError, ValueError) as exc:
        return {
            **base,
            "message": f"GitHub status check failed: {exc}",
        }

    return {
        **base,
        "authenticated": True,
        "login": payload.get("login"),
        "account_type": payload.get("type"),
        "message": "GitHub token is valid.",
    }


def repository_registry() -> dict[str, Any]:
    load_environment()
    api_url = _api_url()
    token = _token()
    status_payload = status()
    base = {
        "source": "github",
        "configured": status_payload["configured"],
        "authenticated": status_payload["authenticated"],
        "login": status_payload["login"],
        "owner": _owner() or status_payload["login"],
        "default_repo": _default_repo(),
        "api_url": api_url,
        "repositories": [],
        "repository_count": 0,
    }

    if not token or not status_payload["authenticated"]:
        return {
            **base,
            "message": status_payload["message"],
        }

    try:
        with httpx.Client(timeout=20) as client:
            repositories = _fetch_visible_repositories(client, api_url, token)
    except httpx.HTTPError as exc:
        return {
            **base,
            "message": f"Could not load GitHub repositories: {exc}",
        }

    summaries = [_repository_summary(repo) for repo in repositories]
    return {
        **base,
        "repositories": summaries,
        "repository_count": len(summaries),
        "message": "Loaded repositories visible to Buddy's GitHub token.",
    }


def _fetch_visible_repositories(
    client: httpx.Client,
    api_url: str,
    token: str,
) -> list[dict[str, Any]]:
    repositories: list[dict[str, Any]] = []
    for page in range(1, 11):
        response = client.get(
            f"{api_url}/user/repos",
            headers=_headers(token),
            params={
                "affiliation": "owner,collaborator,organization_member",
                "visibility": "all",
                "sort": "updated",
                "per_page": 100,
                "page": page,
            },
        )
        response.raise_for_status()
        payload = response.json()
        if not isinstance(payload, list) or not payload:
            break
        repositories.extend(repo for repo in payload if isinstance(repo, dict))
        if len(payload) < 100:
            break
    return repositories


def _repository_summary(repo: dict[str, Any]) -> dict[str, Any]:
    owner = repo.get("owner") if isinstance(repo.get("owner"), dict) else {}
    permissions = repo.get("permissions") if isinstance(repo.get("permissions"), dict) else {}
    return {
        "id": repo.get("id"),
        "name": repo.get("name"),
        "full_name": repo.get("full_name"),
        "owner": owner.get("login"),
        "private": repo.get("private"),
        "visibility": repo.get("visibility"),
        "description": repo.get("description"),
        "html_url": repo.get("html_url"),
        "clone_url": repo.get("clone_url"),
        "default_branch": repo.get("default_branch"),
        "topics": repo.get("topics") or [],
        "archived": repo.get("archived"),
        "disabled": repo.get("disabled"),
        "updated_at": repo.get("updated_at"),
        "pushed_at": repo.get("pushed_at"),
        "permissions": {
            "admin": permissions.get("admin"),
            "maintain": permissions.get("maintain"),
            "push": permissions.get("push"),
            "triage": permissions.get("triage"),
            "pull": permissions.get("pull"),
        },
    }
