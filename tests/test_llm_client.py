from __future__ import annotations

import pytest

from paceforge.ai.llm_client import LLMClientFactory, ModelTier


def test_resolve_tier_cheap() -> None:
    factory = LLMClientFactory(
        anthropic_api_key="sk-test",
        anthropic_model="claude-sonnet-4-20250514",
        anthropic_model_cheap="claude-haiku-4-5-20251001",
        openai_api_key="",
        openai_model="gpt-4o-mini",
        provider="anthropic",
    )
    provider, key, model = factory.resolve(ModelTier.CHEAP)
    assert provider == "anthropic"
    assert model == "claude-haiku-4-5-20251001"


def test_resolve_tier_expensive() -> None:
    factory = LLMClientFactory(
        anthropic_api_key="sk-test",
        anthropic_model="claude-sonnet-4-20250514",
        anthropic_model_cheap="claude-haiku-4-5-20251001",
        openai_api_key="",
        openai_model="gpt-4o-mini",
        provider="anthropic",
    )
    provider, key, model = factory.resolve(ModelTier.EXPENSIVE)
    assert provider == "anthropic"
    assert model == "claude-sonnet-4-20250514"


def test_resolve_auto_prefers_anthropic() -> None:
    factory = LLMClientFactory(
        anthropic_api_key="sk-ant",
        anthropic_model="claude-sonnet-4-20250514",
        anthropic_model_cheap="claude-haiku-4-5-20251001",
        openai_api_key="sk-oai",
        openai_model="gpt-4o-mini",
        provider="",
    )
    provider, key, model = factory.resolve(ModelTier.CHEAP)
    assert provider == "anthropic"


def test_resolve_fallback_to_openai() -> None:
    factory = LLMClientFactory(
        anthropic_api_key="",
        anthropic_model="claude-sonnet-4-20250514",
        anthropic_model_cheap="claude-haiku-4-5-20251001",
        openai_api_key="sk-oai",
        openai_model="gpt-4o-mini",
        provider="",
    )
    provider, key, model = factory.resolve(ModelTier.CHEAP)
    assert provider == "openai"
    assert model == "gpt-4o-mini"


def test_resolve_no_keys_raises() -> None:
    factory = LLMClientFactory(
        anthropic_api_key="",
        anthropic_model="",
        anthropic_model_cheap="",
        openai_api_key="",
        openai_model="",
        provider="",
    )
    with pytest.raises(ValueError, match="No LLM API key configured"):
        factory.resolve(ModelTier.CHEAP)
