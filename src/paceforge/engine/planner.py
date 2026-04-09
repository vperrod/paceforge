"""Plan generator — converts a template + fitness profile + goal into a concrete TrainingPlan."""

from __future__ import annotations

import uuid
from datetime import date, timedelta
from pathlib import Path

import yaml

from paceforge.engine.vdot import (
    RACE_DISTANCES,
    TrainingPaces,
    paces_from_race,
    paces_from_vdot,
)
from paceforge.models.plan import (
    IntensityTarget,
    TrainingPlan,
    TrainingWeek,
    Workout,
    WorkoutStep,
    WorkoutStepType,
    WorkoutType,
)
from paceforge.models.profile import GoalType, TrainingGoal, UserFitnessProfile

TEMPLATES_DIR = Path(__file__).parent / "templates"

# Map goal type + experience to template file
_TEMPLATE_MAP: dict[str, str] = {
    "HALF_MARATHON_intermediate": "half_marathon_intermediate.yaml",
    "HALF_MARATHON_beginner": "half_marathon_intermediate.yaml",
    "HALF_MARATHON_advanced": "half_marathon_intermediate.yaml",
    "MARATHON_intermediate": "marathon_intermediate.yaml",
    "MARATHON_beginner": "marathon_intermediate.yaml",
    "MARATHON_advanced": "marathon_intermediate.yaml",
    "HYROX_intermediate": "hyrox_intermediate.yaml",
    "HYROX_beginner": "hyrox_intermediate.yaml",
    "HYROX_advanced": "hyrox_intermediate.yaml",
}


def generate_plan(
    profile: UserFitnessProfile,
    goal: TrainingGoal,
) -> TrainingPlan:
    """Generate a full training plan from a user profile and goal."""

    # 1. Determine training paces
    paces = _derive_paces(profile)

    # 2. Load template
    template = _load_template(goal)

    # 3. Determine experience level
    level = (goal.experience_level or _estimate_level(profile)).value

    # 4. Compute plan dates
    total_weeks = template["total_weeks"]
    race_date = goal.target_date
    plan_start = race_date - timedelta(weeks=total_weeks)
    # Align to Monday
    plan_start = plan_start - timedelta(days=plan_start.weekday())

    # 5. Get peak volume
    peak_km = template["peak_weekly_km"].get(level, template["peak_weekly_km"]["intermediate"])
    volume_prog = template["volume_progression"]

    # 6. Build weeks
    weeks: list[TrainingWeek] = []
    for wk_idx in range(total_weeks):
        wk_num = wk_idx + 1
        week_start = plan_start + timedelta(weeks=wk_idx)
        multiplier = volume_prog[wk_idx] if wk_idx < len(volume_prog) else volume_prog[-1]
        week_km = round(peak_km * multiplier, 1)

        # Determine phase
        phase = "Build"
        for p in template.get("phases", []):
            if wk_num in p["weeks"]:
                phase = p["name"]
                break

        # Race week uses override template
        is_race_week = wk_num == total_weeks and "race_week" in template
        day_templates = template["race_week"] if is_race_week else template["week_template"]

        workouts = _build_workouts(
            day_templates=day_templates,
            week_start=week_start,
            week_km=week_km,
            paces=paces,
            long_run_day=goal.long_run_day,
        )

        weeks.append(
            TrainingWeek(
                week_number=wk_num,
                phase=phase,
                total_distance_km=week_km,
                workouts=workouts,
            )
        )

    return TrainingPlan(
        plan_id=str(uuid.uuid4())[:8],
        name=template["name"],
        goal_type=goal.goal_type.value,
        target_date=goal.target_date,
        target_time_seconds=goal.target_time_seconds,
        total_weeks=total_weeks,
        weeks=weeks,
        easy_pace=paces.easy_low if paces else None,
        marathon_pace=paces.marathon if paces else None,
        threshold_pace=paces.threshold if paces else None,
        interval_pace=paces.interval if paces else None,
        repetition_pace=paces.repetition if paces else None,
    )


def _derive_paces(profile: UserFitnessProfile) -> TrainingPaces | None:
    """Get training paces from VO2 max or race predictions."""
    # Prefer VO2 max directly
    if profile.vo2_max:
        return paces_from_vdot(profile.vo2_max)

    # Fall back to race predictions
    for pred in profile.race_predictions:
        dist = RACE_DISTANCES.get(pred.distance)
        if dist and pred.predicted_seconds > 0:
            return paces_from_race(dist, pred.predicted_seconds)

    # Fall back to recent activity average pace → rough VDOT estimate
    running = [a for a in profile.recent_activities if a.avg_pace_sec_per_km]
    if running:
        # Use the fastest recent run as a proxy
        fastest = min(running, key=lambda a: a.avg_pace_sec_per_km or 999)
        if fastest.avg_pace_sec_per_km and fastest.distance_meters > 2000:
            return paces_from_race(fastest.distance_meters, fastest.duration_seconds)

    return None


