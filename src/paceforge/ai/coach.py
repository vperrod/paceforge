"""AI running coach — LLM-powered plan adaptation and conversational coaching.

The coach receives the user's fitness profile, current plan state, and a question,
then uses an LLM to provide personalised advice. The LLM adjusts the rule-based
plan rather than generating plans from scratch.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass

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
        provider: str = "openai",
    ) -> None:
        self._api_key = api_key
        self._model = model
        self._base_url = base_url
        self._provider = provider
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
            reply = self._chat_anthropic() if self._provider == "anthropic" else self._chat_openai()
            self._conversation.append({"role": "assistant", "content": reply})
        except Exception as e:
            logger.error("LLM call failed: %s", e, exc_info=True)
            reply = f"Sorry, I couldn't reach the AI service: {e}"

        return CoachResponse(reply=reply)

    def _chat_openai(self) -> str:
        from openai import OpenAI

        kwargs: dict = {"api_key": self._api_key}
        if self._base_url:
            kwargs["base_url"] = self._base_url
        client = OpenAI(**kwargs)
        response = client.chat.completions.create(
            model=self._model,
            messages=self._conversation,
            temperature=0.7,
            max_tokens=1000,
        )
        return response.choices[0].message.content or "I couldn't generate a response."

    def _chat_anthropic(self) -> str:
        import anthropic

        client = anthropic.Anthropic(api_key=self._api_key)
        # Anthropic: system prompt separate, only user/assistant messages
        system_parts = []
        messages = []
        for msg in self._conversation:
            if msg["role"] == "system":
                system_parts.append(msg["content"])
            else:
                messages.append(msg)
        response = client.messages.create(
            model=self._model,
            max_tokens=1000,
            system="\n\n".join(system_parts),
            messages=messages,
            temperature=0.7,
        )
        return response.content[0].text

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

    def analyze_workout(
        self,
        workout: dict,
        activity: dict,
        profile: UserFitnessProfile | None = None,
        user_feedback: dict | None = None,
    ) -> str:
        """Analyze a completed workout against the planned workout.

        Returns AI-generated analysis text comparing planned vs actual metrics.
        """
        def _fp(sec_per_km: float | None) -> str:
            if not sec_per_km:
                return "N/A"
            m, s = divmod(int(sec_per_km), 60)
            return f"{m}:{s:02d}/km"

        lines = ["Analyze this completed workout compared to what was planned.\n"]

        # Planned workout details
        lines.append("## Planned Workout")
        lines.append(f"- Name: {workout.get('name', 'Unknown')}")
        lines.append(f"- Type: {workout.get('workout_type', 'Unknown')}")
        planned_dist = workout.get("estimated_distance_meters", 0)
        if planned_dist:
            lines.append(f"- Planned distance: {planned_dist / 1000:.1f} km")
        planned_dur = workout.get("estimated_duration_seconds", 0)
        if planned_dur:
            m, s = divmod(int(planned_dur), 60)
            lines.append(f"- Planned duration: {m}:{s:02d}")
        if workout.get("notes"):
            lines.append(f"- Coach notes: {workout['notes']}")

        # Step targets
        steps = workout.get("steps", [])
        if steps:
            lines.append("- Planned steps:")
            for step in steps:
                desc = step.get("description", "")
                tl = step.get("target_low")
                th = step.get("target_high")
                if tl:
                    lines.append(f"  - {desc}: {_fp(tl)} to {_fp(th)}")
                else:
                    lines.append(f"  - {desc}")

        # Actual activity details
        lines.append("\n## Actual Activity (from Garmin)")
        lines.append(f"- Name: {activity.get('name', 'Unknown')}")
        actual_dist = activity.get("distance_meters", 0)
        if actual_dist:
            lines.append(f"- Actual distance: {actual_dist / 1000:.1f} km")
        actual_dur = activity.get("duration_seconds", 0)
        if actual_dur:
            m, s = divmod(int(actual_dur), 60)
            lines.append(f"- Actual duration: {m}:{s:02d}")
        if activity.get("avg_pace_sec_per_km"):
            lines.append(f"- Average pace: {_fp(activity['avg_pace_sec_per_km'])}")
        if activity.get("avg_hr"):
            lines.append(f"- Average HR: {activity['avg_hr']} bpm")
        if activity.get("max_hr"):
            lines.append(f"- Max HR: {activity['max_hr']} bpm")
        if activity.get("training_effect_aerobic"):
            lines.append(f"- Aerobic training effect: {activity['training_effect_aerobic']}")
        if activity.get("training_effect_anaerobic"):
            lines.append(f"- Anaerobic training effect: {activity['training_effect_anaerobic']}")
        if activity.get("avg_running_cadence"):
            lines.append(f"- Cadence: {activity['avg_running_cadence']} spm")
        if activity.get("elevation_gain"):
            lines.append(f"- Elevation gain: {activity['elevation_gain']} m")

        # Comparison
        lines.append("\n## Comparison")
        if planned_dist and actual_dist:
            diff_pct = ((actual_dist - planned_dist) / planned_dist) * 100
            lines.append(f"- Distance: {diff_pct:+.0f}% vs planned")
        if planned_dur and actual_dur:
            diff_pct = ((actual_dur - planned_dur) / planned_dur) * 100
            lines.append(f"- Duration: {diff_pct:+.0f}% vs planned")

        # User feedback
        if user_feedback:
            rpe = user_feedback.get("rpe")
            notes = user_feedback.get("notes")
            if rpe or notes:
                lines.append("\n## Athlete Feedback")
                if rpe:
                    rpe_labels = {1: "Very Light", 2: "Light", 3: "Light-Moderate", 4: "Moderate",
                                  5: "Moderate-Hard", 6: "Hard", 7: "Very Hard", 8: "Very Hard+",
                                  9: "Near Maximum", 10: "Maximum"}
                    lines.append(f"- RPE: {rpe}/10 ({rpe_labels.get(rpe, '')})")
                if notes:
                    lines.append(f"- Notes: {notes}")

        lines.append(
            "\nProvide a concise analysis (3-5 sentences) covering: "
            "1) How well the athlete executed the workout goals, "
            "2) Any notable positives, "
            "3) Any concerns or suggestions for next time. "
            "Be specific with numbers and encouraging."
        )

        # Use a fresh conversation for analysis
        saved = self._conversation
        self._conversation = [
            {"role": "system", "content": SYSTEM_PROMPT},
        ]
        if profile:
            ctx = self._build_context(profile, None)
            self._conversation.append({"role": "system", "content": f"Athlete data:\n{ctx}"})

        self._conversation.append({"role": "user", "content": "\n".join(lines)})

        try:
            reply = self._chat_anthropic() if self._provider == "anthropic" else self._chat_openai()
        except Exception as e:
            logger.error("Workout analysis failed: %s", e, exc_info=True)
            reply = f"Could not analyze workout: {e}"

        self._conversation = saved
        return reply

    def analyze_activity(
        self,
        activity: dict,
        profile: UserFitnessProfile | None = None,
    ) -> str:
        """Analyze a standalone Garmin activity (not matched to a plan workout).

        Parameters
        ----------
        activity : dict
            Activity data including summary, splits, HR zones.
        profile : UserFitnessProfile | None
            Optional athlete profile for context.
        """
        act_type = activity.get("activity_type", "running")
        name = activity.get("name", "Activity")
        dist = activity.get("distance_meters", 0)
        dur = activity.get("duration_seconds", 0)

        lines = [f"## Activity Analysis: {name}", f"- Type: {act_type}"]
        if dist:
            lines.append(f"- Distance: {dist / 1000:.2f} km")
        if dur:
            dm, ds = divmod(int(dur), 60)
            lines.append(f"- Duration: {dm}:{ds:02d}")
        pace = activity.get("avg_pace_sec_per_km")
        if pace:
            pm, ps = divmod(int(pace), 60)
            lines.append(f"- Avg Pace: {pm}:{ps:02d}/km")
        for key, label in [
            ("avg_hr", "Avg HR"), ("max_hr", "Max HR"),
            ("calories", "Calories"), ("elevation_gain", "Elevation Gain"),
            ("training_effect_aerobic", "Aerobic TE"),
            ("training_effect_anaerobic", "Anaerobic TE"),
            ("avg_running_cadence", "Cadence"),
        ]:
            val = activity.get(key)
            if val:
                lines.append(f"- {label}: {val}")

        # Include splits if available
        splits = activity.get("splits")
        if splits:
            lap_dtos = splits.get("lapDTOs") or []
            if lap_dtos:
                lines.append("\n## Splits")
                for i, lap in enumerate(lap_dtos, 1):
                    lap_dist = lap.get("distance", 0) / 1000
                    lap_dur_raw = lap.get("duration", 0)
                    lm, ls = divmod(int(lap_dur_raw), 60)
                    lap_hr = lap.get("averageHR", "")
                    lines.append(f"  Lap {i}: {lap_dist:.2f}km in {lm}:{ls:02d}" + (f" @ {lap_hr}bpm" if lap_hr else ""))

        # HR zones if available
        hr_zones = activity.get("hr_zones")
        if hr_zones:
            zone_list = hr_zones if isinstance(hr_zones, list) else hr_zones.get("hrTimeInZones", [])
            if zone_list:
                lines.append("\n## HR Zone Distribution")
                for z in zone_list:
                    zn = z.get("zoneNumber", "?")
                    secs = z.get("secsInZone", 0)
                    zm, zs = divmod(int(secs), 60)
                    lines.append(f"  Zone {zn}: {zm}:{zs:02d}")

        is_running = act_type in ("running", "trail_running", "treadmill_running")
        if is_running:
            lines.append(
                "\nProvide a concise analysis (3-5 sentences) covering: "
                "1) How the effort and pacing look overall, "
                "2) Any notable positives (e.g. consistent splits, good HR management), "
                "3) Any suggestions for improvement. "
                "Be specific with numbers and encouraging."
            )
        else:
            lines.append(
                "\nProvide a concise analysis (3-5 sentences) covering: "
                "1) How the effort and intensity look for this type of session, "
                "2) Any notable positives (e.g. HR response, duration, training effect), "
                "3) How this cross-training complements running fitness. "
                "Be specific with numbers and encouraging."
            )

        saved = self._conversation
        self._conversation = [
            {"role": "system", "content": SYSTEM_PROMPT},
        ]
        if profile:
            ctx = self._build_context(profile, None)
            self._conversation.append({"role": "system", "content": f"Athlete data:\n{ctx}"})

        self._conversation.append({"role": "user", "content": "\n".join(lines)})

        try:
            reply = self._chat_anthropic() if self._provider == "anthropic" else self._chat_openai()
        except Exception as e:
            logger.error("Activity analysis failed: %s", e, exc_info=True)
            reply = f"Could not analyze activity: {e}"

        self._conversation = saved
        return reply
