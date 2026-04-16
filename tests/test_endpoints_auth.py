"""Integration tests for auth-protected API endpoints."""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from paceforge.auth.database import (
    create_user,
    init_db,
    reset_connection,
    update_user_status,
)
from paceforge.auth.security import create_access_token, hash_password


@pytest.fixture(autouse=True)
def _setup_db(tmp_path, monkeypatch):
    """Set up a temp DB and configure settings before importing the app."""
    db = str(tmp_path / "test.db")
    monkeypatch.setenv("PACEFORGE_DB_PATH", db)
    monkeypatch.setenv("PACEFORGE_JWT_SECRET", "test-secret")
    monkeypatch.setenv("PACEFORGE_ADMIN_EMAIL", "admin@test.com")
    monkeypatch.setenv("PACEFORGE_ADMIN_PASSWORD", "adminpass1")
    monkeypatch.setenv("PACEFORGE_CORS_ORIGINS", "http://localhost:8501")

    # Reset DB connection so it picks up the new path
    reset_connection()
    init_db(db)

    # Seed admin
    create_user(
        db,
        name="Admin",
        email="admin@test.com",
        password_hash=hash_password("adminpass1"),
        role="admin",
        status="approved",
    )

    yield db
    reset_connection()


@pytest.fixture()
def client(_setup_db, monkeypatch):
    """Create a test client with fresh settings."""
    # Re-import to pick up monkeypatched env
    from importlib import reload

    import paceforge.api.config as cfg_mod

    reload(cfg_mod)
    monkeypatch.setattr("paceforge.api.app.settings", cfg_mod.Settings())

    from paceforge.api.app import app

    return TestClient(app, raise_server_exceptions=False)


def _admin_token(db_path: str) -> str:
    from paceforge.auth.database import get_user_by_email

    admin = get_user_by_email(db_path, "admin@test.com")
    return create_access_token(admin["id"], "admin", "test-secret")


def _register_and_approve(db_path: str, email: str, password: str, name: str = "User") -> str:
    user = create_user(
        db_path,
        name=name,
        email=email,
        password_hash=hash_password(password),
    )
    update_user_status(db_path, user["id"], status="approved")
    return create_access_token(user["id"], "user", "test-secret")


class TestRegistration:
    def test_register_creates_pending_user(self, client, _setup_db):
        r = client.post(
            "/auth/register",
            json={
                "name": "New User",
                "email": "new@test.com",
                "password": "password123",
                "reason": "Want to train",
            },
        )
        assert r.status_code == 201
        assert "submitted" in r.json()["message"].lower()

    def test_duplicate_email_returns_409(self, client, _setup_db):
        client.post(
            "/auth/register",
            json={"name": "A", "email": "dup@test.com", "password": "password123"},
        )
        r = client.post(
            "/auth/register",
            json={"name": "B", "email": "dup@test.com", "password": "password456"},
        )
        assert r.status_code == 409

    def test_short_password_returns_422(self, client, _setup_db):
        r = client.post(
            "/auth/register",
            json={"name": "C", "email": "c@test.com", "password": "short"},
        )
        assert r.status_code == 422


class TestLogin:
    def test_login_wrong_password_returns_401(self, client, _setup_db):
        r = client.post(
            "/auth/login",
            json={"email": "admin@test.com", "password": "wrongpass"},
        )
        assert r.status_code == 401

    def test_login_pending_returns_403(self, client, _setup_db):
        client.post(
            "/auth/register",
            json={"name": "P", "email": "pending@test.com", "password": "password123"},
        )
        r = client.post(
            "/auth/login",
            json={"email": "pending@test.com", "password": "password123"},
        )
        assert r.status_code == 403

    def test_login_approved_returns_jwt(self, client, _setup_db):
        r = client.post(
            "/auth/login",
            json={"email": "admin@test.com", "password": "adminpass1"},
        )
        assert r.status_code == 200
        data = r.json()
        assert "access_token" in data
        assert data["role"] == "admin"
        assert data["name"] == "Admin"


class TestProtectedEndpoints:
    def test_unauthenticated_profile_returns_401(self, client, _setup_db):
        r = client.get("/profile")
        assert r.status_code == 401

    def test_unauthenticated_plan_returns_401(self, client, _setup_db):
        r = client.get("/plan")
        assert r.status_code == 401

    def test_valid_token_reaches_endpoint(self, client, _setup_db):
        token = _register_and_approve(_setup_db, "user@test.com", "pass1234")
        r = client.get(
            "/plan",
            headers={"Authorization": f"Bearer {token}"},
        )
        # 404 = no plan yet, which means auth passed
        assert r.status_code == 404


