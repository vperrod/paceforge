"""AI running coach — LLM-powered plan adaptation and conversational coaching.

The coach receives the user's fitness profile, current plan state, and a question,
then uses an LLM to provide personalised advice. The LLM adjusts the rule-based
plan rather than generating plans from scratch.
"""

from __future__ import annotations

import json
import logging
from dataclasses import dataclass

from openai import OpenAI

from paceforge.models.plan import TrainingPlan
from paceforge.models.profile import UserFitnessProfile

logger = logging.getLogger(__name__)

SYSTEM_PROMPT = """\
You are PaceForge Coach, an expert running coach assistant.

Your role:
- Analyse the athlete's fitness data and training plan
- Provide evidence-based advice grounded in exercise science
- Suggest plan adjustments when the athlete misses workouts, feels fatigued, or is ahead of schedule
- Never recommend anything that could cause injury (e.g. doubling volume overnight)
- Be concise, supportive, and specific — cite paces, distances, and dates when relevant
- If the athlete asks something outside running/fitness, politely redirect

Safety rules:
- Never recommend training through sharp or acute pain
- Always suggest consulting a medical professional for injury-related questions
- Respect rest days — do not advise eliminating all recovery
- Follow the 10% weekly mileage increase rule unless the athlete is experienced

You will be provided with the athlete's fitness profile and current training plan as context.
"""


@dataclass
class CoachResponse:
    reply: str
    suggested_adjustments: list[str] | None = None


