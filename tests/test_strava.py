"""Tests for Strava OAuth client and activity push logic."""

from __future__ import annotations

from datetime import UTC
from unittest.mock import MagicMock, patch

from paceforge.strava.client import StravaClient

# ── Auth URL Construction ────────────────────────────────────────────


class TestStravaAuthURL:
    def test_auth_url_contains_required_params(self):
        client = StravaClient(client_id="12345", client_secret="secret")
        url = client.get_auth_url(
            redirect_uri="https://example.com/callback",
            state="jwt-token-here",
        )
        assert "client_id=12345" in url
        assert "redirect_uri=https%3A%2F%2Fexample.com%2Fcallback" in url
        assert "response_type=code" in url
        assert "scope=activity%3Aread" in url
        assert "activity%3Awrite" in url
        assert "state=jwt-token-here" in url
        assert url.startswith("https://www.strava.com/oauth/authorize?")

    def test_auth_url_with_different_state(self):
        client = StravaClient(client_id="99", client_secret="s")
        url = client.get_auth_url(redirect_uri="http://localhost/cb", state="abc")
        assert "state=abc" in url
        assert "client_id=99" in url


# ── Token Exchange ───────────────────────────────────────────────────


class TestStravaTokenExchange:
    @patch("paceforge.strava.client.httpx.Client")
    def test_exchange_code_success(self, mock_client_cls):
        mock_resp = MagicMock()
        mock_resp.json.return_value = {
            "access_token": "acc123",
            "refresh_token": "ref456",
            "expires_at": 1700000000,
            "athlete": {"id": 789, "firstname": "John", "lastname": "Doe"},
        }
        mock_resp.raise_for_status = MagicMock()
        mock_ctx = MagicMock()
        mock_ctx.__enter__ = MagicMock(return_value=mock_ctx)
        mock_ctx.__exit__ = MagicMock(return_value=False)
        mock_ctx.post.return_value = mock_resp
        mock_client_cls.return_value = mock_ctx

        client = StravaClient(client_id="cid", client_secret="csec")
        result = client.exchange_code("auth-code-xyz")

        assert result["access_token"] == "acc123"
        assert result["refresh_token"] == "ref456"
        assert result["expires_at"] == 1700000000
        assert result["athlete_id"] == 789
        assert result["athlete_name"] == "John Doe"

    @patch("paceforge.strava.client.httpx.Client")
    def test_refresh_access_token(self, mock_client_cls):
        mock_resp = MagicMock()
        mock_resp.json.return_value = {
            "access_token": "new_acc",
            "refresh_token": "new_ref",
            "expires_at": 1700001000,
        }
        mock_resp.raise_for_status = MagicMock()
        mock_ctx = MagicMock()
        mock_ctx.__enter__ = MagicMock(return_value=mock_ctx)
        mock_ctx.__exit__ = MagicMock(return_value=False)
        mock_ctx.post.return_value = mock_resp
        mock_client_cls.return_value = mock_ctx

        client = StravaClient(client_id="cid", client_secret="csec")
        result = client.refresh_access_token("old_refresh")

        assert result["access_token"] == "new_acc"
        assert result["refresh_token"] == "new_ref"


# ── Token Refresh Logic ─────────────────────────────────────────────


class TestStravaEnsureToken:
    def test_valid_token_not_refreshed(self):
        import time
        client = StravaClient(client_id="cid", client_secret="csec")
        strava_data = {
            "access_token": "valid_token",
            "refresh_token": "ref",
            "expires_at": int(time.time()) + 3600,
        }
        token, updated = client.ensure_valid_token(strava_data)
        assert token == "valid_token"
        assert updated["access_token"] == "valid_token"

    @patch("paceforge.strava.client.httpx.Client")
    def test_expired_token_refreshed(self, mock_client_cls):
        import time
        mock_resp = MagicMock()
        mock_resp.json.return_value = {
            "access_token": "refreshed",
            "refresh_token": "new_ref",
            "expires_at": int(time.time()) + 7200,
        }
        mock_resp.raise_for_status = MagicMock()
        mock_ctx = MagicMock()
        mock_ctx.__enter__ = MagicMock(return_value=mock_ctx)
        mock_ctx.__exit__ = MagicMock(return_value=False)
        mock_ctx.post.return_value = mock_resp
        mock_client_cls.return_value = mock_ctx

        client = StravaClient(client_id="cid", client_secret="csec")
        strava_data = {
            "access_token": "expired_tok",
            "refresh_token": "old_ref",
            "expires_at": int(time.time()) - 100,
        }
        token, updated = client.ensure_valid_token(strava_data)
        assert token == "refreshed"
        assert updated["access_token"] == "refreshed"
        assert updated["refresh_token"] == "new_ref"


# ── Create Activity ──────────────────────────────────────────────────


