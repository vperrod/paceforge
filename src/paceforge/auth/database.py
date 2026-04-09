"""SQLite database layer for user management."""

from __future__ import annotations

import sqlite3
import uuid
from datetime import datetime, timezone
from pathlib import Path
from threading import Lock

_lock = Lock()
_connection: sqlite3.Connection | None = None

_SCHEMA = """\
CREATE TABLE IF NOT EXISTS users (
    id            TEXT PRIMARY KEY,
    name          TEXT NOT NULL,
    email         TEXT NOT NULL UNIQUE COLLATE NOCASE,
    password_hash TEXT NOT NULL,
    role          TEXT NOT NULL DEFAULT 'user' CHECK(role IN ('admin', 'user')),
    status        TEXT NOT NULL DEFAULT 'pending' CHECK(status IN ('pending', 'approved', 'rejected')),
    reason        TEXT DEFAULT '',
    created_at    TEXT NOT NULL,
    approved_at   TEXT,
    garmin_email  TEXT
);
"""


def _get_conn(db_path: str) -> sqlite3.Connection:
    global _connection
    if _connection is None:
        path = Path(db_path).expanduser().resolve()
        path.parent.mkdir(parents=True, exist_ok=True)
        _connection = sqlite3.connect(str(path), check_same_thread=False)
        _connection.row_factory = sqlite3.Row
        _connection.execute("PRAGMA journal_mode=WAL")
    return _connection


def init_db(db_path: str) -> None:
    """Create the users table if it doesn't exist."""
    with _lock:
        conn = _get_conn(db_path)
        conn.executescript(_SCHEMA)


def close_db() -> None:
    """Close the database connection."""
    global _connection
    with _lock:
        if _connection:
            _connection.close()
            _connection = None


def _row_to_dict(row: sqlite3.Row | None) -> dict | None:
    if row is None:
        return None
    return dict(row)


# ── CRUD ─────────────────────────────────────────────────────────────


def create_user(
    db_path: str,
    *,
    name: str,
    email: str,
    password_hash: str,
    role: str = "user",
    status: str = "pending",
    reason: str = "",
) -> dict:
    """Insert a new user. Returns the user dict. Raises on duplicate email."""
    user_id = str(uuid.uuid4())
    now = datetime.now(timezone.utc).isoformat()
    approved_at = now if status == "approved" else None
    with _lock:
        conn = _get_conn(db_path)
        conn.execute(
            "INSERT INTO users (id, name, email, password_hash, role, status, reason, created_at, approved_at) "
            "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (user_id, name, email, password_hash, role, status, reason, now, approved_at),
        )
        conn.commit()
    return get_user_by_id(db_path, user_id)  # type: ignore[return-value]


def get_user_by_email(db_path: str, email: str) -> dict | None:
    with _lock:
        conn = _get_conn(db_path)
        row = conn.execute("SELECT * FROM users WHERE email = ?", (email,)).fetchone()
    return _row_to_dict(row)


def get_user_by_id(db_path: str, user_id: str) -> dict | None:
    with _lock:
        conn = _get_conn(db_path)
        row = conn.execute("SELECT * FROM users WHERE id = ?", (user_id,)).fetchone()
    return _row_to_dict(row)


def list_users(db_path: str, *, status: str | None = None) -> list[dict]:
    with _lock:
        conn = _get_conn(db_path)
        if status:
            rows = conn.execute(
                "SELECT * FROM users WHERE status = ? ORDER BY created_at DESC", (status,)
            ).fetchall()
        else:
            rows = conn.execute("SELECT * FROM users ORDER BY created_at DESC").fetchall()
    return [dict(r) for r in rows]


def update_user_status(
    db_path: str, user_id: str, *, status: str
) -> dict | None:
    """Set user status to 'approved' or 'rejected'. Returns updated user."""
    now = datetime.now(timezone.utc).isoformat() if status == "approved" else None
    with _lock:
        conn = _get_conn(db_path)
        conn.execute(
            "UPDATE users SET status = ?, approved_at = ? WHERE id = ?",
            (status, now, user_id),
        )
        conn.commit()
    return get_user_by_id(db_path, user_id)


def update_garmin_email(db_path: str, user_id: str, garmin_email: str) -> None:
    with _lock:
        conn = _get_conn(db_path)
        conn.execute(
            "UPDATE users SET garmin_email = ? WHERE id = ?",
            (garmin_email, user_id),
        )
        conn.commit()


def reset_connection() -> None:
    """Reset DB connection (useful for tests with temp DBs)."""
    global _connection
    with _lock:
        if _connection:
            _connection.close()
        _connection = None