class Coach:
    """LLM-powered running coach."""

    def __init__(
        self,
        api_key: str,
        model: str = "gpt-4o-mini",
        base_url: str | None = None,
    ) -> None:
        kwargs: dict = {"api_key": api_key}
        if base_url:
            kwargs["base_url"] = base_url
        self._client = OpenAI(**kwargs)
        self._model = model
        self._conversation: list[dict[str, str]] = []

    def _build_context(
        self,
        profile: UserFitnessProfile | None,
        plan: TrainingPlan | None,
    ) -> str:
        parts: list[str] = []

        if profile:
            parts.append("## Athlete Fitness Profile")
            parts.append(f"- VO2 Max: {profile.vo2_max or 'unknown'}")
            parts.append(f"- Resting HR: {profile.resting_hr or 'unknown'} bpm")
            parts.append(f"- Max HR: {profile.max_hr or 'unknown'} bpm")
            parts.append(f"- Training Readiness: {profile.training_readiness or 'unknown'}")
            parts.append(f"- HRV Status: {profile.hrv_status or 'unknown'}")
            parts.append(f"- HRV Last Night: {profile.hrv_last_night or 'unknown'}")
            parts.append(f"- Weekly Mileage: {profile.weekly_mileage_km or 'unknown'} km/week")

            if profile.race_predictions:
                parts.append("- Race Predictions:")
                for rp in profile.race_predictions:
                    h = int(rp.predicted_seconds) // 3600
                    m = (int(rp.predicted_seconds) % 3600) // 60
                    s = int(rp.predicted_seconds) % 60
                    t = f"{h}:{m:02d}:{s:02d}" if h else f"{m}:{s:02d}"
                    parts.append(f"  - {rp.distance}: {t}")

            if profile.recent_activities:
                parts.append(f"- Recent activities ({len(profile.recent_activities)} in last 30 days):")
                for act in profile.recent_activities[:5]:
                    dist = round(act.distance_meters / 1000, 1)
                    pace_str = ""
                    if act.avg_pace_sec_per_km:
                        pm, ps = divmod(int(act.avg_pace_sec_per_km), 60)
                        pace_str = f" @ {pm}:{ps:02d}/km"
                    parts.append(f"  - {act.name}: {dist}km{pace_str}")

        if plan:
            parts.append("")
            parts.append("## Current Training Plan")
            parts.append(f"- Plan: {plan.name}")
            parts.append(f"- Goal: {plan.goal_type}")
            parts.append(f"- Race date: {plan.target_date}")
            parts.append(f"- Total weeks: {plan.total_weeks}")

            if plan.easy_pace:
                from paceforge.engine.vdot import _fmt

                parts.append(f"- Easy pace: {_fmt(plan.easy_pace)}")
            if plan.threshold_pace:
                from paceforge.engine.vdot import _fmt

                parts.append(f"- Threshold pace: {_fmt(plan.threshold_pace)}")

            # Show current and next 2 weeks of workouts
            from datetime import date as dt_date

            today = dt_date.today()
            for week in plan.weeks:
                # Show weeks that haven't passed yet
                week_dates = [
                    w.scheduled_date for w in week.workouts if w.scheduled_date
                ]
                if week_dates and max(week_dates) >= today:
                    parts.append(
                        f"\n### Week {week.week_number} — {week.phase} "
                        f"({week.total_distance_km} km)"
                    )
                    for w in week.workouts:
                        if w.workout_type.value == "rest":
                            parts.append(f"  - {w.scheduled_date}: Rest")
                        else:
                            dist = round((w.estimated_distance_meters or 0) / 1000, 1)
                            parts.append(
                                f"  - {w.scheduled_date}: {w.name} ({dist}km)"
                            )
                            if w.notes:
                                parts.append(f"    Notes: {w.notes}")

                    # Only show 3 upcoming weeks to save tokens
                    if week.week_number >= 3:
                        upcoming_shown = sum(
                            1 for wk in plan.weeks
                            if wk.week_number <= week.week_number
                            and any(
                                wd.scheduled_date and wd.scheduled_date >= today
                                for wd in wk.workouts
                            )
                        )
                        if upcoming_shown >= 3:
                            parts.append(f"\n(... {plan.total_weeks - week.week_number} more weeks)")
                            break

        return "\n".join(parts)

    def chat(
        self,
        message: str,
        profile: UserFitnessProfile | None = None,
        plan: TrainingPlan | None = None,
    ) -> CoachResponse:
        """Send a message to the AI coach and get a response."""
        # Build context on first message or if profile/plan changed
        if not self._conversation:
            context = self._build_context(profile, plan)
            self._conversation = [
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "system", "content": f"Current athlete data:\n{context}"},
            ]

        self._conversation.append({"role": "user", "content": message})

        try:
            response = self._client.chat.completions.create(
                model=self._model,
                messages=self._conversation,
                temperature=0.7,
                max_tokens=1000,
            )
            reply = response.choices[0].message.content or "I couldn't generate a response."
            self._conversation.append({"role": "assistant", "content": reply})
        except Exception as e:
            logger.error("LLM call failed: %s", e, exc_info=True)
            reply = f"Sorry, I couldn't reach the AI service: {e}"

        return CoachResponse(reply=reply)

    def reset_conversation(self) -> None:
        """Clear conversation history for a fresh session."""
        self._conversation = []

    def analyse_fitness_trends(
        self,
        profile: UserFitnessProfile,
        plan: TrainingPlan | None = None,
    ) -> CoachResponse:
        """Automated analysis — called without a user message."""
        prompts: list[str] = []

        # HRV analysis
        if profile.hrv_status and profile.hrv_status.lower() in ("low", "poor"):
            prompts.append(
                "The athlete's HRV status is LOW. Assess recovery state and "
                "suggest whether upcoming workouts should be modified."
            )

        # Training readiness
        if profile.training_readiness and profile.training_readiness < 30:
            prompts.append(
                f"Training readiness is {profile.training_readiness}/100 (very low). "
                "What adjustments do you recommend for this week?"
            )

        # Volume check
        if profile.weekly_mileage_km and profile.weekly_mileage_km < 15:
            prompts.append(
                f"Weekly mileage is only {profile.weekly_mileage_km} km. "
                "Is the athlete undertrained for their goal? Suggest adjustments."
            )

        if not prompts:
            prompts.append(
                "Review the athlete's current fitness data and training plan. "
                "Provide a brief assessment and any recommendations."
            )

        return self.chat(
            "\n".join(prompts),
            profile=profile,
            plan=plan,
        )
