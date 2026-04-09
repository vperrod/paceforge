"""Tests for user registration, login, and JWT authentication."""

from __future__ import annotations

import tempfile
from datetime import timedelta

import pytest

from paceforge.auth.database import (
    close_db,
    create_user,
    get_user_by_email,
    init_db,
    list_users,
    reset_connection,
    update_user_status,
)
from paceforge.auth.security import (
    create_access_token,
    decode_access_token,
    hash_password,
    verify_password,
)


@pytest.fixture()
def db_path(tmp_path):
    """Create a temp DB for each test."""
    path = str(tmp_path / "test.db")
    reset_connection()
    init_db(path)
    yield path
    reset_connection()


SECRET = "test-secret-key-for-jwt"


# ── Password hashing ─────────────────────────────────────────────────


class TestPasswordHashing:
    def test_hash_and_verify(self):
        h = hash_password("mypassword")
        assert verify_password("mypassword", h)

    def test_wrong_password_fails(self):
        h = hash_password("mypassword")
        assert not verify_password("wrongpassword", h)


# ── JWT tokens ────────────────────────────────────────────────────────


class TestJWT:
    def test_create_and_decode(self):
        token = create_access_token("user-123", "user", SECRET)
        payload = decode_access_token(token, SECRET)
        assert payload["sub"] == "user-123"
        assert payload["role"] == "user"

    def test_admin_role_in_token(self):
        token = create_access_token("admin-1", "admin", SECRET)
        payload = decode_access_token(token, SECRET)
        assert payload["role"] == "admin"

    def test_expired_token_raises(self):
        import jwt as pyjwt

        token = create_access_token(
            "user-1", "user", SECRET, expires_delta=timedelta(seconds=-1)
        )
        with pytest.raises(pyjwt.ExpiredSignatureError):
            decode_access_token(token, SECRET)

    def test_invalid_token_raises(self):
        import jwt as pyjwt

        with pytest.raises(pyjwt.InvalidTokenError):
            decode_access_token("garbage.token.here", SECRET)


# ── Database CRUD ─────────────────────────────────────────────────────


class TestUserDB:
    def test_create_pending_user(self, db_path):
        user = create_user(
            db_path,
            name="Alice",
            email="alice@example.com",
            password_hash=hash_password("password1"),
            reason="Training for marathon",
        )
        assert user["status"] == "pending"
        assert user["role"] == "user"
        assert user["name"] == "Alice"

    def test_duplicate_email_raises(self, db_path):
        create_user(db_path, name="A", email="dup@test.com", password_hash="x")
        with pytest.raises(Exception):
            create_user(db_path, name="B", email="dup@test.com", password_hash="y")

    def test_get_user_by_email(self, db_path):
        create_user(db_path, name="Bob", email="bob@test.com", password_hash="h")
        user = get_user_by_email(db_path, "bob@test.com")
        assert user is not None
        assert user["name"] == "Bob"

    def test_get_user_by_email_case_insensitive(self, db_path):
        create_user(db_path, name="Bob", email="Bob@Test.com", password_hash="h")
        user = get_user_by_email(db_path, "bob@test.com")
        assert user is not None

    def test_list_users_by_status(self, db_path):
        create_user(db_path, name="A", email="a@t.com", password_hash="h")
        create_user(
            db_path, name="B", email="b@t.com", password_hash="h",
            role="admin", status="approved",
        )
        pending = list_users(db_path, status="pending")
        assert len(pending) == 1
        assert pending[0]["name"] == "A"

        approved = list_users(db_path, status="approved")
        assert len(approved) == 1
        assert approved[0]["name"] == "B"

    def test_approve_user(self, db_path):
        user = create_user(db_path, name="C", email="c@t.com", password_hash="h")
        updated = update_user_status(db_path, user["id"], status="approved")
        assert updated["status"] == "approved"
        assert updated["approved_at"] is not None

    def test_reject_user(self, db_path):
        user = create_user(db_path, name="D", email="d@t.com", password_hash="h")
        updated = update_user_status(db_path, user["id"], status="rejected")
        assert updated["status"] == "rejected"
        assert updated["approved_at"] is None

    def test_nonexistent_user_returns_none(self, db_path):
        assert get_user_by_email(db_path, "no@one.com") is None
