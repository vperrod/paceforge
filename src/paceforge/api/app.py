"""FastAPI application entry point."""

from __future__ import annotations

import asyncio
import contextlib
import json
import logging
from contextlib import asynccontextmanager
from datetime import UTC, date, datetime, timedelta
from pathlib import Path

import jwt as pyjwt
from fastapi import Depends, FastAPI, Header, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from pydantic import BaseModel

from paceforge.ai.coach import Coach
from paceforge.api.config import settings
from paceforge.auth.database import (
    add_comment,
    create_feed_event,
    create_password_reset_token,
    create_user,
    get_comments,
    get_feed,
    get_friend_ids,
    get_user_by_email,
    get_user_by_id,
    get_user_likes,
    get_valid_reset_token,
    init_db,
    list_friends,
    list_pending_requests,
    list_sent_requests,
    list_users,
    load_user_data,
    mark_reset_token_used,
    register_device_token,
    remove_device_token,
    remove_friend,
    respond_friend_request,
    revoke_all_refresh_tokens,
    revoke_refresh_token,
    save_user_data,
    search_users,
    send_friend_request,
    store_refresh_token,
    toggle_like,
    update_feed_event_metadata,
    update_garmin_email,
    update_last_login,
    update_user_profile,
    update_user_status,
    validate_refresh_token,
)
from paceforge.auth.models import (
    AppLoginRequest,
    DeviceTokenRequest,
    ForgotPasswordRequest,
    ProfileUpdateRequest,
    RefreshRequest,
    RegisterRequest,
    ResetPasswordRequest,
    TokenResponse,
    UserOut,
    UserStatusUpdate,
)
from paceforge.auth.security import (
    create_access_token,
    create_refresh_token,
    decode_access_token,
    decode_refresh_token,
    hash_password,
    verify_password,
)
from paceforge.engine.adaptation import adapt_plan
from paceforge.engine.planner import generate_plan
from paceforge.garmin.client import GarminClient
from paceforge.models.plan import TrainingPlan, Workout
from paceforge.models.profile import (
    ExperienceLevel,
    GoalType,
    RecentActivity,
    TrainingGoal,
    UserFitnessProfile,
    default_training_days,
)
from paceforge.strava.client import DuplicateActivityError, StravaClient

logging.basicConfig(level=settings.log_level)
logger = logging.getLogger(__name__)

# ── Per-user state (keyed by user_id) ────────────────────────────────
_user_garmin: dict[str, GarminClient] = {}
_user_profile: dict[str, UserFitnessProfile] = {}
_user_plans: dict[str, list[TrainingPlan]] = {}
_user_coach: dict[str, Coach] = {}


def _meters_per_sec_to_sec_per_km(speed: float | None) -> float | None:
    if not speed or speed <= 0:
        return None
    return round(1000.0 / speed, 1)


# Map of old/invalid activity type keys to the correct Garmin API values
_ACTIVITY_TYPE_ALIASES = {
    "fitness": "fitness_equipment",
    "cardio": "fitness_equipment",
}


def _normalize_activity_types(types: list[str]) -> list[str]:
    """Convert legacy activity type names to valid Garmin API values."""
    normalized = []
    seen: set[str] = set()
    for t in types:
        mapped = _ACTIVITY_TYPE_ALIASES.get(t, t)
        if mapped not in seen:
            seen.add(mapped)
            normalized.append(mapped)
    return normalized or ["running", "fitness_equipment"]


def _save_plans(uid: str) -> None:
    """Persist all plans for a user."""
    import json as _json
    plans = _user_plans.get(uid, [])
    plans_data = [p.model_dump(mode="json") for p in plans]
    save_user_data(settings.db_path, uid, plan_json=_json.dumps(plans_data))


def _load_plans(uid: str) -> list[TrainingPlan]:
    """Load plans from DB cache (handles both old single-plan and new list format)."""
    import json as _json
    cached = load_user_data(settings.db_path, uid)
    if not cached or not cached.get("plan_json"):
        return []
    try:
        data = _json.loads(cached["plan_json"])
    except Exception:
        return []
    if isinstance(data, list):
        return [TrainingPlan.model_validate(p) for p in data]
    elif isinstance(data, dict):
        return [TrainingPlan.model_validate(data)]
    return []


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Initialise database & seed admin
    init_db(settings.db_path)
    if settings.admin_email and settings.admin_password:
        existing = get_user_by_email(settings.db_path, settings.admin_email)
        if not existing:
            create_user(
                settings.db_path,
                name="Admin",
                email=settings.admin_email,
                password_hash=hash_password(settings.admin_password),
                role="admin",
                status="approved",
            )
            logger.info("Admin user seeded: %s", settings.admin_email)
    # Update welcome feed event text
    _WELCOME_BODY = (
        "Here's how to get started:\n\n"
        "1. To connect your Garmin account — go to User Profile → Connections and enter your "
        "Garmin credentials. This syncs your activities, heart rate zones, and fitness metrics "
        "automatically. Choose between syncing your running workouts only or also include your "
        "cardio and hiit activities.\n\n"
        "2. Check your Performance Profile — once synced, your VO₂max, training load, and "
        "pacing data will appear in the Profile tab.\n\n"
        "3. Create a Training Plan — head to the Plan tab and use the Plan Builder to set your "
        "race goal, timeline, and preferred training days. The AI will generate a periodized plan "
        "tailored to your fitness.\n\n"
        "4. Add friends — find other runners in Settings → Friends and follow their progress "
        "in the feed.\n\n"
        "Feedback is always welcome! If you have questions or run into any issues, reach out to Victor."
    )
    from paceforge.auth.database import _get_conn, _lock
    with _lock:
        conn = _get_conn(settings.db_path)
        conn.execute(
            "UPDATE feed_events SET body = ? WHERE event_type = 'welcome'",
            (_WELCOME_BODY,),
        )
        # One-time cleanup: delete junk feed events created by broken code
        # Keeps: plan events, hyrox events, welcome events, and legitimate
        # "Completed:" workout events from auto-match.
        deleted = conn.execute(
            "DELETE FROM feed_events WHERE event_type = 'activity' "
            "AND title NOT LIKE 'Completed:%'"
        ).rowcount
        if deleted:
            logger.info("Cleaned up %d junk feed events from broken code", deleted)
        conn.commit()
    yield


