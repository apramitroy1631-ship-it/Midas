from __future__ import annotations

from functools import lru_cache

from app.config import AGENT_MODEL_MAP
from app.core.settings import settings

from .anthropic_provider import AnthropicProvider
from .base import BaseLLM
from .ollama_provider import OllamaProvider
from .openai_provider import OpenAIProvider


class LLMFactory:
    @staticmethod
    @lru_cache(maxsize=None)
    def get_llm(agent_type: str) -> BaseLLM:
        """
        Return an LLM for a given agent/node type.
        Reads provider and model from app.config.AGENT_MODEL_MAP;
        falls back to settings when agent is not in the map.
        """
        key = agent_type.lower()
        entry = AGENT_MODEL_MAP.get(key)

        if entry:
            provider = entry["provider"].strip().lower()
            model = (entry.get("model") or "").strip()
        else:
            provider = settings.llm_provider.strip().lower()
            model = ""

        if provider == "ollama":
            return OllamaProvider(model=model or settings.ollama_model_default)
        if provider == "openai":
            return OpenAIProvider(model=model or settings.openai_model_default)
        if provider == "anthropic":
            return AnthropicProvider(model=model or settings.anthropic_model_default)

        raise ValueError(f"Unsupported LLM provider: {provider!r}")
