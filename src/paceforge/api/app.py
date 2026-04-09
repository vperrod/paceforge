"""FastAPI application entry point."""

from __future__ import annotations

import logging
from contextlib import asynccontextmanager
from datetime import date

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

from paceforge.ai.coach import Coach
from paceforge.api.config import settings
from paceforge.engine.adaptation import adapt_plan
from paceforge.engine.planner import generate_plan
from paceforge.garmin.client import GarminClient
from paceforge.models.plan import TrainingPlan
from paceforge.models.profile import (
    ExperienceLevel,
    GoalType,
    TrainingGoal,
    UserFitnessProfile,
)

logging.basicConfig(level=settings.log_level)
logger = logging.getLogger(__name__)

# Shared state (single-user personal app)
_garmin: GarminClient | None = None
_cached_profile: UserFitnessProfile | None = None
_cached_plan: TrainingPlan | None = None
_coach: Coach | None = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    yield


app = FastAPI(
    title="PaceForge",
    description="AI-enhanced running plan generator for Garmin watches",
    version="0.1.0",
    lifespan=lifespan,
)


# ── Request / Response models ────────────────────────────────────────


class LoginRequest(BaseModel):
    email: str | None = None
    password: str | None = None


class GeneratePlanRequest(BaseModel):
    goal_type: GoalType
    target_date: date
    target_time_seconds: float | None = None
    experience_level: ExperienceLevel | None = None
    max_days_per_week: int = 5
    long_run_day: str = "sunday"


class PushPlanRequest(BaseModel):
    week_numbers: list[int] | None = None  # None = push all


class ChatRequest(BaseModel):
    message: str


class ChatResponse(BaseModel):
    reply: str


# ── Endpoints ────────────────────────────────────────────────────────


@app.post("/auth/login")
async def login(req: LoginRequest):
    global _garmin
    email = req.email or settings.garmin_email
    password = req.password or settings.garmin_password
    if not email or not password:
        raise HTTPException(400, "Garmin credentials required (body or env vars)")
    _garmin = GarminClient(email, password, settings.garmin_token_dir)
    try:
        _garmin.login()
    except Exception as e:
        _garmin = None
        raise HTTPException(401, f"Garmin login failed: {e}") from e
    return {"status": "ok", "message": "Authenticated with Garmin Connect"}


@app.get("/profile", response_model=UserFitnessProfile)
async def get_profile():
    global _cached_profile
    if not _garmin:
        raise HTTPException(401, "Not logged in")
    _cached_profile = _garmin.get_fitness_profile()
    return _cached_profile


@app.post("/plan/generate", response_model=TrainingPlan)
async def generate(req: GeneratePlanRequest):
    global _cached_plan
    if not _garmin:
        raise HTTPException(401, "Not logged in")

    profile = _cached_profile or _garmin.get_fitness_profile()

    goal = TrainingGoal(
        goal_type=req.goal_type,
        target_date=req.target_date,
        target_time_seconds=req.target_time_seconds,
        experience_level=req.experience_level,
        max_days_per_week=req.max_days_per_week,
        long_run_day=req.long_run_day,
    )

    _cached_plan = generate_plan(profile, goal)
    return _cached_plan


@app.get("/plan", response_model=TrainingPlan | None)
async def get_plan():
    if not _cached_plan:
        raise HTTPException(404, "No plan generated yet")
    return _cached_plan


@app.post("/plan/push")
async def push_plan(req: PushPlanRequest):
    if not _garmin:
        raise HTTPException(401, "Not logged in")
    if not _cached_plan:
        raise HTTPException(404, "No plan generated yet")

    weeks_to_push = _cached_plan.weeks
    if req.week_numbers:
        weeks_to_push = [w for w in _cached_plan.weeks if w.week_number in req.week_numbers]

    total_pushed = 0
    for week in weeks_to_push:
        results = _garmin.push_plan_week(week.workouts)
        total_pushed += len(results)

    return {"status": "ok", "workouts_pushed": total_pushed}


@app.post("/coach/chat", response_model=ChatResponse)
async def coach_chat(req: ChatRequest):
    """AI coaching endpoint powered by OpenAI."""
    global _coach
    if not settings.openai_api_key:
        return ChatResponse(
            reply=(
                "AI coaching is not configured. "
                "Set PACEFORGE_OPENAI_API_KEY to enable."
            )
        )
    if _coach is None:
        _coach = Coach(
            api_key=settings.openai_api_key,
            model=settings.openai_model,
        )
    result = _coach.chat(
        message=req.message,
        profile=_cached_profile,
        plan=_cached_plan,
    )
    return ChatResponse(reply=result.reply)


@app.post("/plan/adapt", response_model=TrainingPlan)
async def adapt_current_plan():
    """Re-evaluate the plan based on latest fitness data."""
    global _cached_plan, _cached_profile
    if not _garmin:
        raise HTTPException(401, "Not logged in")
    if not _cached_plan:
        raise HTTPException(404, "No plan generated yet")
    _cached_profile = _garmin.get_fitness_profile()
    _cached_plan = adapt_plan(_cached_plan, _cached_profile)
    return _cached_plan
