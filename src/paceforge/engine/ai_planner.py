"""AI Plan Architect — uses LLM to design fully personalised training plans.

The architect analyses the athlete's profile, computed paces, and goal, then produces
a complete plan with detailed per-day workout specifications. Each workout includes
structured steps with specific paces, distances, and coaching rationale.

Supports both OpenAI and Anthropic (Claude) as LLM providers.
"""

from __future__ import annotations

import json
import logging
from dataclasses import dataclass

from paceforge.ai.cache import TTL_PLAN_GENERATION, AICache
from paceforge.engine.vdot import TrainingPaces
from paceforge.models.profile import TrainingGoal, UserFitnessProfile

logger = logging.getLogger(__name__)


SYSTEM_PROMPT = """\
You are PaceForge Plan Architect, an expert running coach who creates fully personalised \
training plans with detailed daily workouts. You design every single workout with specific \
paces, distances, durations, and coaching notes — never generic or repetitive.

## Your expertise
- Jack Daniels' Running Formula (VDOT-based training zones)
- Pfitzinger/Douglas periodization principles
- Hal Higdon's accessible frameworks for beginners
- Hyrox-specific hybrid run/fitness programming

## Design principles
1. **Progressive overload** with cutback weeks every 3-4 weeks (reduce volume 20-30%)
2. **Phase periodization**: Base → Build → Peak → Taper → Race
3. **VARIETY is critical**: No two weeks should have identical workout structures. Vary:
   - Interval distances (200m, 400m, 800m, 1000m, 1200m, 1600m, 2000m)
   - Tempo durations (20min, 25min, 30min, 35min steady-state)
   - Long run styles (easy, progressive, with race-pace insertions, negative split)
   - Recovery types (easy jog, cross-training, active recovery)
   - Quality session types (cruise intervals, tempo, fartlek, hill repeats, VO2max, speed work)
4. **Individualisation**: use the athlete's EXACT paces provided — never invent paces
5. **Coaching notes**: every workout should have a specific coaching note explaining the purpose and feel
6. **Rest placement**: hard days should never be back-to-back; easy/rest days buffer quality sessions

## Workout types (use these exact values)
easy_run, long_run, tempo, intervals, recovery_run, threshold, race_pace, fartlek, \
hills, strides, speed, vo2max, easy_with_strides, long_run_progressive, \
long_run_with_race_pace, progressive, rest

## Step types (use these exact values)
warmup, cooldown, interval, recovery, active, rest

## Output format
Return ONLY valid JSON (no markdown fences) with this structure:
{
  "plan_name": "Goal — Level",
  "total_weeks": <number>,
  "rationale": "2-4 sentences explaining why this specific plan structure suits this athlete",
  "tips": ["tip1", "tip2", "tip3", "tip4", "tip5"],
  "weeks": [
    {
      "week_number": 1,
      "phase": "Base",
      "focus": "Building aerobic foundation with easy volume",
      "workouts": [
        {
          "day": "monday",
          "workout_type": "easy_run",
          "name": "Easy Aerobic Run",
          "purpose": "aerobic_base",
          "estimated_distance_km": 8.0,
          "estimated_duration_minutes": 45,
          "notes": "Keep this truly easy — you should be able to hold a full conversation. This builds your aerobic engine.",
          "steps": [
            {"step_type": "active", "description": "Easy run", "distance_km": 8.0, "pace_zone": "easy"}
          ]
        },
        {
          "day": "tuesday",
          "workout_type": "rest",
          "name": "Rest Day",
          "notes": "Full rest or light walking. Recovery is when adaptation happens."
        },
        {
          "day": "wednesday",
          "workout_type": "intervals",
          "name": "VO2max Intervals — 5×1000m",
          "purpose": "vo2max",
          "estimated_distance_km": 10.0,
          "estimated_duration_minutes": 50,
          "notes": "These should feel hard but controlled. You're building your oxygen processing capacity.",
          "steps": [
            {"step_type": "warmup", "description": "Easy warmup jog", "duration_minutes": 10, "pace_zone": "easy"},
            {"step_type": "interval", "description": "1000m hard", "distance_km": 1.0, "pace_zone": "interval", "repeat_count": 5},
            {"step_type": "recovery", "description": "400m recovery jog", "distance_km": 0.4, "pace_zone": "easy"},
            {"step_type": "cooldown", "description": "Easy cooldown", "duration_minutes": 10, "pace_zone": "easy"}
          ]
        }
      ]
    }
  ]
}

## Pace zones (use the athlete's exact paces provided in the context)
- "easy": Easy/recovery pace
- "marathon": Marathon goal pace
- "threshold": Lactate threshold pace
- "interval": VO2max interval pace (3-5min efforts)
- "repetition": Short repetition pace (<90sec efforts)

## CRITICAL RULES
1. volume_pct is NOT needed — specify exact distances in km for each workout
2. EVERY workout (except rest) MUST have a steps array with structured steps
3. Use the EXACT paces provided — do not invent different paces
4. Each week MUST have different workout combinations — no copy-paste weeks
5. Include coaching notes that are specific and motivating, not generic
6. Cutback weeks should reduce DISTANCE not eliminate quality — keep 1 quality session but shorter
"""


