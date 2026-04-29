"""SQLite database layer for user management."""

from __future__ import annotations

import sqlite3
import uuid
from datetime import UTC, datetime
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
    garmin_email  TEXT,
    last_login    TEXT
);

CREATE TABLE IF NOT EXISTS user_data (
    user_id         TEXT PRIMARY KEY REFERENCES users(id),
    plan_json       TEXT,
    activities_json TEXT,
    profile_json    TEXT,
    hyrox_json      TEXT,
    preferences_json TEXT,
    updated_at      TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS friends (
    id            TEXT PRIMARY KEY,
    requester_id  TEXT NOT NULL REFERENCES users(id),
    recipient_id  TEXT NOT NULL REFERENCES users(id),
    status        TEXT NOT NULL DEFAULT 'pending' CHECK(status IN ('pending', 'accepted', 'rejected')),
    created_at    TEXT NOT NULL,
    responded_at  TEXT,
    UNIQUE(requester_id, recipient_id)
);

CREATE TABLE IF NOT EXISTS feed_events (
    id          TEXT PRIMARY KEY,
    user_id     TEXT NOT NULL REFERENCES users(id),
    event_type  TEXT NOT NULL CHECK(event_type IN ('activity', 'plan', 'pb', 'hyrox', 'milestone', 'welcome')),
    title       TEXT NOT NULL,
    body        TEXT,
    metadata    TEXT,
    created_at  TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS feed_likes (
    id        TEXT PRIMARY KEY,
    event_id  TEXT NOT NULL REFERENCES feed_events(id) ON DELETE CASCADE,
    user_id   TEXT NOT NULL REFERENCES users(id),
    created_at TEXT NOT NULL,
    UNIQUE(event_id, user_id)
);

CREATE TABLE IF NOT EXISTS feed_comments (
    id        TEXT PRIMARY KEY,
    event_id  TEXT NOT NULL REFERENCES feed_events(id) ON DELETE CASCADE,
    user_id   TEXT NOT NULL REFERENCES users(id),
    body      TEXT NOT NULL,
    created_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS refresh_tokens (
    id         TEXT PRIMARY KEY,
    user_id    TEXT NOT NULL REFERENCES users(id),
    token_hash TEXT NOT NULL,
    expires_at TEXT NOT NULL,
    revoked    INTEGER NOT NULL DEFAULT 0,
    created_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS device_tokens (
    id         TEXT PRIMARY KEY,
    user_id    TEXT NOT NULL REFERENCES users(id),
    platform   TEXT NOT NULL CHECK(platform IN ('ios', 'android', 'web')),
    token      TEXT NOT NULL,
    created_at TEXT NOT NULL,
    UNIQUE(user_id, token)
);

CREATE TABLE IF NOT EXISTS password_reset_tokens (
    id         TEXT PRIMARY KEY,
    user_id    TEXT NOT NULL REFERENCES users(id),
    token_hash TEXT NOT NULL,
    expires_at TEXT NOT NULL,
    used_at    TEXT,
    created_at TEXT NOT NULL
);
"""

_MIGRATIONS = [
    # Add hyrox_json column if it doesn't exist (for existing databases)
    "ALTER TABLE user_data ADD COLUMN hyrox_json TEXT",
    # Add preferences_json column for user preferences (Strava tokens, activity analyses, etc.)
    "ALTER TABLE user_data ADD COLUMN preferences_json TEXT",
    # Create refresh_tokens and device_tokens for mobile support
    """CREATE TABLE IF NOT EXISTS refresh_tokens (
        id TEXT PRIMARY KEY, user_id TEXT NOT NULL REFERENCES users(id),
        token_hash TEXT NOT NULL, expires_at TEXT NOT NULL,
        revoked INTEGER NOT NULL DEFAULT 0, created_at TEXT NOT NULL)""",
    """CREATE TABLE IF NOT EXISTS device_tokens (
        id TEXT PRIMARY KEY, user_id TEXT NOT NULL REFERENCES users(id),
        platform TEXT NOT NULL CHECK(platform IN ('ios', 'android', 'web')),
        token TEXT NOT NULL, created_at TEXT NOT NULL, UNIQUE(user_id, token))""",
    # Add health_json column for Apple Health / Google Health Connect data
    "ALTER TABLE user_data ADD COLUMN health_json TEXT",
    # Add activity_details_json for cached per-activity splits/HR zones
    "ALTER TABLE user_data ADD COLUMN activity_details_json TEXT",
    # Add weekly_overview_json for AI weekly analysis cache
    "ALTER TABLE user_data ADD COLUMN weekly_overview_json TEXT",
    # Add last_login column to users table
    "ALTER TABLE users ADD COLUMN last_login TEXT",
    # Create password_reset_tokens table
    """CREATE TABLE IF NOT EXISTS password_reset_tokens (
        id TEXT PRIMARY KEY, user_id TEXT NOT NULL REFERENCES users(id),
        token_hash TEXT NOT NULL, expires_at TEXT NOT NULL,
        used_at TEXT, created_at TEXT NOT NULL)""",
    # Add diet_json column for diet planning & weight management
    "ALTER TABLE user_data ADD COLUMN diet_json TEXT",
]


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
        # Apply migrations for existing databases
        for sql in _MIGRATIONS:
            try:
                conn.execute(sql)
                conn.commit()
            except Exception:
                pass  # Column already exists
        # Migrate feed_events CHECK constraint to add 'welcome' event type
        try:
            info = conn.execute("SELECT sql FROM sqlite_master WHERE type='table' AND name='feed_events'").fetchone()
            if info and "'welcome'" not in (info[0] or ""):
                conn.executescript("""
                    CREATE TABLE feed_events_new (
                        id TEXT PRIMARY KEY, user_id TEXT NOT NULL REFERENCES users(id),
                        event_type TEXT NOT NULL CHECK(event_type IN ('activity','plan','pb','hyrox','milestone','welcome')),
                        title TEXT NOT NULL, body TEXT, metadata TEXT, created_at TEXT NOT NULL);
                    INSERT INTO feed_events_new SELECT * FROM feed_events;
                    DROP TABLE feed_events;
                    ALTER TABLE feed_events_new RENAME TO feed_events;
                """)
        except Exception:
            pass


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
    now = datetime.now(UTC).isoformat()
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
    now = datetime.now(UTC).isoformat() if status == "approved" else None
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


def update_user_profile(
    db_path: str,
    user_id: str,
    *,
    name: str | None = None,
    email: str | None = None,
    password_hash: str | None = None,
) -> dict | None:
    """Update editable profile fields. Returns updated user dict."""
    fields: list[str] = []
    values: list[str] = []
    if name is not None:
        fields.append("name = ?")
        values.append(name)
    if email is not None:
        fields.append("email = ?")
        values.append(email)
    if password_hash is not None:
        fields.append("password_hash = ?")
        values.append(password_hash)
    if not fields:
        return get_user_by_id(db_path, user_id)
    values.append(user_id)
    with _lock:
        conn = _get_conn(db_path)
        conn.execute(
            f"UPDATE users SET {', '.join(fields)} WHERE id = ?",
            values,
        )
        conn.commit()
    return get_user_by_id(db_path, user_id)

def update_last_login(db_path: str, user_id: str) -> None:
    """Set the last_login timestamp to now."""
    now = datetime.now(UTC).isoformat()
    with _lock:
        conn = _get_conn(db_path)
        conn.execute("UPDATE users SET last_login = ? WHERE id = ?", (now, user_id))
        conn.commit()


# ── Password reset tokens ────────────────────────────────────────────


def create_password_reset_token(db_path: str, user_id: str, token_hash: str, expires_at: str) -> str:
    """Insert a hashed password-reset token. Returns the row id."""
    token_id = str(uuid.uuid4())
    now = datetime.now(UTC).isoformat()
    with _lock:
        conn = _get_conn(db_path)
        conn.execute(
            "INSERT INTO password_reset_tokens (id, user_id, token_hash, expires_at, created_at) "
            "VALUES (?, ?, ?, ?, ?)",
            (token_id, user_id, token_hash, expires_at, now),
        )
        conn.commit()
    return token_id


def get_valid_reset_token(db_path: str, token_hash: str) -> dict | None:
    """Return the reset-token row if it exists, is unused, and not yet expired."""
    now = datetime.now(UTC).isoformat()
    with _lock:
        conn = _get_conn(db_path)
        row = conn.execute(
            "SELECT * FROM password_reset_tokens "
            "WHERE token_hash = ? AND used_at IS NULL AND expires_at > ?",
            (token_hash, now),
        ).fetchone()
    return _row_to_dict(row)


def mark_reset_token_used(db_path: str, token_id: str) -> None:
    """Mark a password-reset token as used."""
    now = datetime.now(UTC).isoformat()
    with _lock:
        conn = _get_conn(db_path)
        conn.execute(
            "UPDATE password_reset_tokens SET used_at = ? WHERE id = ?",
            (now, token_id),
        )
        conn.commit()


def revoke_all_refresh_tokens(db_path: str, user_id: str) -> None:
    """Revoke every active refresh token for a user (e.g. after password reset)."""
    with _lock:
        conn = _get_conn(db_path)
        conn.execute(
            "UPDATE refresh_tokens SET revoked = 1 WHERE user_id = ? AND revoked = 0",
            (user_id,),
        )
        conn.commit()

# ── User data persistence ────────────────────────────────────────────


def save_user_data(
    db_path: str,
    user_id: str,
    *,
    plan_json: str | None = None,
    activities_json: str | None = None,
    profile_json: str | None = None,
    hyrox_json: str | None = None,
    preferences_json: str | None = None,
    health_json: str | None = None,
    activity_details_json: str | None = None,
    weekly_overview_json: str | None = None,
    diet_json: str | None = None,
) -> None:
    """Upsert cached user data (plan, activities, profile, hyrox, preferences, health, activity details, weekly overview, diet)."""
    now = datetime.now(UTC).isoformat()
    with _lock:
        conn = _get_conn(db_path)
        existing = conn.execute(
            "SELECT user_id FROM user_data WHERE user_id = ?", (user_id,)
        ).fetchone()
        if existing:
            sets: list[str] = ["updated_at = ?"]
            vals: list[str] = [now]
            if plan_json is not None:
                sets.append("plan_json = ?")
                vals.append(plan_json)
            if activities_json is not None:
                sets.append("activities_json = ?")
                vals.append(activities_json)
            if profile_json is not None:
                sets.append("profile_json = ?")
                vals.append(profile_json)
            if hyrox_json is not None:
                sets.append("hyrox_json = ?")
                vals.append(hyrox_json)
            if preferences_json is not None:
                sets.append("preferences_json = ?")
                vals.append(preferences_json)
            if health_json is not None:
                sets.append("health_json = ?")
                vals.append(health_json)
            if activity_details_json is not None:
                sets.append("activity_details_json = ?")
                vals.append(activity_details_json)
            if weekly_overview_json is not None:
                sets.append("weekly_overview_json = ?")
                vals.append(weekly_overview_json)
            if diet_json is not None:
                sets.append("diet_json = ?")
                vals.append(diet_json)
            vals.append(user_id)
            conn.execute(
                f"UPDATE user_data SET {', '.join(sets)} WHERE user_id = ?",
                vals,
            )
        else:
            conn.execute(
                "INSERT INTO user_data (user_id, plan_json, activities_json, profile_json, hyrox_json, preferences_json, health_json, updated_at) "
                "VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
                (user_id, plan_json, activities_json, profile_json, hyrox_json, preferences_json, health_json, now),
            )
        conn.commit()


def load_user_data(db_path: str, user_id: str) -> dict | None:
    """Load cached user data. Returns dict with plan_json, activities_json, profile_json or None."""
    with _lock:
        conn = _get_conn(db_path)
        row = conn.execute(
            "SELECT * FROM user_data WHERE user_id = ?", (user_id,)
        ).fetchone()
    return _row_to_dict(row)


def reset_connection() -> None:
    """Reset DB connection (useful for tests with temp DBs)."""
    global _connection
    with _lock:
        if _connection:
            _connection.close()
        _connection = None


# ── Friends ───────────────────────────────────────────────────────────


def search_users(db_path: str, query: str, *, exclude_user_id: str | None = None) -> list[dict]:
    """Search approved users by name or email (partial match)."""
    with _lock:
        conn = _get_conn(db_path)
        rows = conn.execute(
            "SELECT id, name, email FROM users "
            "WHERE status = 'approved' AND (name LIKE ? OR email LIKE ?) "
            "ORDER BY name LIMIT 20",
            (f"%{query}%", f"%{query}%"),
        ).fetchall()
    results = [dict(r) for r in rows]
    if exclude_user_id:
        results = [r for r in results if r["id"] != exclude_user_id]
    return results


def send_friend_request(db_path: str, requester_id: str, recipient_id: str) -> dict | None:
    """Send a friend request. Returns the friendship row or None if already exists."""
    if requester_id == recipient_id:
        return None
    fid = str(uuid.uuid4())
    now = datetime.now(UTC).isoformat()
    with _lock:
        conn = _get_conn(db_path)
        # Check for existing relationship in either direction
        existing = conn.execute(
            "SELECT * FROM friends WHERE "
            "(requester_id = ? AND recipient_id = ?) OR "
            "(requester_id = ? AND recipient_id = ?)",
            (requester_id, recipient_id, recipient_id, requester_id),
        ).fetchone()
        if existing:
            return _row_to_dict(existing)
        conn.execute(
            "INSERT INTO friends (id, requester_id, recipient_id, status, created_at) "
            "VALUES (?, ?, ?, 'pending', ?)",
            (fid, requester_id, recipient_id, now),
        )
        conn.commit()
        row = conn.execute("SELECT * FROM friends WHERE id = ?", (fid,)).fetchone()
    return _row_to_dict(row)


def respond_friend_request(db_path: str, friendship_id: str, *, accept: bool) -> dict | None:
    """Accept or reject a friend request."""
    now = datetime.now(UTC).isoformat()
    status = "accepted" if accept else "rejected"
    with _lock:
        conn = _get_conn(db_path)
        conn.execute(
            "UPDATE friends SET status = ?, responded_at = ? WHERE id = ? AND status = 'pending'",
            (status, now, friendship_id),
        )
        conn.commit()
        row = conn.execute("SELECT * FROM friends WHERE id = ?", (friendship_id,)).fetchone()
    return _row_to_dict(row)


def remove_friend(db_path: str, friendship_id: str) -> None:
    """Remove a friendship (either party can remove)."""
    with _lock:
        conn = _get_conn(db_path)
        conn.execute("DELETE FROM friends WHERE id = ?", (friendship_id,))
        conn.commit()


def list_friends(db_path: str, user_id: str) -> list[dict]:
    """List accepted friends with their user info."""
    with _lock:
        conn = _get_conn(db_path)
        rows = conn.execute(
            "SELECT f.id AS friendship_id, f.created_at AS friends_since, "
            "u.id, u.name, u.email "
            "FROM friends f "
            "JOIN users u ON u.id = CASE WHEN f.requester_id = ? THEN f.recipient_id ELSE f.requester_id END "
            "WHERE (f.requester_id = ? OR f.recipient_id = ?) AND f.status = 'accepted' "
            "ORDER BY u.name",
            (user_id, user_id, user_id),
        ).fetchall()
    return [dict(r) for r in rows]


def get_friend_ids(db_path: str, user_id: str) -> list[str]:
    """Return IDs of all accepted friends."""
    with _lock:
        conn = _get_conn(db_path)
        rows = conn.execute(
            "SELECT CASE WHEN requester_id = ? THEN recipient_id ELSE requester_id END AS friend_id "
            "FROM friends "
            "WHERE (requester_id = ? OR recipient_id = ?) AND status = 'accepted'",
            (user_id, user_id, user_id),
        ).fetchall()
    return [r["friend_id"] for r in rows]


def list_pending_requests(db_path: str, user_id: str) -> list[dict]:
    """List incoming pending friend requests."""
    with _lock:
        conn = _get_conn(db_path)
        rows = conn.execute(
            "SELECT f.id AS friendship_id, f.created_at, u.id, u.name, u.email "
            "FROM friends f JOIN users u ON u.id = f.requester_id "
            "WHERE f.recipient_id = ? AND f.status = 'pending' "
            "ORDER BY f.created_at DESC",
            (user_id,),
        ).fetchall()
    return [dict(r) for r in rows]


def list_sent_requests(db_path: str, user_id: str) -> list[dict]:
    """List outgoing pending friend requests."""
    with _lock:
        conn = _get_conn(db_path)
        rows = conn.execute(
            "SELECT f.id AS friendship_id, f.created_at, u.id, u.name, u.email "
            "FROM friends f JOIN users u ON u.id = f.recipient_id "
            "WHERE f.requester_id = ? AND f.status = 'pending' "
            "ORDER BY f.created_at DESC",
            (user_id,),
        ).fetchall()
    return [dict(r) for r in rows]


# ── Feed ──────────────────────────────────────────────────────────────


def create_feed_event(
    db_path: str,
    user_id: str,
    *,
    event_type: str,
    title: str,
    body: str | None = None,
    metadata: dict | None = None,
) -> dict:
    """Create a new feed event."""
    import json as _json
    eid = str(uuid.uuid4())
    now = datetime.now(UTC).isoformat()
    meta_str = _json.dumps(metadata) if metadata else None
    with _lock:
        conn = _get_conn(db_path)
        conn.execute(
            "INSERT INTO feed_events (id, user_id, event_type, title, body, metadata, created_at) "
            "VALUES (?, ?, ?, ?, ?, ?, ?)",
            (eid, user_id, event_type, title, body, meta_str, now),
        )
        conn.commit()
        row = conn.execute("SELECT * FROM feed_events WHERE id = ?", (eid,)).fetchone()
    return dict(row)


def update_feed_event_metadata(db_path: str, event_id: str, metadata: dict) -> None:
    """Update the metadata JSON of an existing feed event."""
    import json as _json
    meta_str = _json.dumps(metadata)
    with _lock:
        conn = _get_conn(db_path)
        conn.execute("UPDATE feed_events SET metadata = ? WHERE id = ?", (meta_str, event_id))
        conn.commit()


def get_feed(db_path: str, user_ids: list[str], *, limit: int = 20, offset: int = 0) -> list[dict]:
    """Get feed events for a list of user IDs, with like/comment counts and user info."""
    if not user_ids:
        return []
    placeholders = ",".join("?" for _ in user_ids)
    with _lock:
        conn = _get_conn(db_path)
        rows = conn.execute(
            f"SELECT e.*, u.name AS user_name, "
            f"(SELECT COUNT(*) FROM feed_likes WHERE event_id = e.id) AS like_count, "
            f"(SELECT COUNT(*) FROM feed_comments WHERE event_id = e.id) AS comment_count "
            f"FROM feed_events e JOIN users u ON u.id = e.user_id "
            f"WHERE e.user_id IN ({placeholders}) OR e.event_type = 'welcome' "
            f"ORDER BY e.created_at DESC LIMIT ? OFFSET ?",
            (*user_ids, limit, offset),
        ).fetchall()
    return [dict(r) for r in rows]


def toggle_like(db_path: str, event_id: str, user_id: str) -> bool:
    """Toggle a like on a feed event. Returns True if liked, False if unliked."""
    with _lock:
        conn = _get_conn(db_path)
        existing = conn.execute(
            "SELECT id FROM feed_likes WHERE event_id = ? AND user_id = ?",
            (event_id, user_id),
        ).fetchone()
        if existing:
            conn.execute("DELETE FROM feed_likes WHERE id = ?", (existing["id"],))
            conn.commit()
            return False
        else:
            lid = str(uuid.uuid4())
            now = datetime.now(UTC).isoformat()
            conn.execute(
                "INSERT INTO feed_likes (id, event_id, user_id, created_at) VALUES (?, ?, ?, ?)",
                (lid, event_id, user_id, now),
            )
            conn.commit()
            return True


def get_user_likes(db_path: str, user_id: str, event_ids: list[str]) -> set[str]:
    """Return set of event_ids that user has liked."""
    if not event_ids:
        return set()
    placeholders = ",".join("?" for _ in event_ids)
    with _lock:
        conn = _get_conn(db_path)
        rows = conn.execute(
            f"SELECT event_id FROM feed_likes WHERE user_id = ? AND event_id IN ({placeholders})",
            (user_id, *event_ids),
        ).fetchall()
    return {r["event_id"] for r in rows}


def add_comment(db_path: str, event_id: str, user_id: str, body: str) -> dict:
    """Add a comment to a feed event."""
    cid = str(uuid.uuid4())
    now = datetime.now(UTC).isoformat()
    with _lock:
        conn = _get_conn(db_path)
        conn.execute(
            "INSERT INTO feed_comments (id, event_id, user_id, body, created_at) VALUES (?, ?, ?, ?, ?)",
            (cid, event_id, user_id, body, now),
        )
        conn.commit()
        row = conn.execute(
            "SELECT c.*, u.name AS user_name FROM feed_comments c "
            "JOIN users u ON u.id = c.user_id WHERE c.id = ?",
            (cid,),
        ).fetchone()
    return dict(row)


def get_comments(db_path: str, event_id: str) -> list[dict]:
    """Get all comments for a feed event."""
    with _lock:
        conn = _get_conn(db_path)
        rows = conn.execute(
            "SELECT c.*, u.name AS user_name FROM feed_comments c "
            "JOIN users u ON u.id = c.user_id "
            "WHERE c.event_id = ? ORDER BY c.created_at ASC",
            (event_id,),
        ).fetchall()
    return [dict(r) for r in rows]


# ── Refresh Tokens ───────────────────────────────────────────────────

import hashlib


def _hash_token(token: str) -> str:
    return hashlib.sha256(token.encode()).hexdigest()


def store_refresh_token(db_path: str, user_id: str, token: str, expires_at: str) -> str:
    """Store a hashed refresh token. Returns the record id."""
    rid = uuid.uuid4().hex
    now = datetime.now(UTC).isoformat()
    with _lock:
        conn = _get_conn(db_path)
        conn.execute(
            "INSERT INTO refresh_tokens (id, user_id, token_hash, expires_at, created_at) "
            "VALUES (?, ?, ?, ?, ?)",
            (rid, user_id, _hash_token(token), expires_at, now),
        )
        conn.commit()
    return rid


def validate_refresh_token(db_path: str, user_id: str, token: str) -> bool:
    """Check if a refresh token is valid (exists, not revoked, not expired)."""
    token_hash = _hash_token(token)
    now = datetime.now(UTC).isoformat()
    with _lock:
        conn = _get_conn(db_path)
        row = conn.execute(
            "SELECT id FROM refresh_tokens "
            "WHERE user_id = ? AND token_hash = ? AND revoked = 0 AND expires_at > ?",
            (user_id, token_hash, now),
        ).fetchone()
    return row is not None


def revoke_refresh_token(db_path: str, user_id: str, token: str) -> None:
    """Revoke a specific refresh token."""
    token_hash = _hash_token(token)
    with _lock:
        conn = _get_conn(db_path)
        conn.execute(
            "UPDATE refresh_tokens SET revoked = 1 WHERE user_id = ? AND token_hash = ?",
            (user_id, token_hash),
        )
        conn.commit()


# ── Device Tokens (Push Notifications) ───────────────────────────────


def register_device_token(db_path: str, user_id: str, platform: str, token: str) -> dict:
    """Register a device push notification token. Upserts on (user_id, token)."""
    did = uuid.uuid4().hex
    now = datetime.now(UTC).isoformat()
    with _lock:
        conn = _get_conn(db_path)
        conn.execute(
            "INSERT INTO device_tokens (id, user_id, platform, token, created_at) "
            "VALUES (?, ?, ?, ?, ?) "
            "ON CONFLICT(user_id, token) DO UPDATE SET platform = excluded.platform, created_at = excluded.created_at",
            (did, user_id, platform, token, now),
        )
        conn.commit()
    return {"id": did, "user_id": user_id, "platform": platform, "token": token}


def remove_device_token(db_path: str, user_id: str, token: str) -> None:
    """Remove a device token."""
    with _lock:
        conn = _get_conn(db_path)
        conn.execute(
            "DELETE FROM device_tokens WHERE user_id = ? AND token = ?",
            (user_id, token),
        )
        conn.commit()
