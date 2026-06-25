"""Tests for running-engine & durability metrics (engine/durability.py)."""

from __future__ import annotations

from datetime import datetime, timedelta

from paceforge.engine.durability import compute_running_metrics
from paceforge.models.profile import RecentActivity, UserFitnessProfile

_BASE = datetime(2026, 6, 1, 7, 0, 0)


def _run(activity_id: int, days: int = 0, **kw) -> RecentActivity:
    defaults = dict(
        name="run",
        activity_type="running",
        start_time=_BASE + timedelta(days=days),
        distance_meters=10000.0,
        duration_seconds=3000.0,
    )
    defaults.update(kw)
    return RecentActivity(activity_id=activity_id, **defaults)


def _profile(**kw) -> UserFitnessProfile:
    defaults = dict(max_hr=190, resting_hr=50, lactate_threshold_speed=4.0)
    defaults.update(kw)
    return UserFitnessProfile(**defaults)


def _steady_series(n: int, pace: float, hr_first: int, hr_second: int) -> list[dict]:
    """Series with constant pace, HR drifting upward in the second half (decoupling)."""
    out = []
    for i in range(n):
        hr = hr_first if i < n // 2 else hr_second
        out.append({"t": i * 10, "hr": hr, "pace": pace})
    return out


# ── efficiency factor ──────────────────────────────────────────────────


def test_ef_trend_is_positive_when_speed_rises_over_time():
    # Two easy runs, the later one faster at the same HR => EF improving.
    runs = [
        _run(1, days=0, distance_meters=10000, duration_seconds=3000, avg_hr=140),
        _run(2, days=14, distance_meters=11000, duration_seconds=3000, avg_hr=140),
    ]
    out = compute_running_metrics(runs, {}, _profile())
    assert out["efficiency_factor"]["trend_per_week"] > 0


def test_ef_excludes_hard_runs_above_easy_cap():
    # avg_hr 180 > 0.80*190=152 => excluded; only the easy run counts.
    runs = [
        _run(1, days=0, avg_hr=140),
        _run(2, days=5, avg_hr=180),
    ]
    out = compute_running_metrics(runs, {}, _profile())
    assert out["efficiency_factor"]["n"] == 1


# ── decoupling ─────────────────────────────────────────────────────────


def test_decoupling_positive_when_hr_drifts_up_second_half():
    # speed constant, HR up in 2nd half => EF2 < EF1 => positive decoupling.
    details = {1: {"activity_id": 1, "series": _steady_series(40, pace=300.0, hr_first=150, hr_second=165)}}
    runs = [_run(1, duration_seconds=2400)]
    out = compute_running_metrics(runs, details, _profile())
    d = out["decoupling"]
    assert d["available"] and d["latest_pct"] > 0


def test_decoupling_skips_high_variance_interval_runs():
    series = [{"t": i * 10, "hr": 150, "pace": 200.0 if i % 2 else 400.0} for i in range(40)]
    details = {1: {"activity_id": 1, "series": series}}
    runs = [_run(1, duration_seconds=2400)]
    out = compute_running_metrics(runs, details, _profile())
    assert out["decoupling"]["available"] is False


# ── compromised run (fade) ─────────────────────────────────────────────


def test_compromised_fade_is_positive_when_late_splits_slower():
    splits = [
        {"n": 1, "pace_sec": 300.0},
        {"n": 2, "pace_sec": 305.0},
        {"n": 3, "pace_sec": 320.0},
        {"n": 4, "pace_sec": 330.0},
    ]
    details = {1: {"activity_id": 1, "splits": splits}}
    out = compute_running_metrics([_run(1)], details, _profile())
    c = out["compromised_run"]
    assert c["available"] and c["mean_fade_pct"] == 10.0  # (330-300)/300*100


# ── critical speed ─────────────────────────────────────────────────────


def test_critical_speed_recovers_known_cs():
    # Construct efforts on the line distance = 4.0*t + 50 (CS=4 m/s, D'=50 m).
    cs_true, dprime_true = 4.0, 50.0
    runs = []
    for i, t in enumerate((180, 360, 720, 1200)):
        dist = cs_true * t + dprime_true
        runs.append(_run(i + 1, days=i, distance_meters=dist, duration_seconds=t, avg_hr=140))
    out = compute_running_metrics(runs, {}, _profile())
    cs = out["critical_speed"]
    assert cs["available"] and abs(cs["cs_mps"] - 4.0) < 0.01
    assert cs["confidence"] == "high" and cs["r2"] > 0.99


