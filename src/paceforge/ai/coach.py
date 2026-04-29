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

    def analyze_week(
        self,
        profile: UserFitnessProfile | None,
        activities: list[dict],
        plan: TrainingPlan | None = None,
        health_data: dict | None = None,
    ) -> dict:
        """Analyze the current week: activities vs plan, recovery, performance.

        Returns a dict with structured sections: summary, plan_adherence,
        performance, recovery, concerns, tips.
        """
        from datetime import date as dt_date

        today = dt_date.today()
        monday = today - __import__("datetime").timedelta(days=today.weekday())
        sunday = monday + __import__("datetime").timedelta(days=6)

        lines: list[str] = []
        lines.append(f"## Weekly Overview: {monday.isoformat()} to {sunday.isoformat()}\n")

        # Activities this week
        if activities:
            lines.append(f"### Activities This Week ({len(activities)} total)")
            total_dist = 0.0
            total_dur = 0
            for act in activities:
                name = act.get("name", "Activity")
                dist = act.get("distance_meters", 0)
                dur = act.get("duration_seconds", 0)
                total_dist += dist
                total_dur += dur
                dist_km = dist / 1000 if dist else 0
                pace = act.get("avg_pace_sec_per_km")
                pace_str = ""
                if pace:
                    pm, ps = divmod(int(pace), 60)
                    pace_str = f" @ {pm}:{ps:02d}/km"
                hr_str = f" | HR {act['avg_hr']}bpm" if act.get("avg_hr") else ""
                te_str = ""
                if act.get("training_effect_aerobic"):
                    te_str = f" | TE {act['training_effect_aerobic']}"
                lines.append(f"- {act.get('start_time', '')}: {name} — {dist_km:.1f}km{pace_str}{hr_str}{te_str}")
            lines.append(f"\nWeekly totals: {total_dist/1000:.1f} km, {total_dur//60} min")
        else:
            lines.append("### No activities recorded this week yet.")

        # Plan adherence
        if plan:
            lines.append("\n### Planned Workouts This Week")
            for week in plan.weeks:
                for wo in week.workouts:
                    if wo.scheduled_date and monday <= wo.scheduled_date <= sunday:
                        planned_dist = round((wo.estimated_distance_meters or 0) / 1000, 1)
                        status = "✅ Completed" if wo.matched_activity_id else ("⏳ Upcoming" if wo.scheduled_date >= today else "❌ Missed")
                        lines.append(f"- {wo.scheduled_date}: {wo.name} ({planned_dist}km) — {status}")
                        if wo.completion_analysis:
                            lines.append(f"  Analysis: {wo.completion_analysis[:150]}")

        # Recovery & wellness
        if profile:
            lines.append("\n### Recovery & Wellness Metrics")
            if profile.training_readiness is not None:
                lines.append(f"- Training Readiness: {profile.training_readiness}/100")
            if profile.hrv_status:
                lines.append(f"- HRV Status: {profile.hrv_status}")
            if profile.hrv_last_night:
                lines.append(f"- HRV Last Night: {profile.hrv_last_night}")

        if health_data:
            if health_data.get("sleep_score"):
                lines.append(f"- Sleep Score: {health_data['sleep_score']}")
            if health_data.get("stress_level"):
                lines.append(f"- Stress Level: {health_data['stress_level']}")
            if health_data.get("body_battery_current"):
                lines.append(f"- Body Battery: {health_data['body_battery_current']}/100")

        # Fitness snapshot
        if profile:
            lines.append("\n### Fitness Snapshot")
            if profile.vo2_max:
                lines.append(f"- VO2max: {profile.vo2_max}")
            if profile.weekly_mileage_km:
                lines.append(f"- Recent weekly mileage: {profile.weekly_mileage_km} km")

        lines.append(
            "\n---\n"
            "Provide a structured weekly analysis with these exact section headers "
            "(use ## for each):\n"
            "## Summary\nA 2-3 sentence overview of how the week is going.\n"
            "## Plan Adherence\nHow well the athlete followed the training plan "
            "(skip if no plan).\n"
            "## Performance Highlights\nKey metrics, pacing observations, "
            "notable achievements.\n"
            "## Recovery & Wellness\nSleep, HRV, stress, body battery assessment "
            "and what it means.\n"
            "## Concerns\nAny red flags, overtraining signs, or things to watch. "
            "Write 'None' if everything looks good.\n"
            "## Tips\n2-3 actionable recommendations for the rest of the week.\n"
            "\nBe specific with numbers. Be encouraging but honest."
        )

        # Use a fresh conversation
        saved = self._conversation
        self._conversation = [
            {"role": "system", "content": SYSTEM_PROMPT},
        ]
        if profile:
            ctx = self._build_context(profile, plan)
            self._conversation.append({"role": "system", "content": f"Athlete data:\n{ctx}"})

        self._conversation.append({"role": "user", "content": "\n".join(lines)})

        try:
            if self._provider == "anthropic":
                reply = self._chat_anthropic()
            else:
                # Temporarily increase max_tokens for weekly analysis
                reply = self._chat_openai_extended()
        except Exception as e:
            logger.error("Weekly analysis failed: %s", e, exc_info=True)
            reply = f"Could not generate weekly analysis: {e}"

        self._conversation = saved

        # Parse sections from reply
        sections = self._parse_weekly_sections(reply)
        return sections

    def _chat_openai_extended(self, max_tokens: int = 1500, json_mode: bool = False) -> str:
        """OpenAI chat with configurable token limit for long-form output."""
        from openai import OpenAI

        kwargs: dict = {"api_key": self._api_key}
        if self._base_url:
            kwargs["base_url"] = self._base_url
        client = OpenAI(**kwargs)
        create_kwargs: dict = {
            "model": self._model,
            "messages": self._conversation,
            "temperature": 0.7,
            "max_tokens": max_tokens,
        }
        if json_mode:
            create_kwargs["response_format"] = {"type": "json_object"}
        response = client.chat.completions.create(**create_kwargs)
        choice = response.choices[0]
        content = choice.message.content or ""
        if choice.finish_reason == "length":
            logger.warning(
                "OpenAI response truncated (max_tokens=%d, model=%s). "
                "Attempting JSON repair.",
                max_tokens, self._model,
            )
            content = self._repair_truncated_json(content)
        return content or "I couldn't generate a response."

    @staticmethod
    def _repair_truncated_json(content: str) -> str:
        """Repair truncated / malformed JSON using json_repair."""
        import json as _json

        from json_repair import loads as repair_loads

        content = content.rstrip()
        try:
            _json.loads(content)
            return content
        except _json.JSONDecodeError:
            pass

        repaired = repair_loads(content)
        if isinstance(repaired, (dict, list)):
            return _json.dumps(repaired)
        return content

    @staticmethod
    def _parse_weekly_sections(text: str) -> dict:
        """Parse the AI response into structured sections."""
        import re

        section_map = {
            "summary": "",
            "plan_adherence": "",
            "performance": "",
            "recovery": "",
            "concerns": "",
            "tips": "",
        }
        # Map heading text → key
        heading_keys = {
            "summary": "summary",
            "plan adherence": "plan_adherence",
            "performance highlights": "performance",
            "performance": "performance",
            "recovery & wellness": "recovery",
            "recovery": "recovery",
            "concerns": "concerns",
            "tips": "tips",
        }
        # Split by ## headings
        parts = re.split(r"##\s+", text)
        for part in parts:
            if not part.strip():
                continue
            first_line_end = part.find("\n")
            if first_line_end == -1:
                heading = part.strip().lower()
                body = ""
            else:
                heading = part[:first_line_end].strip().lower()
                body = part[first_line_end:].strip()
            for h_text, key in heading_keys.items():
                if h_text in heading:
                    section_map[key] = body
                    break
        # If parsing failed, put everything in summary
        if not any(section_map.values()):
            section_map["summary"] = text
        return section_map

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

    # ── Diet & Nutrition ─────────────────────────────────────────────

    def generate_diet_plan(
        self,
        diet_profile: dict,
        fitness_profile: UserFitnessProfile | None = None,
        activities: list[dict] | None = None,
        weight_history: list[dict] | None = None,
        training_plan: TrainingPlan | None = None,
    ) -> str:
        """Generate a personalised diet plan using AI.

        Returns a JSON string representing the full meal plan that the
        caller parses into DietPlan / DailyMealPlan models.
        """
        lines: list[str] = []
        plan_weeks = diet_profile.get("plan_weeks", 1)
        total_days = plan_weeks * 7
        lines.append(f"Generate a detailed {plan_weeks}-week ({total_days}-day) meal plan for this athlete.\n")

        # Diet goals & preferences
        lines.append("## Diet Profile")
        goals = diet_profile.get("goals", [])
        lines.append(f"- Goals: {', '.join(goals) if goals else 'general health'}")
        if diet_profile.get("target_weight_kg"):
            lines.append(f"- Target weight: {diet_profile['target_weight_kg']} kg")
        lines.append(f"- Meals per day: {diet_profile.get('daily_meals_count', 3)}")
        lines.append(f"- Plan duration: {plan_weeks} week(s)")
        preferred = diet_profile.get("preferred_foods", [])
        if preferred:
            lines.append(f"- Preferred foods: {', '.join(preferred)}")
        allergies = diet_profile.get("allergies", [])
        if allergies:
            lines.append(f"- Allergies: {', '.join(allergies)}")
        restrictions = diet_profile.get("restrictions", [])
        if restrictions:
            lines.append(f"- Dietary restrictions: {', '.join(restrictions)}")
        if diet_profile.get("notes"):
            lines.append(f"- Additional notes: {diet_profile['notes']}")

        # Athlete metrics
        if fitness_profile:
            lines.append("\n## Athlete Metrics")
            if fitness_profile.weight_kg:
                lines.append(f"- Current weight: {fitness_profile.weight_kg} kg")
            if fitness_profile.vo2_max:
                lines.append(f"- VO2max: {fitness_profile.vo2_max}")
            if fitness_profile.weekly_mileage_km:
                lines.append(f"- Weekly mileage: {fitness_profile.weekly_mileage_km} km")
            if fitness_profile.training_status:
                lines.append(f"- Training status: {fitness_profile.training_status}")

        # Recent activity calorie burn
        if activities:
            total_cal = sum(a.get("calories") or 0 for a in activities)
            total_dur = sum(a.get("duration_seconds") or 0 for a in activities)
            days = max(1, len({str(a.get("start_time", ""))[:10] for a in activities}))
            lines.append(f"\n## Recent Activity ({len(activities)} sessions, last {days} active days)")
            lines.append(f"- Total calories burned: {total_cal}")
            lines.append(f"- Avg daily exercise calories: {total_cal // days}")
            lines.append(f"- Total training time: {total_dur // 60} min")

        # Weight trend
        if weight_history:
            lines.append("\n## Weight History")
            for w in weight_history[-10:]:
                bf = f" | Body fat: {w['body_fat_pct']}%" if w.get("body_fat_pct") else ""
                lines.append(f"- {w['date']}: {w['weight_kg']} kg{bf}")

        # Training plan context
        if training_plan:
            lines.append(f"\n## Training Plan: {training_plan.name}")
            lines.append(f"- Goal: {training_plan.goal_type}")
            if training_plan.target_date:
                lines.append(f"- Target race date: {training_plan.target_date}")
            lines.append(f"- Total weeks: {training_plan.total_weeks}")

        meals_count = diet_profile.get("daily_meals_count", 3)
        meal_types = ["breakfast", "lunch", "dinner"]
        if meals_count >= 4:
            meal_types.insert(1, "morning_snack")
        if meals_count >= 5:
            meal_types.insert(3, "afternoon_snack")
        if meals_count >= 6:
            meal_types.append("evening_snack")

        lines.append(f"""
## Instructions

Create a {total_days}-day meal plan ({plan_weeks} week(s)). For each day, provide {meals_count} meals: {', '.join(meal_types)}.
{'Vary meals across weeks — do not repeat the same day plan.' if plan_weeks > 1 else ''}

Respond with ONLY valid JSON (no markdown fences, no explanation) in this exact format:
{{
  "macro_targets": {{"calories": <number>, "protein_g": <number>, "carbs_g": <number>, "fat_g": <number>, "fiber_g": <number>}},
  "days": [
    {{
      "day_number": 1,
      "meals": [
        {{
          "name": "<meal name>",
          "meal_type": "<{'/'.join(meal_types)}>",
          "foods": [
            {{"name": "<food>", "quantity": <number>, "unit": "<g/ml/pcs/tbsp/cup>", "calories": <number>, "protein_g": <number>, "carbs_g": <number>, "fat_g": <number>}}
          ],
          "total_calories": <number>,
          "protein_g": <number>,
          "carbs_g": <number>,
          "fat_g": <number>,
          "fiber_g": <number>,
          "recipe_notes": "<brief preparation notes>"
        }}
      ],
      "daily_totals": {{"calories": <number>, "protein_g": <number>, "carbs_g": <number>, "fat_g": <number>, "fiber_g": <number>}}
    }}
  ]
}}

Important rules:
- Calculate macro targets based on the athlete's weight, activity level, and goals
- For weight loss: ~500 kcal deficit from TDEE; protein at 1.6-2.2g/kg body weight
- For muscle gain: ~300-500 kcal surplus; protein at 1.6-2.2g/kg
- For maintenance: match TDEE; protein at 1.4-1.8g/kg
- Prioritize the athlete's preferred foods but add variety
- Every meal must have realistic portion sizes and accurate macros
- Include the exercise calorie burn when calculating daily needs
- Make meals practical and easy to prepare
""")

        saved = self._conversation
        self._conversation = [
            {"role": "system", "content": _DIET_SYSTEM_PROMPT},
        ]

        self._conversation.append({"role": "user", "content": "\n".join(lines)})

        try:
            tokens = min(16000, 12000 + (plan_weeks - 1) * 4000)
            reply = self._chat_openai_extended(max_tokens=tokens, json_mode=True) if self._provider != "anthropic" else self._chat_anthropic()
        except Exception as e:
            logger.error("Diet plan generation failed: %s", e, exc_info=True)
            reply = f'{{"error": "Could not generate diet plan: {e}"}}'

        self._conversation = saved
        return reply

    def adjust_diet_plan(
        self,
        current_plan_summary: dict,
        weight_trend: list[dict],
        activity_data: list[dict],
        user_notes: list[dict] | None = None,
        fitness_profile: UserFitnessProfile | None = None,
    ) -> str:
        """Re-evaluate and adjust an existing diet plan.

        Returns JSON string with updated plan in the same format as generate_diet_plan.
        """
        lines: list[str] = []
        lines.append("Re-evaluate and adjust this athlete's diet plan based on their progress.\n")

        # Current plan
        lines.append("## Current Plan")
        targets = current_plan_summary.get("macro_targets", {})
        lines.append(f"- Daily calorie target: {targets.get('calories', 'unknown')}")
        lines.append(f"- Protein target: {targets.get('protein_g', 'unknown')}g")
        lines.append(f"- Carbs target: {targets.get('carbs_g', 'unknown')}g")
        lines.append(f"- Fat target: {targets.get('fat_g', 'unknown')}g")
        goals = current_plan_summary.get("goals", [])
        if goals:
            lines.append(f"- Goals: {', '.join(goals)}")
        preferred = current_plan_summary.get("preferred_foods", [])
        if preferred:
            lines.append(f"- Preferred foods: {', '.join(preferred)}")

        # Weight progress
        if weight_trend:
            lines.append("\n## Weight Trend (recent)")
            for w in weight_trend[-14:]:
                bf = f" | Body fat: {w['body_fat_pct']}%" if w.get("body_fat_pct") else ""
                lines.append(f"- {w['date']}: {w['weight_kg']} kg{bf}")
            if len(weight_trend) >= 2:
                first_w = weight_trend[0]["weight_kg"]
                last_w = weight_trend[-1]["weight_kg"]
                change = last_w - first_w
                lines.append(f"- Change: {change:+.1f} kg over {len(weight_trend)} entries")

        # Activity
        if activity_data:
            total_cal = sum(a.get("calories") or 0 for a in activity_data)
            lines.append(f"\n## Recent Activity ({len(activity_data)} sessions)")
            lines.append(f"- Total calories burned: {total_cal}")

        # Athlete metrics
        if fitness_profile and fitness_profile.weight_kg:
            lines.append(f"\n## Current Metrics")
            lines.append(f"- Weight: {fitness_profile.weight_kg} kg")

        # User feedback
        if user_notes:
            lines.append("\n## Athlete Feedback")
            for note in user_notes[-5:]:
                lines.append(f"- [{note.get('date', '')}]: {note.get('content', '')}")

        meals_count = current_plan_summary.get("daily_meals_count", 3)
        meal_types = ["breakfast", "lunch", "dinner"]
        if meals_count >= 4:
            meal_types.insert(1, "morning_snack")
        if meals_count >= 5:
            meal_types.insert(3, "afternoon_snack")
        if meals_count >= 6:
            meal_types.append("evening_snack")

        lines.append(f"""
## Instructions

Based on the athlete's progress and feedback, generate an adjusted 7-day meal plan.
First explain in 2-3 sentences what you're changing and why (as "adjustment_reason"),
then provide the new plan.

Respond with ONLY valid JSON (no markdown fences) in this exact format:
{{
  "adjustment_reason": "<what changed and why>",
  "macro_targets": {{"calories": <number>, "protein_g": <number>, "carbs_g": <number>, "fat_g": <number>, "fiber_g": <number>}},
  "days": [
    {{
      "day_number": 1,
      "meals": [
        {{
          "name": "<meal name>",
          "meal_type": "<{'/'.join(meal_types)}>",
          "foods": [
            {{"name": "<food>", "quantity": <number>, "unit": "<g/ml/pcs/tbsp/cup>", "calories": <number>, "protein_g": <number>, "carbs_g": <number>, "fat_g": <number>}}
          ],
          "total_calories": <number>,
          "protein_g": <number>,
          "carbs_g": <number>,
          "fat_g": <number>,
          "fiber_g": <number>,
          "recipe_notes": "<brief preparation notes>"
        }}
      ],
      "daily_totals": {{"calories": <number>, "protein_g": <number>, "carbs_g": <number>, "fat_g": <number>, "fiber_g": <number>}}
    }}
  ]
}}
""")

        saved = self._conversation
        self._conversation = [
            {"role": "system", "content": _DIET_SYSTEM_PROMPT},
        ]

        self._conversation.append({"role": "user", "content": "\n".join(lines)})

        try:
            reply = self._chat_openai_extended(max_tokens=8000, json_mode=True) if self._provider != "anthropic" else self._chat_anthropic()
        except Exception as e:
            logger.error("Diet plan adjustment failed: %s", e, exc_info=True)
            reply = f'{{"error": "Could not adjust diet plan: {e}"}}'

        self._conversation = saved
        return reply


_DIET_SYSTEM_PROMPT = """\
You are PaceForge Nutrition Coach, an expert sports nutritionist specialising \
in meal planning for endurance athletes.

Your role:
- Create personalised meal plans that support the athlete's training and body \
composition goals
- Calculate accurate TDEE (Total Daily Energy Expenditure) based on weight, \
activity level, and exercise data
- Ensure adequate protein intake for recovery (1.4-2.2 g/kg depending on goal)
- Time carbohydrate intake around training sessions
- Prioritise whole foods and the athlete's preferred ingredients
- Provide practical, easy-to-prepare meals with realistic portion sizes

Safety rules:
- Never recommend fewer than 1200 kcal/day for women or 1500 kcal/day for men
- Never suggest eliminating entire macronutrient groups
- Always recommend consulting a dietitian for medical dietary needs
- Flag potential nutrient deficiencies in restrictive diets
- Suggest gradual calorie adjustments (max 500 kcal deficit/surplus)

You respond ONLY with valid JSON — no markdown fences, no prose outside the \
JSON structure.
"""
