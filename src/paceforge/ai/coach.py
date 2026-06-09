"""AI running coach — LLM-powered plan adaptation and conversational coaching.

The coach receives the user's fitness profile, current plan state, and a question,
then uses an LLM to provide personalised advice. The LLM adjusts the rule-based
plan rather than generating plans from scratch.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass

from paceforge.ai.cache import TTL_DIET_PLAN, AICache
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
        cache: AICache | None = None,
    ) -> None:
        self._api_key = api_key
        self._model = model
        self._base_url = base_url
        self._provider = provider
        self._conversation: list[dict[str, str]] = []
        self._cache = cache

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
        # Prompt caching: 90% input token discount on repeated system prompts
        system_text = "\n\n".join(system_parts)
        system_with_cache = [
            {"type": "text", "text": system_text, "cache_control": {"type": "ephemeral"}},
        ]
        response = client.messages.create(
            model=self._model,
            max_tokens=1000,
            system=system_with_cache,
            messages=messages,
            temperature=0.7,
        )
        return response.content[0].text

    def _cached_chat(self, cache_key: str | None, ttl: int = TTL_DIET_PLAN) -> str:
        """Chat with optional cache lookup."""
        if cache_key and self._cache:
            cached = self._cache.get(cache_key)
            if cached is not None:
                logger.debug("Cache hit for %s", cache_key[:12])
                return cached

        reply = self._chat_anthropic() if self._provider == "anthropic" else self._chat_openai()

        if cache_key and self._cache:
            self._cache.set(cache_key, reply, model=self._model, ttl_seconds=ttl)

        return reply

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

    @staticmethod
    def _build_meal_size_instruction(meal_types: list[str], meal_sizes: dict[str, str]) -> str:
        """Build a calorie distribution instruction based on meal size preferences."""
        if not meal_sizes or all(v == "regular" for v in meal_sizes.values()):
            return ""
        size_pct = {"light": "~10-15%", "regular": "~20-25%", "large": "~30-35%"}
        size_label = {"light": "LIGHT", "regular": "REGULAR", "large": "LARGE"}
        parts = []
        for mt in meal_types:
            sz = meal_sizes.get(mt, "regular")
            parts.append(f"{mt}={size_label.get(sz, 'REGULAR')} ({size_pct.get(sz, '~20-25%')})")
        return f"CALORIE DISTRIBUTION: {', '.join(parts)} of daily calories.\n\n"

    def generate_macro_plan(
        self,
        diet_profile: dict,
        fitness_profile: UserFitnessProfile | None = None,
        activities: list[dict] | None = None,
        weight_history: list[dict] | None = None,
        training_plan: TrainingPlan | None = None,
    ) -> str:
        """Generate a nutrition analysis with macro targets and coaching guidance.

        Returns a JSON string with plan_analysis (detailed coaching explanation)
        and macro_targets. No meals — those are generated on demand separately.
        """
        import json as _json

        profile_context = self._build_profile_context(
            diet_profile, fitness_profile, activities, weight_history, training_plan,
        )
        meals_count = diet_profile.get("daily_meals_count", 3)
        meal_types = self._resolve_meal_types(meals_count)

        prompt = f"""{profile_context}

Analyse this athlete's body composition, training load, and goals. Then determine \
their optimal daily nutrition targets for a {meals_count}-meal structure \
({', '.join(meal_types)}).

Respond with ONLY valid JSON:
{{
  "plan_analysis": "<DETAILED coaching analysis (6-10 sentences). Include: \
1) Body composition assessment based on weight, activity, and goals. \
2) TDEE calculation breakdown (BMR × activity factor + exercise burn). \
3) Why you chose these specific macro ratios for their goals. \
4) How protein, carbs, and fats each support their training and recovery. \
5) Practical guidance on meal timing around workouts. \
6) What the athlete should focus on to achieve their goal. \
7) Any adjustments to watch for based on progress.>",
  "macro_targets": {{"calories": <num>, "protein_g": <num>, "carbs_g": <num>, \
"fat_g": <num>, "fiber_g": <num>}}
}}