@dataclass
class PlanBlueprint:
    """Structured plan blueprint from the AI architect."""
    plan_name: str
    total_weeks: int
    rationale: str
    tips: list[str]
    weeks: list[dict]
    raw_json: dict


def _fmt_pace(sec_per_km: float) -> str:
    """Format seconds-per-km as M:SS."""
    m, s = divmod(int(sec_per_km), 60)
    return f"{m}:{s:02d}"


def _build_athlete_context(
    profile: UserFitnessProfile,
    goal: TrainingGoal,
    paces: TrainingPaces | None = None,
) -> str:
    """Build a concise athlete summary for the LLM prompt, including computed paces."""
    lines = ["## Athlete Profile"]

    if profile.vo2_max:
        lines.append(f"- VO2 Max: {profile.vo2_max}")
    if profile.resting_hr:
        lines.append(f"- Resting HR: {profile.resting_hr} bpm")
    if profile.max_hr:
        lines.append(f"- Max HR: {profile.max_hr} bpm")
    if profile.weekly_mileage_km:
        lines.append(f"- Current weekly mileage: {profile.weekly_mileage_km:.1f} km")
    if profile.training_readiness:
        lines.append(f"- Training readiness: {profile.training_readiness}")
    if profile.training_status:
        lines.append(f"- Training status: {profile.training_status}")
    if profile.hrv_status:
        lines.append(f"- HRV status: {profile.hrv_status}")
    if profile.hrv_last_night:
        lines.append(f"- HRV last night: {profile.hrv_last_night} ms")
    if profile.lactate_threshold_hr:
        lines.append(f"- Lactate threshold HR: {profile.lactate_threshold_hr:.0f} bpm")
    if profile.endurance_score:
        lines.append(f"- Endurance score: {profile.endurance_score}")
    if profile.weight_kg:
        lines.append(f"- Weight: {profile.weight_kg} kg")

    if profile.personal_records:
        lines.append("- Personal records:")
        for pr in profile.personal_records:
            mins, secs = divmod(int(pr.time_seconds), 60)
            hrs, mins = divmod(mins, 60)
            time_str = f"{hrs}:{mins:02d}:{secs:02d}" if hrs else f"{mins}:{secs:02d}"
            lines.append(f"  - {pr.distance}: {time_str}")

    if profile.race_predictions:
        lines.append("- Garmin race predictions:")
        for rp in profile.race_predictions:
            mins, secs = divmod(int(rp.predicted_seconds), 60)
            hrs, mins = divmod(mins, 60)
            time_str = f"{hrs}:{mins:02d}:{secs:02d}" if hrs else f"{mins}:{secs:02d}"
            lines.append(f"  - {rp.distance}: {time_str}")

    running = [a for a in profile.recent_activities if a.avg_pace_sec_per_km]
    if running:
        avg_dist = sum(a.distance_meters for a in running) / len(running) / 1000
        avg_pace = sum(a.avg_pace_sec_per_km for a in running if a.avg_pace_sec_per_km) / len(running)
        lines.append(f"- Recent runs: {len(running)} activities, avg {avg_dist:.1f}km @ {_fmt_pace(avg_pace)}/km")
        longest = max(running, key=lambda a: a.distance_meters)
        lines.append(f"- Longest recent run: {longest.distance_meters / 1000:.1f}km")

    # CRITICAL: provide computed paces so AI uses exact values
    if paces:
        lines.append("")
        lines.append("## Computed Training Paces (use these EXACTLY)")
        lines.append(f"- VDOT: {paces.vdot:.1f}")
        lines.append(f"- Easy pace: {_fmt_pace(paces.easy_low)}-{_fmt_pace(paces.easy_high)}/km")
        lines.append(f"- Marathon pace: {_fmt_pace(paces.marathon)}/km")
        lines.append(f"- Threshold pace: {_fmt_pace(paces.threshold)}/km")
        lines.append(f"- Interval pace: {_fmt_pace(paces.interval)}/km")
        lines.append(f"- Repetition pace: {_fmt_pace(paces.repetition)}/km")

    lines.append("")
    lines.append("## Training Goal")
    lines.append(f"- Goal: {goal.goal_type.value}")
    lines.append(f"- Race date: {goal.target_date}")
    if goal.target_time_seconds:
        mins, secs = divmod(int(goal.target_time_seconds), 60)
        hrs, mins = divmod(mins, 60)
        time_str = f"{hrs}:{mins:02d}:{secs:02d}" if hrs else f"{mins}:{secs:02d}"
        lines.append(f"- Target time: {time_str}")
    if goal.experience_level:
        lines.append(f"- Experience: {goal.experience_level.value}")
    if goal.start_date:
        lines.append(f"- Plan start date: {goal.start_date}")
        weeks_available = (goal.target_date - goal.start_date).days // 7
        lines.append(f"- Available weeks: {weeks_available}")
    lines.append(f"- Training days: {', '.join(goal.training_days)}")
    lines.append(f"- Long run day: {goal.long_run_day}")

    return "\n".join(lines)