class TestAdminEndpoints:
    def test_admin_can_list_users(self, client, _setup_db):
        token = _admin_token(_setup_db)
        r = client.get(
            "/admin/users",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert r.status_code == 200
        assert isinstance(r.json(), list)

    def test_admin_can_approve_user(self, client, _setup_db):
        # Register a pending user
        client.post(
            "/auth/register",
            json={"name": "Pending", "email": "p@test.com", "password": "password123"},
        )
        from paceforge.auth.database import get_user_by_email

        pending = get_user_by_email(_setup_db, "p@test.com")

        token = _admin_token(_setup_db)
        r = client.patch(
            f"/admin/users/{pending['id']}",
            json={"status": "approved"},
            headers={"Authorization": f"Bearer {token}"},
        )
        assert r.status_code == 200
        assert r.json()["status"] == "approved"

    def test_non_admin_gets_403(self, client, _setup_db):
        token = _register_and_approve(_setup_db, "regular@test.com", "pass1234")
        r = client.get(
            "/admin/users",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert r.status_code == 403

    def test_admin_can_reject_user(self, client, _setup_db):
        client.post(
            "/auth/register",
            json={"name": "Rej", "email": "rej@test.com", "password": "password123"},
        )
        from paceforge.auth.database import get_user_by_email

        pending = get_user_by_email(_setup_db, "rej@test.com")
        token = _admin_token(_setup_db)
        r = client.patch(
            f"/admin/users/{pending['id']}",
            json={"status": "rejected"},
            headers={"Authorization": f"Bearer {token}"},
        )
        assert r.status_code == 200
        assert r.json()["status"] == "rejected"

    def test_admin_filter_by_status(self, client, _setup_db):
        token = _admin_token(_setup_db)
        r = client.get(
            "/admin/users?status=approved",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert r.status_code == 200
        users = r.json()
        assert all(u["status"] == "approved" for u in users)

    def test_admin_can_get_user_data(self, client, _setup_db):
        _register_and_approve(_setup_db, "data@test.com", "pass1234", name="DataUser")
        from paceforge.auth.database import get_user_by_email

        user = get_user_by_email(_setup_db, "data@test.com")
        token = _admin_token(_setup_db)
        r = client.get(
            f"/admin/users/{user['id']}/data",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert r.status_code == 200
        data = r.json()
        assert data["user"]["email"] == "data@test.com"

    def test_admin_users_include_last_login(self, client, _setup_db):
        token = _admin_token(_setup_db)
        r = client.get(
            "/admin/users",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert r.status_code == 200
        for u in r.json():
            assert "last_login" in u


class TestForgotPassword:
    def test_forgot_password_existing_email_returns_200(self, client, _setup_db):
        r = client.post(
            "/auth/forgot-password",
            json={"email": "admin@test.com"},
        )
        assert r.status_code == 200
        assert "reset link" in r.json()["message"].lower()

    def test_forgot_password_nonexistent_email_returns_200(self, client, _setup_db):
        r = client.post(
            "/auth/forgot-password",
            json={"email": "nobody@test.com"},
        )
        assert r.status_code == 200  # No email enumeration

    def test_reset_password_invalid_token_returns_400(self, client, _setup_db):
        r = client.post(
            "/auth/reset-password",
            json={"token": "invalid-token", "new_password": "newpass123"},
        )
        assert r.status_code == 400

    def test_reset_password_valid_token_works(self, client, _setup_db):
        import hashlib
        import secrets
        from datetime import UTC, datetime, timedelta

        from paceforge.auth.database import (
            create_password_reset_token,
            get_user_by_email,
        )

        user = get_user_by_email(_setup_db, "admin@test.com")
        raw_token = secrets.token_urlsafe(32)
        token_hash = hashlib.sha256(raw_token.encode()).hexdigest()
        expires = (datetime.now(UTC) + timedelta(hours=1)).isoformat()
        create_password_reset_token(_setup_db, user["id"], token_hash, expires)

        r = client.post(
            "/auth/reset-password",
            json={"token": raw_token, "new_password": "newpassword1"},
        )
        assert r.status_code == 200

        # Can login with new password
        r2 = client.post(
            "/auth/login",
            json={"email": "admin@test.com", "password": "newpassword1"},
        )
        assert r2.status_code == 200

    def test_reset_password_expired_token_returns_400(self, client, _setup_db):
        import hashlib
        import secrets
        from datetime import UTC, datetime, timedelta

        from paceforge.auth.database import (
            create_password_reset_token,
            get_user_by_email,
        )

        user = get_user_by_email(_setup_db, "admin@test.com")
        raw_token = secrets.token_urlsafe(32)
        token_hash = hashlib.sha256(raw_token.encode()).hexdigest()
        expires = (datetime.now(UTC) - timedelta(hours=1)).isoformat()
        create_password_reset_token(_setup_db, user["id"], token_hash, expires)

        r = client.post(
            "/auth/reset-password",
            json={"token": raw_token, "new_password": "newpassword1"},
        )
        assert r.status_code == 400

    def test_login_tracks_last_login(self, client, _setup_db):
        r = client.post(
            "/auth/login",
            json={"email": "admin@test.com", "password": "adminpass1"},
        )
        assert r.status_code == 200
        from paceforge.auth.database import get_user_by_email

        user = get_user_by_email(_setup_db, "admin@test.com")
        assert user["last_login"] is not None