Rules:
- TDEE: BMR (Mifflin-St Jeor) × activity factor, then apply goal adjustment
- Weight loss: ~500 kcal deficit, protein 1.6-2.2g/kg bodyweight
- Muscle gain: ~300-500 kcal surplus, protein 1.6-2.2g/kg bodyweight
- Maintain: match TDEE, protein 1.4-1.8g/kg bodyweight
- Body recomposition: slight deficit (~200 kcal), high protein 2.0-2.2g/kg
- Include exercise calorie burn from recent activity data
- Carbs: 3-7g/kg depending on training volume (higher for endurance athletes)
- Fat: minimum 0.8g/kg, typically 25-35% of calories
- Fiber: 25-35g/day"""

        saved = self._conversation
        self._conversation = [
            {"role": "system", "content": _DIET_SYSTEM_PROMPT},
            {"role": "user", "content": prompt},
        ]
        try:
            cache_key = AICache.make_key(
                _DIET_SYSTEM_PROMPT, prompt, self._model
            ) if self._cache else None
            reply = self._cached_chat(cache_key, ttl=TTL_DIET_PLAN)
        except Exception as e:
            logger.error("Macro plan generation failed: %s", e, exc_info=True)
            reply = _json.dumps({
                "plan_analysis": "Could not generate analysis. Please try again.",
                "macro_targets": {"calories": 2000, "protein_g": 120, "carbs_g": 250, "fat_g": 65, "fiber_g": 30},
            })
        finally:
            self._conversation = saved

        # Validate JSON
        try:
            parsed = _json.loads(reply)
        except _json.JSONDecodeError:
            from json_repair import loads as repair_loads
            parsed = repair_loads(reply)
            if not isinstance(parsed, dict):
                parsed = {
                    "plan_analysis": "Could not generate analysis. Please try again.",
                    "macro_targets": {"calories": 2000, "protein_g": 120, "carbs_g": 250, "fat_g": 65, "fiber_g": 30},
                }
        return _json.dumps(parsed)

    @staticmethod
    def _resolve_meal_types(meals_count: int) -> list[str]:
        """Return ordered meal type list for the given meal count."""
        meal_types = ["breakfast", "lunch", "dinner"]
        if meals_count >= 4:
            meal_types.insert(1, "morning_snack")
        if meals_count >= 5:
            meal_types.insert(3, "afternoon_snack")
        if meals_count >= 6:
            meal_types.append("evening_snack")
        return meal_types

    @staticmethod
    def _build_profile_context(
        diet_profile: dict,
        fitness_profile: UserFitnessProfile | None = None,
        activities: list[dict] | None = None,
        weight_history: list[dict] | None = None,
        training_plan: TrainingPlan | None = None,
    ) -> str:
        """Build shared athlete context string for diet AI calls."""
        lines: list[str] = []
        lines.append("## Diet Profile")
        goals = diet_profile.get("goals", [])
        lines.append(f"- Goals: {', '.join(goals) if goals else 'general health'}")
        if diet_profile.get("target_weight_kg"):
            lines.append(f"- Target weight: {diet_profile['target_weight_kg']} kg")
        lines.append(f"- Meals per day: {diet_profile.get('daily_meals_count', 3)}")
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

        if activities:
            total_cal = sum(a.get("calories") or 0 for a in activities)
            total_dur = sum(a.get("duration_seconds") or 0 for a in activities)
            days = max(1, len({str(a.get("start_time", ""))[:10] for a in activities}))
            lines.append(f"\n## Recent Activity ({len(activities)} sessions, last {days} active days)")
            lines.append(f"- Total calories burned: {total_cal}")
            lines.append(f"- Avg daily exercise calories: {total_cal // days}")
            lines.append(f"- Total training time: {total_dur // 60} min")

        if weight_history:
            lines.append("\n## Weight History")
            for w in weight_history[-10:]:
                bf = f" | Body fat: {w['body_fat_pct']}%" if w.get("body_fat_pct") else ""
                lines.append(f"- {w['date']}: {w['weight_kg']} kg{bf}")

        if training_plan:
            lines.append(f"\n## Training Plan: {training_plan.name}")
            lines.append(f"- Goal: {training_plan.goal_type}")
            if training_plan.target_date:
                lines.append(f"- Target race date: {training_plan.target_date}")
            lines.append(f"- Total weeks: {training_plan.total_weeks}")

        return "\n".join(lines)

    def _generate_single_day_meals(
        self,
        day_number: int,
        protein_focus: str,
        macro_targets: dict,
        meal_types: list[str],
        diet_profile: dict,
        used_meal_names: list[str],
        meal_size_instruction: str = "",
    ) -> dict:
        """AI call to generate one day's meals with variety enforcement."""
        import json as _json

        meals_count = len(meal_types)
        avoid_list = ", ".join(used_meal_names[-30:]) if used_meal_names else "none"

        preferred = diet_profile.get("preferred_foods", [])
        allergies = diet_profile.get("allergies", [])
        restrictions = diet_profile.get("restrictions", [])

        prompt = f"""Generate Day {day_number} meals for this athlete.

Daily macro targets: {macro_targets.get('calories', 2000)} cal, \
{macro_targets.get('protein_g', 120)}g protein, \
{macro_targets.get('carbs_g', 250)}g carbs, \
{macro_targets.get('fat_g', 65)}g fat, \
{macro_targets.get('fiber_g', 30)}g fiber.

PRIMARY PROTEIN for today: {protein_focus} — feature this in at least lunch or dinner.
{'Preferred foods: ' + ', '.join(preferred) if preferred else ''}
{'Allergies (AVOID): ' + ', '.join(allergies) if allergies else ''}
{'Restrictions: ' + ', '.join(restrictions) if restrictions else ''}

Meals already used on previous days (DO NOT repeat these): {avoid_list}

{meal_size_instruction}Create EXACTLY {meals_count} meals — one for each type: {', '.join(meal_types)}.
Keep each meal compact: 2-4 food items, 1-sentence recipe_notes.

Respond with ONLY valid JSON:
{{
  "day_number": {day_number},
  "meals": [
    {{"name": "<meal name>", "meal_type": "<type>", \
"foods": [{{"name": "<food>", "quantity": <num>, "unit": "<g/ml/pcs/tbsp/cup>", \
"calories": <num>, "protein_g": <num>, "carbs_g": <num>, "fat_g": <num>}}], \
"total_calories": <num>, "protein_g": <num>, "carbs_g": <num>, "fat_g": <num>, \
"fiber_g": <num>, "recipe_notes": "<brief prep notes>"}}
  ],
  "daily_totals": {{"calories": <num>, "protein_g": <num>, "carbs_g": <num>, \
"fat_g": <num>, "fiber_g": <num>}}
}}"""

        saved = self._conversation
        self._conversation = [
            {"role": "system", "content": _DIET_SYSTEM_PROMPT},
            {"role": "user", "content": prompt},
        ]
        try:
            cache_key = AICache.make_key(
                _DIET_SYSTEM_PROMPT, prompt, self._model
            ) if self._cache else None
            reply = self._cached_chat(cache_key, ttl=TTL_DIET_PLAN)
        except Exception as e:
            logger.error("Day %d meal generation failed: %s", day_number, e, exc_info=True)
            reply = f'{{"error": "Could not generate day {day_number}: {e}"}}'
        finally:
            self._conversation = saved

        try:
            return _json.loads(reply)
        except _json.JSONDecodeError:
            from json_repair import loads as repair_loads
            logger.warning("Day %d JSON parse failed, attempting repair", day_number)
            result = repair_loads(reply)
            return result if isinstance(result, dict) else {"day_number": day_number, "meals": [], "daily_totals": {}}

    def generate_single_meal(
        self,
        meal_type: str,
        current_meal_name: str,
        other_meals_today: list[str],
        macro_targets: dict,
        diet_profile: dict,
    ) -> str:
        """Generate a single replacement meal using AI.

        Returns a JSON string with one meal object.
        """
        preferred = diet_profile.get("preferred_foods", [])
        allergies = diet_profile.get("allergies", [])
        restrictions = diet_profile.get("restrictions", [])

        prompt = f"""Suggest an alternative {meal_type} meal that is DIFFERENT from "{current_meal_name}".

Daily macro targets: {macro_targets.get('calories', 2000)} cal, {macro_targets.get('protein_g', 120)}g protein, {macro_targets.get('carbs_g', 250)}g carbs, {macro_targets.get('fat_g', 70)}g fat.

Other meals today (do NOT repeat ingredients): {', '.join(other_meals_today) if other_meals_today else 'none yet'}.
{'Preferred foods: ' + ', '.join(preferred) if preferred else ''}
{'Allergies (AVOID): ' + ', '.join(allergies) if allergies else ''}
{'Restrictions: ' + ', '.join(restrictions) if restrictions else ''}

Respond with ONLY valid JSON for a single meal:
{{
  "name": "<meal name>",
  "meal_type": "{meal_type}",
  "foods": [
    {{"name": "<food>", "quantity": <number>, "unit": "<g/ml/pcs/tbsp/cup>", "calories": <number>, "protein_g": <number>, "carbs_g": <number>, "fat_g": <number>}}
  ],
  "total_calories": <number>,
  "protein_g": <number>,
  "carbs_g": <number>,
  "fat_g": <number>,
  "fiber_g": <number>,
  "recipe_notes": "<brief preparation notes>"
}}"""

        saved = self._conversation
        self._conversation = [
            {"role": "system", "content": _DIET_SYSTEM_PROMPT},
            {"role": "user", "content": prompt},
        ]
        try:
            reply = self._chat_openai_extended(max_tokens=2000, json_mode=True) if self._provider != "anthropic" else self._chat_anthropic()
        except Exception as e:
            logger.error("Single meal generation failed: %s", e, exc_info=True)
            reply = f'{{"error": "Could not generate meal: {e}"}}'
        self._conversation = saved
        return reply