def generate_blueprint(
    profile: UserFitnessProfile,
    goal: TrainingGoal,
    *,
    api_key: str,
    model: str = "gpt-4o-mini",
    provider: str = "openai",
    paces: TrainingPaces | None = None,
    cache: AICache | None = None,
) -> PlanBlueprint:
    """Call the LLM to generate a fully detailed plan blueprint.

    Args:
        provider: "openai" or "anthropic"
        paces: Computed training paces to include in context

    Raises ValueError if the LLM response cannot be parsed.
    """
    athlete_context = _build_athlete_context(profile, goal, paces=paces)

    logger.info(
        "Requesting full AI plan for %s %s via %s/%s",
        goal.goal_type.value, goal.experience_level, provider, model,
    )

    raw_text = None
    last_error = None
    for attempt in range(3):
        try:
            if provider == "anthropic":
                raw_text = _call_anthropic(api_key, model, athlete_context, cache=cache)
            else:
                raw_text = _call_openai(api_key, model, athlete_context, cache=cache)

            data = _parse_blueprint_json(raw_text)
            if data is not None:
                break
            last_error = "AI plan missing 'weeks' array"
            logger.warning("Attempt %d: %s — retrying", attempt + 1, last_error)
        except json.JSONDecodeError as e:
            last_error = f"AI returned invalid JSON: {e}"
            logger.warning("Attempt %d: %s — retrying", attempt + 1, last_error)
        except Exception:
            raise
    else:
        logger.error("AI plan failed after retries: %s\nRaw: %s", last_error, (raw_text or "")[:500])
        raise ValueError(last_error or "AI plan generation failed")

    return PlanBlueprint(
        plan_name=data.get("plan_name", f"{goal.goal_type.value} Plan"),
        total_weeks=data.get("total_weeks", len(data["weeks"])),
        rationale=data.get("rationale", ""),
        tips=data.get("tips", []),
        weeks=data["weeks"],
        raw_json=data,
    )


