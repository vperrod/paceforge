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
    avg_running_cadence: float | None = None


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


_ALL_DAYS = ["monday", "tuesday", "wednesday", "thursday", "friday", "saturday", "sunday"]

_DEFAULT_DAYS: dict[int, list[str]] = {
    3: ["tuesday", "thursday", "sunday"],
    4: ["tuesday", "thursday", "saturday", "sunday"],
    5: ["tuesday", "wednesday", "thursday", "saturday", "sunday"],
    6: ["monday", "tuesday", "wednesday", "thursday", "saturday", "sunday"],
    7: _ALL_DAYS,
}


def default_training_days(n: int = 5) -> list[str]:
    """Return a sensible default set of training days for *n* days/week."""
    return list(_DEFAULT_DAYS.get(n, _DEFAULT_DAYS[5]))


class TrainingGoal(BaseModel):
    goal_type: GoalType
    target_date: date
    target_time_seconds: float | None = Field(
        None, description="Target finish time in seconds (optional)"
    )
    experience_level: ExperienceLevel | None = None
    training_days: list[str] = Field(
        default_factory=lambda: default_training_days(5),
        description="Which days of the week to train (e.g. ['monday','wednesday','friday','saturday','sunday'])",
    )
    long_run_day: str = Field(default="sunday", description="Preferred long run day")
    start_date: date | None = Field(None, description="Optional plan start date")
    custom_easy_pace: float | None = Field(None, description="User-provided easy pace in sec/km")
    custom_marathon_pace: float | None = Field(None, description="User-provided marathon pace in sec/km")
    custom_threshold_pace: float | None = Field(None, description="User-provided threshold pace in sec/km")

    @property
    def max_days_per_week(self) -> int:
        return len(self.training_days)