_DIET_SYSTEM_PROMPT = """\
You are PaceForge Nutrition Coach — a registered dietitian, private chef, and \
sports nutritionist combined. Optimise for adherence first, perfection second.

## Philosophy
- Create meals a real person would actually cook and enjoy — restaurant-inspired, \
meal-prep friendly, and culturally aware.
- NEVER produce bland bodybuilding-style plans (plain chicken + rice + broccoli) \
unless the user explicitly requests it.
- Prioritise: nutritional adequacy > practicality > variety > enjoyment > budget.

## Methodology
Draw on evidence-based meal planning frameworks:
- Precision Nutrition: habit-based coaching, portion hand method, whole-food emphasis
- RP Strength: body composition meal structuring, protein distribution across meals
- Eat This Much: automated meal variety patterns, realistic portion combinations
- Academy of Nutrition and Dietetics: evidence-based nutrition principles
- Cronometer: micronutrient adequacy awareness (iron, calcium, B12, omega-3)
- Noom: behavioural adherence — meals people actually look forward to eating
- WW International: sustainable, non-restrictive approaches
- PlateJoy: personalised lifestyle-aware planning
- Lifesum: lifestyle-matched meal timing
- MyFitnessPal: accurate calorie/macronutrient targeting

## Meal Quality Rules
Every main meal (breakfast, lunch, dinner) MUST:
✅ Include a quality protein source (lean meat, fish, eggs, legumes, dairy, tofu)
✅ Include at least one fruit or vegetable
✅ Include a fibre-rich component
✅ Use healthy fats (olive oil, avocado, nuts, seeds — not excessive butter/cream)
✅ Be realistic for a normal kitchen (no exotic/hard-to-find ingredients)
✅ Feel like something from a healthy cookbook or restaurant menu

Snacks MUST be simple, satisfying combinations (2-3 items max).

## Meal Structure Templates
BREAKFAST — choose from these patterns:
- Eggs + toast/avocado + fruit side
- Oatmeal/porridge + fruit + nuts/seeds (NO meat in oatmeal)
- Greek yogurt + granola + berries
- Smoothie bowl with protein
- Pancakes/waffles + fruit + maple syrup
- Smoked salmon + bagel/toast + cream cheese
- Breakfast burrito/wrap with eggs + vegetables

LUNCH — protein + grain/bread + vegetables:
- Salad bowl with protein (chicken, tuna, salmon, falafel, tofu)
- Wrap or sandwich with protein + vegetables
- Grain bowl (quinoa, rice, couscous) with roasted vegetables + protein
- Soup + crusty bread (lentil, chicken, minestrone)
- Stir-fry with rice or noodles

DINNER — protein + starch + cooked vegetables:
- Grilled/baked protein + roasted potatoes/sweet potato + steamed vegetables
- Pasta with protein-rich sauce (bolognese, pesto chicken, shrimp)
- Curry/stew with rice (chicken tikka, lentil dal, beef stew)
- Tacos/fajitas with protein + toppings
- Stir-fry with rice or noodles

SNACKS — simple 2-3 item combinations:
- Fruit + nut butter (apple + almond butter, banana + peanut butter)
- Yogurt + berries/granola
- Hummus + vegetable sticks (carrots, cucumbers, bell pepper)
- Trail mix (nuts, seeds, dried fruit)
- Cottage cheese + fruit
- Rice cakes + avocado or cheese
- Hard-boiled eggs + cherry tomatoes

## Flavour Coherence (CRITICAL)
All items within a single meal MUST share a coherent cuisine or flavour profile.
NEVER combine:
❌ Meat or fish with breakfast cereals or oatmeal
❌ Dessert toppings (chocolate, syrup) with savory proteins
❌ Raw fruit mixed into cooked savory meat dishes
❌ Incompatible cuisines in one meal (e.g. soy sauce + Italian cheese)
If unsure whether foods pair well, imagine serving it in a restaurant — if it \
would be strange on a menu, do not combine them.

## Smart Personalisation
- High training volume → emphasise pre/post workout carbs + protein timing
- Fat loss goal → prioritise high-satiety foods (high protein, high fibre, \
high volume, low calorie density)
- Muscle gain goal → ensure protein spread across ALL meals (not front-loaded)
- If restrictions present → use real culinary alternatives, not just "remove ingredient"
- Prefer overlapping ingredients across days to reduce grocery waste

## Reference Meal Inspiration
Use these as starting points — vary and adapt, do not copy verbatim:
Breakfast: Scrambled eggs with whole wheat toast and avocado, Overnight oats \
with berries and chia seeds, Greek yogurt parfait with granola and honey, \
Veggie omelette with side fruit, Banana pancakes with maple syrup, Smoked \
salmon bagel with cream cheese, Açaí smoothie bowl with granola, Breakfast \
burrito with eggs and black beans
Lunch: Grilled chicken Caesar salad, Turkey and avocado wrap, Quinoa bowl \
with roasted vegetables and feta, Tuna Niçoise salad, Chicken tikka with \
basmati rice, Mediterranean falafel bowl, Thai peanut noodle salad, Lentil \
soup with crusty bread
Dinner: Pan-seared salmon with sweet potato and asparagus, Chicken stir-fry \
with vegetables and jasmine rice, Beef bolognese with whole wheat pasta, Baked \
cod with roasted potatoes and greens, Turkey meatballs with marinara and \
spaghetti, Shrimp tacos with cabbage slaw, Lamb chops with couscous and \
roasted vegetables, Tofu curry with jasmine rice
Snacks: Apple slices with almond butter, Greek yogurt with mixed berries, \
Hummus with carrot and cucumber sticks, Trail mix with nuts and dried fruit, \
Cottage cheese with pineapple, Rice cakes with avocado, Hard-boiled eggs with \
cherry tomatoes, Banana with peanut butter

## Safety Rules
- Never recommend fewer than 1200 kcal/day for women or 1500 kcal/day for men
- Never suggest eliminating entire macronutrient groups
- Always recommend consulting a dietitian for medical dietary needs
- Flag potential nutrient deficiencies in restrictive diets
- Suggest gradual calorie adjustments (max 500 kcal deficit/surplus)

## Output Format
You respond ONLY with valid JSON — no markdown fences, no extra text. \
All explanations go inside the JSON "plan_analysis" field.
"""
