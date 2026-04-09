"""Training plan and workout models."""

from __future__ import annotations

from datetime import date
from enum import Enum

from pydantic import BaseModel, Field


class WorkoutStepType(str, Enum):
    WARMUP = "warmup"
    COOLDOWN = "cooldown"
    INTERVAL = "interval"
    RECOVERY = "recovery"
    ACTIVE = "active"  # steady-state (easy, tempo, marathon pace)
    REST = "rest"


class IntensityTarget(str, Enum):
    """How the target is expressed."""

    PACE = "pace"
    HEART_RATE = "heart_rate"
    OPEN = "open"  # no specific target (by feel)


class WorkoutStep(BaseModel):
    step_type: WorkoutStepType
    description: str = ""
    duration_seconds: float | None = None
    distance_meters: float | None = None
    target_type: IntensityTarget = IntensityTarget.OPEN
    target_low: float | None = Field(None, description="Low end — pace (sec/km) or HR (bpm)")
    target_high: float | None = Field(None, description="High end — pace (sec/km) or HR (bpm)")
    repeat_count: int | None = Field(None, description="For repeat groups only")
    steps: list[WorkoutStep] | None = Field(None, description="Sub-steps for repeat groups")


class WorkoutType(str, Enum):
    EASY_RUN = "easy_run"
    LONG_RUN = "long_run"
    TEMPO = "tempo"
    INTERVALS = "intervals"
    RECOVERY = "recovery_run"
    THRESHOLD = "threshold"
    RACE_PACE = "race_pace"
    FARTLEK = "fartlek"
    HYROX_MIXED = "hyrox_mixed"
    CROSS_TRAINING = "cross_training"
    REST = "rest"


class Workout(BaseModel):
    workout_type: WorkoutType
    name: str
    description: str = ""
    scheduled_date: date | None = None
    estimated_duration_seconds: float | None = None
    estimated_distance_meters: float | None = None
    steps: list[WorkoutStep] = Field(default_factory=list)
    notes: str = ""


class TrainingWeek(BaseModel):
    week_number: int
    phase: str = Field(default="", description="e.g. 'Base', 'Build', 'Peak', 'Taper'")
    total_distance_km: float | None = None
    workouts: list[Workout] = Field(default_factory=list)


class TrainingPlan(BaseModel):
    plan_id: str = ""
    name: str
    goal_type: str
    target_date: date
    target_time_seconds: float | None = None
    total_weeks: int
    weeks: list[TrainingWeek] = Field(default_factory=list)
    created_at: date = Field(default_factory=date.today)

    # Paces derived from VDOT (sec/km)
    easy_pace: float | None = None
    marathon_pace: float | None = None
    threshold_pace: float | None = None
    interval_pace: float | None = None
    repetition_pace: float | None = None