class TestStravaCreateActivity:
    @patch("paceforge.strava.client.httpx.Client")
    def test_create_activity_success(self, mock_client_cls):
        mock_resp = MagicMock()
        mock_resp.json.return_value = {"id": 999888}
        mock_resp.raise_for_status = MagicMock()
        mock_ctx = MagicMock()
        mock_ctx.__enter__ = MagicMock(return_value=mock_ctx)
        mock_ctx.__exit__ = MagicMock(return_value=False)
        mock_ctx.post.return_value = mock_resp
        mock_client_cls.return_value = mock_ctx

        client = StravaClient(client_id="cid", client_secret="csec")
        result = client.create_activity(
            "token123",
            name="Morning Run",
            sport_type="Run",
            start_date_local="2026-04-15T07:00:00",
            elapsed_time=3600,
            description="Test description",
            distance=10000.0,
        )
        assert result["id"] == 999888


# ── List Activities ──────────────────────────────────────────────────


class TestListActivities:
    @patch("paceforge.strava.client.httpx.Client")
    def test_list_activities(self, mock_client_cls):
        mock_resp = MagicMock()
        mock_resp.json.return_value = [
            {"id": 111, "start_date": "2026-04-15T07:00:00Z", "distance": 10000},
        ]
        mock_resp.raise_for_status = MagicMock()
        mock_ctx = MagicMock()
        mock_ctx.__enter__ = MagicMock(return_value=mock_ctx)
        mock_ctx.__exit__ = MagicMock(return_value=False)
        mock_ctx.get.return_value = mock_resp
        mock_client_cls.return_value = mock_ctx

        client = StravaClient(client_id="cid", client_secret="csec")
        result = client.list_activities("tok", after=1000, before=2000, per_page=10)
        assert len(result) == 1
        assert result[0]["id"] == 111


# ── Update Activity ──────────────────────────────────────────────────


class TestUpdateActivity:
    @patch("paceforge.strava.client.httpx.Client")
    def test_update_activity(self, mock_client_cls):
        mock_resp = MagicMock()
        mock_resp.json.return_value = {"id": 111, "name": "Updated Title"}
        mock_resp.raise_for_status = MagicMock()
        mock_ctx = MagicMock()
        mock_ctx.__enter__ = MagicMock(return_value=mock_ctx)
        mock_ctx.__exit__ = MagicMock(return_value=False)
        mock_ctx.put.return_value = mock_resp
        mock_client_cls.return_value = mock_ctx

        client = StravaClient(client_id="cid", client_secret="csec")
        result = client.update_activity(
            "tok", 111, name="Updated Title", description="New desc",
        )
        assert result["name"] == "Updated Title"
        # Verify PUT was called with json body
        call_args = mock_ctx.put.call_args
        assert call_args.kwargs.get("json") or call_args[1].get("json")


# ── Find Matching Activity ───────────────────────────────────────────


class TestFindMatchingActivity:
    def test_match_by_time(self):
        client = StravaClient(client_id="cid", client_secret="csec")
        # Mock list_activities to return a matching activity
        client.list_activities = MagicMock(return_value=[
            {"id": 222, "start_date": "2026-04-15T07:00:00Z", "distance": 10000},
        ])
        from datetime import datetime
        epoch = datetime(2026, 4, 15, 7, 0, 30, tzinfo=UTC).timestamp()
        result = client.find_matching_activity("tok", epoch, distance_meters=10000)
        assert result is not None
        assert result["id"] == 222

    def test_no_match_time_too_far(self):
        client = StravaClient(client_id="cid", client_secret="csec")
        # 16h gap exceeds the 14h timezone-aware window
        client.list_activities = MagicMock(return_value=[
            {"id": 333, "start_date": "2026-04-14T15:00:00Z", "distance": 10000},
        ])
        from datetime import datetime
        epoch = datetime(2026, 4, 15, 7, 0, 0, tzinfo=UTC).timestamp()
        result = client.find_matching_activity("tok", epoch, distance_meters=10000)
        assert result is None

    def test_no_match_distance_too_different(self):
        client = StravaClient(client_id="cid", client_secret="csec")
        client.list_activities = MagicMock(return_value=[
            {"id": 444, "start_date": "2026-04-15T07:00:00Z", "distance": 5000},
        ])
        from datetime import datetime
        epoch = datetime(2026, 4, 15, 7, 0, 0, tzinfo=UTC).timestamp()
        result = client.find_matching_activity("tok", epoch, distance_meters=10000)
        assert result is None

    def test_match_without_distance(self):
        client = StravaClient(client_id="cid", client_secret="csec")
        client.list_activities = MagicMock(return_value=[
            {"id": 555, "start_date": "2026-04-15T07:00:00Z"},
        ])
        from datetime import datetime
        epoch = datetime(2026, 4, 15, 7, 0, 0, tzinfo=UTC).timestamp()
        result = client.find_matching_activity("tok", epoch)
        assert result is not None
        assert result["id"] == 555
