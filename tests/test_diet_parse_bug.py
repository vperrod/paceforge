"""Reproduce the single-quote-to-double-quote corruption bug."""
import json
import re


def test_apostrophe_corruption():
    """Valid JSON with apostrophes in values gets corrupted by re.sub(r"'", '"')."""
    valid = json.dumps({
        "macro_targets": {"calories": 2200},
        "days": [{"day_number": 1, "meals": [
            {"name": "Chef's Omelette", "recipe_notes": "Use day's freshest eggs"}
        ]}]
    })

    # This is what the parser does — it should parse fine
    assert json.loads(valid)

    # The single-quote replacement breaks it
    corrupted = re.sub(r"'", '"', valid)
    try:
        json.loads(corrupted)
        assert False, "Should have raised JSONDecodeError"
    except json.JSONDecodeError as e:
        assert "Unterminated string" in str(e) or "Expecting" in str(e)


def test_trailing_comma_fix_is_safe():
    """Trailing comma removal doesn't corrupt valid JSON."""
    with_trailing = '{"a": 1, "b": [1, 2,], "c": {"x": 1,}}'
    cleaned = re.sub(r",\s*}", "}", with_trailing)
    cleaned = re.sub(r",\s*]", "]", cleaned)
    parsed = json.loads(cleaned)
    assert parsed == {"a": 1, "b": [1, 2], "c": {"x": 1}}