def _estimate_level(profile: UserFitnessProfile):
    """Estimate experience level from weekly mileage."""
    from paceforge.models.profile import ExperienceLevel

    km = profile.weekly_mileage_km or 0
    if km >= 50:
        return ExperienceLevel.ADVANCED
    elif km >= 25:
        return ExperienceLevel.INTERMEDIATE
    return ExperienceLevel.BEGINNER


def _load_template(goal: TrainingGoal) -> dict:
    level = (goal.experience_level or "intermediate").value if goal.experience_level else "intermediate"
    key = f"{goal.goal_type.value}_{level}"
    filename = _TEMPLATE_MAP.get(key)
    if not filename:
        # Default to half marathon
        filename = "half_marathon_intermediate.yaml"

    path = TEMPLATES_DIR / filename
    with open(path) as f:
        return yaml.safe_load(f)


_DAY_OFFSETS = {
    "monday": 0,
    "tuesday": 1,
    "wednesday": 2,
    "thursday": 3,
    "friday": 4,
    "saturday": 5,
    "sunday": 6,
}


def _build_workouts(
    day_templates: list[dict],
    week_start: date,
    week_km: float,
    paces: TrainingPaces | None,
    long_run_day: str,
) -> list[Workout]:
    workouts: list[Workout] = []

    for day_tmpl in day_templates:
        day_name = day_tmpl["day"]
        offset = _DAY_OFFSETS.get(day_name, 0)
        workout_date = week_start + timedelta(days=offset)

        wtype = WorkoutType(day_tmpl["type"])

        if wtype == WorkoutType.REST:
            workouts.append(
                Workout(
                    workout_type=WorkoutType.REST,
                    name="Rest Day",
                    scheduled_date=workout_date,
                )
            )
            continue

        # Compute distance
        distance_km = day_tmpl.get("distance_km")
        if not distance_km and "fraction_of_weekly" in day_tmpl:
            distance_km = round(week_km * day_tmpl["fraction_of_weekly"], 1)

        distance_m = (distance_km or 0) * 1000

        # Build steps
        steps = _build_steps(day_tmpl.get("steps", []), paces)

        # Estimate duration from distance + easy pace
        est_duration = None
        if distance_km and paces:
            est_duration = distance_km * paces.easy_low

        workouts.append(
            Workout(
                workout_type=wtype,
                name=day_tmpl.get("description", wtype.value.replace("_", " ").title()),
                description=day_tmpl.get("description", ""),
                scheduled_date=workout_date,
                estimated_duration_seconds=est_duration,
                estimated_distance_meters=distance_m,
                steps=steps,
                notes=day_tmpl.get("notes", ""),
            )
        )

    return workouts


def _build_steps(
    step_defs: list[dict],
    paces: TrainingPaces | None,
) -> list[WorkoutStep]:
    steps: list[WorkoutStep] = []
    for sd in step_defs:
        stype = WorkoutStepType(sd["type"]) if sd["type"] != "repeat" else WorkoutStepType.INTERVAL

        duration_sec = sd.get("duration_min", 0) * 60 if "duration_min" in sd else None
        distance_m = sd.get("distance_km", 0) * 1000 if "distance_km" in sd else None

        # Resolve pace targets
        target_type = IntensityTarget.OPEN
        target_low = None
        target_high = None
        if paces and "pace" in sd:
            target_type = IntensityTarget.PACE
            pace_key = sd["pace"]
            if pace_key == "easy":
                target_low = paces.easy_low
                target_high = paces.easy_high
            elif pace_key == "marathon":
                target_low = paces.marathon - 3
                target_high = paces.marathon + 3
            elif pace_key == "threshold":
                target_low = paces.threshold - 3
                target_high = paces.threshold + 3
            elif pace_key == "interval":
                target_low = paces.interval - 3
                target_high = paces.interval + 3
            elif pace_key == "repetition":
                target_low = paces.repetition - 3
                target_high = paces.repetition + 3

        # Handle repeat groups
        if sd["type"] == "repeat":
            sub_steps = _build_steps(sd.get("steps", []), paces)
            steps.append(
                WorkoutStep(
                    step_type=WorkoutStepType.INTERVAL,
                    description=sd.get("description", f"Repeat x{sd.get('count', 1)}"),
                    repeat_count=sd.get("count", 1),
                    steps=sub_steps,
                )
            )
        else:
            steps.append(
                WorkoutStep(
                    step_type=stype,
                    description=sd.get("description", ""),
                    duration_seconds=duration_sec,
                    distance_meters=distance_m,
                    target_type=target_type,
                    target_low=target_low,
                    target_high=target_high,
                )
            )

    return steps
