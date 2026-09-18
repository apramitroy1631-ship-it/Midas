# app/services/llm/llm_factory.py
from __future__ import annotations

import logging
from functools import lru_cache

from app.core.config import AGENT_MODEL_MAP
from app.core.settings import settings

from .anthropic_provider import AnthropicProvider
from .base import BaseLLM
from .gemini_provider import GeminiProvider
from .groq_provider import GroqProvider
from .ollama_provider import OllamaProvider
from .openai_provider import OpenAIProvider
from .simulator_provider import SimulatorProvider

logger = logging.getLogger("llm.factory")


@lru_cache(maxsize=64)
def _build(provider: str, model: str) -> BaseLLM:
    """Providers are stateless and expensive to construct, so they are cached
    on (provider, model) rather than on agent name."""
    if provider == "ollama":
        return OllamaProvider(model=model or settings.ollama_model_default)
    if provider == "openai":
        return OpenAIProvider(model=model or settings.openai_model_default)
    if provider == "anthropic":
        return AnthropicProvider(model=model or settings.anthropic_model_default)
    if provider == "gemini":
        return GeminiProvider(model=model or settings.gemini_model_default)
    if provider == "groq":
        return GroqProvider(model=model or settings.groq_model_default)
    if provider == "simulator":
        return SimulatorProvider(model=model)
    raise ValueError("Unsupported LLM provider: " + repr(provider))


class LLMFactory:
    @staticmethod
    def get_llm(agent_type: str, overrides: dict | None = None) -> BaseLLM:
        """Resolve the model for an agent.

        Resolution order: tenant override -> global agent map -> settings default.
        A tenant override looks like {"content": {"provider": "anthropic", "model": "claude-sonnet-5"}}.
        """
        # A global simulator setting overrides per-agent routing: it is an
        # environment-level switch, not a model preference.
        if settings.llm_provider.strip().lower() == "simulator":
            return _build("simulator", "")

        key = agent_type.lower()
        entry = (overrides or {}).get(key) or AGENT_MODEL_MAP.get(key)

        if entry:
            provider = str(entry.get("provider", settings.llm_provider)).strip().lower()
            model = str(entry.get("model") or "").strip()
        else:
            provider = settings.llm_provider.strip().lower()
            model = ""

        return _build(provider, model)