def test_critical_power_fits_when_power_present():
    # work = CP*t + W' with CP=250 W, W'=20000 J  => avg_power = CP + W'/t.
    cp, wprime = 250.0, 20000.0
    runs = []
    for i, t in enumerate((180, 360, 720)):
        power = cp + wprime / t
        runs.append(_run(i + 1, days=i, duration_seconds=t, avg_power=power, avg_hr=140))
    out = compute_running_metrics(runs, {}, _profile())
    cs = out["critical_speed"]
    assert cs["cp_available"] and abs(cs["cp_watts"] - 250.0) < 1.0


# ── HRR ────────────────────────────────────────────────────────────────


def test_hrr_detects_recovery_60s_after_peak():
    # peak 180 at t=100, then 150 at t=160 (60s later) => HRR60 = 30.
    series = [
        {"t": 0, "hr": 120},
        {"t": 100, "hr": 180},
        {"t": 160, "hr": 150},
        {"t": 220, "hr": 140},
    ]
    details = {1: {"activity_id": 1, "series": series}}
    out = compute_running_metrics([_run(1)], details, _profile())
    h = out["hrr"]
    assert h["available"] and h["best_hrr60"] == 30.0 and h["grade"] == "moderate"


# ── intensity distribution ─────────────────────────────────────────────


def test_intensity_distribution_percentages_sum_and_split():
    # 80% low (Z1-2), 5% mid (Z3), 15% high (Z4-5).
    details = {
        1: {
            "activity_id": 1,
            "hr_zones": [
                {"zone": 1, "secs": 4000},
                {"zone": 2, "secs": 4000},
                {"zone": 3, "secs": 500},
                {"zone": 4, "secs": 1000},
                {"zone": 5, "secs": 500},
            ],
        }
    }
    runs = [_run(1, days=0)]
    out = compute_running_metrics(runs, details, _profile())
    i = out["intensity_distribution"]
    assert i["low_pct"] == 80.0 and i["mid_pct"] == 5.0 and i["high_pct"] == 15.0
    assert i["grade"] == "polarized"


# ── pacing ─────────────────────────────────────────────────────────────


def test_pacing_negative_split_tendency():
    # second half faster (lower pace_sec) => ratio < 1 => negative.
    splits = [
        {"n": 1, "pace_sec": 320.0},
        {"n": 2, "pace_sec": 320.0},
        {"n": 3, "pace_sec": 300.0},
        {"n": 4, "pace_sec": 300.0},
    ]
    details = {1: {"activity_id": 1, "splits": splits}}
    out = compute_running_metrics([_run(1)], details, _profile())
    p = out["pacing"]
    assert p["tendency"] == "negative" and p["mean_ratio"] < 1.0


# ── vVO2max ────────────────────────────────────────────────────────────


def test_vvo2max_falls_back_to_lactate_threshold():
    out = compute_running_metrics([_run(1)], {}, _profile(lactate_threshold_speed=4.0))
    v = out["vvo2max"]
    assert v["available"] and v["source"] == "estimated_from_lt"
    assert abs(v["vvo2max_mps"] - 4.48) < 0.01  # 4.0 * 1.12


# ── economy vs pace ────────────────────────────────────────────────────


def test_economy_cadence_grade_and_current():
    runs = [
        _run(1, days=0, avg_running_cadence=170, avg_pace_sec_per_km=300),
        _run(2, days=5, avg_running_cadence=172, avg_pace_sec_per_km=290),
    ]
    out = compute_running_metrics(runs, {}, _profile())
    cad = out["economy_vs_pace"]["cadence"]
    assert cad["available"] and cad["current"] == 172.0 and cad["grade"] == "ok"


# ── graceful empty ─────────────────────────────────────────────────────


def test_no_details_does_not_crash_and_sets_flags():
    out = compute_running_metrics([_run(1)], {}, _profile())
    assert out["decoupling"]["available"] is False
    assert out["hrr"]["available"] is False
    assert out["intensity_distribution"]["available"] is False


def test_empty_inputs_return_full_schema():
    out = compute_running_metrics([], {}, _profile())
    for key in (
        "efficiency_factor",
        "decoupling",
        "compromised_run",
        "critical_speed",
        "hrr",
        "intensity_distribution",
        "pacing",
        "vvo2max",
        "economy_vs_pace",
        "headline",
    ):
        assert key in out


def test_non_run_activities_are_ignored():
    strength = _run(1, activity_type="strength_training", avg_hr=140)
    out = compute_running_metrics([strength], {}, _profile())
    assert out["efficiency_factor"]["n"] == 0
