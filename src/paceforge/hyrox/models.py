"""Pydantic models for HYROX race results."""

from __future__ import annotations

from pydantic import BaseModel, Field


class HyroxSplit(BaseModel):
    """A single timed segment (run or station) within a HYROX race."""

    name: str = Field(description="Segment name, e.g. 'Running_1', 'SkiErg_1000m'")
    time_seconds: float | None = Field(None, description="Time in seconds (None if N/A)")
    rank: str = Field("", description="Rank for this segment within the field")
    field_size: str = Field("", description="Number of athletes in the ranked field")


class HyroxRaceResult(BaseModel):
    """Complete result for one HYROX race."""

    rank: str = ""
    rank_gender: str = ""
    rank_age_group: str = ""
    field_size: str = Field("", description="Athletes in the gender field for this race")
    name: str = ""
    nationality: str = ""
    city: str = Field("", description="Race city / event name")
    event_date: str = Field("", description="Event date or season (e.g. 'Dublin 2025')")
    division: str = ""
    age_group: str = ""
    total_time_seconds: float | None = None
    total_time_display: str = ""
    splits: list[HyroxSplit] = Field(default_factory=list)
    athlete_url: str = ""


# All expected split names in HYROX race order
HYROX_SPLIT_NAMES = [
    "Running_1",
    "SkiErg_1000m",
    "Running_2",
    "Sled_Push_50m",
    "Running_3",
    "Sled_Pull_50m",
    "Running_4",
    "Burpee_Broad_Jump_80m",
    "Running_5",
    "Row_1000m",
    "Running_6",
    "Farmers_Carry_200m",
    "Running_7",
    "Sandbag_Lunges_100m",
    "Running_8",
    "Wall_Balls",
    "Roxzone_Time",
]

RUNNING_SPLITS = [f"Running_{i}" for i in range(1, 9)]
STATION_SPLITS = [
    "SkiErg_1000m",
    "Sled_Push_50m",
    "Sled_Pull_50m",
    "Burpee_Broad_Jump_80m",
    "Row_1000m",
    "Farmers_Carry_200m",
    "Sandbag_Lunges_100m",
    "Wall_Balls",
]


class HyroxCachedData(BaseModel):
    """Wrapper stored in user_data.hyrox_json for persistence."""

    search_name: str = ""
    search_gender: str = "M"
    results: list[HyroxRaceResult] = Field(default_factory=list)
