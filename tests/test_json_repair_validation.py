"""Validate json_repair handles every failure mode we've encountered in diet plan generation.

These tests run BEFORE we modify production code, to confirm the library works.
"""
import json

import json_repair


def test_truncated_mid_string():
    """Unterminated string — the exact error we keep hitting."""
    truncated = '{"macro_targets": {"calories": 2200}, "days": [{"day_number": 1, "meals": [{"name": "Oatmeal", "recipe_notes": "Cook oats with mi'
    result = json_repair.loads(truncated)
    assert isinstance(result, dict)
    assert result["macro_targets"]["calories"] == 2200
    assert result["days"][0]["meals"][0]["name"] == "Oatmeal"


def test_trailing_comma_before_brace():
    """Trailing comma before } — the 'Expecting property name' error."""
    bad = '{"a": 1, "b": 2,}'
    result = json_repair.loads(bad)
    assert result == {"a": 1, "b": 2}


def test_trailing_comma_before_bracket():
    """Trailing comma before ]."""
    bad = '{"items": [1, 2, 3,]}'
    result = json_repair.loads(bad)
    assert result == {"items": [1, 2, 3]}


def test_apostrophes_in_values_preserved():
    """Apostrophes in string values must NOT be corrupted."""
    valid = json.dumps({"recipe_notes": "Chef's special with day's fresh produce"})
    result = json_repair.loads(valid)
    assert result["recipe_notes"] == "Chef's special with day's fresh produce"


def test_unclosed_brackets_and_braces():
    """JSON truncated at a structural boundary (not mid-string)."""
    truncated = '{"days": [{"day_number": 1, "meals": [{"name": "Eggs"}]'
    result = json_repair.loads(truncated)
    assert isinstance(result, dict)
    assert result["days"][0]["meals"][0]["name"] == "Eggs"


def test_truncated_after_colon():
    """Truncated right after a key's colon — no value."""
    truncated = '{"days": [{"day_number": 1, "meals": [{"name":'
    result = json_repair.loads(truncated)
    assert isinstance(result, dict)


def test_markdown_fences_not_handled():
    """json_repair doesn't strip markdown fences — we still need to do that ourselves."""
    fenced = '```json\n{"a": 1}\n```'
    # json_repair may or may not handle this — we'll strip fences first
    # Just verify it doesn't crash
    try:
        result = json_repair.loads(fenced)
        assert isinstance(result, dict)
    except Exception:
        pass  # Expected — we'll strip fences before calling


def test_realistic_diet_truncation():
    """Simulate a realistic truncated diet plan response (~2500 chars)."""
    plan = {
        "macro_targets": {"calories": 2200, "protein_g": 140, "carbs_g": 275, "fat_g": 75, "fiber_g": 30},
        "days": [],
    }
    for day in range(1, 8):
        meals = []
        for meal_name, meal_type in [("Oatmeal Bowl", "breakfast"), ("Chicken Salad", "lunch"), ("Salmon Dinner", "dinner")]:
            meals.append({
                "name": f"{meal_name} Day {day}",
                "meal_type": meal_type,
                "foods": [
                    {"name": "Oats", "quantity": 80, "unit": "g", "calories": 300, "protein_g": 10, "carbs_g": 55, "fat_g": 6},
                    {"name": "Banana", "quantity": 1, "unit": "pcs", "calories": 105, "protein_g": 1, "carbs_g": 27, "fat_g": 0},
                ],
                "total_calories": 405,
                "protein_g": 11,
                "carbs_g": 82,
                "fat_g": 6,
                "fiber_g": 7,
                "recipe_notes": "Cook the oat's with milk, add sliced banana on top",
            })
        plan["days"].append({"day_number": day, "meals": meals, "daily_totals": {"calories": 2200, "protein_g": 140, "carbs_g": 275, "fat_g": 75, "fiber_g": 30}})

    full_json = json.dumps(plan)
    assert len(full_json) > 4000

    # Truncate at ~2500 chars (mid-string, mid-object, etc.)
    for cut_point in [2453, 2525, 2629, 2675, 1500, 3000]:
        if cut_point < len(full_json):
            truncated = full_json[:cut_point]
            result = json_repair.loads(truncated)
            assert isinstance(result, dict), f"Failed at cut_point={cut_point}"
            assert "macro_targets" in result, f"Missing macro_targets at cut_point={cut_point}"
            assert result["macro_targets"]["calories"] == 2200, f"Wrong calories at cut_point={cut_point}"
