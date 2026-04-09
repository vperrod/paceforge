"""Plan adaptation — adjust upcoming workouts based on completed activity data."""

from __future__ import annotations

import logging
from datetime import date

from paceforge.engine.vdot import paces_from_race, paces_from_vdot, TrainingPaces
from paceforge.models.plan import (
    IntensityTarget,
    TrainingPlan,
    Workout,
    WorkoutType,
)
from paceforge.models.profile import RecentActivity, UserFitnessProfile

logger = logging.getLogger(__name__)


def adapt_plan(
    plan: TrainingPlan,
    profile: UserFitnessProfile,
) -> TrainingPlan:
    """Re-evaluate and adapt a plan based on latest fitness data.

    Adjustments:
    1. Recalculate VDOT from new race/activity data → update all paces
    2. Detect missed workouts → redistribute or skip
    3. Detect overtraining signals (low HRV, low readiness) → add recovery
    """
    today = date.today()

    # 1. Recalculate paces from latest data
    new_paces = _recalculate_paces(profile, plan)
    if new_paces:
        plan = _update_plan_paces(plan, new_paces)

    # 2. Check for overtraining signals
    needs_recovery = _check_recovery_needed(profile)
    if needs_recovery:
        plan = _inject_recovery(plan, today)

    # 3. Detect missed workouts and adjust
    plan = _handle_missed_workouts(plan, profile, today)

    return plan


def _recalculate_paces(
    profile: UserFitnessProfile,
    plan: TrainingPlan,
) -> TrainingPaces | None:
    """Check if fitness has improved and update paces accordingly."""
    if profile.vo2_max and plan.easy_pace:
        new_paces = paces_from_vdot(profile.vo2_max)
        old_easy = plan.easy_pace

        # Only update if meaningful change (> 3 sec/km)
        if abs(new_paces.easy_low - old_easy) > 3:
            logger.info(
                "VDOT pace update: easy %s → %s sec/km",
                round(old_easy, 1),
                round(new_paces.easy_low, 1),
            )
            return new_paces

    # Check if a recent hard effort suggests higher fitness
    fast_runs = [
        a for a in profile.recent_activities
        if a.avg_pace_sec_per_km
        and a.distance_meters > 3000
        and a.training_effect_aerobic
        and a.training_effect_aerobic >= 3.0
    ]
    if fast_runs:
        best = min(fast_runs, key=lambda a: a.avg_pace_sec_per_km or 999)
        if best.avg_pace_sec_per_km and best.distance_meters > 3000:
            new_paces = paces_from_race(best.distance_meters, best.duration_seconds)
            if plan.easy_pace and abs(new_paces.easy_low - plan.easy_pace) > 3:
                return new_paces

    return None


def _update_plan_paces(plan: TrainingPlan, paces: TrainingPaces) -> TrainingPlan:
    """Update all future workout pace targets in the plan."""
    today = date.today()
    plan.easy_pace = paces.easy_low
    plan.marathon_pace = paces.marathon
    plan.threshold_pace = paces.threshold
    plan.interval_pace = paces.interval
    plan.repetition_pace = paces.repetition

    for week in plan.weeks:
        for workout in week.workouts:
            if workout.scheduled_date and workout.scheduled_date <= today:
                continue  # Don't modify past workouts
            for step in workout.steps:
                if step.target_type == IntensityTarget.PACE:
                    _update_step_pace(step, paces)
                if step.steps:
                    for sub in step.steps:
                        if sub.target_type == IntensityTarget.PACE:
                            _update_step_pace(sub, paces)

    return plan


def _update_step_pace(step, paces: TrainingPaces) -> None:  # noqa: ANN001
    """Update a single step's pace targets based on the range."""
    if step.target_low is None:
        return

    # Determine which pace zone this step is targeting by checking proximity
    old_mid = ((step.target_low or 0) + (step.target_high or 0)) / 2

    candidates = [
        (paces.easy_low, paces.easy_high, "easy"),
        (paces.marathon - 3, paces.marathon + 3, "marathon"),
        (paces.threshold - 3, paces.threshold + 3, "threshold"),
        (paces.interval - 3, paces.interval + 3, "interval"),
        (paces.repetition - 3, paces.repetition + 3, "repetition"),
    ]

    best_match = min(candidates, key=lambda c: abs((c[0] + c[1]) / 2 - old_mid))
    step.target_low = best_match[0]
    step.target_high = best_match[1]


def _check_recovery_needed(profile: UserFitnessProfile) -> bool:
    """Check overtraining signals."""
    if profile.hrv_status and profile.hrv_status.lower() in ("low", "poor", "unbalanced"):
        return True
    if profile.training_readiness is not None and profile.training_readiness < 25:
        return True
    return False


def _inject_recovery(plan: TrainingPlan, today: date) -> TrainingPlan:
    """Convert the next hard workout into an easy/recovery run."""
    for week in plan.weeks:
        for i, workout in enumerate(week.workouts):
            if not workout.scheduled_date or workout.scheduled_date <= today:
                continue
            if workout.workout_type in (
                WorkoutType.INTERVALS,
                WorkoutType.TEMPO,
                WorkoutType.THRESHOLD,
            ):
                logger.info(
                    "Recovery override: converting %s on %s to easy run",
                    workout.name,
                    workout.scheduled_date,
                )
                week.workouts[i] = Workout(
                    workout_type=WorkoutType.EASY_RUN,
                    name=f"Recovery (was: {workout.name})",
                    description="Converted to easy run due to low recovery signals",
                    scheduled_date=workout.scheduled_date,
                    estimated_duration_seconds=workout.estimated_duration_seconds,
                    estimated_distance_meters=(workout.estimated_distance_meters or 0) * 0.7,
                    steps=[],
                )
                return plan  # Only convert one workout
    return plan


def _handle_missed_workouts(
    plan: TrainingPlan,
    profile: UserFitnessProfile,
    today: date,
) -> TrainingPlan:
    """Detect missed workouts (past scheduled with no matching activity) and adjust.

    Strategy: if a long run was missed, don't try to make it up —
    just ensure this week's long run isn't too ambitious.
    """
    recent_dates = set()
    for act in profile.recent_activities:
        if hasattr(act.start_time, "date"):
            recent_dates.add(act.start_time.date() if callable(getattr(act.start_time, "date", None)) else str(act.start_time)[:10])

    missed_long_runs = 0
    for week in plan.weeks:
        for workout in week.workouts:
            if (
                workout.scheduled_date
                and workout.scheduled_date < today
                and workout.workout_type == WorkoutType.LONG_RUN
            ):
                workout_date_str = workout.scheduled_date.isoformat()
                if workout_date_str not in {str(d) for d in recent_dates}:
                    missed_long_runs += 1

    # If 2+ long runs missed, reduce next long run distance by 20%
    if missed_long_runs >= 2:
        for week in plan.weeks:
            for workout in week.workouts:
                if (
                    workout.scheduled_date
                    and workout.scheduled_date >= today
                    and workout.workout_type == WorkoutType.LONG_RUN
                ):
                    if workout.estimated_distance_meters:
                        original = workout.estimated_distance_meters
                        workout.estimated_distance_meters = round(original * 0.8)
                        workout.notes += (
                            f" [Reduced from {original/1000:.1f}km due to missed long runs]"
                        )
                    return plan  # Only adjust one

    return plan
