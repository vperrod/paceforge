"""Strava OAuth2 + Activity API client."""

from __future__ import annotations

import logging
import time
from datetime import datetime
from urllib.parse import urlencode

import httpx

logger = logging.getLogger(__name__)

STRAVA_AUTH_URL = "https://www.strava.com/oauth/authorize"
STRAVA_TOKEN_URL = "https://www.strava.com/oauth/token"
STRAVA_DEAUTH_URL = "https://www.strava.com/oauth/deauthorize"
STRAVA_API_BASE = "https://www.strava.com/api/v3"


class DuplicateActivityError(Exception):
    """Raised when Strava returns 409 Conflict (activity already exists)."""


class StravaClient:
    """Handles Strava OAuth2 flow and activity CRUD."""

    def __init__(self, client_id: str, client_secret: str) -> None:
        self.client_id = client_id
        self.client_secret = client_secret

    def get_auth_url(self, redirect_uri: str, state: str) -> str:
        """Build the Strava OAuth authorize URL."""
        params = {
            "client_id": self.client_id,
            "redirect_uri": redirect_uri,
            "response_type": "code",
            "approval_prompt": "auto",
            "scope": "activity:read,activity:write",
            "state": state,
        }
        return f"{STRAVA_AUTH_URL}?{urlencode(params)}"

    def exchange_code(self, code: str) -> dict:
        """Exchange authorization code for access/refresh tokens.

        Returns dict with: access_token, refresh_token, expires_at, athlete.
        """
        with httpx.Client(timeout=15) as client:
            resp = client.post(STRAVA_TOKEN_URL, data={
                "client_id": self.client_id,
                "client_secret": self.client_secret,
                "code": code,
                "grant_type": "authorization_code",
            })
            resp.raise_for_status()
            data = resp.json()
        athlete = data.get("athlete", {})
        return {
            "access_token": data["access_token"],
            "refresh_token": data["refresh_token"],
            "expires_at": data["expires_at"],
            "athlete_id": athlete.get("id"),
            "athlete_name": f"{athlete.get('firstname', '')} {athlete.get('lastname', '')}".strip(),
        }

    def refresh_access_token(self, refresh_token: str) -> dict:
        """Refresh an expired access token."""
        with httpx.Client(timeout=15) as client:
            resp = client.post(STRAVA_TOKEN_URL, data={
                "client_id": self.client_id,
                "client_secret": self.client_secret,
                "grant_type": "refresh_token",
                "refresh_token": refresh_token,
            })
            resp.raise_for_status()
            data = resp.json()
        return {
            "access_token": data["access_token"],
            "refresh_token": data["refresh_token"],
            "expires_at": data["expires_at"],
        }

    def ensure_valid_token(self, strava_data: dict) -> tuple[str, dict]:
        """Return a valid access token, refreshing if expired."""
        expires_at = strava_data.get("expires_at", 0)
        if time.time() < expires_at - 300:
            return strava_data["access_token"], strava_data

        logger.info("Strava token expired, refreshing...")
        refreshed = self.refresh_access_token(strava_data["refresh_token"])
        strava_data["access_token"] = refreshed["access_token"]
        strava_data["refresh_token"] = refreshed["refresh_token"]
        strava_data["expires_at"] = refreshed["expires_at"]
        return refreshed["access_token"], strava_data

    # ── Activity Search & Update ─────────────────────────────────────

    def list_activities(
        self,
        access_token: str,
        *,
        after: int | None = None,
        before: int | None = None,
        per_page: int = 30,
    ) -> list[dict]:
        """List the authenticated athlete's activities."""
        params: dict = {"per_page": per_page}
        if after is not None:
            params["after"] = after
        if before is not None:
            params["before"] = before
        with httpx.Client(timeout=15) as client:
            resp = client.get(
                f"{STRAVA_API_BASE}/athlete/activities",
                params=params,
                headers={"Authorization": f"Bearer {access_token}"},
            )
            resp.raise_for_status()
        return resp.json()

    def find_matching_activity(
        self,
        access_token: str,
        start_time_epoch: float,
        distance_meters: float | None = None,
    ) -> dict | None:
        """Find a Strava activity matching by start time (±120s) and distance (±10%)."""
        activities = self.list_activities(
            access_token,
            after=int(start_time_epoch) - 120,
            before=int(start_time_epoch) + 86400,
            per_page=30,
        )
        for act in activities:
            act_start_str = act.get("start_date", "")
            if not act_start_str:
                continue
            try:
                act_epoch = datetime.fromisoformat(
                    act_start_str.replace("Z", "+00:00")
                ).timestamp()
            except (ValueError, TypeError):
                continue
            if abs(act_epoch - start_time_epoch) > 120:
                continue
            if distance_meters and distance_meters > 0 and act.get("distance"):
                if abs(act["distance"] - distance_meters) / max(distance_meters, 1) > 0.15:
                    continue
            return act
        return None

    def update_activity(
        self,
        access_token: str,
        strava_activity_id: int,
        *,
        name: str | None = None,
        description: str | None = None,
        sport_type: str | None = None,
        trainer: bool | None = None,
    ) -> dict:
        """Update an existing Strava activity (name, description, etc.)."""
        payload: dict = {}
        if name is not None:
            payload["name"] = name
        if description is not None:
            payload["description"] = description
        if sport_type is not None:
            payload["sport_type"] = sport_type
        if trainer is not None:
            payload["trainer"] = trainer
        with httpx.Client(timeout=15) as client:
            resp = client.put(
                f"{STRAVA_API_BASE}/activities/{strava_activity_id}",
                json=payload,
                headers={"Authorization": f"Bearer {access_token}"},
            )
            resp.raise_for_status()
        return resp.json()

    # ── Activity Creation ────────────────────────────────────────────

    def create_activity(
        self,
        access_token: str,
        *,
        name: str,
        sport_type: str,
        start_date_local: str,
        elapsed_time: int,
        description: str = "",
        distance: float | None = None,
        trainer: bool = False,
    ) -> dict:
        """Create a manual activity on Strava."""
        payload: dict = {
            "name": name,
            "sport_type": sport_type,
            "start_date_local": start_date_local,
            "elapsed_time": elapsed_time,
            "description": description,
        }
        if distance is not None and distance > 0:
            payload["distance"] = distance
        if trainer:
            payload["trainer"] = 1

        with httpx.Client(timeout=15) as client:
            resp = client.post(
                f"{STRAVA_API_BASE}/activities",
                data=payload,
                headers={"Authorization": f"Bearer {access_token}"},
            )
            if resp.status_code == 409:
                raise DuplicateActivityError(
                    "Activity already exists on Strava (duplicate detected)"
                )
            resp.raise_for_status()
        return resp.json()

    def deauthorize(self, access_token: str) -> None:
        """Revoke Strava access for this application."""
        with httpx.Client(timeout=15) as client:
            client.post(
                STRAVA_DEAUTH_URL,
                data={"access_token": access_token},
            )
