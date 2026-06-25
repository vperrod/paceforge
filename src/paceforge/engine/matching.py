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
    """Link run activities to scheduled run workouts, preferring an exact-date match
    and falling back to ±1 day. Each activity matches at most ONE workout.

    Authoritative: clears existing matches first and recomputes, so an activity can
    never end up attached to two workouts. Sets matched_activity_ids + completed.
    Returns the number of matched workouts.
    """
    runs = [a for a in activities if _is_run(a)]
    workouts = sorted(
        (wo for wk in plan.weeks for wo in wk.workouts
         if wo.scheduled_date and wo.workout_type != "rest"),
        key=lambda wo: wo.scheduled_date,
    )
    for wo in workouts:
        wo.matched_activity_ids = []
        wo.completed = False

    used: set[int] = set()
    matched = 0
    # Exact date first (tol=0), then ±1 day — so a run lands on its own day before a
    # neighbouring workout can claim it.
    for tol in (0, _DAY_TOLERANCE):
        for wo in workouts:
            if wo.matched_activity_ids:
                continue
            target = wo.estimated_distance_meters or 0
            candidates = [
                a for a in runs
                if a.activity_id not in used
                and abs((a.start_time.date() - wo.scheduled_date).days) <= tol
            ]
            if not candidates:
                continue
            best = min(candidates, key=lambda a: abs((a.distance_meters or 0) - target))
            used.add(best.activity_id)
            wo.matched_activity_ids = [best.activity_id]
            wo.completed = True
            matched += 1
    return matched
