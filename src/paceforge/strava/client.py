"""Strava OAuth2 + Activity API client."""

from __future__ import annotations

import logging
import time
from urllib.parse import urlencode

import httpx

logger = logging.getLogger(__name__)

STRAVA_AUTH_URL = "https://www.strava.com/oauth/authorize"
STRAVA_TOKEN_URL = "https://www.strava.com/oauth/token"
STRAVA_DEAUTH_URL = "https://www.strava.com/oauth/deauthorize"
STRAVA_API_BASE = "https://www.strava.com/api/v3"


class StravaClient:
    """Handles Strava OAuth2 flow and activity creation."""

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
            "scope": "activity:write",
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
        """Refresh an expired access token.

        Returns dict with: access_token, refresh_token, expires_at.
        """
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
        """Return a valid access token, refreshing if expired.

        Parameters
        ----------
        strava_data : dict
            Stored Strava connection data with access_token, refresh_token,
            expires_at.

        Returns
        -------
        tuple[str, dict]
            (valid_access_token, updated_strava_data) — the dict is updated
            in-place and also returned for convenience.
        """
        expires_at = strava_data.get("expires_at", 0)
        if time.time() < expires_at - 300:  # 5-min buffer
            return strava_data["access_token"], strava_data

        logger.info("Strava token expired, refreshing...")
        refreshed = self.refresh_access_token(strava_data["refresh_token"])
        strava_data["access_token"] = refreshed["access_token"]
        strava_data["refresh_token"] = refreshed["refresh_token"]
        strava_data["expires_at"] = refreshed["expires_at"]
        return refreshed["access_token"], strava_data

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
    ) -> dict:
        """Create a manual activity on Strava.

        Parameters
        ----------
        access_token : str
            Valid Strava access token.
        name : str
            Activity title.
        sport_type : str
            E.g. "Run", "TrailRun", "Walk", "Workout".
        start_date_local : str
            ISO 8601 datetime string.
        elapsed_time : int
            Duration in seconds.
        description : str
            Activity description text.
        distance : float | None
            Distance in meters.

        Returns
        -------
        dict
            Strava activity response including 'id'.
        """
        payload: dict = {
            "name": name,
            "sport_type": sport_type,
            "start_date_local": start_date_local,
            "elapsed_time": elapsed_time,
            "description": description,
        }
        if distance is not None and distance > 0:
            payload["distance"] = distance

        with httpx.Client(timeout=15) as client:
            resp = client.post(
                f"{STRAVA_API_BASE}/activities",
                data=payload,
                headers={"Authorization": f"Bearer {access_token}"},
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
