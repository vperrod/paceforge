"""Limiter-ranking engine — synthesis of the metric dicts into prioritized actions."""
from paceforge.engine.limiters import rank_limiters


def test_empty_inputs_do_not_crash():
    out = rank_limiters({}, {}, {})
    assert out["limiters"] == [] and "coach_input" in out


def test_decoupling_gap_is_flagged():
    running = {"decoupling": {"available": True, "average_pct": 14.0}}
    out = rank_limiters(running, {}, {})
    assert any(l["area"] == "durability" for l in out["limiters"])


def test_grey_zone_distribution_flagged():
    running = {"intensity_distribution": {"availability": "ok", "available": True,
                                          "adherence": "too_hard", "low_pct": 30, "mid_pct": 58}}
    out = rank_limiters(running, {}, {})
    assert any(l["area"] == "distribution" for l in out["limiters"])


def test_weak_stations_flagged():
    strength = {"station_percentiles": {"available": True, "weakest": ["Row_1000m", "Wall_Balls"]}}
    out = rank_limiters({}, {}, strength)
    assert any(l["area"] == "strength" for l in out["limiters"])


def test_readiness_red_makes_recovery_the_top_limiter():
    load = {"readiness_composite": {"score": 30, "band": "low"},
            "overtraining_composite": {"level": "deload"}}
    running = {"decoupling": {"available": True, "average_pct": 18.0}}  # a fitness gap exists too
    out = rank_limiters(running, load, strength={})
    assert out["limiters"][0]["area"] == "recovery"


def test_caps_at_three_limiters():
    running = {
        "decoupling": {"available": True, "average_pct": 14.0},
        "intensity_distribution": {"available": True, "adherence": "too_hard", "low_pct": 30, "mid_pct": 58},
        "compromised_run": {"mean_fade_pct": 20.0},
        "pacing": {"available": True, "tendency": "positive", "mean_ratio": 1.05},
    }
    out = rank_limiters(running, {}, {})
    assert len(out["limiters"]) == 3


def test_coach_input_carries_data_gaps():
    strength = {"data_gaps": ["no strength benchmarks", "no bodyweight"]}
    out = rank_limiters({}, {}, strength)
    assert out["coach_input"]["data_gaps"] == ["no strength benchmarks", "no bodyweight"]
