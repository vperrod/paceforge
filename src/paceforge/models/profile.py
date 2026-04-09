"""User fitness profile and Garmin-sourced metrics."""

from __future__ import annotations

from datetime import date, datetime
from enum import Enum

from pydantic import BaseModel, Field


class HRZone(BaseModel):
    zone: int
    low_bpm: int
    high_bpm: int


class RacePrediction(BaseModel):
    distance: str  # "5K", "10K", "HALF_MARATHON", "MARATHON"
    predicted_seconds: float


class RecentActivity(BaseModel):
    activity_id: int
    name: str
    activity_type: str
    start_time: datetime
    distance_meters: float
    duration_seconds: float
    avg_hr: int | None = None
    max_hr: int | None = None
    avg_pace_sec_per_km: float | None = None
    calories: int | None = None
    training_effect_aerobic: float | None = None
    training_effect_anaerobic: float | None = None
    vo2_max_value: float | None = None


class UserFitnessProfile(BaseModel):
    """Aggregated fitness snapshot pulled from Garmin Connect."""

    garmin_display_name: str | None = None
    vo2_max: float | None = Field(None, description="Current VO2 max estimate")
    resting_hr: int | None = None
    max_hr: int | None = None
    hr_zones: list[HRZone] = Field(default_factory=list)
    training_readiness: float | None = Field(None, description="Garmin Training Readiness score")
    hrv_status: str | None = Field(None, description="e.g. 'Balanced', 'Low', 'High'")
    hrv_last_night: float | None = None
    weekly_mileage_km: float | None = Field(None, description="Average weekly running distance (km)")
    race_predictions: list[RacePrediction] = Field(default_factory=list)
    recent_activities: list[RecentActivity] = Field(default_factory=list)
    profile_date: date = Field(default_factory=date.today)


class GoalType(str, Enum):
    FIVE_K = "5K"
    TEN_K = "10K"
    HALF_MARATHON = "HALF_MARATHON"
    MARATHON = "MARATHON"
    HYROX = "HYROX"
    CUSTOM = "CUSTOM"


class ExperienceLevel(str, Enum):
    BEGINNER = "beginner"
    INTERMEDIATE = "intermediate"
    ADVANCED = "advanced"


class TrainingGoal(BaseModel):
    goal_type: GoalType
    target_date: date
    target_time_seconds: float | None = Field(
        None, description="Target finish time in seconds (optional)"
    )
    experience_level: ExperienceLevel | None = None
    max_days_per_week: int = Field(default=5, ge=3, le=7)
    long_run_day: str = Field(default="sunday", description="Preferred long run day")
