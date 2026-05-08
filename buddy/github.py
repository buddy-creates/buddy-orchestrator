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
                headers={
                    "Accept": "application/vnd.github+json",
                    "Authorization": f"Bearer {token}",
                    "X-GitHub-Api-Version": "2022-11-28",
                },
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
