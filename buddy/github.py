from __future__ import annotations

import base64
import os
import re
from typing import Any
from urllib.parse import quote

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


def default_repository() -> tuple[str, str] | None:
    repo = _default_repo()
    owner = _owner()
    if not repo:
        return None
    if "/" in repo:
        return parse_repository(repo)
    if not owner:
        status_payload = status()
        owner = status_payload.get("login")
    if not owner:
        return None
    return owner, repo


def parse_repository(repository: str) -> tuple[str, str]:
    normalized = repository.strip().removeprefix("https://github.com/").removesuffix(".git")
    parts = normalized.split("/")
    if len(parts) != 2 or not parts[0] or not parts[1]:
        raise ValueError("Repository must be in owner/name form.")
    return parts[0], parts[1]


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


def list_issues(
    *,
    owner: str,
    repo: str,
    state: str = "open",
    limit: int = 30,
) -> dict[str, Any]:
    api_url, token = _require_github()
    safe_limit = max(1, min(limit, 100))
    response = _request(
        "GET",
        f"{api_url}/repos/{owner}/{repo}/issues",
        token=token,
        params={
            "state": state,
            "per_page": safe_limit,
            "sort": "updated",
            "direction": "desc",
        },
    )
    payload = response.json()
    issues = [
        _issue_summary(item)
        for item in payload
        if isinstance(item, dict) and "pull_request" not in item
    ]
    return {
        "repository": f"{owner}/{repo}",
        "state": state,
        "issues": issues,
        "issue_count": len(issues),
    }


def create_issue(
    *,
    owner: str,
    repo: str,
    title: str,
    body: str = "",
    labels: list[str] | None = None,
    assignees: list[str] | None = None,
) -> dict[str, Any]:
    api_url, token = _require_github()
    response = _request(
        "POST",
        f"{api_url}/repos/{owner}/{repo}/issues",
        token=token,
        json={
            "title": title,
            "body": body,
            **({"labels": labels} if labels else {}),
            **({"assignees": assignees} if assignees else {}),
        },
    )
    return _issue_summary(response.json())


