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
from paceforge.engine.workouts import WorkoutFactory
from paceforge.models.plan import (
    IntensityTarget,
    TrainingPlan,
    TrainingPurpose,
    TrainingWeek,
    Workout,
    WorkoutStep,
    WorkoutStepType,
    WorkoutType,
)
from paceforge.models.profile import TrainingGoal, UserFitnessProfile

TEMPLATES_DIR = Path(__file__).parent / "templates"

# Map goal type + experience to template file
_TEMPLATE_MAP: dict[str, str] = {
    "HALF_MARATHON_beginner": "half_marathon_beginner.yaml",
    "HALF_MARATHON_intermediate": "half_marathon_intermediate.yaml",
    "HALF_MARATHON_advanced": "half_marathon_advanced.yaml",
    "MARATHON_beginner": "marathon_beginner.yaml",
    "MARATHON_intermediate": "marathon_intermediate.yaml",
    "MARATHON_advanced": "marathon_advanced.yaml",
    "HYROX_beginner": "hyrox_intermediate.yaml",
    "HYROX_intermediate": "hyrox_intermediate.yaml",
    "HYROX_advanced": "hyrox_intermediate.yaml",
}

# ── Workout rotation pools per phase ────────────────────────────────

# Quality session 1: VO2max / speed / hills / fartlek
_Q1_BASE = ["fartlek", "hills", "easy_with_strides", "fartlek"]
_Q1_BUILD = ["vo2max", "speed_400s", "hills", "fartlek"]
_Q1_PEAK = ["vo2max", "speed_400s", "speed_200s", "vo2max"]
_Q1_TAPER = ["easy_with_strides", "speed_200s"]

# Quality session 2: tempo / threshold cruise / progressive / race pace
_Q2_BASE = ["tempo", "progressive", "tempo", "progressive"]
_Q2_BUILD = ["tempo", "threshold_cruise", "progressive", "race_pace"]
_Q2_PEAK = ["threshold_cruise", "race_pace", "tempo", "race_pace"]
_Q2_TAPER = ["tempo", "easy_with_strides"]

# Easy run slot: alternate easy and easy+strides
_EASY_ROTATION = ["easy", "easy_with_strides"]

# Long run slot: alternate types
_LR_BASE = ["long", "long", "long_progressive", "long"]
_LR_BUILD = ["long", "long_progressive", "long_with_race_pace", "long"]
_LR_PEAK = ["long_progressive", "long_with_race_pace", "long_with_race_pace", "long"]
_LR_TAPER = ["long", "long"]

# Phase focus descriptions
_FOCUS_BASE = [
    "Aerobic base + running economy",
    "Aerobic base + neuromuscular strides",
    "Aerobic endurance + strength (hills)",
    "Recovery week — maintain aerobic base",
]
_FOCUS_BUILD = [
    "VO2max development + lactate threshold",
    "Speed + sustained tempo effort",
    "Hill power + race-pace specificity",
    "Recovery week — absorb build-phase gains",
]
_FOCUS_PEAK = [
    "VO2max sharpening + race-pace confidence",
    "Speed + threshold tuning",
    "Race-specific rehearsal",
    "Final sharpening",
]
_FOCUS_TAPER = [
    "Volume reduction — maintain intensity",
    "Race week — freshness and confidence",
]


