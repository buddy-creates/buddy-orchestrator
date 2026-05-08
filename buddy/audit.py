from __future__ import annotations

import json
import os
import sqlite3
import uuid
from pathlib import Path
from typing import Any

from buddy.config import load_environment


DEFAULT_DB_PATH = "audit.db"


load_environment()


def db_path() -> Path:
    return Path(os.getenv("BUDDY_AUDIT_DB", DEFAULT_DB_PATH))


def connect() -> sqlite3.Connection:
    return sqlite3.connect(db_path())


def init_db() -> None:
    with connect() as conn:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS audit_log (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                input_text TEXT NOT NULL,
                route_json TEXT NOT NULL,
                executor TEXT NOT NULL,
                output_text TEXT NOT NULL,
                latency_ms INTEGER NOT NULL,
                created_at TEXT NOT NULL DEFAULT (datetime('now'))
            )
            """
        )
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS pending_confirmations (
                id TEXT PRIMARY KEY,
                input_text TEXT NOT NULL,
                route_json TEXT NOT NULL,
                executor TEXT NOT NULL,
                status TEXT NOT NULL CHECK (
                    status IN ('pending', 'approved', 'rejected', 'executed', 'failed')
                ),
                created_at TEXT NOT NULL DEFAULT (datetime('now')),
                resolved_at TEXT
            )
            """
        )
        conn.commit()


def log_audit(
    *,
    input_text: str,
    route: dict[str, Any],
    executor: str,
    output_text: str,
    latency_ms: int,
) -> None:
    init_db()
    with connect() as conn:
        conn.execute(
            """
            INSERT INTO audit_log (
                input_text,
                route_json,
                executor,
                output_text,
                latency_ms
            )
            VALUES (?, ?, ?, ?, ?)
            """,
            (
                input_text,
                json.dumps(route, sort_keys=True),
                executor,
                output_text,
                latency_ms,
            ),
        )
        conn.commit()


def recent_audit_rows(limit: int = 10) -> list[dict[str, Any]]:
    init_db()
    safe_limit = max(1, min(limit, 100))
    with connect() as conn:
        conn.row_factory = sqlite3.Row
        rows = conn.execute(
            """
            SELECT
                id,
                input_text,
                route_json,
                executor,
                output_text,
                latency_ms,
                created_at
            FROM audit_log
            ORDER BY id DESC
            LIMIT ?
            """,
            (safe_limit,),
        ).fetchall()
    return [dict(row) for row in rows]


def create_pending_confirmation(
    *,
    input_text: str,
    route: dict[str, Any],
    executor: str,
) -> str:
    init_db()
    confirmation_id = str(uuid.uuid4())
    with connect() as conn:
        conn.execute(
            """
            INSERT INTO pending_confirmations (
                id,
                input_text,
                route_json,
                executor,
                status
            )
            VALUES (?, ?, ?, ?, 'pending')
            """,
            (
                confirmation_id,
                input_text,
                json.dumps(route, sort_keys=True),
                executor,
            ),
        )
        conn.commit()
    return confirmation_id


def get_confirmation(confirmation_id: str) -> dict[str, Any] | None:
    init_db()
    with connect() as conn:
        conn.row_factory = sqlite3.Row
        row = conn.execute(
            """
            SELECT
                id,
                input_text,
                route_json,
                executor,
                status,
                created_at,
                resolved_at
            FROM pending_confirmations
            WHERE id = ?
            """,
            (confirmation_id,),
        ).fetchone()
    if row is None:
        return None
    return _confirmation_from_row(row)


def update_confirmation_status(confirmation_id: str, status: str) -> None:
    if status not in {"pending", "approved", "rejected", "executed", "failed"}:
        raise ValueError(f"Invalid confirmation status: {status}")

    resolved_sql = "datetime('now')" if status in {"rejected", "executed", "failed"} else "NULL"
    with connect() as conn:
        conn.execute(
            f"""
            UPDATE pending_confirmations
            SET status = ?, resolved_at = {resolved_sql}
            WHERE id = ?
            """,
            (status, confirmation_id),
        )
        conn.commit()


def recent_confirmations(limit: int = 10) -> list[dict[str, Any]]:
    init_db()
    safe_limit = max(1, min(limit, 100))
    with connect() as conn:
        conn.row_factory = sqlite3.Row
        rows = conn.execute(
            """
            SELECT
                id,
                input_text,
                route_json,
                executor,
                status,
                created_at,
                resolved_at
            FROM pending_confirmations
            ORDER BY
                CASE WHEN status = 'pending' THEN 0 ELSE 1 END,
                created_at DESC
            LIMIT ?
            """,
            (safe_limit,),
        ).fetchall()
    return [_confirmation_from_row(row) for row in rows]


def _confirmation_from_row(row: sqlite3.Row) -> dict[str, Any]:
    route_json = row["route_json"]
    try:
        route = json.loads(route_json)
    except json.JSONDecodeError:
        route = {}

    return {
        "id": row["id"],
        "input_text": row["input_text"],
        "route_json": route_json,
        "route": route,
        "executor": row["executor"],
        "status": row["status"],
        "created_at": row["created_at"],
        "resolved_at": row["resolved_at"],
    }
