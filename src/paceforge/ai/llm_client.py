"""Shared LLM client factory with model tier routing."""

from __future__ import annotations

import enum
import logging

logger = logging.getLogger(__name__)


class ModelTier(enum.Enum):
    CHEAP = "cheap"
    EXPENSIVE = "expensive"


class LLMClientFactory:
    """Resolves provider, API key, and model for a given cost tier."""

    def __init__(
        self,
        anthropic_api_key: str,
        anthropic_model: str,
        anthropic_model_cheap: str,
        openai_api_key: str,
        openai_model: str,
        provider: str,
    ) -> None:
        self._anthropic_key = anthropic_api_key
        self._anthropic_model = anthropic_model
        self._anthropic_model_cheap = anthropic_model_cheap
        self._openai_key = openai_api_key
        self._openai_model = openai_model
        self._provider = provider

    def resolve(self, tier: ModelTier = ModelTier.CHEAP) -> tuple[str, str, str]:
        """Return (provider, api_key, model) for the requested tier.

        Raises ValueError if no API key is configured.
        """
        if self._provider == "anthropic" and self._anthropic_key:
            model = self._anthropic_model if tier == ModelTier.EXPENSIVE else self._anthropic_model_cheap
            return "anthropic", self._anthropic_key, model

        if self._provider == "openai" and self._openai_key:
            return "openai", self._openai_key, self._openai_model

        # Auto-detect
        if self._anthropic_key:
            model = self._anthropic_model if tier == ModelTier.EXPENSIVE else self._anthropic_model_cheap
            return "anthropic", self._anthropic_key, model

        if self._openai_key:
            return "openai", self._openai_key, self._openai_model

        raise ValueError("No LLM API key configured")