def generate_plan(
    profile: UserFitnessProfile,
    goal: TrainingGoal,
) -> TrainingPlan:
    """Generate a full training plan from a user profile and goal."""

    # 1. Determine training paces
    paces = _derive_paces(profile)

    # 2. Load template (still used for volume_progression, phases, peak_weekly_km)
    template = _load_template(goal)

    # 3. Determine experience level
    level = (goal.experience_level or _estimate_level(profile)).value

    # 4. Compute plan dates
    total_weeks = template["total_weeks"]
    race_date = goal.target_date
    plan_start = race_date - timedelta(weeks=total_weeks)
    plan_start = plan_start - timedelta(days=plan_start.weekday())

    # 5. Get peak volume
    peak_km = template["peak_weekly_km"].get(level, template["peak_weekly_km"]["intermediate"])
    volume_prog = template["volume_progression"]

    # 6. Build phase lookup: week_number -> phase name
    phase_map: dict[int, str] = {}
    for p in template.get("phases", []):
        for wk in p["weeks"]:
            phase_map[wk] = p["name"]

    # 7. Create workout factory
    factory = WorkoutFactory(paces)

    # 8. Build weeks with varied workouts
    weeks: list[TrainingWeek] = []
    for wk_idx in range(total_weeks):
        wk_num = wk_idx + 1
        week_start = plan_start + timedelta(weeks=wk_idx)
        multiplier = volume_prog[wk_idx] if wk_idx < len(volume_prog) else volume_prog[-1]
        week_km = round(peak_km * multiplier, 1)

        phase = phase_map.get(wk_num, "Build")

        # Race week override (last week)
        is_race_week = wk_num == total_weeks and "race_week" in template
        if is_race_week:
            day_templates = template["race_week"]
            workouts = _build_workouts(
                day_templates=day_templates,
                week_start=week_start,
                week_km=week_km,
                paces=paces,
                long_run_day=goal.long_run_day,
            )
            # Add purpose to non-rest workouts that lack it
            for w in workouts:
                if w.workout_type != WorkoutType.REST and w.purpose is None:
                    w.purpose = TrainingPurpose.RECOVERY
            weeks.append(
                TrainingWeek(
                    week_number=wk_num,
                    phase=phase,
                    total_distance_km=week_km,
                    workouts=workouts,
                    focus="Race week — trust the training",
                )
            )
            continue

        # Generate varied workouts for this week
        workouts = _build_varied_week(
            factory=factory,
            phase=phase,
            week_km=week_km,
            week_start=week_start,
            wk_idx=wk_idx,
            long_run_day=goal.long_run_day,
            max_days=goal.max_days_per_week,
        )

        focus = _get_focus(phase, wk_idx)

        weeks.append(
            TrainingWeek(
                week_number=wk_num,
                phase=phase,
                total_distance_km=week_km,
                workouts=workouts,
                focus=focus,
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


def _get_focus(phase: str, wk_idx: int) -> str:
    """Get a focus string for the week based on phase and rotation index."""
    pool = {
        "Base": _FOCUS_BASE,
        "Build": _FOCUS_BUILD,
        "Peak": _FOCUS_PEAK,
        "Taper": _FOCUS_TAPER,
    }.get(phase, _FOCUS_BUILD)
    return pool[wk_idx % len(pool)]


def _build_varied_week(
    factory: WorkoutFactory,
    phase: str,
    week_km: float,
    week_start: date,
    wk_idx: int,
    long_run_day: str,
    max_days: int = 5,
) -> list[Workout]:
    """Build a week of workouts with variety based on phase and rotation index."""
    workouts: list[Workout] = []

    # Distance allocation fractions
    long_frac = 0.35
    q1_frac = 0.15
    q2_frac = 0.17
    easy_frac = 0.15

    long_km = round(week_km * long_frac, 1)
    q1_km = round(week_km * q1_frac, 1)
    q2_km = round(week_km * q2_frac, 1)
    easy1_km = round(week_km * easy_frac, 1)
    easy2_km = round(week_km * (1 - long_frac - q1_frac - q2_frac - easy_frac), 1)
    if easy2_km < 0:
        easy2_km = 3

    # Pick workout types from rotation pools
    q1_pool = {
        "Base": _Q1_BASE, "Build": _Q1_BUILD, "Peak": _Q1_PEAK, "Taper": _Q1_TAPER,
    }.get(phase, _Q1_BUILD)
    q2_pool = {
        "Base": _Q2_BASE, "Build": _Q2_BUILD, "Peak": _Q2_PEAK, "Taper": _Q2_TAPER,
    }.get(phase, _Q2_BUILD)
    lr_pool = {
        "Base": _LR_BASE, "Build": _LR_BUILD, "Peak": _LR_PEAK, "Taper": _LR_TAPER,
    }.get(phase, _LR_BUILD)

    q1_type = q1_pool[wk_idx % len(q1_pool)]
    q2_type = q2_pool[wk_idx % len(q2_pool)]
    lr_type = lr_pool[wk_idx % len(lr_pool)]
    easy_type = _EASY_ROTATION[wk_idx % len(_EASY_ROTATION)]

    # Monday: Rest
    workouts.append(Workout(
        workout_type=WorkoutType.REST,
        name="Rest Day",
        scheduled_date=week_start + timedelta(days=0),
    ))

    # Tuesday: Quality 1
    q1 = _make_q1(factory, q1_type, q1_km)
    q1.scheduled_date = week_start + timedelta(days=1)
    workouts.append(q1)

    # Wednesday: Easy / Easy+Strides
    if easy_type == "easy_with_strides":
        e1 = factory.easy_with_strides(easy1_km)
    else:
        e1 = factory.easy_run(easy1_km)
    e1.scheduled_date = week_start + timedelta(days=2)
    workouts.append(e1)

    # Thursday: Quality 2
    q2 = _make_q2(factory, q2_type, q2_km)
    q2.scheduled_date = week_start + timedelta(days=3)
    workouts.append(q2)

    # Friday: Rest
    workouts.append(Workout(
        workout_type=WorkoutType.REST,
        name="Rest Day",
        scheduled_date=week_start + timedelta(days=4),
    ))

    # Long run + easy: respect long_run_day preference
    lr_offset = _DAY_OFFSETS.get(long_run_day, 6)
    easy2_offset = 5 if lr_offset == 6 else 6

    e2 = (
        factory.easy_with_strides(easy2_km)
        if easy_type == "easy"
        else factory.easy_run(easy2_km)
    )
    e2.scheduled_date = week_start + timedelta(days=easy2_offset)
    workouts.append(e2)

    lr = _make_long_run(factory, lr_type, long_km)
    lr.scheduled_date = week_start + timedelta(days=lr_offset)
    workouts.append(lr)

    # Reduce running days if needed
    if max_days < 5:
        drop_count = 5 - max_days
        drop_indices = [5, 2][:drop_count]
        for idx in sorted(drop_indices, reverse=True):
            workouts[idx] = Workout(
                workout_type=WorkoutType.REST,
                name="Rest Day",
                scheduled_date=workouts[idx].scheduled_date,
            )

    return workouts


def _make_q1(factory: WorkoutFactory, q1_type: str, distance_km: float) -> Workout:
    """Generate quality session 1 based on rotation type."""
    if q1_type == "vo2max":
        return factory.vo2max_intervals(reps=5, rep_min=3.5)
    elif q1_type == "speed_400s":
        return factory.speed_400s(reps=8)
    elif q1_type == "speed_200s":
        return factory.speed_200s(reps=10)
    elif q1_type == "hills":
        return factory.hills(reps=8)
    elif q1_type == "fartlek":
        return factory.fartlek(total_min=40)
    elif q1_type == "easy_with_strides":
        return factory.easy_with_strides(distance_km)
    else:
        return factory.fartlek(total_min=40)


def _make_q2(factory: WorkoutFactory, q2_type: str, distance_km: float) -> Workout:
    """Generate quality session 2 based on rotation type."""
    if q2_type == "tempo":
        tempo_km = max(distance_km - 3, 3)
        return factory.tempo(tempo_km)
    elif q2_type == "threshold_cruise":
        return factory.threshold_cruise_intervals(reps=4, rep_min=6)
    elif q2_type == "progressive":
        return factory.progressive_run(distance_km)
    elif q2_type == "race_pace":
        return factory.race_pace_intervals(reps=4, rep_km=1.0, pace_key="marathon")
    elif q2_type == "easy_with_strides":
        return factory.easy_with_strides(distance_km)
    else:
        return factory.tempo(max(distance_km - 3, 3))


def _make_long_run(factory: WorkoutFactory, lr_type: str, distance_km: float) -> Workout:
    """Generate long run based on rotation type."""
    if lr_type == "long_progressive":
        return factory.long_run_progressive(distance_km)
    elif lr_type == "long_with_race_pace":
        return factory.long_run_with_race_pace(distance_km, race_pace_km=min(4, distance_km * 0.25))
    else:
        return factory.long_run(distance_km)


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
    level = (
        goal.experience_level.value
        if goal.experience_level
        else "intermediate"
    )
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
    max_days: int = 5,
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
