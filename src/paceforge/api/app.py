"""FastAPI application entry point."""

from __future__ import annotations

import logging
from contextlib import asynccontextmanager
from datetime import date
from pathlib import Path

import jwt as pyjwt
from fastapi import Depends, FastAPI, HTTPException, Header
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from paceforge.ai.coach import Coach
from paceforge.api.config import settings
from paceforge.auth.database import (
    create_user,
    get_user_by_email,
    get_user_by_id,
    init_db,
    list_users,
    update_garmin_email,
    update_user_profile,
    update_user_status,
)
from paceforge.auth.models import (
    AppLoginRequest,
    ProfileUpdateRequest,
    RegisterRequest,
    TokenResponse,
    UserOut,
    UserStatusUpdate,
)
from paceforge.auth.security import (
    create_access_token,
    decode_access_token,
    hash_password,
    verify_password,
)
from paceforge.engine.adaptation import adapt_plan
from paceforge.engine.planner import generate_plan
from paceforge.garmin.client import GarminClient
from paceforge.models.plan import TrainingPlan
from paceforge.models.profile import (
    ExperienceLevel,
    GoalType,
    RecentActivity,
    TrainingGoal,
    UserFitnessProfile,
    default_training_days,
)

logging.basicConfig(level=settings.log_level)
logger = logging.getLogger(__name__)

# ── Per-user state (keyed by user_id) ────────────────────────────────
_user_garmin: dict[str, GarminClient] = {}
_user_profile: dict[str, UserFitnessProfile] = {}
_user_plan: dict[str, TrainingPlan] = {}
_user_coach: dict[str, Coach] = {}


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
    return {"status": "ok", "message": "Registration submitted. An admin will review your request."}


@app.post("/auth/login", response_model=TokenResponse)
async def app_login(req: AppLoginRequest):
    user = get_user_by_email(settings.db_path, req.email)
    if not user or not verify_password(req.password, user["password_hash"]):
        raise HTTPException(401, "Invalid email or password")
    if user["status"] == "pending":
        raise HTTPException(403, "Your account is pending admin approval")
    if user["status"] == "rejected":
        raise HTTPException(403, "Your account has been rejected")
    token = create_access_token(user["id"], user["role"], settings.jwt_secret)
    return TokenResponse(access_token=token, role=user["role"], name=user["name"], email=user["email"])


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


# ── Helper: per-user Garmin token dir ────────────────────────────────

def _token_dir_for(user_id: str) -> str:
    base = Path(settings.garmin_token_dir).expanduser()
    return str(base / user_id)


# ── Garmin endpoints (protected) ─────────────────────────────────────


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
async def get_profile(user: dict = Depends(get_current_user)):
    uid = user["id"]
    garmin = _user_garmin.get(uid)
    if not garmin:
        raise HTTPException(401, "Not logged in to Garmin")
    _user_profile[uid] = garmin.get_fitness_profile()
    return _user_profile[uid]


@app.get("/activities", response_model=list[RecentActivity])
async def get_activities(
    days: int = 240, user: dict = Depends(get_current_user)
):
    """Return running activities from the last N days (default 240)."""
    uid = user["id"]
    garmin = _user_garmin.get(uid)
    if not garmin:
        raise HTTPException(401, "Not logged in to Garmin")
    profile = garmin.get_fitness_profile(lookback_days=min(days, 365))
    return profile.recent_activities


@app.get("/activities/{activity_id}")
async def get_activity_detail(activity_id: int, user: dict = Depends(get_current_user)):
    """Return detailed splits, HR zones, and summary for an activity."""
    uid = user["id"]
    garmin = _user_garmin.get(uid)
    if not garmin:
        raise HTTPException(401, "Not logged in to Garmin")
    return garmin.get_activity_detail(activity_id)


@app.post("/plan/generate", response_model=TrainingPlan)
async def generate(req: GeneratePlanRequest, user: dict = Depends(get_current_user)):
    uid = user["id"]
    garmin = _user_garmin.get(uid)
    if not garmin:
        raise HTTPException(401, "Not logged in to Garmin")

    profile = _user_profile.get(uid) or garmin.get_fitness_profile()

    goal = TrainingGoal(
        goal_type=req.goal_type,
        target_date=req.target_date,
        target_time_seconds=req.target_time_seconds,
        experience_level=req.experience_level,
        training_days=req.training_days or default_training_days(req.max_days_per_week),
        long_run_day=req.long_run_day,
    )

    _user_plan[uid] = generate_plan(profile, goal)
    return _user_plan[uid]


@app.get("/plan", response_model=TrainingPlan | None)
async def get_plan(user: dict = Depends(get_current_user)):
    uid = user["id"]
    plan = _user_plan.get(uid)
    if not plan:
        raise HTTPException(404, "No plan generated yet")
    return plan


@app.post("/plan/push")
async def push_plan(req: PushPlanRequest, user: dict = Depends(get_current_user)):
    uid = user["id"]
    garmin = _user_garmin.get(uid)
    if not garmin:
        raise HTTPException(401, "Not logged in to Garmin")
    plan = _user_plan.get(uid)
    if not plan:
        raise HTTPException(404, "No plan generated yet")

    weeks_to_push = plan.weeks
    if req.week_numbers:
        weeks_to_push = [w for w in plan.weeks if w.week_number in req.week_numbers]

    total_pushed = 0
    for week in weeks_to_push:
        results = garmin.push_plan_week(week.workouts)
        total_pushed += len(results)

    return {"status": "ok", "workouts_pushed": total_pushed}


@app.post("/plan/reschedule")
async def reschedule_workout(req: RescheduleRequest, user: dict = Depends(get_current_user)):
    uid = user["id"]
    plan = _user_plan.get(uid)
    if not plan:
        raise HTTPException(404, "No plan generated yet")
    for week in plan.weeks:
        for w in week.workouts:
            if w.name == req.workout_name and str(w.scheduled_date) == req.old_date:
                w.scheduled_date = date.fromisoformat(req.new_date)
                return {"status": "ok", "message": f"Moved '{w.name}' to {req.new_date}"}
    raise HTTPException(404, "Workout not found")


@app.post("/coach/chat", response_model=ChatResponse)
async def coach_chat(req: ChatRequest, user: dict = Depends(get_current_user)):
    uid = user["id"]
    if not settings.openai_api_key:
        return ChatResponse(
            reply=(
                "AI coaching is not configured. "
                "Set PACEFORGE_OPENAI_API_KEY to enable."
            )
        )
    coach = _user_coach.get(uid)
    if coach is None:
        coach = Coach(
            api_key=settings.openai_api_key,
            model=settings.openai_model,
        )
        _user_coach[uid] = coach

    result = coach.chat(
        message=req.message,
        profile=_user_profile.get(uid),
        plan=_user_plan.get(uid),
    )
    return ChatResponse(reply=result.reply)


@app.post("/plan/adapt", response_model=TrainingPlan)
async def adapt_current_plan(user: dict = Depends(get_current_user)):
    uid = user["id"]
    garmin = _user_garmin.get(uid)
    if not garmin:
        raise HTTPException(401, "Not logged in to Garmin")
    plan = _user_plan.get(uid)
    if not plan:
        raise HTTPException(404, "No plan generated yet")
    _user_profile[uid] = garmin.get_fitness_profile()
    _user_plan[uid] = adapt_plan(plan, _user_profile[uid])
    return _user_plan[uid]
