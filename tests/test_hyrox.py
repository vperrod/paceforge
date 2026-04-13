"""Tests for HYROX scraper parsing and analyzer computations."""

from __future__ import annotations

import pytest

from paceforge.hyrox.models import HyroxCachedData, HyroxRaceResult, HyroxSplit
from paceforge.hyrox.scraper import _seconds_to_display, _time_to_seconds

# ── Time conversion tests ──────────────────────────────────────────


class TestTimeToSeconds:
    def test_mm_ss(self):
        assert _time_to_seconds("05:30") == 330.0

    def test_hh_mm_ss(self):
        assert _time_to_seconds("1:23:45") == 5025.0

    def test_mm_ss_fractional(self):
        result = _time_to_seconds("59:06.59")
        assert result == pytest.approx(59 * 60 + 6 + 0.59, abs=0.01)

    def test_na_returns_none(self):
        assert _time_to_seconds("N/A") is None
        assert _time_to_seconds("–") is None
        assert _time_to_seconds("-") is None
        assert _time_to_seconds("") is None
        assert _time_to_seconds("00.00") is None

    def test_none_returns_none(self):
        assert _time_to_seconds(None) is None

    def test_seconds_display_roundtrip(self):
        assert _seconds_to_display(3600 + 23 * 60 + 45) == "1:23:45"
        assert _seconds_to_display(330) == "5:30"
        assert _seconds_to_display(None) == "—"


# ── Model tests ────────────────────────────────────────────────────


class TestHyroxModels:
    def test_race_result_defaults(self):
        r = HyroxRaceResult()
        assert r.rank == ""
        assert r.splits == []
        assert r.total_time_seconds is None

    def test_split_creation(self):
        s = HyroxSplit(name="Running_1", time_seconds=320.5)
        assert s.name == "Running_1"
        assert s.time_seconds == 320.5

    def test_cached_data_model(self):
        data = HyroxCachedData(
            search_name="McIntyre",
            search_gender="M",
            results=[
                HyroxRaceResult(
                    name="McIntyre, Hunter",
                    rank="1",
                    city="Stockholm 2023",
                    total_time_seconds=3202.0,
                    splits=[HyroxSplit(name="Running_1", time_seconds=280.0)],
                ),
            ],
        )
        assert data.search_name == "McIntyre"
        assert len(data.results) == 1
        # Roundtrip via JSON
        dumped = data.model_dump_json()
        restored = HyroxCachedData.model_validate_json(dumped)
        assert restored.results[0].name == "McIntyre, Hunter"
        assert restored.results[0].splits[0].time_seconds == 280.0


# ── Analyzer tests ─────────────────────────────────────────────────