def _parse_blueprint_json(raw_text: str) -> dict | None:
    """Parse the AI blueprint response, handling various LLM output quirks.

    Returns the parsed dict with a valid 'weeks' array, or None if unusable.
    """
    # Strip markdown code fences if present
    text = raw_text.strip()
    if text.startswith("```"):
        lines = text.splitlines()
        end = len(lines) - 1 if lines[-1].strip() == "```" else len(lines)
        text = "\n".join(lines[1:end])

    # Try to extract JSON from text that may have surrounding prose
    json_start = text.find("{")
    json_end = text.rfind("}")
    if json_start >= 0 and json_end > json_start:
        text = text[json_start:json_end + 1]

    data = json.loads(text)

    # Handle nested structure — LLM might wrap in {"plan": {..., "weeks": [...]}}
    if "weeks" not in data:
        # Check for common alternate keys wrapping the weeks
        for key in ("plan", "training_plan", "blueprint"):
            if key in data and isinstance(data[key], dict) and "weeks" in data[key]:
                inner = data.pop(key)
                data.update(inner)
                break
        # Check if weeks are under a different name
        for key in ("schedule", "training_weeks", "week_plan", "phases"):
            if key in data and isinstance(data[key], list):
                data["weeks"] = data.pop(key)
                break

    # If still no weeks, search any list value that looks like weekly data
    if "weeks" not in data:
        for key, val in data.items():
            if isinstance(val, list) and len(val) > 0 and isinstance(val[0], dict):
                if any(k in val[0] for k in ("phase", "volume_pct", "focus", "week", "week_number")):
                    data["weeks"] = val
                    break

    # Normalize week entries: accept "week" as alias for "week_number"
    if "weeks" in data and isinstance(data["weeks"], list):
        for w in data["weeks"]:
            if "week_number" not in w and "week" in w:
                w["week_number"] = w.pop("week")

    # Infer total_weeks if missing
    if "total_weeks" not in data and "weeks" in data:
        data["total_weeks"] = len(data["weeks"])

    # Infer plan_name if missing
    if "plan_name" not in data:
        data["plan_name"] = data.get("name", data.get("title", "Training Plan"))

    if "weeks" not in data or not isinstance(data["weeks"], list) or len(data["weeks"]) == 0:
        return None

    return data

def _call_openai(api_key: str, model: str, athlete_context: str, cache: AICache | None = None) -> str:
    """Call OpenAI chat completions API with optional caching."""
    cache_key = AICache.make_key(SYSTEM_PROMPT, athlete_context, model) if cache else None
    if cache_key and cache:
        cached = cache.get(cache_key)
        if cached is not None:
            logger.info("AI plan cache hit")
            return cached

    from openai import OpenAI

    client = OpenAI(api_key=api_key)
    response = client.chat.completions.create(
        model=model,
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": athlete_context},
        ],
        response_format={"type": "json_object"},
        temperature=0.7,
        max_tokens=16000,
    )
    raw = response.choices[0].message.content or "{}"

    if cache_key and cache:
        cache.set(cache_key, raw, model=model, ttl_seconds=TTL_PLAN_GENERATION)

    return raw


def _call_anthropic(api_key: str, model: str, athlete_context: str, cache: AICache | None = None) -> str:
    """Call Anthropic Messages API with optional caching."""
    cache_key = AICache.make_key(SYSTEM_PROMPT, athlete_context, model) if cache else None
    if cache_key and cache:
        cached = cache.get(cache_key)
        if cached is not None:
            logger.info("AI plan cache hit")
            return cached

    import anthropic

    client = anthropic.Anthropic(api_key=api_key)
    # Prompt caching: 90% input token discount on repeated system prompts
    system_with_cache = [
        {"type": "text", "text": SYSTEM_PROMPT, "cache_control": {"type": "ephemeral"}},
    ]
    response = client.messages.create(
        model=model,
        max_tokens=16000,
        system=system_with_cache,
        messages=[{"role": "user", "content": athlete_context}],
        temperature=0.7,
    )
    raw = response.content[0].text

    if cache_key and cache:
        cache.set(cache_key, raw, model=model, ttl_seconds=TTL_PLAN_GENERATION)

    return raw
