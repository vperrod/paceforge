"""Diet planning and weight management models."""

from __future__ import annotations

from datetime import date, datetime
from enum import StrEnum

from pydantic import BaseModel, Field


class DietGoal(StrEnum):
    LOSE_WEIGHT = "lose_weight"
    LOSE_FAT = "lose_fat"
    GAIN_MUSCLE = "gain_muscle"
    MAINTAIN = "maintain"
    BODY_RECOMPOSITION = "body_recomposition"


class MealType(StrEnum):
    BREAKFAST = "breakfast"
    MORNING_SNACK = "morning_snack"
    LUNCH = "lunch"
    AFTERNOON_SNACK = "afternoon_snack"
    DINNER = "dinner"
    EVENING_SNACK = "evening_snack"


class WeightSource(StrEnum):
    GARMIN = "garmin"
    MANUAL = "manual"


class MacroTotals(BaseModel):
    calories: float = 0
    protein_g: float = 0
    carbs_g: float = 0
    fat_g: float = 0
    fiber_g: float = 0


class FoodItem(BaseModel):
    name: str
    quantity: float = 0
    unit: str = "g"
    calories: float = 0
    protein_g: float = 0
    carbs_g: float = 0
    fat_g: float = 0


class Meal(BaseModel):
    name: str
    meal_type: MealType
    foods: list[FoodItem] = Field(default_factory=list)
    total_calories: float = 0
    protein_g: float = 0
    carbs_g: float = 0
    fat_g: float = 0
    fiber_g: float = 0
    recipe_notes: str = ""


class DailyMealPlan(BaseModel):
    date: date
    meals: list[Meal] = Field(default_factory=list)
    daily_totals: MacroTotals = Field(default_factory=MacroTotals)
    notes: str = ""
    adjustment_reason: str = ""


class WeeklyMealTemplate(BaseModel):
    week_number: int
    days: list[DailyMealPlan] = Field(default_factory=list)


class WeightEntry(BaseModel):
    date: date
    weight_kg: float
    body_fat_pct: float | None = None
    muscle_mass_kg: float | None = None
    bmi: float | None = None
    source: WeightSource = WeightSource.MANUAL


class DietProfile(BaseModel):
    goals: list[DietGoal] = Field(default_factory=list)
    target_weight_kg: float | None = None
    daily_meals_count: int = Field(default=3, ge=2, le=6)
    plan_weeks: int = Field(default=1, ge=1, le=4)
    start_date: date | None = None
    preferred_foods: list[str] = Field(default_factory=list)
    allergies: list[str] = Field(default_factory=list)
    restrictions: list[str] = Field(default_factory=list)
    notes: str = ""


class UserNote(BaseModel):
    date: date
    content: str
    ai_response: str = ""
    created_at: str = Field(default_factory=lambda: datetime.now().isoformat())


class DietPlan(BaseModel):
    plan_id: str = ""
    profile: DietProfile = Field(default_factory=DietProfile)
    created_at: str = Field(default_factory=lambda: datetime.now().isoformat())
    plan_analysis: str = ""
    macro_targets: MacroTotals = Field(default_factory=MacroTotals)
    weekly_templates: list[WeeklyMealTemplate] = Field(default_factory=list)
    weight_history: list[WeightEntry] = Field(default_factory=list)
    user_notes: list[UserNote] = Field(default_factory=list)
    active: bool = True
    auto_adjust: bool = True
    last_adjusted: str = ""


class DietData(BaseModel):
    """Top-level container stored in diet_json."""
    profile: DietProfile = Field(default_factory=DietProfile)
    active_plan: DietPlan | None = None
    weight_history: list[WeightEntry] = Field(default_factory=list)
    user_notes: list[UserNote] = Field(default_factory=list)
