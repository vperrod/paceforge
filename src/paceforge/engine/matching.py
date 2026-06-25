"""Match completed Garmin activities to scheduled plan workouts.

The matcher was dropped in the serverless rewrite, so nothing populated
Workout.matched_activity_ids and the "planned vs actual" view was always empty.
This links each run activity to the nearest-distance scheduled run on the same day.
"""
from __future__ import annotations

from paceforge.models.plan import TrainingPlan
from paceforge.models.profile import RecentActivity

# Garmin activity_types that count as a run for plan matching.
_RUN_TYPES = {"running", "treadmill_running"}
# Days a workout can slip and still match — you sometimes run a session a day off.
_DAY_TOLERANCE = 1


def _is_run(act: RecentActivity) -> bool:
    return (act.activity_type or "").lower() in _RUN_TYPES


def match_plan_to_activities(plan: TrainingPlan, activities: list[RecentActivity]) -> int:
    """Link run activities to scheduled run workouts within ±1 day, preferring the
    nearest date then nearest distance. Each activity matches at most one workout.

    Sets matched_activity_ids + completed on each matched workout. Workouts are
    processed in date order so an earlier session claims a shared-day run first.
    Returns the number of workouts whose match changed.
    """
    runs = [a for a in activities if _is_run(a)]
    workouts = sorted(
        (wo for wk in plan.weeks for wo in wk.workouts
         if wo.scheduled_date and wo.workout_type != "rest"),
        key=lambda wo: wo.scheduled_date,
    )

    used: set[int] = set()
    changed = 0
    for wo in workouts:
        target = wo.estimated_distance_meters or 0
        candidates = [
            a for a in runs
            if a.activity_id not in used
            and abs((a.start_time.date() - wo.scheduled_date).days) <= _DAY_TOLERANCE
        ]
        if not candidates:
            continue
        best = min(candidates, key=lambda a: (
            abs((a.start_time.date() - wo.scheduled_date).days),
            abs((a.distance_meters or 0) - target),
        ))
        used.add(best.activity_id)
        if wo.matched_activity_ids != [best.activity_id]:
            wo.matched_activity_ids = [best.activity_id]
            changed += 1
        wo.completed = True
    return changed
