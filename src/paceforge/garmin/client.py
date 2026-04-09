"""Thin wrapper around python-garminconnect for PaceForge."""

from __future__ import annotations

import logging
from datetime import date, timedelta
from pathlib import Path

from garminconnect import Garmin
from garminconnect.workout import (
    RunningWorkout,
    WorkoutSegment,
    create_cooldown_step,
    create_interval_step,
    create_recovery_step,
    create_repeat_group,
    create_warmup_step,
)

from paceforge.models.plan import (
    IntensityTarget,
    Workout,
    WorkoutStepType,
)
from paceforge.models.profile import (
    HRZone,
    RacePrediction,
    RecentActivity,
    UserFitnessProfile,
)

logger = logging.getLogger(__name__)

DEFAULT_TOKEN_DIR = "~/.garminconnect"


class GarminClient:
    """High-level Garmin Connect operations for PaceForge."""

    def __init__(
        self,
        email: str,
        password: str,
        token_dir: str = DEFAULT_TOKEN_DIR,
        prompt_mfa: object | None = None,
    ) -> None:
        self._email = email
        self._password = password
        self._token_dir = token_dir
        self._prompt_mfa = prompt_mfa or (lambda: input("MFA code: "))
        self._client: Garmin | None = None

    def login(self) -> None:
        self._client = Garmin(
            self._email,
            self._password,
            prompt_mfa=self._prompt_mfa,
        )
        self._client.login(self._token_dir)
        logger.info("Authenticated with Garmin Connect")

    @property
    def client(self) -> Garmin:
        if self._client is None:
            raise RuntimeError("Not logged in. Call login() first.")
        return self._client

    # ── Read operations ──────────────────────────────────────────────

    def get_fitness_profile(self, lookback_days: int = 30) -> UserFitnessProfile:
        """Build an aggregated fitness profile from Garmin data."""
        today = date.today().isoformat()

        # Basic stats
        stats = self.client.get_stats(today) or {}
        hr_data = self.client.get_heart_rates(today) or {}

        # VO2 max
        vo2 = None
        try:
            vo2_data = self.client.get_max_metrics(today)
            if vo2_data and isinstance(vo2_data, list) and len(vo2_data) > 0:
                vo2 = vo2_data[0].get("generic", {}).get("vo2MaxPreciseValue")
        except Exception:
            logger.warning("Could not fetch VO2 max", exc_info=True)

        # Training readiness
        readiness = None
        try:
            tr_data = self.client.get_training_readiness(today)
            if tr_data:
                readiness = tr_data.get("score")
        except Exception:
            logger.warning("Could not fetch training readiness", exc_info=True)

        # HRV
        hrv_status = None
        hrv_value = None
        try:
            hrv_data = self.client.get_hrv_data(today)
            if hrv_data:
                hrv_status = hrv_data.get("hrvSummary", {}).get("status")
                hrv_value = hrv_data.get("hrvSummary", {}).get("lastNightAvg")
        except Exception:
            logger.warning("Could not fetch HRV", exc_info=True)

        # Race predictions
        predictions: list[RacePrediction] = []
        try:
            rp_data = self.client.get_race_predictions()
            if rp_data:
                for key, label in [
                    ("5K", "5K"),
                    ("10K", "10K"),
                    ("half", "HALF_MARATHON"),
                    ("marathon", "MARATHON"),
                ]:
                    val = rp_data.get(key)
                    if val and val.get("predictedTime"):
                        predictions.append(
                            RacePrediction(
                                distance=label,
                                predicted_seconds=val["predictedTime"],
                            )
                        )
        except Exception:
            logger.warning("Could not fetch race predictions", exc_info=True)

        # Recent running activities
        activities: list[RecentActivity] = []
        try:
            start = (date.today() - timedelta(days=lookback_days)).isoformat()
            raw = self.client.get_activities_by_date(start, today, "running")
            for act in (raw or [])[:20]:
                activities.append(
                    RecentActivity(
                        activity_id=act.get("activityId", 0),
                        name=act.get("activityName", ""),
                        activity_type=act.get("activityType", {}).get("typeKey", "running"),
                        start_time=act.get("startTimeLocal", ""),
                        distance_meters=act.get("distance", 0),
                        duration_seconds=act.get("duration", 0),
                        avg_hr=act.get("averageHR"),
                        max_hr=act.get("maxHR"),
                        avg_pace_sec_per_km=_meters_per_sec_to_sec_per_km(
                            act.get("averageSpeed")
                        ),
                        calories=act.get("calories"),
                        training_effect_aerobic=act.get("aerobicTrainingEffect"),
                        training_effect_anaerobic=act.get("anaerobicTrainingEffect"),
                        vo2_max_value=act.get("vO2MaxValue"),
                    )
                )
        except Exception:
            logger.warning("Could not fetch recent activities", exc_info=True)

        # Weekly mileage estimate
        weekly_km = None
        if activities:
            total_m = sum(a.distance_meters for a in activities)
            weekly_km = round((total_m / 1000) / max(lookback_days / 7, 1), 1)

        # HR zones
        zones: list[HRZone] = []
        try:
            zone_data = hr_data.get("heartRateZones")
            if zone_data:
                for i, z in enumerate(zone_data, 1):
                    zones.append(
                        HRZone(
                            zone=i,
                            low_bpm=z.get("startBPM", 0),
                            high_bpm=z.get("endBPM", 0),
                        )
                    )
        except Exception:
            logger.warning("Could not parse HR zones", exc_info=True)

        return UserFitnessProfile(
            garmin_display_name=stats.get("displayName"),
            vo2_max=vo2,
            resting_hr=hr_data.get("restingHeartRate"),
            max_hr=hr_data.get("maxHeartRate") or stats.get("maxAvgHeartRate"),
            hr_zones=zones,
            training_readiness=readiness,
            hrv_status=hrv_status,
            hrv_last_night=hrv_value,
            weekly_mileage_km=weekly_km,
            race_predictions=predictions,
            recent_activities=activities,
        )

    # ── Write operations ─────────────────────────────────────────────

    def push_workout(self, workout: Workout, schedule_date: date | None = None) -> dict:
        """Upload a structured running workout to Garmin Connect and optionally schedule it."""
        garmin_steps = []
        for step in workout.steps:
            garmin_steps.append(_to_garmin_step(step))

        garmin_workout = RunningWorkout(
            workoutName=workout.name,
            description=workout.description,
            estimatedDurationInSecs=workout.estimated_duration_seconds or 3600,
            workoutSegments=[
                WorkoutSegment(
                    segmentOrder=1,
                    sportType={"sportTypeId": 1, "sportTypeKey": "running"},
                    workoutSteps=garmin_steps,
                )
            ],
        )

        result = self.client.upload_running_workout(garmin_workout)
        workout_id = result.get("workoutId")
        logger.info("Uploaded workout %s (id=%s)", workout.name, workout_id)

        if schedule_date and workout_id:
            self.client.schedule_workout(workout_id, schedule_date.isoformat())
            logger.info("Scheduled workout %s on %s", workout_id, schedule_date)

        return result

    def push_plan_week(self, workouts: list[Workout]) -> list[dict]:
        """Push a list of workouts (typically one week) to Garmin Connect."""
        results = []
        for w in workouts:
            if w.workout_type.value == "rest":
                continue
            r = self.push_workout(w, schedule_date=w.scheduled_date)
            results.append(r)
        return results


def _meters_per_sec_to_sec_per_km(speed: float | None) -> float | None:
    if not speed or speed <= 0:
        return None
    return round(1000.0 / speed, 1)


def _to_garmin_step(step):  # noqa: ANN001
    """Convert a PaceForge WorkoutStep to a garminconnect workout step dict."""
    duration = step.duration_seconds or 600.0

    if step.step_type == WorkoutStepType.WARMUP:
        return create_warmup_step(duration)
    elif step.step_type == WorkoutStepType.COOLDOWN:
        return create_cooldown_step(duration)
    elif step.step_type == WorkoutStepType.RECOVERY:
        return create_recovery_step(duration)
    elif step.step_type == WorkoutStepType.INTERVAL:
        return create_interval_step(duration)
    elif step.repeat_count and step.steps:
        sub_steps = [_to_garmin_step(s) for s in step.steps]
        return create_repeat_group(step.repeat_count, sub_steps)
    else:
        # Default to interval step for active/other types
        return create_interval_step(duration)
