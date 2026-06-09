"""AI response cache backed by SQLite."""

from __future__ import annotations

import hashlib
import logging
import sqlite3
import threading
import time

logger = logging.getLogger(__name__)

# Default TTLs per use case (seconds)
TTL_WORKOUT_ANALYSIS = 7 * 24 * 3600   # 7 days — workout data doesn't change
TTL_WEEKLY_OVERVIEW = 12 * 3600         # 12 hours — refreshes daily anyway
TTL_DIET_PLAN = 24 * 3600              # 1 day — macro targets shift with activity
TTL_PLAN_GENERATION = 30 * 24 * 3600   # 30 days — plans are explicitly regenerated
TTL_CHAT = 0                            # Never cache conversational chat


class AICache:
    """Hash-based AI response cache with TTL expiry."""

    _CREATE_SQL = """
        CREATE TABLE IF NOT EXISTS ai_cache (
            cache_key TEXT PRIMARY KEY,
            response TEXT NOT NULL,
            model TEXT NOT NULL,
            created_at REAL NOT NULL,
            expires_at REAL NOT NULL
        )
    """

    def __init__(self, db_path: str) -> None:
        self._db_path = db_path
        self._lock = threading.Lock()
        self._ensure_table()

    def _connect(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self._db_path, timeout=5)
        conn.execute("PRAGMA journal_mode=WAL")
        return conn

    def _ensure_table(self) -> None:
        with self._lock:
            conn = self._connect()
            try:
                conn.execute(self._CREATE_SQL)
                conn.commit()
            finally:
                conn.close()

    @staticmethod
    def make_key(system_prompt: str, user_message: str, model: str) -> str:
        raw = f"{system_prompt}|{user_message}|{model}"
        return hashlib.sha256(raw.encode()).hexdigest()

    def get(self, cache_key: str) -> str | None:
        with self._lock:
            conn = self._connect()
            try:
                row = conn.execute(
                    "SELECT response, expires_at FROM ai_cache WHERE cache_key = ?",
                    (cache_key,),
                ).fetchone()
                if row is None:
                    return None
                if row[1] < time.time():
                    conn.execute("DELETE FROM ai_cache WHERE cache_key = ?", (cache_key,))
                    conn.commit()
                    return None
                return row[0]
            finally:
                conn.close()

    def set(
        self,
        cache_key: str,
        response: str,
        model: str,
        ttl_seconds: int = 7 * 24 * 3600,
    ) -> None:
        now = time.time()
        with self._lock:
            conn = self._connect()
            try:
                conn.execute(
                    "INSERT OR REPLACE INTO ai_cache (cache_key, response, model, created_at, expires_at) "
                    "VALUES (?, ?, ?, ?, ?)",
                    (cache_key, response, model, now, now + ttl_seconds),
                )
                conn.commit()
            finally:
                conn.close()

    def cleanup(self) -> int:
        with self._lock:
            conn = self._connect()
            try:
                cursor = conn.execute(
                    "DELETE FROM ai_cache WHERE expires_at < ?", (time.time(),)
                )
                conn.commit()
                return cursor.rowcount
            finally:
                conn.close()