app = FastAPI(
    title="PaceForge",
    description="AI-enhanced running plan generator for Garmin watches",
    version="0.1.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[o.strip() for o in settings.cors_origins.split(",")],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ── Auth dependencies ────────────────────────────────────────────────


async def get_current_user(authorization: str = Header(default="")) -> dict:
    """Extract and validate the Bearer token. Returns user dict."""
    if not authorization.startswith("Bearer "):
        raise HTTPException(401, "Missing or invalid authorization header")
    token = authorization.removeprefix("Bearer ")
    try:
        payload = decode_access_token(token, settings.jwt_secret)
    except pyjwt.ExpiredSignatureError:
        raise HTTPException(401, "Token has expired")
    except pyjwt.InvalidTokenError:
        raise HTTPException(401, "Invalid token")

    user = get_user_by_id(settings.db_path, payload["sub"])
    if not user or user["status"] != "approved":
        raise HTTPException(401, "Account not active")
    return user


async def require_admin(user: dict = Depends(get_current_user)) -> dict:
    """Require the current user to be an admin."""
    if user["role"] != "admin":
        raise HTTPException(403, "Admin access required")
    return user


def _send_registration_email(name: str, email: str, reason: str) -> None:
    """Send admin notification email for a new registration (best-effort)."""
    if not settings.smtp_host or not settings.notify_email:
        return
    import smtplib
    from email.mime.text import MIMEText

    body = (
        f"New PaceForge registration:\n\n"
        f"Name: {name}\n"
        f"Email: {email}\n"
        f"Reason: {reason or '(none)'}\n\n"
        f"Log in to the admin panel to approve or reject."
    )
    msg = MIMEText(body)
    msg["Subject"] = f"PaceForge: New registration — {name}"
    msg["From"] = settings.smtp_from or settings.smtp_user
    msg["To"] = settings.notify_email

    try:
        with smtplib.SMTP(settings.smtp_host, settings.smtp_port, timeout=10) as srv:
            srv.starttls()
            srv.login(settings.smtp_user, settings.smtp_password)
            srv.send_message(msg)
        logger.info("Registration notification sent for %s", email)
    except Exception as e:
        logger.warning("Failed to send registration email: %s", e)


# ── Public auth endpoints ────────────────────────────────────────────


@app.post("/auth/register", status_code=201)
async def register(req: RegisterRequest):
    existing = get_user_by_email(settings.db_path, req.email)
    if existing:
        raise HTTPException(409, "Email already registered")
    create_user(
        settings.db_path,
        name=req.name,
        email=req.email,
        password_hash=hash_password(req.password),
        reason=req.reason,
    )
    _send_registration_email(req.name, req.email, req.reason)
    return {"status": "ok", "message": "Registration submitted. An admin will review your request."}


def _send_password_reset_email(email: str, reset_url: str) -> None:
    """Send a password-reset link to the user (best-effort)."""
    if not settings.smtp_host:
        return
    import smtplib
    from email.mime.text import MIMEText

    body = (
        f"You requested a password reset for your PaceForge account.\n\n"
        f"Click the link below to set a new password (valid for 1 hour):\n\n"
        f"{reset_url}\n\n"
        f"If you did not request this, you can safely ignore this email."
    )
    msg = MIMEText(body)
    msg["Subject"] = "PaceForge: Password Reset"
    msg["From"] = settings.smtp_from or settings.smtp_user
    msg["To"] = email

    try:
        with smtplib.SMTP(settings.smtp_host, settings.smtp_port, timeout=10) as srv:
            srv.starttls()
            srv.login(settings.smtp_user, settings.smtp_password)
            srv.send_message(msg)
        logger.info("Password reset email sent to %s", email)
    except Exception as e:
        logger.warning("Failed to send password reset email: %s", e)


@app.post("/auth/forgot-password")
async def forgot_password(req: ForgotPasswordRequest):
    """Send a password-reset link. Always returns 200 to prevent email enumeration."""
    import hashlib
    import secrets
    user = get_user_by_email(settings.db_path, req.email)
    if user and user["status"] == "approved":
        raw_token = secrets.token_urlsafe(32)
        token_hash = hashlib.sha256(raw_token.encode()).hexdigest()
        expires_at = (datetime.now(UTC) + timedelta(hours=1)).isoformat()
        create_password_reset_token(settings.db_path, user["id"], token_hash, expires_at)
        reset_url = f"{settings.app_base_url}/?reset_token={raw_token}"
        _send_password_reset_email(user["email"], reset_url)
    return {"status": "ok", "message": "If that email is registered, a reset link has been sent."}


@app.post("/auth/reset-password")
async def reset_password(req: ResetPasswordRequest):
    """Reset the user's password using a valid reset token."""
    import hashlib
    token_hash = hashlib.sha256(req.token.encode()).hexdigest()
    token_row = get_valid_reset_token(settings.db_path, token_hash)
    if not token_row:
        raise HTTPException(400, "Invalid or expired reset token")
    user_id = token_row["user_id"]
    update_user_profile(settings.db_path, user_id, password_hash=hash_password(req.new_password))
    mark_reset_token_used(settings.db_path, token_row["id"])
    revoke_all_refresh_tokens(settings.db_path, user_id)
    return {"status": "ok", "message": "Password has been reset. You can now log in with your new password."}


@app.post("/auth/login", response_model=TokenResponse)
async def app_login(req: AppLoginRequest):
    user = get_user_by_email(settings.db_path, req.email)
    if not user or not verify_password(req.password, user["password_hash"]):
        raise HTTPException(401, "Invalid email or password")
    if user["status"] == "pending":
        raise HTTPException(403, "Your account is pending admin approval")
    if user["status"] == "rejected":
        raise HTTPException(403, "Your account has been rejected")
    access = create_access_token(user["id"], user["role"], settings.jwt_secret)
    refresh = create_refresh_token(user["id"], settings.jwt_secret)
    # Decode refresh to get expiry for DB storage
    refresh_payload = decode_refresh_token(refresh, settings.jwt_secret)
    from datetime import UTC, datetime
    expires_at = datetime.fromtimestamp(refresh_payload["exp"], tz=UTC).isoformat()
    store_refresh_token(settings.db_path, user["id"], refresh, expires_at)
    update_last_login(settings.db_path, user["id"])
    return TokenResponse(
        access_token=access, refresh_token=refresh,
        role=user["role"], name=user["name"], email=user["email"],
    )


@app.post("/auth/refresh", response_model=TokenResponse)
async def auth_refresh(req: RefreshRequest):
    """Exchange a valid refresh token for a new access + refresh token pair."""
    try:
        payload = decode_refresh_token(req.refresh_token, settings.jwt_secret)
    except pyjwt.ExpiredSignatureError:
        raise HTTPException(401, "Refresh token has expired")
    except pyjwt.InvalidTokenError:
        raise HTTPException(401, "Invalid refresh token")

    user_id = payload["sub"]
    if not validate_refresh_token(settings.db_path, user_id, req.refresh_token):
        raise HTTPException(401, "Refresh token revoked or invalid")

    user = get_user_by_id(settings.db_path, user_id)
    if not user or user["status"] != "approved":
        raise HTTPException(401, "Account not active")

    update_last_login(settings.db_path, user_id)

    # Rotate: revoke old refresh token, issue new pair
    revoke_refresh_token(settings.db_path, user_id, req.refresh_token)
    new_access = create_access_token(user["id"], user["role"], settings.jwt_secret)
    new_refresh = create_refresh_token(user["id"], settings.jwt_secret)
    refresh_payload = decode_refresh_token(new_refresh, settings.jwt_secret)
    from datetime import UTC, datetime
    expires_at = datetime.fromtimestamp(refresh_payload["exp"], tz=UTC).isoformat()
    store_refresh_token(settings.db_path, user["id"], new_refresh, expires_at)
    return TokenResponse(
        access_token=new_access, refresh_token=new_refresh,
        role=user["role"], name=user["name"], email=user["email"],
    )


@app.post("/auth/logout")
async def auth_logout(req: RefreshRequest, user: dict = Depends(get_current_user)):
    """Revoke the provided refresh token."""
    revoke_refresh_token(settings.db_path, user["id"], req.refresh_token)
    return {"ok": True}


@app.post("/auth/device-token")
async def auth_device_token(req: DeviceTokenRequest, user: dict = Depends(get_current_user)):
    """Register a push notification device token."""
    register_device_token(settings.db_path, user["id"], req.platform, req.token)
    return {"ok": True}


@app.delete("/auth/device-token")
async def auth_remove_device_token(req: DeviceTokenRequest, user: dict = Depends(get_current_user)):
    """Remove a push notification device token."""
    remove_device_token(settings.db_path, user["id"], req.token)
    return {"ok": True}


@app.get("/auth/profile", response_model=UserOut)
async def get_profile(user: dict = Depends(get_current_user)):
    """Return the current user's profile."""
    return UserOut(**{k: v for k, v in user.items() if k != "password_hash"})


@app.patch("/auth/profile", response_model=UserOut)
async def update_profile(req: ProfileUpdateRequest, user: dict = Depends(get_current_user)):
    """Update current user's name, email, or password."""
    if not verify_password(req.current_password, user["password_hash"]):
        raise HTTPException(403, "Current password is incorrect")

    kwargs: dict = {}
    if req.name is not None:
        kwargs["name"] = req.name
    if req.email is not None and req.email != user["email"]:
        existing = get_user_by_email(settings.db_path, req.email)
        if existing and existing["id"] != user["id"]:
            raise HTTPException(409, "Email already in use by another account")
        kwargs["email"] = req.email
    if req.new_password is not None:
        kwargs["password_hash"] = hash_password(req.new_password)

    updated = update_user_profile(settings.db_path, user["id"], **kwargs)
    return UserOut(**{k: v for k, v in updated.items() if k != "password_hash"})


# ── Admin endpoints ──────────────────────────────────────────────────


@app.get("/admin/users", response_model=list[UserOut])
async def admin_list_users(
    status: str | None = None,
    admin: dict = Depends(require_admin),
):
    rows = list_users(settings.db_path, status=status)
    return [UserOut(**{k: v for k, v in r.items() if k != "password_hash"}) for r in rows]


@app.patch("/admin/users/{user_id}", response_model=UserOut)
async def admin_update_user(
    user_id: str,
    body: UserStatusUpdate,
    admin: dict = Depends(require_admin),
):
    target = get_user_by_id(settings.db_path, user_id)
    if not target:
        raise HTTPException(404, "User not found")
    updated = update_user_status(settings.db_path, user_id, status=body.status)
    if not updated:
        raise HTTPException(500, "Failed to update user")
    return UserOut(**{k: v for k, v in updated.items() if k != "password_hash"})


@app.get("/admin/users/{user_id}/data")
async def admin_get_user_data(
    user_id: str,
    admin: dict = Depends(require_admin),
):
    """Return a user's profile, plan, and activities data (admin only)."""
    user = get_user_by_id(settings.db_path, user_id)
    if not user:
        raise HTTPException(404, "User not found")
    data = load_user_data(settings.db_path, user_id)
    return {
        "user": UserOut(**{k: v for k, v in user.items() if k != "password_hash"}).model_dump(),
        "plan_json": data.get("plan_json") if data else None,
        "activities_json": data.get("activities_json") if data else None,
        "profile_json": data.get("profile_json") if data else None,
    }


# ── Request / Response models ────────────────────────────────────────


class GarminLoginRequest(BaseModel):
    email: str | None = None
    password: str | None = None


class GeneratePlanRequest(BaseModel):
    goal_type: GoalType
    target_date: date
    target_time_seconds: float | None = None
    experience_level: ExperienceLevel | None = None
    training_days: list[str] | None = None
    max_days_per_week: int = 5
    long_run_day: str = "sunday"
    start_date: date | None = None
    custom_easy_pace: float | None = None
    custom_marathon_pace: float | None = None
    custom_threshold_pace: float | None = None


class PushPlanRequest(BaseModel):
    week_numbers: list[int] | None = None  # None = push all


class ChatRequest(BaseModel):
    message: str


class ChatResponse(BaseModel):
    reply: str


class MfaRequest(BaseModel):
    code: str


class RescheduleRequest(BaseModel):
    workout_name: str
    old_date: str
    new_date: str


class AcceptPlanRequest(BaseModel):
    plan_id: str
    accepted: bool


class DeleteWorkoutRequest(BaseModel):
    workout_name: str
    scheduled_date: str


class UnmatchSingleRequest(BaseModel):
    workout_name: str
    scheduled_date: str
    activity_id: int


class MatchWorkoutRequest(BaseModel):
    plan_id: str
    workout_name: str
    scheduled_date: str
    activity_id: int


class AnalyzeWorkoutRequest(BaseModel):
    plan_id: str
    workout_name: str
    scheduled_date: str


class WorkoutFeedbackRequest(BaseModel):
    plan_id: str
    workout_name: str
    scheduled_date: str
    rpe: int | None = None  # 1-10
    notes: str | None = None


# ── Helper: per-user Garmin token dir ────────────────────────────────

def _token_dir_for(user_id: str) -> str:
    base = Path(settings.garmin_token_dir).expanduser()
    return str(base / user_id)


# ── Garmin endpoints (protected) ─────────────────────────────────────


def _ensure_garmin(uid: str) -> GarminClient | None:
    """Return existing GarminClient or try reconnecting from cached tokens."""
    existing = _user_garmin.get(uid)
    if existing:
        return existing
    user = get_user_by_id(settings.db_path, uid)
    garmin_email = user.get("garmin_email") if user else None
    if not garmin_email:
        return None
    client = GarminClient.try_reconnect(garmin_email, _token_dir_for(uid))
    if client:
        _user_garmin[uid] = client
    return client


@app.get("/garmin/status")
async def garmin_status(user: dict = Depends(get_current_user)):
    """Check if Garmin is connected (and try auto-reconnect from cached tokens)."""
    uid = user["id"]
    client = _ensure_garmin(uid)
    cached = load_user_data(settings.db_path, uid)
    return {
        "connected": client is not None,
        "last_synced": cached.get("updated_at") if cached else None,
    }


@app.post("/garmin/login")
async def garmin_login(req: GarminLoginRequest, user: dict = Depends(get_current_user)):
    uid = user["id"]
    email = req.email or ""
    password = req.password or ""
    if not email or not password:
        raise HTTPException(400, "Garmin email and password are required")

    client = GarminClient(email, password, _token_dir_for(uid))
    try:
        result = client.login()
    except Exception as e:
        raise HTTPException(401, f"Garmin login failed: {e}") from e

    _user_garmin[uid] = client
    update_garmin_email(settings.db_path, uid, email)

    if result == "mfa_required":
        return {"status": "mfa_required", "message": "Enter the MFA code sent to your email"}
    return {"status": "ok", "message": "Authenticated with Garmin Connect"}


@app.post("/garmin/mfa")
async def garmin_mfa(req: MfaRequest, user: dict = Depends(get_current_user)):
    uid = user["id"]
    garmin = _user_garmin.get(uid)
    if not garmin:
        raise HTTPException(401, "Not logged in to Garmin. Call /garmin/login first.")
    try:
        garmin.complete_mfa(req.code)
    except Exception as e:
        raise HTTPException(401, f"MFA verification failed: {e}") from e
    return {"status": "ok", "message": "MFA verified — authenticated with Garmin Connect"}


# ── Protected endpoints ──────────────────────────────────────────────


@app.get("/profile", response_model=UserFitnessProfile)
async def get_fitness_profile(sync: bool = False, user: dict = Depends(get_current_user)):
    uid = user["id"]
    # Try cached data first (in-memory, then DB)
    if not sync:
        if uid in _user_profile:
            return _user_profile[uid]
        cached = load_user_data(settings.db_path, uid)
        if cached and cached.get("profile_json"):
            profile = UserFitnessProfile.model_validate_json(cached["profile_json"])
            _user_profile[uid] = profile
            return profile
    # Sync from Garmin if requested or no cached data
    garmin = _ensure_garmin(uid)
    if garmin:
        # Load user preferences for activity types
        _prefs_p = load_user_data(settings.db_path, uid)
        _act_types_p = ["running", "fitness_equipment"]
        if _prefs_p and _prefs_p.get("preferences_json"):
            try:
                _pref_data_p = json.loads(_prefs_p["preferences_json"])
                _act_types_p = _normalize_activity_types(_pref_data_p.get("sync_activity_types", ["running", "fitness_equipment"]))
            except (json.JSONDecodeError, TypeError):
                pass
        _user_profile[uid] = garmin.get_fitness_profile(activity_types=_act_types_p)
        save_user_data(settings.db_path, uid, profile_json=_user_profile[uid].model_dump_json())
        return _user_profile[uid]
    # Final fallback to cache even on sync if Garmin is unavailable
    if uid in _user_profile:
        return _user_profile[uid]
    cached = load_user_data(settings.db_path, uid)
    if cached and cached.get("profile_json"):
        profile = UserFitnessProfile.model_validate_json(cached["profile_json"])
        _user_profile[uid] = profile
        return profile
    raise HTTPException(404, "No profile data available. Connect to Garmin to sync.")


@app.get("/profile/analytics")
async def get_profile_analytics(user: dict = Depends(get_current_user)):
    """Compute derived performance analytics from the cached fitness profile."""
    from paceforge.engine.analytics import compute_all

    uid = user["id"]
    profile = _user_profile.get(uid)
    if not profile:
        # Try loading from DB cache
        cached = load_user_data(settings.db_path, uid)
        if cached and cached.get("profile_json"):
            profile = UserFitnessProfile.model_validate_json(cached["profile_json"])
            _user_profile[uid] = profile
    if not profile:
        raise HTTPException(404, "No profile data. Sync from Garmin first.")
    return compute_all(profile)


@app.get("/activities", response_model=list[RecentActivity])
async def get_activities(
    days: int = 240, sync: bool = False, user: dict = Depends(get_current_user)
):
    """Return running activities from the last N days (default 240).

    By default returns cached data. Pass sync=true to re-fetch from Garmin.
    """
    uid = user["id"]
    # Try cached data first
    if not sync:
        cached = load_user_data(settings.db_path, uid)
        if cached and cached.get("activities_json"):
            activities = [RecentActivity(**a) for a in json.loads(cached["activities_json"])]
            if activities:
                return activities
    # Sync from Garmin if requested or no cached data
    garmin = _ensure_garmin(uid)
    if garmin:
        # Load user preferences for activity types
        _prefs = load_user_data(settings.db_path, uid)
        _act_types = ["running", "fitness_equipment"]
        if _prefs and _prefs.get("preferences_json"):
            try:
                _pref_data = json.loads(_prefs["preferences_json"])
                _act_types = _normalize_activity_types(_pref_data.get("sync_activity_types", ["running", "fitness_equipment"]))
            except (json.JSONDecodeError, TypeError):
                pass
        profile = garmin.get_fitness_profile(lookback_days=min(days, 365), activity_types=_act_types)
        logger.info("Synced %d activities (types=%s)", len(profile.recent_activities), _act_types)
        activities = [a.model_dump(mode="json") for a in profile.recent_activities]
        save_user_data(settings.db_path, uid, activities_json=json.dumps(activities))
        # Auto-match activities to planned workouts
        _auto_match_activities(uid, profile.recent_activities)
        # Auto-adjust diet plan if due
        _maybe_auto_adjust_diet(uid)
        return profile.recent_activities
    # Final fallback to cache
    cached = load_user_data(settings.db_path, uid)
    if cached and cached.get("activities_json"):
        return [RecentActivity(**a) for a in json.loads(cached["activities_json"])]
    return []


@app.get("/garmin/scheduled-workouts")
async def get_scheduled_workouts(user: dict = Depends(get_current_user)):
    """Return workouts scheduled on the Garmin calendar."""
    uid = user["id"]
    garmin = _ensure_garmin(uid)
    if not garmin:
        return []
    try:
        return garmin.get_scheduled_workouts()
    except Exception:
        logger.warning("Failed to fetch scheduled workouts", exc_info=True)
        return []


@app.post("/garmin/cleanup-duplicates")
async def cleanup_duplicate_workouts(user: dict = Depends(get_current_user)):
    """Remove duplicate scheduled workouts from Garmin, keeping one per name+date."""
    uid = user["id"]
    garmin = _ensure_garmin(uid)
    if not garmin:
        raise HTTPException(401, "Not logged in to Garmin")
    try:
        all_workouts = garmin.get_all_workouts()
    except Exception:
        raise HTTPException(500, "Could not fetch Garmin workout library")
    # Group by (name, scheduled_date) — keep first, delete rest
    seen: dict[tuple[str, str], int] = {}
    deleted = 0
    for w in all_workouts:
        name = w.get("workoutName", "")
        wid = w.get("workoutId")
        cal_date = w.get("calendarDate") or ""
        if not wid:
            continue
        key = (name, str(cal_date)[:10])
        if key in seen:
            garmin.delete_workout(wid)
            deleted += 1
        else:
            seen[key] = wid
    return {"status": "ok", "duplicates_deleted": deleted, "remaining": len(seen)}


@app.get("/preferences")
async def get_preferences(user: dict = Depends(get_current_user)):
    """Return user preferences (activity types to sync, etc.)."""
    cached = load_user_data(settings.db_path, user["id"])
    if cached and cached.get("preferences_json"):
        prefs = json.loads(cached["preferences_json"])
        # Normalize legacy activity type values
        if "sync_activity_types" in prefs:
            prefs["sync_activity_types"] = _normalize_activity_types(prefs["sync_activity_types"])
        return prefs
    return {"sync_activity_types": ["running", "fitness_equipment"]}


@app.put("/preferences")
async def save_preferences(body: dict, user: dict = Depends(get_current_user)):
    """Save user preferences (merges with existing)."""
    uid = user["id"]
    # Merge with existing preferences to avoid clobbering other keys
    existing: dict = {}
    cached = load_user_data(settings.db_path, uid)
    if cached and cached.get("preferences_json"):
        try:
            existing = json.loads(cached["preferences_json"])
        except (json.JSONDecodeError, TypeError):
            existing = {}
    existing.update(body)
    save_user_data(settings.db_path, uid, preferences_json=json.dumps(existing))
    return existing


@app.get("/activities/{activity_id}")
async def get_activity_detail(activity_id: int, user: dict = Depends(get_current_user)):
    """Return detailed splits, HR zones, and summary for an activity."""
    uid = user["id"]
    garmin = _ensure_garmin(uid)
    if not garmin:
        raise HTTPException(404, "Garmin not connected \u2014 detailed view unavailable")
    return garmin.get_activity_detail(activity_id)


@app.post("/activities/{activity_id}/analyze")
async def analyze_activity(activity_id: int, user: dict = Depends(get_current_user)):
    """Run AI coach analysis on any synced Garmin activity."""
    uid = user["id"]

    # Check for cached analysis in preferences_json
    cached = load_user_data(settings.db_path, uid)
    prefs: dict = {}
    if cached and cached.get("preferences_json"):
        try:
            prefs = json.loads(cached["preferences_json"])
        except (json.JSONDecodeError, TypeError):
            prefs = {}
    analyses: dict = prefs.get("activity_analyses", {})
    aid_key = str(activity_id)
    if aid_key in analyses:
        return {"analysis": analyses[aid_key]}

    # Fetch activity detail from Garmin
    garmin = _ensure_garmin(uid)
    if not garmin:
        raise HTTPException(404, "Garmin not connected")

    detail = garmin.get_activity_detail(activity_id)

    # Build activity dict from cached activities list
    act_dict: dict = {}
    if cached and cached.get("activities_json"):
        for a in json.loads(cached["activities_json"]):
            if a.get("activity_id") == activity_id:
                act_dict = a
                break
    act_dict["splits"] = detail.get("splits")
    act_dict["hr_zones"] = detail.get("hr_zones")

    # Get profile for context
    profile = _user_profile.get(uid)
    if not profile and cached and cached.get("profile_json"):
        profile = UserFitnessProfile.model_validate_json(cached["profile_json"])

    coach = _get_or_create_coach(uid)
    analysis = coach.analyze_activity(act_dict, profile=profile)

    # Cache the result
    analyses[aid_key] = analysis
    prefs["activity_analyses"] = analyses
    save_user_data(settings.db_path, uid, preferences_json=json.dumps(prefs))

    return {"analysis": analysis}


def _get_or_create_coach(uid: str) -> Coach:
    """Get or create a Coach instance for a user."""
    if uid not in _user_coach:
        coach_key = settings.anthropic_api_key or settings.openai_api_key
        coach_model = settings.anthropic_model if settings.anthropic_api_key else settings.openai_model
        coach_provider = "anthropic" if settings.anthropic_api_key else "openai"
        _user_coach[uid] = Coach(api_key=coach_key, model=coach_model, provider=coach_provider)
    return _user_coach[uid]


def _extract_compact_splits(completion_metrics: dict | None) -> list[dict] | None:
    """Extract compact per-lap split data from Garmin activity detail.

    Returns a list of {km, pace_sec, avg_hr, duration_sec} dicts, or None if unavailable.
    Uses lapDTOs from the splits endpoint (reliable per-km data).
    """
    if not completion_metrics:
        return None
    detail = completion_metrics.get("detail")
    if not detail:
        return None
    splits_data = detail.get("splits")
    if not splits_data:
        return None
    laps = splits_data.get("lapDTOs") if isinstance(splits_data, dict) else None
    if not laps or not isinstance(laps, list):
        return None
    compact = []
    cumulative_sec = 0.0
    for i, lap in enumerate(laps, 1):
        speed = lap.get("averageSpeed") or 0
        pace_sec = round(1000 / speed) if speed > 0 else None
        dur = lap.get("duration") or 0
        compact.append({
            "km": i,
            "pace_sec": pace_sec,
            "avg_hr": round(lap["averageHR"]) if lap.get("averageHR") else None,
            "duration_sec": round(dur, 1),
            "elapsed_min": round(cumulative_sec / 60, 2),
        })
        cumulative_sec += dur
    return compact or None


def _build_feed_metadata(wo, metrics: dict, splits: list[dict] | None = None) -> dict:
    """Build enriched feed event metadata from a completed workout."""
    dist_km = round(metrics.get("distance_meters", 0) / 1000, 2) if metrics.get("distance_meters") else None
    pace = metrics.get("avg_pace_sec_per_km")
    pace_str = f"{int(pace // 60)}:{int(pace % 60):02d}/km" if pace else None
    meta = {
        "workout_type": wo.workout_type.value,
        "distance_km": dist_km,
        "pace": pace_str,
        "distance_meters": metrics.get("distance_meters"),
        "duration_seconds": metrics.get("duration_seconds"),
        "avg_pace_sec_per_km": pace,
        "avg_hr": metrics.get("avg_hr"),
        "max_hr": metrics.get("max_hr"),
        "calories": metrics.get("calories"),
        "elevation_gain": metrics.get("elevation_gain"),
        "training_effect_aerobic": metrics.get("training_effect_aerobic"),
        "activity_type": metrics.get("activity_type", "running"),
    }
    if wo.description:
        meta["description"] = wo.description
    if wo.purpose:
        meta["purpose"] = wo.purpose.value
    if splits:
        meta["splits"] = splits
    return meta


# Activity types that count as "running" for auto-matching to planned workouts
_RUNNING_ACTIVITY_TYPES = {
    "running", "treadmill_running", "trail_running",
    "track_running", "indoor_running", "virtual_run",
}


def _aggregate_activity_metrics(activities: list[RecentActivity]) -> dict:
    """Aggregate metrics from multiple activities into a single dict.

    Distances and durations are summed. Paces, HR, and cadence are
    weighted averages by duration. Calories are summed.
    """
    if not activities:
        return {}
    if len(activities) == 1:
        a = activities[0]
        return {
            k: v for k, v in {
                "distance_meters": a.distance_meters,
                "duration_seconds": a.duration_seconds,
                "avg_pace_sec_per_km": a.avg_pace_sec_per_km,
                "avg_hr": a.avg_hr,
                "max_hr": a.max_hr,
                "calories": a.calories,
                "training_effect_aerobic": a.training_effect_aerobic,
                "avg_running_cadence": a.avg_running_cadence,
                "elevation_gain": a.elevation_gain,
            }.items() if v is not None
        }
    total_dist = sum(a.distance_meters for a in activities)
    total_dur = sum(a.duration_seconds for a in activities)
    total_cal = sum(a.calories or 0 for a in activities) or None
    total_elev = sum(a.elevation_gain or 0 for a in activities) or None
    max_hr = max((a.max_hr for a in activities if a.max_hr), default=None)
    # Weighted averages by duration
    def _wavg(field: str) -> float | None:
        vals = [(getattr(a, field), a.duration_seconds) for a in activities if getattr(a, field) is not None]
        if not vals:
            return None
        return round(sum(v * d for v, d in vals) / sum(d for _, d in vals), 2)

    avg_pace = round(total_dur / (total_dist / 1000), 2) if total_dist > 0 else None
    return {
        k: v for k, v in {
            "distance_meters": total_dist,
            "duration_seconds": total_dur,
            "avg_pace_sec_per_km": avg_pace,
            "avg_hr": _wavg("avg_hr"),
            "max_hr": max_hr,
            "calories": total_cal,
            "training_effect_aerobic": _wavg("training_effect_aerobic"),
            "avg_running_cadence": _wavg("avg_running_cadence"),
            "elevation_gain": total_elev,
        }.items() if v is not None
    }


def _auto_match_activities(uid: str, activities: list[RecentActivity]) -> None:
    """Auto-match Garmin activities to planned workouts by date.

    For each accepted plan, find unmatched workouts whose scheduled_date
    matches an activity's date. Pick the best activity by closest distance.
    Only running-type activities are matched to running workouts.
    Automatically runs AI analysis on newly matched workouts.
    """
    if uid not in _user_plans:
        _user_plans[uid] = _load_plans(uid)
    plans = _user_plans.get(uid, [])
    if not plans:
        return

    from collections import defaultdict
    acts_by_date: dict[str, list[RecentActivity]] = defaultdict(list)
    for act in activities:
        act_date = str(act.start_time.date()) if hasattr(act.start_time, 'date') else str(act.start_time)[:10]
        acts_by_date[act_date].append(act)

    newly_matched: list[tuple[TrainingPlan, Workout]] = []
    for plan in plans:
        if not plan.accepted:
            continue
        for week in plan.weeks:
            for wo in week.workouts:
                if wo.workout_type.value == "rest":
                    continue
                wo_date = str(wo.scheduled_date)
                all_candidates = acts_by_date.get(wo_date, [])
                if not all_candidates:
                    continue
                # Only match running activities to running workouts
                is_running_wo = wo.workout_type.value not in ("cross_training", "rest")
                if is_running_wo:
                    candidates = [a for a in all_candidates if a.activity_type in _RUNNING_ACTIVITY_TYPES]
                else:
                    candidates = list(all_candidates)
                if not candidates:
                    continue
                # Match all eligible activities to this workout
                already_ids = set(wo.matched_activity_ids)
                matched_any_new = False
                for act in candidates:
                    if act.activity_id not in already_ids:
                        wo.matched_activity_ids.append(act.activity_id)
                        already_ids.add(act.activity_id)
                        matched_any_new = True
                if not matched_any_new:
                    continue
                wo.completed = True
                # Aggregate metrics across all matched activities
                wo.completion_metrics = _aggregate_activity_metrics(
                    [a for a in candidates if a.activity_id in already_ids]
                )
                newly_matched.append((plan, wo))
                # Remove matched activities so they don't match other workouts
                for act in candidates:
                    if act.activity_id in already_ids and act in all_candidates:
                        all_candidates.remove(act)

    if not newly_matched:
        return
    _save_plans(uid)
    logger.info("Auto-matched %d activities for user %s", len(newly_matched), uid)

    # Auto-analyze newly matched workouts (only those without existing analysis)
    garmin = _user_garmin.get(uid)
    for plan, wo in newly_matched:
        if wo.completion_analysis:
            continue
        try:
            # Enrich with full Garmin detail (splits, HR zones) for richer analysis
            activity_data = dict(wo.completion_metrics or {})
            if garmin and wo.matched_activity_ids:
                per_activity_details = []
                for aid in wo.matched_activity_ids:
                    try:
                        detail = garmin.get_activity_detail(aid)
                        summary = detail.get("summary") or {}
                        summary_dto = summary.get("summaryDTO") or summary
                        per_activity_details.append({
                            "activity_id": aid,
                            "distance_meters": summary_dto.get("distance"),
                            "duration_seconds": summary_dto.get("duration"),
                            "avg_pace_sec_per_km": _meters_per_sec_to_sec_per_km(summary_dto.get("averageSpeed")),
                            "avg_hr": summary_dto.get("averageHR"),
                            "max_hr": summary_dto.get("maxHR"),
                            "calories": summary_dto.get("calories"),
                            "training_effect_aerobic": summary_dto.get("aerobicTrainingEffect"),
                            "training_effect_anaerobic": summary_dto.get("anaerobicTrainingEffect"),
                            "avg_running_cadence": summary_dto.get("averageRunningCadenceInStepsPerMinute"),
                            "elevation_gain": summary_dto.get("elevationGain"),
                            "splits": detail.get("splits"),
                            "hr_zones": detail.get("hr_zones"),
                            "weather": detail.get("weather"),
                            "split_summaries": detail.get("split_summaries"),
                        })
                    except Exception:
                        logger.debug("Could not fetch detail for activity %s", aid)
                if per_activity_details:
                    if len(per_activity_details) == 1:
                        # Single activity — use its metrics directly
                        d = per_activity_details[0]
                        activity_data.update({k: v for k, v in d.items() if v is not None and k not in ("splits", "hr_zones", "weather", "split_summaries", "activity_id")})
                        wo.completion_metrics = activity_data
                        wo.completion_metrics["detail"] = {
                            "splits": d.get("splits"),
                            "hr_zones": d.get("hr_zones"),
                            "weather": d.get("weather"),
                            "split_summaries": d.get("split_summaries"),
                        }
                    else:
                        # Multiple activities — keep aggregated totals, store per-activity breakdown
                        # Re-aggregate with richer detail data
                        total_dist = sum(d.get("distance_meters") or 0 for d in per_activity_details)
                        total_dur = sum(d.get("duration_seconds") or 0 for d in per_activity_details)
                        if total_dist > 0:
                            activity_data["distance_meters"] = total_dist
                            activity_data["avg_pace_sec_per_km"] = round(total_dur / (total_dist / 1000), 2)
                        if total_dur > 0:
                            activity_data["duration_seconds"] = total_dur
                        activity_data["calories"] = sum(d.get("calories") or 0 for d in per_activity_details) or None
                        activity_data["elevation_gain"] = sum(d.get("elevation_gain") or 0 for d in per_activity_details) or None
                        activity_data["max_hr"] = max((d["max_hr"] for d in per_activity_details if d.get("max_hr")), default=None)
                        # Weighted averages
                        for field in ("avg_hr", "avg_running_cadence"):
                            vals = [(d[field], d.get("duration_seconds") or 0) for d in per_activity_details if d.get(field)]
                            if vals:
                                activity_data[field] = round(sum(v * w for v, w in vals) / sum(w for _, w in vals), 2)
                        wo.completion_metrics = {k: v for k, v in activity_data.items() if v is not None}
                        wo.completion_metrics["per_activity"] = per_activity_details

            coach = _get_or_create_coach(uid)
            profile = _user_profile.get(uid)
            analysis = coach.analyze_workout(
                workout=wo.model_dump(mode="json"),
                activity=activity_data,
                profile=profile,
            )
            wo.completion_analysis = analysis
        except Exception:
            logger.warning("Auto-analysis failed for workout %s", wo.name, exc_info=True)

    # Post feed events for newly completed workouts
    for plan, wo in newly_matched:
        metrics = wo.completion_metrics or {}
        splits = _extract_compact_splits(metrics)
        meta = _build_feed_metadata(wo, metrics, splits)
        try:
            create_feed_event(
                settings.db_path, uid,
                event_type="activity",
                title=f"Completed: {wo.name}",
                body=None,
                metadata=meta,
            )
        except Exception:
            logger.debug("Failed to post feed event for %s", wo.name)

    _save_plans(uid)

    # Auto-push to Strava if enabled
    try:
        strava_data = _load_strava_data(uid)
        if strava_data:
            cached = load_user_data(settings.db_path, uid)
            prefs: dict = {}
            if cached and cached.get("preferences_json"):
                try:
                    prefs = json.loads(cached["preferences_json"])
                except (json.JSONDecodeError, TypeError):
                    prefs = {}
            if prefs.get("strava_auto_update"):
                sent = prefs.get("strava_sent_activities", [])
                for _plan, _wo in newly_matched:
                    for aid in _wo.matched_activity_ids:
                        if aid not in sent:
                            try:
                                result = _do_strava_push(uid, aid, raise_on_error=False)
                                if result.get("error"):
                                    logger.warning("Auto Strava push failed for %s: %s", aid, result["error"])
                                else:
                                    logger.info("Auto Strava push succeeded for activity %s", aid)
                            except Exception:
                                logger.warning("Auto Strava push error for activity %s", aid, exc_info=True)
    except Exception:
        logger.warning("Auto Strava push check failed", exc_info=True)


@app.post("/plan/generate", response_model=TrainingPlan)
async def generate(req: GeneratePlanRequest, user: dict = Depends(get_current_user)):
    uid = user["id"]

    # Try in-memory profile, then Garmin, then cached DB profile
    profile = _user_profile.get(uid)
    if not profile:
        garmin = _ensure_garmin(uid)
        if garmin:
            profile = garmin.get_fitness_profile()
        else:
            cached = load_user_data(settings.db_path, uid)
            if cached and cached.get("profile_json"):
                profile = UserFitnessProfile.model_validate_json(cached["profile_json"])
    if not profile:
        raise HTTPException(400, "No fitness profile available — connect Garmin or sync first")
    _user_profile[uid] = profile
    save_user_data(settings.db_path, uid, profile_json=profile.model_dump_json())

    goal = TrainingGoal(
        goal_type=req.goal_type,
        target_date=req.target_date,
        target_time_seconds=req.target_time_seconds,
        experience_level=req.experience_level,
        training_days=req.training_days or default_training_days(req.max_days_per_week),
        long_run_day=req.long_run_day,
        start_date=req.start_date,
        custom_easy_pace=req.custom_easy_pace,
        custom_marathon_pace=req.custom_marathon_pace,
        custom_threshold_pace=req.custom_threshold_pace,
    )

    try:
        new_plan = await asyncio.to_thread(
            generate_plan,
            profile, goal,
            openai_api_key=settings.openai_api_key,
            openai_model=settings.openai_model,
            anthropic_api_key=settings.anthropic_api_key,
            anthropic_model=settings.anthropic_model,
            llm_provider=settings.llm_provider,
        )
    except Exception as e:
        logger.error("Plan generation failed: %s", e, exc_info=True)
        raise HTTPException(500, f"Plan generation failed: {e}")

    # Add to user's plan list
    if uid not in _user_plans:
        _user_plans[uid] = _load_plans(uid)
    _user_plans[uid].append(new_plan)
    _save_plans(uid)

    # Post feed event
    try:
        weeks = len(new_plan.weeks)
        goal_label = req.goal_type.value if hasattr(req.goal_type, "value") else str(req.goal_type)
        create_feed_event(
            settings.db_path, uid,
            event_type="plan",
            title=f"Started a {weeks}-week {goal_label} training plan",
            body=f"Target date: {req.target_date}" if req.target_date else None,
        )
    except Exception:
        logger.debug("Failed to post plan feed event")

    return new_plan


@app.get("/plans", response_model=list[TrainingPlan])
async def get_plans(user: dict = Depends(get_current_user)):
    uid = user["id"]
    if uid not in _user_plans:
        _user_plans[uid] = _load_plans(uid)
    return _user_plans[uid]


@app.get("/plan", response_model=TrainingPlan | None)
async def get_plan(user: dict = Depends(get_current_user)):
    """Legacy endpoint — returns the most recent plan."""
    uid = user["id"]
    if uid not in _user_plans:
        _user_plans[uid] = _load_plans(uid)
    plans = _user_plans.get(uid, [])
    if not plans:
        raise HTTPException(404, "No plan generated yet")
    return plans[-1]


@app.post("/plan/push")
async def push_plan(req: PushPlanRequest, user: dict = Depends(get_current_user)):
    uid = user["id"]
    garmin = _ensure_garmin(uid)
    if not garmin:
        raise HTTPException(401, "Not logged in to Garmin")
    if uid not in _user_plans:
        _user_plans[uid] = _load_plans(uid)
    # Find the accepted plan to push
    plan = next((p for p in _user_plans.get(uid, []) if p.accepted), None)
    if not plan:
        raise HTTPException(404, "No accepted plan to push")

    weeks_to_push = plan.weeks
    if req.week_numbers:
        weeks_to_push = [w for w in plan.weeks if w.week_number in req.week_numbers]

    plan_paces = {
        "easy_pace": plan.easy_pace,
        "marathon_pace": plan.marathon_pace,
        "threshold_pace": plan.threshold_pace,
        "interval_pace": plan.interval_pace,
        "repetition_pace": plan.repetition_pace,
    }

    total_pushed = 0
    for week in weeks_to_push:
        results = garmin.push_plan_week(week.workouts, plan_paces=plan_paces)
        total_pushed += len(results)

    return {"status": "ok", "workouts_pushed": total_pushed}


@app.post("/plan/reschedule")
async def reschedule_workout(req: RescheduleRequest, user: dict = Depends(get_current_user)):
    uid = user["id"]
    if uid not in _user_plans:
        _user_plans[uid] = _load_plans(uid)
    for plan in _user_plans.get(uid, []):
        for week in plan.weeks:
            for w in week.workouts:
                if w.name == req.workout_name and str(w.scheduled_date) == req.old_date:
                    w.scheduled_date = date.fromisoformat(req.new_date)
                    _save_plans(uid)
                    return {"status": "ok", "message": f"Moved '{w.name}' to {req.new_date}"}
    raise HTTPException(404, "Workout not found")


@app.post("/plan/delete-workout")
async def delete_workout(req: DeleteWorkoutRequest, user: dict = Depends(get_current_user)):
    uid = user["id"]
    if uid not in _user_plans:
        _user_plans[uid] = _load_plans(uid)
    for plan in _user_plans.get(uid, []):
        for week in plan.weeks:
            for w in week.workouts:
                if w.name == req.workout_name and str(w.scheduled_date) == req.scheduled_date:
                    week.workouts.remove(w)
                    week.total_distance_km = round(
                        sum((wo.estimated_distance_meters or 0) for wo in week.workouts) / 1000, 1
                    )
                    _save_plans(uid)
                    return {"status": "ok", "message": f"Deleted '{w.name}' on {req.scheduled_date}"}
    raise HTTPException(404, "Workout not found")


@app.post("/plan/unmatch-workout")
async def unmatch_workout(req: DeleteWorkoutRequest, user: dict = Depends(get_current_user)):
    """Revert a wrongly matched activity from a planned workout."""
    uid = user["id"]
    if uid not in _user_plans:
        _user_plans[uid] = _load_plans(uid)
    for plan in _user_plans.get(uid, []):
        for week in plan.weeks:
            for w in week.workouts:
                if w.name == req.workout_name and str(w.scheduled_date) == req.scheduled_date:
                    w.completed = False
                    w.matched_activity_ids = []
                    w.completion_metrics = None
                    w.completion_analysis = None
                    _save_plans(uid)
                    return {"status": "ok", "message": f"Unmatched '{w.name}' on {req.scheduled_date}"}
    raise HTTPException(404, "Workout not found")


@app.post("/plan/unmatch-single-activity")
async def unmatch_single_activity(req: UnmatchSingleRequest, user: dict = Depends(get_current_user)):
    """Remove a single activity from a multi-matched workout."""
    uid = user["id"]
    if uid not in _user_plans:
        _user_plans[uid] = _load_plans(uid)
    for plan in _user_plans.get(uid, []):
        for week in plan.weeks:
            for w in week.workouts:
                if w.name == req.workout_name and str(w.scheduled_date) == req.scheduled_date:
                    if req.activity_id not in w.matched_activity_ids:
                        raise HTTPException(404, "Activity not linked to this workout")
                    w.matched_activity_ids.remove(req.activity_id)
                    if not w.matched_activity_ids:
                        w.completed = False
                        w.completion_metrics = None
                        w.completion_analysis = None
                    else:
                        # Re-aggregate metrics from remaining activities
                        cached = load_user_data(settings.db_path, uid)
                        remaining_acts = []
                        if cached and cached.get("activities_json"):
                            all_acts = json.loads(cached["activities_json"])
                            for a in all_acts:
                                if a.get("activity_id") in w.matched_activity_ids:
                                    remaining_acts.append(RecentActivity(**a))
                        if remaining_acts:
                            w.completion_metrics = _aggregate_activity_metrics(remaining_acts)
                        w.completion_analysis = None
                    _save_plans(uid)
                    return {"status": "ok", "remaining": len(w.matched_activity_ids)}
    raise HTTPException(404, "Workout not found")


@app.post("/plan/accept", response_model=TrainingPlan)
async def accept_plan(req: AcceptPlanRequest, user: dict = Depends(get_current_user)):
    uid = user["id"]
    if uid not in _user_plans:
        _user_plans[uid] = _load_plans(uid)
    plan = next((p for p in _user_plans.get(uid, []) if p.plan_id == req.plan_id), None)
    if not plan:
        raise HTTPException(404, "Plan not found")
    plan.accepted = req.accepted
    _save_plans(uid)
    return plan


@app.delete("/plan/{plan_id}")
async def delete_plan(plan_id: str, user: dict = Depends(get_current_user)):
    uid = user["id"]
    if uid not in _user_plans:
        _user_plans[uid] = _load_plans(uid)
    plans = _user_plans.get(uid, [])
    plan = next((p for p in plans if p.plan_id == plan_id), None)
    if not plan:
        raise HTTPException(404, "Plan not found")
    plans.remove(plan)
    _save_plans(uid)
    return {"status": "ok", "message": f"Plan '{plan.name}' deleted"}


@app.post("/coach/chat", response_model=ChatResponse)
async def coach_chat(req: ChatRequest, user: dict = Depends(get_current_user)):
    uid = user["id"]

    # Resolve which LLM to use for coaching
    if settings.llm_provider == "anthropic" and settings.anthropic_api_key:
        coach_key = settings.anthropic_api_key
        coach_model = settings.anthropic_model
        coach_provider = "anthropic"
    elif settings.llm_provider == "openai" and settings.openai_api_key:
        coach_key = settings.openai_api_key
        coach_model = settings.openai_model
        coach_provider = "openai"
    elif settings.anthropic_api_key:
        coach_key = settings.anthropic_api_key
        coach_model = settings.anthropic_model
        coach_provider = "anthropic"
    elif settings.openai_api_key:
        coach_key = settings.openai_api_key
        coach_model = settings.openai_model
        coach_provider = "openai"
    else:
        return ChatResponse(
            reply=(
                "AI coaching is not configured. "
                "Set PACEFORGE_ANTHROPIC_API_KEY or PACEFORGE_OPENAI_API_KEY to enable."
            )
        )

    coach = _user_coach.get(uid)
    if coach is None or getattr(coach, "_provider", None) != coach_provider:
        coach = Coach(
            api_key=coach_key,
            model=coach_model,
            provider=coach_provider,
        )
        _user_coach[uid] = coach

    # Load profile/plan from DB if not in memory (mobile web SPA)
    profile = _user_profile.get(uid)
    if not profile:
        cached = load_user_data(settings.db_path, uid)
        if cached and cached.get("profile_json"):
            profile = UserFitnessProfile.model_validate_json(cached["profile_json"])
            _user_profile[uid] = profile
    if uid not in _user_plans:
        _user_plans[uid] = _load_plans(uid)
    plans = _user_plans.get(uid, [])
    plan = plans[-1] if plans else None

    result = coach.chat(
        message=req.message,
        profile=profile,
        plan=plan,
    )
    return ChatResponse(reply=result.reply)


# ── Weekly Overview ──────────────────────────────────────────────────


def _get_weekly_overview(uid: str, *, force: bool = False) -> dict:
    """Generate or return cached AI weekly overview for the current week."""
    today = date.today()
    monday = today - timedelta(days=today.weekday())

    # Check cache
    if not force:
        cached = load_user_data(settings.db_path, uid)
        if cached and cached.get("weekly_overview_json"):
            try:
                overview = json.loads(cached["weekly_overview_json"])
                cached_monday = overview.get("week_start")
                cached_date = overview.get("generated_at", "")[:10]
                if cached_monday == monday.isoformat() and cached_date == today.isoformat():
                    return overview
            except (json.JSONDecodeError, TypeError):
                pass

    # Resolve LLM
    if settings.llm_provider == "anthropic" and settings.anthropic_api_key:
        coach_key, coach_model, coach_provider = settings.anthropic_api_key, settings.anthropic_model, "anthropic"
    elif settings.llm_provider == "openai" and settings.openai_api_key:
        coach_key, coach_model, coach_provider = settings.openai_api_key, settings.openai_model, "openai"
    elif settings.anthropic_api_key:
        coach_key, coach_model, coach_provider = settings.anthropic_api_key, settings.anthropic_model, "anthropic"
    elif settings.openai_api_key:
        coach_key, coach_model, coach_provider = settings.openai_api_key, settings.openai_model, "openai"
    else:
        raise HTTPException(503, "AI not configured. Set PACEFORGE_ANTHROPIC_API_KEY or PACEFORGE_OPENAI_API_KEY.")

    coach = Coach(api_key=coach_key, model=coach_model, provider=coach_provider)

    # Load profile
    profile = _user_profile.get(uid)
    if not profile:
        cached_data = load_user_data(settings.db_path, uid)
        if cached_data and cached_data.get("profile_json"):
            profile = UserFitnessProfile.model_validate_json(cached_data["profile_json"])
            _user_profile[uid] = profile

    # Load activities and filter to this week
    week_activities: list[dict] = []
    cached_data = load_user_data(settings.db_path, uid)
    if cached_data and cached_data.get("activities_json"):
        try:
            all_acts = json.loads(cached_data["activities_json"])
            sunday = monday + timedelta(days=6)
            for act in all_acts:
                start = act.get("start_time") or act.get("start_time_local", "")
                if start:
                    act_date_str = start[:10]
                    if monday.isoformat() <= act_date_str <= sunday.isoformat():
                        week_activities.append(act)
        except (json.JSONDecodeError, TypeError):
            pass

    # Load plan
    if uid not in _user_plans:
        _user_plans[uid] = _load_plans(uid)
    plans = _user_plans.get(uid, [])
    plan = plans[-1] if plans else None

    # Load health data
    health_data: dict | None = None
    if cached_data and cached_data.get("health_json"):
        with __import__("contextlib").suppress(json.JSONDecodeError, TypeError):
            health_data = json.loads(cached_data["health_json"])

    # Generate analysis
    sections = coach.analyze_week(
        profile=profile,
        activities=week_activities,
        plan=plan,
        health_data=health_data,
    )

    overview = {
        "week_start": monday.isoformat(),
        "generated_at": datetime.now(UTC).isoformat(),
        "content": sections,
    }

    # Cache
    save_user_data(settings.db_path, uid, weekly_overview_json=json.dumps(overview))
    return overview


@app.get("/weekly-overview")
async def get_weekly_overview(user: dict = Depends(get_current_user)):
    """Return AI-generated weekly overview (cached per day)."""
    return _get_weekly_overview(user["id"])


@app.post("/weekly-overview/regenerate")
async def regenerate_weekly_overview(user: dict = Depends(get_current_user)):
    """Force-regenerate the weekly overview (bypass cache)."""
    return _get_weekly_overview(user["id"], force=True)


@app.post("/plan/adapt", response_model=TrainingPlan)
async def adapt_current_plan(plan_id: str | None = None, user: dict = Depends(get_current_user)):
    uid = user["id"]
    garmin = _ensure_garmin(uid)
    if not garmin:
        raise HTTPException(401, "Not logged in to Garmin")
    if uid not in _user_plans:
        _user_plans[uid] = _load_plans(uid)
    plans = _user_plans.get(uid, [])
    if plan_id:
        plan = next((p for p in plans if p.plan_id == plan_id), None)
    else:
        plan = plans[-1] if plans else None
    if not plan:
        raise HTTPException(404, "No plan found")
    _user_profile[uid] = garmin.get_fitness_profile()
    idx = plans.index(plan)
    adapted = adapt_plan(plan, _user_profile[uid])
    adapted.accepted = False
    plans[idx] = adapted
    _save_plans(uid)
    return adapted


@app.post("/plan/match-workout")
async def match_workout(req: MatchWorkoutRequest, user: dict = Depends(get_current_user)):
    """Match a Garmin activity to a planned workout and mark it complete."""
    uid = user["id"]
    if uid not in _user_plans:
        _user_plans[uid] = _load_plans(uid)
    plans = _user_plans.get(uid, [])
    plan = next((p for p in plans if p.plan_id == req.plan_id), None)
    if not plan:
        raise HTTPException(404, "Plan not found")

    # Find the workout
    workout = None
    for week in plan.weeks:
        for wo in week.workouts:
            if wo.name == req.workout_name and str(wo.scheduled_date) == req.scheduled_date:
                workout = wo
                break
        if workout:
            break
    if not workout:
        raise HTTPException(404, "Workout not found in plan")

    # Fetch activity details to build completion metrics
    garmin = _ensure_garmin(uid)
    completion_metrics: dict = {}
    if garmin:
        try:
            detail = garmin.get_activity_detail(req.activity_id)
            summary = detail.get("summary") or {}
            summary_dto = summary.get("summaryDTO") or summary
            completion_metrics = {
                "distance_meters": summary_dto.get("distance"),
                "duration_seconds": summary_dto.get("duration"),
                "avg_pace_sec_per_km": _meters_per_sec_to_sec_per_km(summary_dto.get("averageSpeed")),
                "avg_hr": summary_dto.get("averageHR"),
                "max_hr": summary_dto.get("maxHR"),
                "calories": summary_dto.get("calories"),
                "training_effect_aerobic": summary_dto.get("aerobicTrainingEffect"),
                "training_effect_anaerobic": summary_dto.get("anaerobicTrainingEffect"),
                "avg_running_cadence": summary_dto.get("averageRunningCadenceInStepsPerMinute"),
                "elevation_gain": summary_dto.get("elevationGain"),
            }
            # Store full detail for dashboard graphs
            completion_metrics["detail"] = {
                "splits": detail.get("splits"),
                "hr_zones": detail.get("hr_zones"),
                "weather": detail.get("weather"),
                "split_summaries": detail.get("split_summaries"),
            }
        except Exception:
            logger.warning("Could not fetch activity detail for %s", req.activity_id)
    # Fallback: try to find in cached activities
    if not any(v for k, v in completion_metrics.items() if k != "detail" and v is not None):
        cached = load_user_data(settings.db_path, uid)
        if cached and cached.get("activities_json"):
            for act in json.loads(cached["activities_json"]):
                if act.get("activity_id") == req.activity_id:
                    completion_metrics = {
                        "distance_meters": act.get("distance_meters"),
                        "duration_seconds": act.get("duration_seconds"),
                        "avg_pace_sec_per_km": act.get("avg_pace_sec_per_km"),
                        "avg_hr": act.get("avg_hr"),
                        "max_hr": act.get("max_hr"),
                        "calories": act.get("calories"),
                        "training_effect_aerobic": act.get("training_effect_aerobic"),
                        "avg_running_cadence": act.get("avg_running_cadence"),
                        "elevation_gain": act.get("elevation_gain"),
                    }
                    break

    workout.completed = True
    if req.activity_id not in workout.matched_activity_ids:
        workout.matched_activity_ids.append(req.activity_id)
    workout.completion_metrics = {k: v for k, v in completion_metrics.items() if v is not None}
    _save_plans(uid)
    return {"ok": True, "workout": workout.model_dump(mode="json")}


@app.post("/plan/analyze-workout")
async def analyze_workout_endpoint(req: AnalyzeWorkoutRequest, user: dict = Depends(get_current_user)):
    """Run AI analysis on a completed workout comparing planned vs actual."""
    uid = user["id"]
    if uid not in _user_plans:
        _user_plans[uid] = _load_plans(uid)
    plans = _user_plans.get(uid, [])
    plan = next((p for p in plans if p.plan_id == req.plan_id), None)
    if not plan:
        raise HTTPException(404, "Plan not found")

    workout = None
    for week in plan.weeks:
        for wo in week.workouts:
            if wo.name == req.workout_name and str(wo.scheduled_date) == req.scheduled_date:
                workout = wo
                break
        if workout:
            break
    if not workout:
        raise HTTPException(404, "Workout not found in plan")
    if not workout.completed or not workout.matched_activity_ids:
        raise HTTPException(400, "Workout is not matched to an activity yet")

    # Build activity dict from completion_metrics or fetch from Garmin
    activity_data = {k: v for k, v in (workout.completion_metrics or {}).items() if k != "detail"}
    if not activity_data or not any(activity_data.values()):
        garmin = _ensure_garmin(uid)
        if garmin:
            try:
                detail = garmin.get_activity_detail(workout.matched_activity_ids[0])
                summary = detail.get("summary") or {}
                summary_dto = summary.get("summaryDTO") or summary
                activity_data = {
                    "name": summary_dto.get("activityName", "Activity"),
                    "distance_meters": summary_dto.get("distance"),
                    "duration_seconds": summary_dto.get("duration"),
                    "avg_pace_sec_per_km": _meters_per_sec_to_sec_per_km(summary_dto.get("averageSpeed")),
                    "avg_hr": summary_dto.get("averageHR"),
                    "max_hr": summary_dto.get("maxHR"),
                    "calories": summary_dto.get("calories"),
                    "training_effect_aerobic": summary_dto.get("aerobicTrainingEffect"),
                    "training_effect_anaerobic": summary_dto.get("anaerobicTrainingEffect"),
                    "avg_running_cadence": summary_dto.get("averageRunningCadenceInStepsPerMinute"),
                    "elevation_gain": summary_dto.get("elevationGain"),
                }
                workout.completion_metrics = {k: v for k, v in activity_data.items() if v is not None}
            except Exception:
                pass
        if not any(v for v in activity_data.values() if v is not None):
            cached = load_user_data(settings.db_path, uid)
            if cached and cached.get("activities_json"):
                for act in json.loads(cached["activities_json"]):
                    if act.get("activity_id") in workout.matched_activity_ids:
                        activity_data = act
                        break
    if not any(v for v in activity_data.values() if v is not None):
        raise HTTPException(400, "No activity data available \u2014 try syncing activities from Garmin first")

    coach = _get_or_create_coach(uid)

    profile = _user_profile.get(uid)
    analysis = coach.analyze_workout(
        workout=workout.model_dump(mode="json"),
        activity=activity_data,
        profile=profile,
    )

    workout.completion_analysis = analysis
    _save_plans(uid)
    return {"ok": True, "analysis": analysis}


@app.post("/plan/workout-feedback")
async def workout_feedback(req: WorkoutFeedbackRequest, user: dict = Depends(get_current_user)):
    """Save user feedback (RPE + notes) and re-run AI analysis including the feedback."""
    uid = user["id"]
    if uid not in _user_plans:
        _user_plans[uid] = _load_plans(uid)
    plans = _user_plans.get(uid, [])
    plan = next((p for p in plans if p.plan_id == req.plan_id), None)
    if not plan:
        raise HTTPException(404, "Plan not found")

    workout = None
    for week in plan.weeks:
        for wo in week.workouts:
            if wo.name == req.workout_name and str(wo.scheduled_date) == req.scheduled_date:
                workout = wo
                break
        if workout:
            break
    if not workout:
        raise HTTPException(404, "Workout not found")
    if not workout.completed:
        raise HTTPException(400, "Workout is not completed yet")

    # Save user feedback
    if req.rpe is not None:
        workout.user_rpe = max(1, min(10, req.rpe))
    if req.notes is not None:
        workout.user_notes = req.notes

    # Re-run AI analysis with user feedback
    activity_data = {k: v for k, v in (workout.completion_metrics or {}).items() if k != "detail"}
    coach = _get_or_create_coach(uid)
    profile = _user_profile.get(uid)
    analysis = coach.analyze_workout(
        workout=workout.model_dump(mode="json"),
        activity=activity_data,
        profile=profile,
        user_feedback={"rpe": workout.user_rpe, "notes": workout.user_notes},
    )
    workout.completion_analysis = analysis
    _save_plans(uid)
    return {"ok": True, "analysis": analysis}


@app.post("/plan/ai-review")
async def ai_review_plan(plan_id: str | None = None, user: dict = Depends(get_current_user)):
    """AI reviews completed workouts and adapts the remaining plan."""
    from datetime import datetime

    uid = user["id"]
    if uid not in _user_plans:
        _user_plans[uid] = _load_plans(uid)
    plans = _user_plans.get(uid, [])
    if plan_id:
        plan = next((p for p in plans if p.plan_id == plan_id), None)
    else:
        plan = plans[-1] if plans else None
    if not plan:
        raise HTTPException(404, "No plan found")

    # Refresh profile
    garmin = _ensure_garmin(uid)
    if garmin:
        profile = garmin.get_fitness_profile()
        _user_profile[uid] = profile
        save_user_data(settings.db_path, uid, profile_json=profile.model_dump_json())
    profile = _user_profile.get(uid)

    # Gather completed workout summaries
    completed = []
    for week in plan.weeks:
        for wo in week.workouts:
            if wo.completed:
                entry = {
                    "name": wo.name,
                    "type": wo.workout_type.value,
                    "date": str(wo.scheduled_date),
                    "planned_distance_km": round(wo.estimated_distance_meters / 1000, 1) if wo.estimated_distance_meters else None,
                }
                if wo.completion_metrics:
                    entry["actual"] = wo.completion_metrics
                if wo.completion_analysis:
                    entry["ai_analysis"] = wo.completion_analysis
                completed.append(entry)

    if not completed:
        raise HTTPException(400, "No completed workouts to review")

    # Build review prompt for coach
    coach_key = settings.anthropic_api_key or settings.openai_api_key
    coach_model = settings.anthropic_model if settings.anthropic_api_key else settings.openai_model
    coach_provider = "anthropic" if settings.anthropic_api_key else "openai"
    if uid not in _user_coach:
        _user_coach[uid] = Coach(api_key=coach_key, model=coach_model, provider=coach_provider)

    review_prompt = (
        "Review the athlete's completed workouts and provide:\n"
        "1. Overall assessment of how training is going\n"
        "2. Are they on track for their goal?\n"
        "3. Any patterns (positive or concerning)?\n"
        "4. Specific recommendations for upcoming workouts\n\n"
        f"Goal: {plan.goal_type} by {plan.target_date}\n"
    )
    if plan.target_time_seconds:
        m, s = divmod(int(plan.target_time_seconds), 60)
        review_prompt += f"Target time: {m}:{s:02d}\n"
    review_prompt += f"\nCompleted workouts ({len(completed)}):\n"
    for c in completed:
        review_prompt += f"- {c['date']} | {c['name']} ({c['type']})"
        if c.get("actual"):
            act = c["actual"]
            if act.get("distance_meters"):
                review_prompt += f" | {act['distance_meters']/1000:.1f}km"
            if act.get("avg_pace_sec_per_km"):
                pm, ps = divmod(int(act["avg_pace_sec_per_km"]), 60)
                review_prompt += f" | {pm}:{ps:02d}/km"
            if act.get("avg_hr"):
                review_prompt += f" | HR {act['avg_hr']}"
        if c.get("ai_analysis"):
            review_prompt += f"\n  Analysis: {c['ai_analysis'][:200]}"
        review_prompt += "\n"

    review_result = _user_coach[uid].chat(
        message=review_prompt,
        profile=profile,
        plan=plan,
    )

    plan.last_ai_review = datetime.now().isoformat()
    plan.adaptation_notes = review_result.reply
    _save_plans(uid)
    return {"ok": True, "review": review_result.reply, "reviewed_at": plan.last_ai_review}


# ── HYROX endpoints ──────────────────────────────────────────────────

_user_hyrox: dict[str, list] = {}  # per-user cached HyroxRaceResult list


def _load_hyrox(uid: str) -> dict | None:
    """Load cached HYROX data from DB."""
    cached = load_user_data(settings.db_path, uid)
    if cached and cached.get("hyrox_json"):
        return json.loads(cached["hyrox_json"])
    return None


def _save_hyrox(uid: str, data: dict) -> None:
    """Persist HYROX data to DB."""
    save_user_data(settings.db_path, uid, hyrox_json=json.dumps(data))


@app.delete("/hyrox/results")
async def hyrox_delete_results(user: dict = Depends(get_current_user)):
    """Delete cached HYROX results from DB."""
    uid = user["id"]
    _save_hyrox(uid, {})
    _user_hyrox.pop(uid, None)
    return {"ok": True}


@app.get("/hyrox/results")
async def hyrox_get_results(user: dict = Depends(get_current_user)):
    """Return cached HYROX results from DB (no scraping)."""
    uid = user["id"]
    cached = _load_hyrox(uid)
    if cached:
        return cached
    return {"search_name": "", "search_gender": "", "results": []}


@app.get("/hyrox/search")
async def hyrox_search(
    name: str,
    firstname: str = "",
    division: str = "all",
    gender: str = "M",
    user: dict = Depends(get_current_user),
):
    """Preview HYROX search results (listing only, no detail scraping).

    Returns a list of race summaries for the user to select from.
    """
    from paceforge.hyrox.scraper import HyroxScraper

    scraper = HyroxScraper()
    try:
        summaries = scraper.search_preview(name, firstname=firstname, division=division, gender=gender)
    finally:
        scraper.close()

    return {"summaries": summaries}


@app.post("/hyrox/confirm")
async def hyrox_confirm(
    body: dict,
    user: dict = Depends(get_current_user),
):
    """Fetch full details for user-selected races and persist to DB.

    Body: { name, firstname?, gender?, selected_urls: [...] }
    """
    from paceforge.hyrox.scraper import HyroxScraper

    uid = user["id"]
    name = body.get("name", "")
    firstname = body.get("firstname", "")
    gender = body.get("gender", "M")
    selected_urls = body.get("selected_urls", [])

    if not name or not selected_urls:
        raise HTTPException(400, "name and selected_urls are required")

    scraper = HyroxScraper()
    try:
        results = scraper.search_athlete(
            name, firstname=firstname, division="all", gender=gender,
            max_results=30, selected_urls=selected_urls,
        )
    finally:
        scraper.close()

    results_data = [r.model_dump(mode="json") for r in results]
    cache_payload = {
        "search_name": name,
        "search_firstname": firstname,
        "search_gender": gender,
        "results": results_data,
    }

    _save_hyrox(uid, cache_payload)

    # Post feed event for new HYROX results
    try:
        n = len(results_data)
        create_feed_event(
            settings.db_path, uid,
            event_type="hyrox",
            title=f"Added {n} HYROX race result{'s' if n != 1 else ''}",
        )
    except Exception:
        logger.debug("Failed to post HYROX feed event")

    return cache_payload


@app.post("/hyrox/refresh")
async def hyrox_refresh(user: dict = Depends(get_current_user)):
    """Re-scrape HYROX results using the previously saved search parameters."""
    from paceforge.hyrox.scraper import HyroxScraper

    uid = user["id"]
    cached = _load_hyrox(uid)
    if not cached or not cached.get("search_name"):
        raise HTTPException(400, "No previous HYROX search to refresh. Search first.")

    name = cached["search_name"]
    firstname = cached.get("search_firstname", "")
    gender = cached.get("search_gender", "M")
    # Preserve user's race selection
    old_urls = {r.get("athlete_url") for r in cached.get("results", []) if r.get("athlete_url")}

    scraper = HyroxScraper()
    try:
        results = scraper.search_athlete(
            name, firstname=firstname, division="all", gender=gender,
            max_results=30, selected_urls=list(old_urls) if old_urls else None,
        )
    finally:
        scraper.close()

    results_data = [r.model_dump(mode="json") for r in results]
    cache_payload = {
        "search_name": name,
        "search_firstname": firstname,
        "search_gender": gender,
        "results": results_data,
    }

    _save_hyrox(uid, cache_payload)
    return cache_payload


@app.get("/hyrox/analyze/{race_index}")
async def hyrox_analyze_race(race_index: int, user: dict = Depends(get_current_user)):
    """Analyze a specific cached HYROX race result."""
    from paceforge.hyrox.analyzer import analyze_race, compute_training_priorities
    from paceforge.hyrox.models import HyroxRaceResult as HR

    uid = user["id"]
    cached = _load_hyrox(uid)
    if not cached or not cached.get("results"):
        raise HTTPException(404, "No HYROX results cached. Search first.")

    results = cached["results"]
    if race_index < 0 or race_index >= len(results):
        raise HTTPException(400, f"Invalid race index. Must be 0-{len(results)-1}")

    race = HR.model_validate(results[race_index])
    analysis = analyze_race(race)
    priorities = compute_training_priorities(race)
    return {"analysis": analysis, "priorities": priorities}


@app.get("/hyrox/progression")
async def hyrox_progression(user: dict = Depends(get_current_user)):
    """Compute progression trends across all cached HYROX races."""
    from paceforge.hyrox.analyzer import compute_race_progression
    from paceforge.hyrox.models import HyroxRaceResult as HR

    uid = user["id"]
    cached = _load_hyrox(uid)
    if not cached or not cached.get("results"):
        raise HTTPException(404, "No HYROX results cached. Search first.")

    races = [HR.model_validate(r) for r in cached["results"]]
    return compute_race_progression(races)


# ── Friends ───────────────────────────────────────────────────────────


@app.get("/users/search")
async def user_search(q: str, user: dict = Depends(get_current_user)):
    """Search approved users by name or email."""
    if len(q) < 2:
        return []
    return search_users(settings.db_path, q, exclude_user_id=user["id"])


@app.get("/users/approved")
async def approved_users(user: dict = Depends(get_current_user)):
    """Return all approved users (excluding current user) for friend discovery."""
    rows = list_users(settings.db_path, status="approved")
    uid = user["id"]
    return [
        {"id": r["id"], "name": r["name"], "email": r["email"]}
        for r in rows
        if r["id"] != uid
    ]


@app.get("/friends")
async def get_friends(user: dict = Depends(get_current_user)):
    uid = user["id"]
    return {
        "friends": list_friends(settings.db_path, uid),
        "pending": list_pending_requests(settings.db_path, uid),
        "sent": list_sent_requests(settings.db_path, uid),
    }


@app.post("/friends/request")
async def friend_request(body: dict, user: dict = Depends(get_current_user)):
    recipient_id = body.get("recipient_id")
    if not recipient_id:
        raise HTTPException(400, "recipient_id is required")
    result = send_friend_request(settings.db_path, user["id"], recipient_id)
    if not result:
        raise HTTPException(400, "Cannot send friend request")
    return result


@app.post("/friends/respond")
async def friend_respond(body: dict, user: dict = Depends(get_current_user)):
    friendship_id = body.get("friendship_id")
    accept = body.get("accept", False)
    if not friendship_id:
        raise HTTPException(400, "friendship_id is required")
    result = respond_friend_request(settings.db_path, friendship_id, accept=accept)
    return result


@app.delete("/friends/{friendship_id}")
async def friend_remove(friendship_id: str, user: dict = Depends(get_current_user)):
    remove_friend(settings.db_path, friendship_id)
    return {"ok": True}


@app.get("/users/{user_id}/profile")
async def get_user_public_profile(user_id: str, user: dict = Depends(get_current_user)):
    """Return a friend's profile: fitness highlights, activities, HYROX, plan summary."""
    uid = user["id"]
    if user_id != uid:
        friend_ids = get_friend_ids(settings.db_path, uid)
        if user_id not in friend_ids:
            raise HTTPException(403, "You can only view profiles of friends")

    cached = load_user_data(settings.db_path, user_id)
    result: dict = {"user_id": user_id}

    # User name
    u = get_user_by_id(settings.db_path, user_id)
    result["name"] = u["name"] if u else "Unknown"

    # Fitness profile highlights
    if cached and cached.get("profile_json"):
        profile = UserFitnessProfile.model_validate_json(cached["profile_json"])
        result["profile"] = {
            "vo2_max": profile.vo2_max,
            "resting_hr": profile.resting_hr,
            "max_hr": profile.max_hr,
            "training_readiness": profile.training_readiness,
            "training_status": profile.training_status,
            "hrv_status": profile.hrv_status,
            "hrv_last_night": profile.hrv_last_night,
            "weekly_mileage_km": profile.weekly_mileage_km,
        }
    else:
        result["profile"] = None

    # Recent activities
    if cached and cached.get("activities_json"):
        activities = json.loads(cached["activities_json"])
        result["activities"] = activities[:15]
    else:
        result["activities"] = []

    # HYROX results
    if cached and cached.get("hyrox_json"):
        result["hyrox"] = json.loads(cached["hyrox_json"])
    else:
        result["hyrox"] = None

    # Training plan summary (accepted plans only)
    plans_data = _user_plans[user_id] if user_id in _user_plans else _load_plans(user_id)
    accepted = [p for p in plans_data if p.accepted]
    if accepted:
        plan = accepted[0]
        total_workouts = sum(len(w.workouts) for w in plan.weeks)
        completed_workouts = sum(1 for w in plan.weeks for wo in w.workouts if wo.completed)
        result["plan"] = {
            "name": plan.name,
            "goal_type": plan.goal_type,
            "target_date": str(plan.target_date),
            "total_weeks": plan.total_weeks,
            "total_workouts": total_workouts,
            "completed_workouts": completed_workouts,
            "progress_pct": round(completed_workouts / total_workouts * 100) if total_workouts else 0,
        }
    else:
        result["plan"] = None

    # Feed events for this user
    events = get_feed(settings.db_path, [user_id], limit=20)
    result["feed"] = events

    return result


# ── Feed ──────────────────────────────────────────────────────────────

# Track which users have already been backfilled this process lifetime
_backfilled_users: set[str] = set()


def _backfill_feed_events(uid: str) -> None:
    """Create feed events for completed workouts that don't have one yet,
    and retroactively enrich existing events with description/splits."""
    if uid in _backfilled_users:
        return
    _backfilled_users.add(uid)

    if uid not in _user_plans:
        _user_plans[uid] = _load_plans(uid)
    plans = _user_plans.get(uid, [])
    if not plans:
        return

    existing = get_feed(settings.db_path, [uid], limit=500)
    existing_by_title: dict[str, dict] = {}
    for e in existing:
        existing_by_title[e.get("title", "")] = e

    created = 0
    updated = 0
    for plan in plans:
        if not plan.accepted:
            continue
        for week in plan.weeks:
            for wo in week.workouts:
                if not wo.completed or wo.workout_type.value == "rest":
                    continue
                title = f"Completed: {wo.name}"
                metrics = wo.completion_metrics or {}
                splits = _extract_compact_splits(metrics)
                meta = _build_feed_metadata(wo, metrics, splits)

                if title not in existing_by_title:
                    # Create new event
                    try:
                        create_feed_event(
                            settings.db_path, uid,
                            event_type="activity",
                            title=title,
                            body=None,
                            metadata=meta,
                        )
                        created += 1
                    except Exception:
                        pass
                else:
                    # Retroactively enrich existing event if missing new fields
                    ev = existing_by_title[title]
                    ev_meta_raw = ev.get("metadata")
                    ev_meta = {}
                    if ev_meta_raw:
                        try:
                            ev_meta = json.loads(ev_meta_raw) if isinstance(ev_meta_raw, str) else (ev_meta_raw or {})
                        except (json.JSONDecodeError, TypeError):
                            ev_meta = {}
                    needs_update = not ev_meta.get("description") and meta.get("description")
                    needs_update = needs_update or (not ev_meta.get("purpose") and meta.get("purpose"))
                    # Always re-update splits (fixes bad data from old split_summaries source)
                    needs_update = needs_update or (meta.get("splits") and ev_meta.get("splits") != meta.get("splits"))
                    if needs_update:
                        ev_meta.update(meta)
                        try:
                            update_feed_event_metadata(settings.db_path, ev["id"], ev_meta)
                            updated += 1
                        except Exception:
                            pass
    if created:
        logger.info("Backfilled %d feed events for user %s", created, uid)
    if updated:
        logger.info("Retroactively enriched %d feed events for user %s", updated, uid)


@app.get("/feed")
async def feed(limit: int = 20, offset: int = 0, user: dict = Depends(get_current_user)):
    uid = user["id"]
    _backfill_feed_events(uid)
    friend_ids = get_friend_ids(settings.db_path, uid)
    all_ids = [uid] + friend_ids
    events = get_feed(settings.db_path, all_ids, limit=limit, offset=offset)
    event_ids = [e["id"] for e in events]
    liked = get_user_likes(settings.db_path, uid, event_ids)
    for e in events:
        e["liked_by_me"] = e["id"] in liked
    return events


@app.post("/feed/{event_id}/like")
async def feed_like(event_id: str, user: dict = Depends(get_current_user)):
    liked = toggle_like(settings.db_path, event_id, user["id"])
    return {"liked": liked}


@app.post("/feed/{event_id}/comment")
async def feed_comment(event_id: str, body: dict, user: dict = Depends(get_current_user)):
    text = body.get("body", "").strip()
    if not text:
        raise HTTPException(400, "Comment body is required")
    if len(text) > 500:
        raise HTTPException(400, "Comment too long (max 500 chars)")
    comment = add_comment(settings.db_path, event_id, user["id"], text)
    return comment


@app.get("/feed/{event_id}/comments")
async def feed_comments(event_id: str, user: dict = Depends(get_current_user)):
    return get_comments(settings.db_path, event_id)


# ── Strava OAuth & Activity Push ─────────────────────────────────────

_STRAVA_SPORT_TYPE_MAP: dict[str, str] = {
    "running": "Run",
    "trail_running": "TrailRun",
    "treadmill_running": "Run",
    "fitness_equipment": "Workout",
    "cycling": "Ride",
    "indoor_cycling": "Ride",
    "walking": "Walk",
    "hiking": "Hike",
    "swimming": "Swim",
    "open_water_swimming": "Swim",
    "strength_training": "WeightTraining",
    "yoga": "Yoga",
    "elliptical": "Elliptical",
    "stair_climbing": "StairStepper",
}

_STRAVA_TRAINER_TYPES: set[str] = {
    "treadmill_running",
    "indoor_cycling",
    "fitness_equipment",
    "elliptical",
    "stair_climbing",
}


def _get_strava_client() -> StravaClient:
    if not settings.strava_client_id or not settings.strava_client_secret:
        raise HTTPException(503, "Strava integration not configured")
    return StravaClient(settings.strava_client_id, settings.strava_client_secret)


def _load_strava_data(uid: str) -> dict | None:
    """Load Strava connection data from user preferences."""
    cached = load_user_data(settings.db_path, uid)
    if not cached or not cached.get("preferences_json"):
        return None
    try:
        prefs = json.loads(cached["preferences_json"])
    except (json.JSONDecodeError, TypeError):
        return None
    return prefs.get("strava")


def _save_strava_data(uid: str, strava_data: dict | None) -> None:
    """Save Strava connection data into user preferences."""
    cached = load_user_data(settings.db_path, uid)
    prefs: dict = {}
    if cached and cached.get("preferences_json"):
        try:
            prefs = json.loads(cached["preferences_json"])
        except (json.JSONDecodeError, TypeError):
            prefs = {}
    if strava_data is None:
        prefs.pop("strava", None)
    else:
        prefs["strava"] = strava_data
    save_user_data(settings.db_path, uid, preferences_json=json.dumps(prefs))


@app.get("/strava/auth-url")
async def strava_auth_url(user: dict = Depends(get_current_user)):
    """Return the Strava OAuth authorize URL for the current user."""
    client = _get_strava_client()
    # Encode user_id into the state param as a signed JWT so the callback
    # can identify which user authorized without requiring a Bearer token.
    state_token = create_access_token(user["id"], user["role"], settings.jwt_secret)
    redirect_uri = f"{settings.cors_origins.split(',')[0].strip()}/strava/callback"
    url = client.get_auth_url(redirect_uri=redirect_uri, state=state_token)
    return {"url": url, "redirect_uri": redirect_uri}


@app.get("/strava/callback")
async def strava_callback(code: str = "", state: str = "", error: str = ""):
    """Handle Strava OAuth callback — exchanges code for tokens."""
    if error:
        raise HTTPException(400, f"Strava authorization denied: {error}")
    if not code or not state:
        raise HTTPException(400, "Missing code or state parameter")

    # Decode user from state JWT
    try:
        payload = decode_access_token(state, settings.jwt_secret)
    except Exception:
        raise HTTPException(400, "Invalid or expired state token")
    uid = payload["sub"]

    client = _get_strava_client()
    try:
        tokens = client.exchange_code(code)
    except Exception as e:
        logger.error("Strava token exchange failed: %s", e)
        raise HTTPException(502, "Failed to exchange Strava authorization code")

    _save_strava_data(uid, tokens)
    logger.info("Strava connected for user %s (athlete: %s)", uid, tokens.get("athlete_name"))

    # Return an HTML page that closes the popup / redirects to dashboard
    from fastapi.responses import HTMLResponse
    return HTMLResponse(
        "<html><body><h2>Strava connected!</h2>"
        "<p>You can close this window and return to PaceForge.</p>"
        "<script>window.close();</script></body></html>"
    )


@app.get("/strava/status")
async def strava_status(user: dict = Depends(get_current_user)):
    """Return Strava connection status."""
    uid = user["id"]
    data = _load_strava_data(uid)
    if not data:
        return {"connected": False, "auto_update": False}
    # Read auto_update preference
    auto_update = False
    cached = load_user_data(settings.db_path, uid)
    if cached and cached.get("preferences_json"):
        try:
            prefs = json.loads(cached["preferences_json"])
            auto_update = bool(prefs.get("strava_auto_update", False))
        except (json.JSONDecodeError, TypeError):
            pass
    return {
        "connected": True,
        "athlete_name": data.get("athlete_name", ""),
        "athlete_id": data.get("athlete_id"),
        "auto_update": auto_update,
    }


@app.post("/strava/auto-update")
async def strava_auto_update(body: dict, user: dict = Depends(get_current_user)):
    """Toggle automatic Strava updates on Garmin sync."""
    uid = user["id"]
    enabled = bool(body.get("enabled", False))
    cached = load_user_data(settings.db_path, uid)
    prefs: dict = {}
    if cached and cached.get("preferences_json"):
        try:
            prefs = json.loads(cached["preferences_json"])
        except (json.JSONDecodeError, TypeError):
            prefs = {}
    prefs["strava_auto_update"] = enabled
    save_user_data(settings.db_path, uid, preferences_json=json.dumps(prefs))
    return {"auto_update": enabled}


@app.delete("/strava/disconnect")
async def strava_disconnect(user: dict = Depends(get_current_user)):
    """Disconnect Strava — revoke access and remove tokens."""
    uid = user["id"]
    data = _load_strava_data(uid)
    if not data:
        return {"ok": True}
    client = _get_strava_client()
    try:
        client.deauthorize(data.get("access_token", ""))
    except Exception:
        logger.warning("Strava deauthorize call failed (continuing anyway)")
    _save_strava_data(uid, None)
    # Also clear sent-activities list
    cached = load_user_data(settings.db_path, uid)
    if cached and cached.get("preferences_json"):
        try:
            prefs = json.loads(cached["preferences_json"])
            prefs.pop("strava_sent_activities", None)
            save_user_data(settings.db_path, uid, preferences_json=json.dumps(prefs))
        except (json.JSONDecodeError, TypeError):
            pass
    return {"ok": True}


def _build_strava_description(
    activity: dict,
    workout_description: str | None,
    ai_analysis: str | None,
) -> str:
    """Build the rich description for a Strava activity post."""
    parts: list[str] = []

    # Metrics summary from Garmin data
    metrics: list[str] = []
    dist_m = activity.get("distance_meters")
    dur_s = activity.get("duration_seconds")
    if dist_m and dist_m > 0:
        km = dist_m / 1000
        metrics.append(f"Distance: {km:.2f} km")
        if dur_s and dur_s > 0:
            pace_s = dur_s / km
            pm, ps = divmod(int(pace_s), 60)
            metrics.append(f"Avg Pace: {pm}:{ps:02d} /km")
    if dur_s and dur_s > 0:
        dm, ds = divmod(int(dur_s), 60)
        dh, dm = divmod(dm, 60)
        metrics.append(f"Duration: {dh}:{dm:02d}:{ds:02d}" if dh else f"Duration: {dm}:{ds:02d}")
    avg_hr = activity.get("avg_hr")
    max_hr = activity.get("max_hr")
    if avg_hr:
        hr_str = f"Heart Rate: {avg_hr} bpm avg"
        if max_hr:
            hr_str += f" / {max_hr} bpm max"
        metrics.append(hr_str)
    cadence = activity.get("avg_running_cadence")
    if cadence:
        metrics.append(f"Cadence: {int(cadence * 2)} spm")
    elev = activity.get("elevation_gain")
    if elev and elev > 0:
        metrics.append(f"Elevation: +{int(elev)}m")
    cals = activity.get("calories")
    if cals:
        metrics.append(f"Calories: {cals} kcal")
    if metrics:
        parts.append("\n".join(metrics))

    if workout_description:
        if parts:
            parts.append("")
        parts.append(f"Planned workout:\n{workout_description}")
    if ai_analysis:
        if parts:
            parts.append("")
        parts.append(f"AI Coach Analysis:\n{ai_analysis}")
    # Footer
    parts.append("")
    parts.append("---")
    parts.append("Training plan generated with PaceForge \u2014 want to be a BETA tester? Get in touch!")
    return "\n".join(parts)


def _do_strava_push(uid: str, activity_id: int, *, raise_on_error: bool = True) -> dict:
    """Core logic for pushing a single activity to Strava.

    Used by both the /strava/push endpoint and the auto-push hook.
    When *raise_on_error* is False (auto-push), errors return an error dict
    instead of raising HTTPException.
    """
    strava_data = _load_strava_data(uid)
    if not strava_data:
        if raise_on_error:
            raise HTTPException(400, "Strava not connected")
        return {"error": "Strava not connected"}

    cached = load_user_data(settings.db_path, uid)
    prefs: dict = {}
    if cached and cached.get("preferences_json"):
        try:
            prefs = json.loads(cached["preferences_json"])
        except (json.JSONDecodeError, TypeError):
            prefs = {}
    sent: list = prefs.get("strava_sent_activities", [])

    # Find activity in cached data
    act_dict: dict | None = None
    if cached and cached.get("activities_json"):
        for a in json.loads(cached["activities_json"]):
            if a.get("activity_id") == activity_id:
                act_dict = a
                break
    if not act_dict:
        if raise_on_error:
            raise HTTPException(404, "Activity not found in cached data")
        return {"error": "Activity not found"}

    # Find matched planned workout (for description)
    workout_description: str | None = None
    if uid not in _user_plans:
        _user_plans[uid] = _load_plans(uid)
    for plan in _user_plans.get(uid, []):
        if not plan.accepted:
            continue
        for week in plan.weeks:
            for wo in week.workouts:
                if activity_id in wo.matched_activity_ids and wo.description:
                    workout_description = wo.description
                    break
            if workout_description:
                break
        if workout_description:
            break

    # Load or generate AI analysis
    analyses: dict = prefs.get("activity_analyses", {})
    ai_analysis: str | None = analyses.get(str(activity_id))
    if not ai_analysis:
        try:
            garmin = _ensure_garmin(uid)
            if garmin:
                detail = garmin.get_activity_detail(activity_id)
                act_for_ai = dict(act_dict)
                act_for_ai["splits"] = detail.get("splits")
                act_for_ai["hr_zones"] = detail.get("hr_zones")
                profile = _user_profile.get(uid)
                if not profile and cached and cached.get("profile_json"):
                    profile = UserFitnessProfile.model_validate_json(cached["profile_json"])
                coach = _get_or_create_coach(uid)
                ai_analysis = coach.analyze_activity(act_for_ai, profile=profile)
                analyses[str(activity_id)] = ai_analysis
                prefs["activity_analyses"] = analyses
        except Exception as e:
            logger.warning("On-the-fly AI analysis failed for Strava push: %s", e)

    # Build description
    description = _build_strava_description(act_dict, workout_description, ai_analysis)

    # Map activity type to Strava sport_type
    act_type = act_dict.get("activity_type", "running")
    sport_type = _STRAVA_SPORT_TYPE_MAP.get(act_type, "Workout")
    is_trainer = act_type in _STRAVA_TRAINER_TYPES

    # Build PaceForge-branded title
    strava_title = act_dict.get("name", "PaceForge Activity")
    if workout_description:
        first_line = workout_description.split("\n")[0].strip()
        if first_line:
            strava_title = f"{first_line} / PaceForge AI plan"
    elif "PaceForge" not in strava_title:
        strava_title = f"{strava_title} / PaceForge"

    # Parse start_time for matching
    start_time = act_dict.get("start_time", "")
    if hasattr(start_time, "isoformat"):
        start_time = start_time.isoformat()

    # Ensure valid token
    try:
        client = _get_strava_client()
        access_token, strava_data = client.ensure_valid_token(strava_data)
        _save_strava_data(uid, strava_data)
    except Exception as e:
        logger.error("Strava token refresh failed: %s", e)
        if raise_on_error:
            raise HTTPException(502, "Failed to refresh Strava token — please reconnect")
        return {"error": f"Token refresh failed: {e}"}

    # Parse epoch for activity matching
    start_epoch: float | None = None
    try:
        from datetime import datetime as _dt
        if isinstance(start_time, str) and start_time:
            parsed = _dt.fromisoformat(start_time.replace("Z", "+00:00"))
            if parsed.tzinfo is None:
                parsed = parsed.replace(tzinfo=UTC)
            start_epoch = parsed.timestamp()
    except (ValueError, TypeError):
        pass

    logger.info("Strava push %s: start_time=%s, start_epoch=%s, distance=%s",
                activity_id, start_time, start_epoch, act_dict.get("distance_meters"))

    strava_id: int | str = ""
    updated = False

    if start_epoch:
        try:
            existing = client.find_matching_activity(
                access_token,
                start_epoch,
                distance_meters=act_dict.get("distance_meters"),
            )
            logger.info("Strava find_matching_activity result: %s",
                        existing.get("id") if existing else None)
            if existing:
                strava_id = existing["id"]
                client.update_activity(
                    access_token,
                    strava_id,
                    name=strava_title,
                    description=description,
                )
                updated = True
                logger.info(
                    "Updated existing Strava activity %s with PaceForge data",
                    strava_id,
                )
        except Exception as e:
            logger.warning("Strava find/update failed, falling back to create: %s", e)

    # Fallback: create new activity if no match found
    if not updated:
        try:
            result = client.create_activity(
                access_token,
                name=strava_title,
                sport_type=sport_type,
                start_date_local=start_time,
                elapsed_time=int(act_dict.get("duration_seconds", 0)),
                description=description,
                distance=act_dict.get("distance_meters"),
                trainer=is_trainer,
            )
            strava_id = result.get("id", "")
        except DuplicateActivityError:
            if start_epoch:
                try:
                    existing = client.find_matching_activity(
                        access_token, start_epoch,
                        distance_meters=act_dict.get("distance_meters"),
                    )
                    if existing:
                        strava_id = existing["id"]
                        client.update_activity(
                            access_token, strava_id,
                            name=strava_title, description=description,
                        )
                        updated = True
                        logger.info("Updated duplicate Strava activity %s with PaceForge data", strava_id)
                except Exception as ue:
                    logger.warning("Failed to update duplicate Strava activity: %s", ue)
            if not updated:
                if activity_id not in sent:
                    sent.append(activity_id)
                    prefs["strava_sent_activities"] = sent
                    save_user_data(settings.db_path, uid, preferences_json=json.dumps(prefs))
                return {
                    "strava_activity_id": None,
                    "url": None,
                    "duplicate": True,
                    "message": "Activity exists on Strava but could not be updated",
                }
        except Exception as e:
            logger.error("Strava create activity failed: %s", e)
            if raise_on_error:
                raise HTTPException(502, f"Strava API error: {e}")
            return {"error": f"Strava API error: {e}"}

    # Record that we sent this activity
    if activity_id not in sent:
        sent.append(activity_id)
        prefs["strava_sent_activities"] = sent
    save_user_data(settings.db_path, uid, preferences_json=json.dumps(prefs))

    return {
        "strava_activity_id": strava_id,
        "url": f"https://www.strava.com/activities/{strava_id}",
        "updated": updated,
    }


@app.post("/strava/push/{activity_id}")
async def strava_push(activity_id: int, user: dict = Depends(get_current_user)):
    """Push a completed activity to Strava."""
    return _do_strava_push(user["id"], activity_id, raise_on_error=True)


# ── Health Data (Apple Health / Google Health Connect) ───────────────

_HEALTH_METRICS = ("weight_kg", "bmi", "body_fat_pct", "lean_body_mass_kg")


@app.get("/health/data")
async def get_health_data(user: dict = Depends(get_current_user)):
    """Return stored health data from Apple Health / Google Health Connect."""
    uid = user["id"]
    cached = load_user_data(settings.db_path, uid)
    if cached and cached.get("health_json"):
        try:
            return json.loads(cached["health_json"])
        except (json.JSONDecodeError, TypeError):
            pass
    return {"sources": [], "last_sync": None, "body_composition": {
        "height_cm": None, "weight_kg": [], "bmi": [], "body_fat_pct": [], "lean_body_mass_kg": [],
    }}


@app.post("/health/data")
async def post_health_data(payload: dict, user: dict = Depends(get_current_user)):
    """Store health data from mobile app (Apple Health / Google Health Connect)."""
    from datetime import UTC, datetime, timedelta

    uid = user["id"]

    # Load existing data
    cached = load_user_data(settings.db_path, uid)
    existing: dict = {}
    if cached and cached.get("health_json"):
        try:
            existing = json.loads(cached["health_json"])
        except (json.JSONDecodeError, TypeError):
            existing = {}

    # Merge sources
    old_sources = set(existing.get("sources", []))
    new_sources = set(payload.get("sources", []))
    merged_sources = sorted(old_sources | new_sources)

    # Merge body composition
    old_bc = existing.get("body_composition", {})
    new_bc = payload.get("body_composition", {})
    merged_bc: dict = {}

    # Scalar fields (height_cm)
    merged_bc["height_cm"] = new_bc.get("height_cm") or old_bc.get("height_cm")

    # Time-series fields — deduplicate by date (new values win), trim to 90 days
    cutoff = (datetime.now(UTC) - timedelta(days=90)).strftime("%Y-%m-%d")
    for metric in _HEALTH_METRICS:
        old_entries = old_bc.get(metric, [])
        new_entries = new_bc.get(metric, [])
        if not isinstance(old_entries, list):
            old_entries = []
        if not isinstance(new_entries, list):
            new_entries = []
        by_date: dict = {}
        for entry in old_entries:
            d = entry.get("date", "")
            if d >= cutoff:
                by_date[d] = entry
        for entry in new_entries:
            d = entry.get("date", "")
            if d >= cutoff:
                by_date[d] = entry  # new wins
        merged_bc[metric] = sorted(by_date.values(), key=lambda e: e.get("date", ""))

    now = datetime.now(UTC).isoformat(timespec="seconds")
    result = {
        "sources": merged_sources,
        "last_sync": now,
        "body_composition": merged_bc,
    }

    save_user_data(settings.db_path, uid, health_json=json.dumps(result))
    return result


# ── Diet & Nutrition ─────────────────────────────────────────────────


def _maybe_auto_adjust_diet(uid: str) -> None:
    """Auto-adjust diet plan if enabled and 7+ days since last adjustment."""
    try:
        data = _load_diet_data(uid)
        if not data.active_plan or not data.active_plan.active or not data.active_plan.auto_adjust:
            return
        last = data.active_plan.last_adjusted
        if last:
            from datetime import datetime as dt
            last_dt = dt.fromisoformat(last.replace("Z", "+00:00")) if isinstance(last, str) else last
            if (datetime.now(UTC) - last_dt).days < 7:
                return
        # Trigger adjustment
        profile = _user_profile.get(uid)
        activities: list[dict] = []
        cached = load_user_data(settings.db_path, uid)
        if cached and cached.get("activities_json"):
            with contextlib.suppress(json.JSONDecodeError, TypeError):
                activities = json.loads(cached["activities_json"])
        weight_hist = [w.model_dump(mode="json") for w in data.weight_history[-30:]]
        user_notes = [n.model_dump(mode="json") for n in data.user_notes[-10:]]
        coach = _get_or_create_coach(uid)
        raw_json = coach.adjust_diet_plan(
            current_plan_summary={
                "macro_targets": data.active_plan.macro_targets.model_dump(mode="json"),
                "goals": [g.value for g in data.profile.goals],
            },
            weight_trend=weight_hist,
            activity_data=activities[-14:],
            user_notes=user_notes,
            fitness_profile=profile,
        )
        plan = _parse_diet_plan_response(raw_json, data.profile, existing_plan=data.active_plan)
        data.active_plan = plan
        _save_diet_data(uid, data)
        logger.info("Auto-adjusted diet plan for user %s", uid)
    except Exception:
        logger.warning("Diet auto-adjust failed for %s", uid, exc_info=True)


from paceforge.models.diet import (  # noqa: E402
    DailyMealPlan,
    DietData,
    DietGoal,
    DietPlan,
    DietProfile,
    FoodItem,
    MacroTotals,
    Meal,
    MealType,
    UserNote,
    WeeklyMealTemplate,
    WeightEntry,
    WeightSource,
)


class DietProfileRequest(BaseModel):
    goals: list[str] = []
    target_weight_kg: float | None = None
    daily_meals_count: int = 3
    plan_weeks: int = 1
    start_date: str | None = None
    meal_sizes: dict[str, str] = {}
    preferred_foods: list[str] = []
    allergies: list[str] = []
    restrictions: list[str] = []
    notes: str = ""


class WeightEntryRequest(BaseModel):
    weight_kg: float
    body_fat_pct: float | None = None
    date: str | None = None


class DietNoteRequest(BaseModel):
    content: str


def _load_diet_data(uid: str) -> DietData:
    """Load diet data from DB, returning empty DietData if none exists."""
    cached = load_user_data(settings.db_path, uid)
    if cached and cached.get("diet_json"):
        try:
            return DietData.model_validate_json(cached["diet_json"])
        except Exception:
            logger.warning("Could not parse diet_json for %s", uid)
    return DietData()


def _save_diet_data(uid: str, data: DietData) -> None:
    """Persist diet data to DB."""
    save_user_data(
        settings.db_path, uid,
        diet_json=data.model_dump_json(),
    )


@app.get("/diet/profile")
async def get_diet_profile(user: dict = Depends(get_current_user)):
    """Get diet profile and active plan summary."""
    uid = user["id"]
    data = _load_diet_data(uid)
    result: dict = {"profile": data.profile.model_dump(mode="json")}
    if data.active_plan:
        result["plan_summary"] = {
            "plan_id": data.active_plan.plan_id,
            "active": data.active_plan.active,
            "created_at": data.active_plan.created_at,
            "macro_targets": data.active_plan.macro_targets.model_dump(mode="json"),
            "weeks_count": len(data.active_plan.weekly_templates),
            "auto_adjust": data.active_plan.auto_adjust,
        }
    return result


@app.post("/diet/profile")
async def save_diet_profile(req: DietProfileRequest, user: dict = Depends(get_current_user)):
    """Save/update diet profile."""
    uid = user["id"]
    data = _load_diet_data(uid)
    valid_goals = {g.value for g in DietGoal}
    parsed_start = None
    if req.start_date:
        with contextlib.suppress(ValueError):
            parsed_start = date.fromisoformat(req.start_date)
    valid_sizes = {"light", "regular", "large"}
    meal_sizes = {k: v for k, v in req.meal_sizes.items() if v in valid_sizes}
    data.profile = DietProfile(
        goals=[DietGoal(g) for g in req.goals if g in valid_goals],
        target_weight_kg=req.target_weight_kg,
        daily_meals_count=req.daily_meals_count,
        plan_weeks=max(1, min(4, req.plan_weeks)),
        start_date=parsed_start,
        meal_sizes=meal_sizes,
        preferred_foods=req.preferred_foods,
        allergies=req.allergies,
        restrictions=req.restrictions,
        notes=req.notes,
    )
    _save_diet_data(uid, data)
    return {"ok": True}


@app.post("/diet/generate")
async def generate_diet_plan(user: dict = Depends(get_current_user)):
    """Generate a new AI diet plan based on profile, Garmin data, and weight history."""
    uid = user["id"]
    data = _load_diet_data(uid)

    if not data.profile.goals:
        raise HTTPException(400, "Set diet goals in your profile first")

    try:
        # Gather context
        profile = _user_profile.get(uid)
        activities: list[dict] = []
        cached = load_user_data(settings.db_path, uid)
        if cached and cached.get("activities_json"):
            with contextlib.suppress(json.JSONDecodeError, TypeError):
                activities = json.loads(cached["activities_json"])

        weight_hist = [w.model_dump(mode="json") for w in data.weight_history[-30:]]

        # Get active training plan
        training_plan = None
        if uid in _user_plans:
            accepted = [p for p in _user_plans[uid] if p.accepted]
            if accepted:
                training_plan = accepted[0]

        coach = _get_or_create_coach(uid)
        raw_json = coach.generate_diet_plan(
            diet_profile=data.profile.model_dump(mode="json"),
            fitness_profile=profile,
            activities=activities[-30:],
            weight_history=weight_hist,
            training_plan=training_plan,
        )

        # Parse the AI response
        plan = _parse_diet_plan_response(raw_json, data.profile)
        data.active_plan = plan
        _save_diet_data(uid, data)
        return plan.model_dump(mode="json")
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Diet plan generation failed for %s: %s", uid, e, exc_info=True)
        raise HTTPException(500, f"Diet plan generation failed: {e}")


@app.get("/diet/plan")
async def get_diet_plan(user: dict = Depends(get_current_user)):
    """Get the active diet plan."""
    uid = user["id"]
    data = _load_diet_data(uid)
    if not data.active_plan:
        return {"plan": None}
    return data.active_plan.model_dump(mode="json")


class MealRegenerateRequest(BaseModel):
    day_index: int = 0
    meal_index: int = 0


@app.post("/diet/meal/regenerate")
async def regenerate_single_meal(
    req: MealRegenerateRequest,
    user: dict = Depends(get_current_user),
):
    """Regenerate a single meal in the active diet plan."""
    uid = user["id"]
    data = _load_diet_data(uid)
    if not data.active_plan:
        raise HTTPException(404, "No active diet plan")

    plan = data.active_plan
    # Flatten all days across weekly templates
    all_days = [d for w in plan.weekly_templates for d in w.days]
    if req.day_index < 0 or req.day_index >= len(all_days):
        raise HTTPException(400, f"Invalid day_index {req.day_index}")
    target_day = all_days[req.day_index]
    if req.meal_index < 0 or req.meal_index >= len(target_day.meals):
        raise HTTPException(400, f"Invalid meal_index {req.meal_index}")

    target_meal = target_day.meals[req.meal_index]
    other_names = [m.name for i, m in enumerate(target_day.meals) if i != req.meal_index]

    coach = _get_or_create_coach(uid)
    raw = coach.generate_single_meal(
        meal_type=target_meal.meal_type.value,
        current_meal_name=target_meal.name,
        other_meals_today=other_names,
        macro_targets=plan.macro_targets.model_dump(),
        diet_profile=data.profile.model_dump(mode="json"),
    )

    # Parse single meal JSON
    try:
        parsed = json.loads(raw)
    except json.JSONDecodeError:
        from json_repair import loads as repair_loads
        parsed = repair_loads(raw)
        if not isinstance(parsed, dict):
            raise HTTPException(500, "AI returned invalid meal format")

    if parsed.get("error"):
        raise HTTPException(500, parsed["error"])

    # Build replacement meal
    foods = [
        FoodItem(
            name=f.get("name", ""), quantity=f.get("quantity", 0),
            unit=f.get("unit", "g"), calories=f.get("calories", 0),
            protein_g=f.get("protein_g", 0), carbs_g=f.get("carbs_g", 0),
            fat_g=f.get("fat_g", 0),
        )
        for f in parsed.get("foods", [])
    ]
    raw_type = parsed.get("meal_type", target_meal.meal_type.value)
    try:
        meal_type = MealType(raw_type)
    except ValueError:
        meal_type = target_meal.meal_type
    new_meal = Meal(
        name=parsed.get("name", "Meal"),
        meal_type=meal_type,
        foods=foods,
        total_calories=parsed.get("total_calories", 0),
        protein_g=parsed.get("protein_g", 0),
        carbs_g=parsed.get("carbs_g", 0),
        fat_g=parsed.get("fat_g", 0),
        fiber_g=parsed.get("fiber_g", 0),
        recipe_notes=parsed.get("recipe_notes", ""),
    )
    target_day.meals[req.meal_index] = new_meal

    # Recalculate daily totals
    target_day.daily_totals = MacroTotals(
        calories=sum(m.total_calories for m in target_day.meals),
        protein_g=sum(m.protein_g for m in target_day.meals),
        carbs_g=sum(m.carbs_g for m in target_day.meals),
        fat_g=sum(m.fat_g for m in target_day.meals),
        fiber_g=sum(m.fiber_g for m in target_day.meals),
    )

    _save_diet_data(uid, data)
    return plan.model_dump(mode="json")


@app.delete("/diet/plan")
async def delete_diet_plan(user: dict = Depends(get_current_user)):
    """Delete the active diet plan."""
    uid = user["id"]
    data = _load_diet_data(uid)
    if not data.active_plan:
        raise HTTPException(404, "No active diet plan to delete")
    data.active_plan = None
    _save_diet_data(uid, data)
    return {"ok": True}


@app.post("/diet/plan/regenerate")
async def regenerate_diet_plan(user: dict = Depends(get_current_user)):
    """Re-evaluate and adjust the current diet plan based on progress."""
    uid = user["id"]
    data = _load_diet_data(uid)

    if not data.active_plan:
        raise HTTPException(404, "No active diet plan to adjust")

    profile = _user_profile.get(uid)
    activities: list[dict] = []
    cached = load_user_data(settings.db_path, uid)
    if cached and cached.get("activities_json"):
        with contextlib.suppress(json.JSONDecodeError, TypeError):
            activities = json.loads(cached["activities_json"])

    weight_hist = [w.model_dump(mode="json") for w in data.weight_history[-30:]]
    user_notes = [n.model_dump(mode="json") for n in data.user_notes[-10:]]

    coach = _get_or_create_coach(uid)
    raw_json = coach.adjust_diet_plan(
        current_plan_summary={
            "macro_targets": data.active_plan.macro_targets.model_dump(mode="json"),
            "goals": [g.value for g in data.profile.goals],
            "preferred_foods": data.profile.preferred_foods,
            "daily_meals_count": data.profile.daily_meals_count,
        },
        weight_trend=weight_hist,
        activity_data=activities[-14:],
        user_notes=user_notes,
        fitness_profile=profile,
    )

    plan = _parse_diet_plan_response(raw_json, data.profile, existing_plan=data.active_plan)
    data.active_plan = plan
    _save_diet_data(uid, data)
    return plan.model_dump(mode="json")


@app.get("/diet/weight-history")
async def get_weight_history(user: dict = Depends(get_current_user)):
    """Get weight history (combined Garmin + manual entries)."""
    uid = user["id"]
    data = _load_diet_data(uid)
    return [w.model_dump(mode="json") for w in data.weight_history]


@app.post("/diet/weight")
async def add_weight_entry(req: WeightEntryRequest, user: dict = Depends(get_current_user)):
    """Add a manual weight entry."""
    uid = user["id"]
    data = _load_diet_data(uid)
    entry_date = date.fromisoformat(req.date) if req.date else date.today()
    entry = WeightEntry(
        date=entry_date,
        weight_kg=req.weight_kg,
        body_fat_pct=req.body_fat_pct,
        source=WeightSource.MANUAL,
    )
    # Replace if same date exists, otherwise append
    data.weight_history = [w for w in data.weight_history if str(w.date) != str(entry_date)]
    data.weight_history.append(entry)
    data.weight_history.sort(key=lambda w: w.date)
    _save_diet_data(uid, data)
    return {"ok": True, "entry": entry.model_dump(mode="json")}


@app.post("/diet/sync-weight")
async def sync_weight_from_garmin(user: dict = Depends(get_current_user)):
    """Pull weight history from Garmin Connect."""
    uid = user["id"]
    garmin = _ensure_garmin(uid)
    data = _load_diet_data(uid)

    end = date.today()
    start = end - timedelta(days=90)
    entries = garmin.get_weight_history(start, end)

    new_count = 0
    existing_dates = {str(w.date) for w in data.weight_history if w.source == WeightSource.GARMIN}
    for e in entries:
        d = str(e["date"])
        if d not in existing_dates:
            data.weight_history.append(WeightEntry(
                date=date.fromisoformat(d) if isinstance(e["date"], str) else e["date"],
                weight_kg=e["weight_kg"],
                body_fat_pct=e.get("body_fat_pct"),
                muscle_mass_kg=e.get("muscle_mass_kg"),
                bmi=e.get("bmi"),
                source=WeightSource.GARMIN,
            ))
            new_count += 1

    data.weight_history.sort(key=lambda w: w.date)
    _save_diet_data(uid, data)
    return {"ok": True, "synced": new_count, "total": len(data.weight_history)}


@app.post("/diet/note")
async def add_diet_note(req: DietNoteRequest, user: dict = Depends(get_current_user)):
    """Add user feedback note and get AI response."""
    uid = user["id"]
    data = _load_diet_data(uid)

    note = UserNote(
        date=date.today(),
        content=req.content,
    )

    # Get AI response to the note
    coach = _get_or_create_coach(uid)
    try:
        profile = _user_profile.get(uid)
        context_parts = [f"The athlete submitted this diet feedback: \"{req.content}\""]
        if data.active_plan:
            targets = data.active_plan.macro_targets
            context_parts.append(f"Current plan targets: {targets.calories} cal, {targets.protein_g}g protein")
        if data.weight_history:
            last = data.weight_history[-1]
            context_parts.append(f"Latest weight: {last.weight_kg} kg ({last.date})")
        context_parts.append("Provide a brief, supportive response (2-3 sentences) addressing their feedback and suggesting adjustments if needed.")

        response = coach.chat("\n".join(context_parts), profile=profile)
        note.ai_response = response.reply
    except Exception:
        logger.warning("Could not generate AI response to diet note", exc_info=True)
        note.ai_response = ""

    data.user_notes.append(note)
    if data.active_plan:
        data.active_plan.user_notes.append(note)
    _save_diet_data(uid, data)
    return note.model_dump(mode="json")


@app.get("/diet/macros-summary")
async def get_macros_summary(user: dict = Depends(get_current_user)):
    """Get macro targets and daily plan totals for charting."""
    uid = user["id"]
    data = _load_diet_data(uid)
    if not data.active_plan:
        return {"targets": None, "daily": []}

    plan = data.active_plan
    daily_data = []
    for week in plan.weekly_templates:
        for day in week.days:
            daily_data.append({
                "date": str(day.date),
                "calories": day.daily_totals.calories,
                "protein_g": day.daily_totals.protein_g,
                "carbs_g": day.daily_totals.carbs_g,
                "fat_g": day.daily_totals.fat_g,
                "fiber_g": day.daily_totals.fiber_g,
            })

    # Add Garmin calorie burn data
    burn_data = []
    cached = load_user_data(settings.db_path, uid)
    if cached and cached.get("activities_json"):
        try:
            acts = json.loads(cached["activities_json"])
            for a in acts:
                start = str(a.get("start_time", ""))[:10]
                if start:
                    burn_data.append({
                        "date": start,
                        "calories_burned": a.get("calories") or 0,
                        "activity": a.get("name", ""),
                    })
        except (json.JSONDecodeError, TypeError):
            pass

    return {
        "targets": plan.macro_targets.model_dump(mode="json"),
        "daily": daily_data,
        "calorie_burn": burn_data,
        "weight_history": [w.model_dump(mode="json") for w in data.weight_history[-60:]],
    }


@app.post("/diet/auto-adjust-toggle")
async def toggle_diet_auto_adjust(body: dict, user: dict = Depends(get_current_user)):
    """Toggle automatic weekly diet plan adjustment."""
    uid = user["id"]
    data = _load_diet_data(uid)
    if data.active_plan:
        data.active_plan.auto_adjust = bool(body.get("enabled", True))
        _save_diet_data(uid, data)
    return {"ok": True}


def _parse_diet_plan_response(
    raw_json: str,
    profile: DietProfile,
    existing_plan: DietPlan | None = None,
) -> DietPlan:
    """Parse AI JSON response into a DietPlan model."""
    import re
    import uuid

    logger.info("Raw diet AI response (%d chars): %.500s…", len(raw_json), raw_json)

    # Strip markdown code fences if present
    cleaned = raw_json.strip()
    fence_match = re.search(r"```(?:json)?\s*\n?(.*?)\n?\s*```", cleaned, re.DOTALL)
    if fence_match:
        cleaned = fence_match.group(1).strip()
    # Fallback: extract first { ... } block
    if not cleaned.startswith("{"):
        brace_match = re.search(r"\{.*\}", cleaned, re.DOTALL)
        if brace_match:
            cleaned = brace_match.group(0)

    # Parse JSON — use json_repair as fallback for truncated / malformed output
    try:
        parsed = json.loads(cleaned)
    except json.JSONDecodeError:
        from json_repair import loads as repair_loads

        logger.warning("json.loads failed, attempting json_repair on %d chars", len(cleaned))
        try:
            parsed = repair_loads(cleaned)
            if not isinstance(parsed, dict):
                raise ValueError(f"Expected dict, got {type(parsed).__name__}")
        except Exception as exc:
            logger.error("json_repair also failed: %s — raw: %.500s", exc, cleaned)
            raise HTTPException(500, f"AI returned invalid diet plan format: {exc}")

    if parsed.get("error"):
        raise HTTPException(500, parsed["error"])

    # Build macro targets
    mt = parsed.get("macro_targets", {})
    macro_targets = MacroTotals(
        calories=mt.get("calories", 0),
        protein_g=mt.get("protein_g", 0),
        carbs_g=mt.get("carbs_g", 0),
        fat_g=mt.get("fat_g", 0),
        fiber_g=mt.get("fiber_g", 0),
    )

    # Build daily meal plans — use profile start_date or default to next Monday
    today = date.today()
    if profile.start_date and profile.start_date >= today:
        start_date = profile.start_date
    else:
        days_until_monday = (7 - today.weekday()) % 7 or 7
        start_date = today + timedelta(days=days_until_monday)

    days_data = parsed.get("days", [])
    if not days_data:
        logger.error("AI returned 0 days. Raw: %.500s", raw_json)
        raise HTTPException(500, "AI returned an empty meal plan. Please try again.")
    if len(days_data) < 7:
        logger.warning(
            "AI returned only %d days (expected 7), will cycle to fill week", len(days_data),
        )
    daily_plans: list[DailyMealPlan] = []
    for day_info in days_data:
        day_num = day_info.get("day_number", len(daily_plans) + 1)
        plan_date = start_date + timedelta(days=day_num - 1)
        meals: list[Meal] = []
        for m in day_info.get("meals", []):
            foods = [
                FoodItem(
                    name=f.get("name", ""),
                    quantity=f.get("quantity", 0),
                    unit=f.get("unit", "g"),
                    calories=f.get("calories", 0),
                    protein_g=f.get("protein_g", 0),
                    carbs_g=f.get("carbs_g", 0),
                    fat_g=f.get("fat_g", 0),
                )
                for f in m.get("foods", [])
            ]
            # Validate meal_type
            raw_type = m.get("meal_type", "lunch")
            try:
                meal_type = MealType(raw_type)
            except ValueError:
                meal_type = MealType.LUNCH
            meals.append(Meal(
                name=m.get("name", "Meal"),
                meal_type=meal_type,
                foods=foods,
                total_calories=m.get("total_calories", 0),
                protein_g=m.get("protein_g", 0),
                carbs_g=m.get("carbs_g", 0),
                fat_g=m.get("fat_g", 0),
                fiber_g=m.get("fiber_g", 0),
                recipe_notes=m.get("recipe_notes", ""),
            ))

        dt = day_info.get("daily_totals", {})
        daily_plans.append(DailyMealPlan(
            date=plan_date,
            meals=meals,
            daily_totals=MacroTotals(
                calories=dt.get("calories", 0),
                protein_g=dt.get("protein_g", 0),
                carbs_g=dt.get("carbs_g", 0),
                fat_g=dt.get("fat_g", 0),
                fiber_g=dt.get("fiber_g", 0),
            ),
            adjustment_reason=parsed.get("adjustment_reason", ""),
        ))

    # Pad to 7 days by cycling available days (safety net — day-by-day
    # generation should always produce 7, so log an error if this triggers)
    if daily_plans and len(daily_plans) < 7:
        logger.error(
            "AI returned only %d days (expected 7) — cycling to fill. "
            "This should not happen with day-by-day generation.",
            len(daily_plans),
        )
        base = list(daily_plans)
        while len(daily_plans) < 7:
            src = base[len(daily_plans) % len(base)]
            daily_plans.append(DailyMealPlan(
                date=start_date + timedelta(days=len(daily_plans)),
                meals=src.meals,
                daily_totals=src.daily_totals,
                notes=src.notes,
                adjustment_reason=src.adjustment_reason,
            ))

    # Post-validate: ensure each day has the correct number of meals
    expected_count = profile.daily_meals_count
    expected_types = ["breakfast", "lunch", "dinner"]
    if expected_count >= 4:
        expected_types.insert(1, "morning_snack")
    if expected_count >= 5:
        expected_types.insert(3, "afternoon_snack")
    if expected_count >= 6:
        expected_types.append("evening_snack")

    # Default snack templates when AI omits snack types
    _snack_defaults = {
        "morning_snack": ("Greek Yogurt & Mixed Berries", [
            FoodItem(name="Greek yogurt", quantity=150, unit="g", calories=130, protein_g=15, carbs_g=8, fat_g=4),
            FoodItem(name="Mixed berries", quantity=80, unit="g", calories=40, protein_g=0.5, carbs_g=9, fat_g=0.3),
        ]),
        "afternoon_snack": ("Apple & Almond Butter", [
            FoodItem(name="Apple", quantity=1, unit="pcs", calories=95, protein_g=0.5, carbs_g=25, fat_g=0.3),
            FoodItem(name="Almond butter", quantity=15, unit="g", calories=90, protein_g=3, carbs_g=3, fat_g=8),
        ]),
        "evening_snack": ("Cottage Cheese & Walnuts", [
            FoodItem(name="Cottage cheese", quantity=100, unit="g", calories=98, protein_g=11, carbs_g=3, fat_g=4),
            FoodItem(name="Walnuts", quantity=15, unit="g", calories=98, protein_g=2, carbs_g=1, fat_g=10),
        ]),
    }
    for day_plan in daily_plans:
        if len(day_plan.meals) < expected_count:
            existing_types = {m.meal_type.value for m in day_plan.meals}
            for mt_str in expected_types:
                if mt_str not in existing_types and len(day_plan.meals) < expected_count:
                    default = _snack_defaults.get(mt_str)
                    if default:
                        sname, sfoods = default
                        tcal = sum(f.calories for f in sfoods)
                        tp = sum(f.protein_g for f in sfoods)
                        tc = sum(f.carbs_g for f in sfoods)
                        tf = sum(f.fat_g for f in sfoods)
                        day_plan.meals.append(Meal(
                            name=sname,
                            meal_type=MealType(mt_str),
                            foods=sfoods,
                            total_calories=tcal,
                            protein_g=tp,
                            carbs_g=tc,
                            fat_g=tf,
                            recipe_notes="Default snack — tap Suggest Alternative for a personalised option.",
                        ))
                    else:
                        day_plan.meals.append(Meal(
                            name="Quick Snack",
                            meal_type=MealType(mt_str),
                            recipe_notes="Tap Suggest Alternative for a personalised option.",
                        ))
            # Re-sort meals to match expected type order
            type_order = {t: i for i, t in enumerate(expected_types)}
            day_plan.meals.sort(key=lambda m: type_order.get(m.meal_type.value, 99))
            # Recalculate daily totals
            day_plan.daily_totals = MacroTotals(
                calories=sum(m.total_calories for m in day_plan.meals),
                protein_g=sum(m.protein_g for m in day_plan.meals),
                carbs_g=sum(m.carbs_g for m in day_plan.meals),
                fat_g=sum(m.fat_g for m in day_plan.meals),
                fiber_g=sum(m.fiber_g for m in day_plan.meals),
            )
            logger.warning("Day %s had missing meal types, backfilled with defaults", day_plan.date)

    # Group days into weekly templates
    plan_weeks = max(1, profile.plan_weeks)
    weeks: list[WeeklyMealTemplate] = []
    for wk in range(plan_weeks):
        week_days = daily_plans[wk * 7 : (wk + 1) * 7]
        if not week_days:
            # Repeat week 1 with shifted dates for weeks beyond the AI output
            base_days = daily_plans[:7]
            week_days = [
                DailyMealPlan(
                    date=start_date + timedelta(days=wk * 7 + i),
                    meals=d.meals,
                    daily_totals=d.daily_totals,
                    notes=d.notes,
                    adjustment_reason=d.adjustment_reason,
                )
                for i, d in enumerate(base_days)
            ]
        weeks.append(WeeklyMealTemplate(week_number=wk + 1, days=week_days))

    plan = DietPlan(
        plan_id=existing_plan.plan_id if existing_plan else str(uuid.uuid4())[:8],
        profile=profile,
        plan_analysis=parsed.get("plan_analysis", ""),
        macro_targets=macro_targets,
        weekly_templates=weeks,
        weight_history=existing_plan.weight_history if existing_plan else [],
        user_notes=existing_plan.user_notes if existing_plan else [],
        active=True,
        auto_adjust=existing_plan.auto_adjust if existing_plan else True,
        last_adjusted=datetime.now(UTC).isoformat(),
    )
    return plan


# ── Mobile Web SPA ───────────────────────────────────────────────────
_mobile_web_dir = Path(__file__).resolve().parent.parent / "mobile_web"


@app.get("/m")
async def mobile_web_redirect():
    """Redirect /m to /m/ for consistency."""
    from fastapi.responses import RedirectResponse

    return RedirectResponse("/m/")


@app.get("/m/{path:path}")
async def mobile_web_spa(path: str = ""):
    """Serve the mobile web SPA — always return index.html for client-side routing."""
    if path and (_mobile_web_dir / path).is_file():
        return FileResponse(_mobile_web_dir / path)
    index = _mobile_web_dir / "index.html"
    if not index.exists():
        raise HTTPException(404, "Mobile web app not found")
    return FileResponse(index, media_type="text/html")