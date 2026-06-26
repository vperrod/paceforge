"""Parse a saved hyresult.com result page (no network)."""

from pathlib import Path

from paceforge.hyrox.hyresult import parse_result

FIXTURE = (Path(__file__).parent / "fixtures" / "hyresult_berlin.html").read_text()


def test_parses_city_and_year():
    assert parse_result(FIXTURE).event_date == "Berlin 2026"


def test_parses_total_time():
    assert parse_result(FIXTURE).total_time_display == "1:06:19"


def test_overall_rank_is_per_race_not_season_cumulative():
    assert parse_result(FIXTURE).rank == "203"


def test_field_size():
    assert parse_result(FIXTURE).field_size == "4142"


def test_age_group_rank():
    assert parse_result(FIXTURE).rank_age_group == "12"


def test_age_group_bracket():
    assert parse_result(FIXTURE).age_group == "40-44"


def test_all_seventeen_splits_present():
    timed = [s for s in parse_result(FIXTURE).splits if s.time_seconds]
    assert len(timed) == 17


def test_split_carries_its_own_rank():
    skierg = next(s for s in parse_result(FIXTURE).splits if s.name == "SkiErg_1000m")
    assert skierg.rank == "236"
