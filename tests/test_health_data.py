"""Tests for health data endpoints (Apple Health / Google Health Connect)."""

from __future__ import annotations

import json

import pytest
from fastapi.testclient import TestClient

from paceforge.auth.database import (
    create_user,
    init_db,
    load_user_data,
    reset_connection,
    save_user_data,
)
from paceforge.auth.security import create_access_token, hash_password


@pytest.fixture(autouse=True)
def _setup_db(tmp_path, monkeypatch):
    db = str(tmp_path / "test.db")
    monkeypatch.setenv("PACEFORGE_DB_PATH", db)
    monkeypatch.setenv("PACEFORGE_JWT_SECRET", "test-secret")
    monkeypatch.setenv("PACEFORGE_ADMIN_EMAIL", "admin@test.com")
    monkeypatch.setenv("PACEFORGE_ADMIN_PASSWORD", "adminpass1")
    monkeypatch.setenv("PACEFORGE_CORS_ORIGINS", "http://localhost:8501")
    reset_connection()
    init_db(db)
    create_user(
        db,
        name="Health User",
        email="health@test.com",
        password_hash=hash_password("pass123"),
        role="user",
        status="approved",
    )
    yield db
    reset_connection()


@pytest.fixture()
def client(_setup_db, monkeypatch):
    from importlib import reload

    import paceforge.api.config as cfg_mod
    reload(cfg_mod)
    monkeypatch.setattr("paceforge.api.app.settings", cfg_mod.Settings())
    from paceforge.api.app import app
    return TestClient(app, raise_server_exceptions=False)


@pytest.fixture()
def auth_header(_setup_db):
    from paceforge.auth.database import get_user_by_email
    user = get_user_by_email(_setup_db, "health@test.com")
    token = create_access_token(user["id"], "user", "test-secret")
    return {"Authorization": f"Bearer {token}"}


# ── GET /health/data ──


def test_get_health_data_empty(client, auth_header):
    r = client.get("/health/data", headers=auth_header)
    assert r.status_code == 200
    data = r.json()
    assert data["sources"] == []
    assert data["last_sync"] is None


def test_get_health_data_with_stored_data(client, auth_header, _setup_db):
    from paceforge.auth.database import get_user_by_email
    user = get_user_by_email(_setup_db, "health@test.com")
    health = {
        "sources": ["apple_health"],
        "last_sync": "2026-04-15T10:00:00",
        "body_composition": {
            "height_cm": 175.0,
            "weight_kg": [{"date": "2026-04-15", "value": 72.5, "source": "apple_health"}],
            "bmi": [],
            "body_fat_pct": [],
            "lean_body_mass_kg": [],
        },
    }
    save_user_data(_setup_db, user["id"], health_json=json.dumps(health))
    r = client.get("/health/data", headers=auth_header)
    assert r.status_code == 200
    data = r.json()
    assert data["sources"] == ["apple_health"]
    assert len(data["body_composition"]["weight_kg"]) == 1
    assert data["body_composition"]["weight_kg"][0]["value"] == 72.5


# ── POST /health/data ──


def test_post_health_data_stores_data(client, auth_header):
    payload = {
        "sources": ["apple_health"],
        "body_composition": {
            "height_cm": 180.0,
            "weight_kg": [
                {"date": "2026-04-10", "value": 75.0, "source": "apple_health"},
                {"date": "2026-04-15", "value": 74.5, "source": "apple_health"},
            ],
            "bmi": [
                {"date": "2026-04-15", "value": 23.0, "source": "apple_health"},
            ],
            "body_fat_pct": [
                {"date": "2026-04-15", "value": 15.2, "source": "apple_health"},
            ],
            "lean_body_mass_kg": [
                {"date": "2026-04-15", "value": 63.2, "source": "apple_health"},
            ],
        },
    }
    r = client.post("/health/data", json=payload, headers=auth_header)
    assert r.status_code == 200
    data = r.json()
    assert "apple_health" in data["sources"]
    assert data["last_sync"] is not None
    assert len(data["body_composition"]["weight_kg"]) == 2
    assert data["body_composition"]["height_cm"] == 180.0

    # Verify persisted
    r2 = client.get("/health/data", headers=auth_header)
    assert r2.status_code == 200
    assert len(r2.json()["body_composition"]["weight_kg"]) == 2


def test_post_health_data_deduplicates_by_date(client, auth_header):
    # First post
    payload1 = {
        "sources": ["apple_health"],
        "body_composition": {
            "weight_kg": [{"date": "2026-04-15", "value": 75.0, "source": "apple_health"}],
        },
    }
    client.post("/health/data", json=payload1, headers=auth_header)

    # Second post with same date, different value — should overwrite
    payload2 = {
        "sources": ["apple_health"],
        "body_composition": {
            "weight_kg": [{"date": "2026-04-15", "value": 74.0, "source": "apple_health"}],
        },
    }
    r = client.post("/health/data", json=payload2, headers=auth_header)
    data = r.json()
    weights = data["body_composition"]["weight_kg"]
    assert len(weights) == 1
    assert weights[0]["value"] == 74.0  # New value wins


def test_post_health_data_trims_to_90_days(client, auth_header):
    payload = {
        "sources": ["google_health_connect"],
        "body_composition": {
            "weight_kg": [
                {"date": "2025-01-01", "value": 80.0, "source": "google_health_connect"},  # > 90 days ago
                {"date": "2026-04-15", "value": 74.0, "source": "google_health_connect"},  # recent
            ],
        },
    }
    r = client.post("/health/data", json=payload, headers=auth_header)
    data = r.json()
    weights = data["body_composition"]["weight_kg"]
    assert len(weights) == 1
    assert weights[0]["date"] == "2026-04-15"


def test_post_health_data_merges_sources(client, auth_header):
    # Post from Apple Health
    client.post("/health/data", json={
        "sources": ["apple_health"],
        "body_composition": {
            "weight_kg": [{"date": "2026-04-14", "value": 75.0, "source": "apple_health"}],
        },
    }, headers=auth_header)

    # Post from Google Health Connect
    r = client.post("/health/data", json={
        "sources": ["google_health_connect"],
        "body_composition": {
            "weight_kg": [{"date": "2026-04-15", "value": 74.5, "source": "google_health_connect"}],
        },
    }, headers=auth_header)
    data = r.json()
    assert "apple_health" in data["sources"]
    assert "google_health_connect" in data["sources"]
    assert len(data["body_composition"]["weight_kg"]) == 2


# ── Database: health_json column ──


def test_save_load_health_json(_setup_db):
    from paceforge.auth.database import get_user_by_email
    user = get_user_by_email(_setup_db, "health@test.com")
    health = {"sources": ["test"], "body_composition": {"weight_kg": []}}
    save_user_data(_setup_db, user["id"], health_json=json.dumps(health))
    loaded = load_user_data(_setup_db, user["id"])
    assert loaded is not None
    assert loaded["health_json"] is not None
    parsed = json.loads(loaded["health_json"])
    assert parsed["sources"] == ["test"]
