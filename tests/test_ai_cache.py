# tests/test_ai_cache.py
from __future__ import annotations

import time
from pathlib import Path

import pytest

from paceforge.ai.cache import AICache


@pytest.fixture
def cache(tmp_path: Path) -> AICache:
    db_path = str(tmp_path / "test.db")
    return AICache(db_path)


def test_cache_miss_returns_none(cache: AICache) -> None:
    result = cache.get("nonexistent-key")
    assert result is None


def test_cache_set_and_get(cache: AICache) -> None:
    cache.set("key1", "hello world", model="claude-haiku-4-5-20251001")
    result = cache.get("key1")
    assert result == "hello world"


def test_cache_expired_returns_none(cache: AICache) -> None:
    cache.set("key2", "old data", model="claude-haiku-4-5-20251001", ttl_seconds=1)
    time.sleep(1.1)
    result = cache.get("key2")
    assert result is None


def test_cache_key_generation(cache: AICache) -> None:
    key1 = AICache.make_key("system prompt", "user msg", "model-a")
    key2 = AICache.make_key("system prompt", "user msg", "model-a")
    key3 = AICache.make_key("system prompt", "user msg", "model-b")
    assert key1 == key2
    assert key1 != key3


def test_cache_cleanup_removes_expired(cache: AICache) -> None:
    cache.set("expired", "old", model="m", ttl_seconds=1)
    cache.set("fresh", "new", model="m", ttl_seconds=3600)
    time.sleep(1.1)
    removed = cache.cleanup()
    assert removed >= 1
    assert cache.get("expired") is None
    assert cache.get("fresh") == "new"