class TestAnalyzer:
    @pytest.fixture()
    def sample_race(self):
        """A sample HYROX race with all splits filled in."""
        splits = [
            HyroxSplit(name="Running_1", time_seconds=310),
            HyroxSplit(name="SkiErg_1000m", time_seconds=240),
            HyroxSplit(name="Running_2", time_seconds=320),
            HyroxSplit(name="Sled_Push_50m", time_seconds=160),
            HyroxSplit(name="Running_3", time_seconds=325),
            HyroxSplit(name="Sled_Pull_50m", time_seconds=180),
            HyroxSplit(name="Running_4", time_seconds=330),
            HyroxSplit(name="Burpee_Broad_Jump_80m", time_seconds=200),
            HyroxSplit(name="Running_5", time_seconds=335),
            HyroxSplit(name="Row_1000m", time_seconds=230),
            HyroxSplit(name="Running_6", time_seconds=340),
            HyroxSplit(name="Farmers_Carry_200m", time_seconds=130),
            HyroxSplit(name="Running_7", time_seconds=350),
            HyroxSplit(name="Sandbag_Lunges_100m", time_seconds=180),
            HyroxSplit(name="Running_8", time_seconds=360),
            HyroxSplit(name="Wall_Balls", time_seconds=240),
            HyroxSplit(name="Roxzone_Time", time_seconds=120),
        ]
        return HyroxRaceResult(
            name="Test Athlete",
            rank="42",
            city="TestCity 2025",
            total_time_seconds=4530,
            total_time_display="1:15:30",
            splits=splits,
        )

    def test_analyze_race(self, sample_race):
        from paceforge.hyrox.analyzer import analyze_race

        result = analyze_race(sample_race)
        assert result["total_running"] == 310 + 320 + 325 + 330 + 335 + 340 + 350 + 360
        assert result["fade_pct"] > 0  # Last run > first run
        assert result["running_class"] in ("Strong Compromised Runner", "Moderate Drop-off", "Severe Fade")
        assert len(result["split_analysis"]) > 0
        assert result["running_pct"] > 0
        assert result["station_pct"] > 0

    def test_training_priorities(self, sample_race):
        from paceforge.hyrox.analyzer import compute_training_priorities

        priorities = compute_training_priorities(sample_race)
        assert len(priorities) > 0
        # Should be sorted by priority_score descending
        scores = [p["priority_score"] for p in priorities]
        assert scores == sorted(scores, reverse=True)
        # Each priority should have a rank
        assert priorities[0]["rank"] == 1

    def test_race_progression_single_race(self, sample_race):
        from paceforge.hyrox.analyzer import compute_race_progression

        result = compute_race_progression([sample_race])
        assert result["num_races"] == 1
        assert not result["improving"]

    def test_race_progression_multiple_races(self, sample_race):
        from paceforge.hyrox.analyzer import compute_race_progression

        race2 = sample_race.model_copy(deep=True)
        race2.total_time_seconds = 4400  # Faster
        race2.city = "TestCity 2026"

        result = compute_race_progression([sample_race, race2])
        assert result["num_races"] == 2
        assert len(result["total_trend"]) == 2

    def test_analyze_race_missing_splits(self):
        """Race with no splits should not crash."""
        from paceforge.hyrox.analyzer import analyze_race

        race = HyroxRaceResult(name="Empty", total_time_seconds=5000)
        result = analyze_race(race)
        assert result["total_running"] == 0
        assert result["fade_pct"] == 0


# ── Database persistence tests ─────────────────────────────────────


class TestHyroxDB:
    def test_hyrox_json_save_and_load(self, tmp_path):
        from paceforge.auth.database import (
            create_user,
            init_db,
            load_user_data,
            reset_connection,
            save_user_data,
        )
        from paceforge.auth.security import hash_password

        db_path = str(tmp_path / "test.db")
        reset_connection()
        init_db(db_path)

        # Create user first
        user = create_user(
            db_path,
            name="Test",
            email="test@example.com",
            password_hash=hash_password("pass123"),
            status="approved",
        )

        # Save hyrox data
        import json
        hyrox_data = {"search_name": "McIntyre", "search_gender": "M", "results": []}
        save_user_data(db_path, user["id"], hyrox_json=json.dumps(hyrox_data))

        # Load it back
        loaded = load_user_data(db_path, user["id"])
        assert loaded is not None
        assert loaded["hyrox_json"] is not None
        parsed = json.loads(loaded["hyrox_json"])
        assert parsed["search_name"] == "McIntyre"

        reset_connection()

    def test_hyrox_json_independent_of_other_fields(self, tmp_path):
        """Saving hyrox_json should not overwrite plan_json or profile_json."""
        from paceforge.auth.database import (
            create_user,
            init_db,
            load_user_data,
            reset_connection,
            save_user_data,
        )
        from paceforge.auth.security import hash_password

        db_path = str(tmp_path / "test2.db")
        reset_connection()
        init_db(db_path)

        user = create_user(
            db_path,
            name="Test2",
            email="test2@example.com",
            password_hash=hash_password("pass123"),
            status="approved",
        )

        # Save plan data first
        save_user_data(db_path, user["id"], plan_json='{"test": "plan"}')
        # Save hyrox data separately
        save_user_data(db_path, user["id"], hyrox_json='{"test": "hyrox"}')

        # Both should be preserved
        loaded = load_user_data(db_path, user["id"])
        assert loaded["plan_json"] == '{"test": "plan"}'
        assert loaded["hyrox_json"] == '{"test": "hyrox"}'

        reset_connection()