def create_pull_request_with_files(
    *,
    owner: str,
    repo: str,
    title: str,
    body: str,
    files: list[dict[str, str]],
    head_branch: str | None = None,
    base_branch: str | None = None,
    commit_message: str | None = None,
) -> dict[str, Any]:
    if not files:
        raise ValueError("At least one file is required.")

    api_url, token = _require_github()
    repo_payload = _request("GET", f"{api_url}/repos/{owner}/{repo}", token=token).json()
    base = base_branch or repo_payload.get("default_branch") or "main"
    branch = head_branch or _branch_name(title)
    base_sha = _branch_sha(api_url, token, owner, repo, base)

    _create_branch_if_needed(api_url, token, owner, repo, branch, base_sha)

    committed_files: list[dict[str, Any]] = []
    for file_spec in files:
        path = file_spec["path"].strip().lstrip("/")
        if not path:
            raise ValueError("File path cannot be empty.")
        content = file_spec["content"]
        message = file_spec.get("message") or commit_message or f"Update {path}"
        committed_files.append(
            _put_file(
                api_url=api_url,
                token=token,
                owner=owner,
                repo=repo,
                branch=branch,
                path=path,
                content=content,
                message=message,
            )
        )

    pull = _request(
        "POST",
        f"{api_url}/repos/{owner}/{repo}/pulls",
        token=token,
        json={
            "title": title,
            "body": body,
            "head": branch,
            "base": base,
        },
    ).json()

    return {
        "repository": f"{owner}/{repo}",
        "base_branch": base,
        "head_branch": branch,
        "pull_request": _pull_request_summary(pull),
        "files": committed_files,
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


def _require_github() -> tuple[str, str]:
    api_url = _api_url()
    token = _token()
    if not token:
        raise ValueError("Set BUDDY_GITHUB_TOKEN in Buddy's private .env file.")
    return api_url, token


def _request(
    method: str,
    url: str,
    *,
    token: str,
    params: dict[str, Any] | None = None,
    json: dict[str, Any] | None = None,
) -> httpx.Response:
    with httpx.Client(timeout=30) as client:
        response = client.request(
            method,
            url,
            headers=_headers(token),
            params=params,
            json=json,
        )
    if response.status_code >= 400:
        raise ValueError(_github_error(response))
    return response


def _request_allowing(
    method: str,
    url: str,
    *,
    token: str,
    ok_statuses: set[int],
    json: dict[str, Any] | None = None,
) -> httpx.Response:
    with httpx.Client(timeout=30) as client:
        response = client.request(method, url, headers=_headers(token), json=json)
    if response.status_code not in ok_statuses:
        raise ValueError(_github_error(response))
    return response


def _github_error(response: httpx.Response) -> str:
    try:
        payload = response.json()
    except ValueError:
        return f"GitHub returned HTTP {response.status_code}: {response.text}"
    message = payload.get("message") if isinstance(payload, dict) else None
    return f"GitHub returned HTTP {response.status_code}: {message or response.text}"


def _branch_sha(
    api_url: str,
    token: str,
    owner: str,
    repo: str,
    branch: str,
) -> str:
    response = _request(
        "GET",
        f"{api_url}/repos/{owner}/{repo}/git/ref/heads/{quote(branch, safe='')}",
        token=token,
    )
    payload = response.json()
    obj = payload.get("object") if isinstance(payload, dict) else None
    sha = obj.get("sha") if isinstance(obj, dict) else None
    if not sha:
        raise ValueError(f"Could not resolve base branch {branch}.")
    return sha


def _create_branch_if_needed(
    api_url: str,
    token: str,
    owner: str,
    repo: str,
    branch: str,
    sha: str,
) -> None:
    response = _request_allowing(
        "POST",
        f"{api_url}/repos/{owner}/{repo}/git/refs",
        token=token,
        json={
            "ref": f"refs/heads/{branch}",
            "sha": sha,
        },
        ok_statuses={201, 422},
    )
    if response.status_code == 422:
        payload = response.json()
        message = payload.get("message") if isinstance(payload, dict) else ""
        if "Reference already exists" not in message:
            raise ValueError(_github_error(response))


def _put_file(
    *,
    api_url: str,
    token: str,
    owner: str,
    repo: str,
    branch: str,
    path: str,
    content: str,
    message: str,
) -> dict[str, Any]:
    existing_sha = _file_sha(api_url, token, owner, repo, branch, path)
    payload: dict[str, Any] = {
        "message": message,
        "content": base64.b64encode(content.encode("utf-8")).decode("ascii"),
        "branch": branch,
    }
    if existing_sha:
        payload["sha"] = existing_sha

    response = _request(
        "PUT",
        f"{api_url}/repos/{owner}/{repo}/contents/{quote(path, safe='/')}",
        token=token,
        json=payload,
    ).json()
    commit = response.get("commit") if isinstance(response, dict) else {}
    content_payload = response.get("content") if isinstance(response, dict) else {}
    return {
        "path": path,
        "sha": content_payload.get("sha") if isinstance(content_payload, dict) else None,
        "commit_sha": commit.get("sha") if isinstance(commit, dict) else None,
    }


def _file_sha(
    api_url: str,
    token: str,
    owner: str,
    repo: str,
    branch: str,
    path: str,
) -> str | None:
    with httpx.Client(timeout=30) as client:
        response = client.get(
            f"{api_url}/repos/{owner}/{repo}/contents/{quote(path, safe='/')}",
            headers=_headers(token),
            params={"ref": branch},
        )
    if response.status_code == 404:
        return None
    if response.status_code >= 400:
        raise ValueError(_github_error(response))
    payload = response.json()
    return payload.get("sha") if isinstance(payload, dict) else None


def _branch_name(title: str) -> str:
    slug = re.sub(r"[^a-z0-9]+", "-", title.lower()).strip("-")
    return f"buddy/{(slug[:48] or 'change').strip('-')}"


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


def _issue_summary(issue: dict[str, Any]) -> dict[str, Any]:
    labels = issue.get("labels") if isinstance(issue.get("labels"), list) else []
    assignees = issue.get("assignees") if isinstance(issue.get("assignees"), list) else []
    user = issue.get("user") if isinstance(issue.get("user"), dict) else {}
    return {
        "number": issue.get("number"),
        "title": issue.get("title"),
        "state": issue.get("state"),
        "html_url": issue.get("html_url"),
        "body": issue.get("body"),
        "labels": [
            label.get("name")
            for label in labels
            if isinstance(label, dict) and label.get("name")
        ],
        "assignees": [
            assignee.get("login")
            for assignee in assignees
            if isinstance(assignee, dict) and assignee.get("login")
        ],
        "author": user.get("login"),
        "created_at": issue.get("created_at"),
        "updated_at": issue.get("updated_at"),
    }


def _pull_request_summary(pull: dict[str, Any]) -> dict[str, Any]:
    head = pull.get("head") if isinstance(pull.get("head"), dict) else {}
    base = pull.get("base") if isinstance(pull.get("base"), dict) else {}
    user = pull.get("user") if isinstance(pull.get("user"), dict) else {}
    return {
        "number": pull.get("number"),
        "title": pull.get("title"),
        "state": pull.get("state"),
        "draft": pull.get("draft"),
        "html_url": pull.get("html_url"),
        "author": user.get("login"),
        "head": head.get("ref"),
        "base": base.get("ref"),
        "created_at": pull.get("created_at"),
        "updated_at": pull.get("updated_at"),
    }
