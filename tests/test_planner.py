"""Tests for the plan generator."""

from datetime import date, timedelta

from paceforge.engine.planner import generate_plan
from paceforge.models.plan import WorkoutType
from paceforge.models.profile import (
    ExperienceLevel,
    GoalType,
    TrainingGoal,
    UserFitnessProfile,
)


def _make_profile(vo2_max: float = 45.0) -> UserFitnessProfile:
    return UserFitnessProfile(
        vo2_max=vo2_max,
        resting_hr=55,
        max_hr=185,
        weekly_mileage_km=35,
    )


def _make_goal(
    goal_type: GoalType = GoalType.HALF_MARATHON,
    weeks_out: int = 14,
) -> TrainingGoal:
    return TrainingGoal(
        goal_type=goal_type,
        target_date=date.today() + timedelta(weeks=weeks_out),
        experience_level=ExperienceLevel.INTERMEDIATE,
    )


class TestPlanGeneration:
    def test_half_marathon_plan_has_correct_weeks(self):
        plan = generate_plan(_make_profile(), _make_goal())
        assert plan.total_weeks == 12
        assert len(plan.weeks) == 12

    def test_marathon_plan_has_correct_weeks(self):
        goal = _make_goal(GoalType.MARATHON, weeks_out=18)
        plan = generate_plan(_make_profile(), goal)
        assert plan.total_weeks == 16
        assert len(plan.weeks) == 16

    def test_hyrox_plan_has_correct_weeks(self):
        goal = _make_goal(GoalType.HYROX, weeks_out=12)
        plan = generate_plan(_make_profile(), goal)
        assert plan.total_weeks == 10
        assert len(plan.weeks) == 10

    def test_plan_has_paces(self):
        plan = generate_plan(_make_profile(vo2_max=50), _make_goal())
        assert plan.easy_pace is not None
        assert plan.threshold_pace is not None
        assert plan.interval_pace is not None

    def test_each_week_has_workouts(self):
        plan = generate_plan(_make_profile(), _make_goal())
        for week in plan.weeks:
            assert len(week.workouts) > 0

    def test_plan_includes_rest_days(self):
        plan = generate_plan(_make_profile(), _make_goal())
        rest_count = sum(
            1
            for week in plan.weeks
            for w in week.workouts
            if w.workout_type.value == "rest"
        )
        assert rest_count > 0

    def test_progressive_volume(self):
        plan = generate_plan(_make_profile(), _make_goal())
        # Week 1 should have less km than the peak week (ignoring taper)
        wk1_km = plan.weeks[0].total_distance_km or 0
        # Find max volume week (should be in Build/Peak phase)
        max_km = max(w.total_distance_km or 0 for w in plan.weeks)
        assert wk1_km < max_km

    def test_plan_without_vo2max_still_works(self):
        """Plan generation should handle missing VO2 max gracefully."""
        profile = UserFitnessProfile()
        plan = generate_plan(profile, _make_goal())
        assert plan.total_weeks > 0
        assert len(plan.weeks) > 0

    def test_workouts_have_variety(self):
        """Across all weeks, at least 4 different WorkoutType values should be used."""
        plan = generate_plan(_make_profile(), _make_goal())
        all_types = {
            w.workout_type
            for week in plan.weeks
            for w in week.workouts
        }
        # Filter out REST since it's not a "real" workout type for variety purposes
        non_rest_types = all_types - {WorkoutType.REST}
        assert len(non_rest_types) >= 4, f"Only found {len(non_rest_types)} types: {non_rest_types}"

    def test_workouts_have_purpose(self):
        """Non-rest workouts should have a purpose field set."""
        plan = generate_plan(_make_profile(), _make_goal())
        for week in plan.weeks:
            for w in week.workouts:
                if w.workout_type != WorkoutType.REST:
                    assert w.purpose is not None, (
                        f"Week {week.week_number}, workout '{w.name}' has no purpose"
                    )

    def test_weeks_have_focus(self):
        """Each week should have a non-empty focus field."""
        plan = generate_plan(_make_profile(), _make_goal())
        for week in plan.weeks:
            assert week.focus, f"Week {week.week_number} has empty focus"
