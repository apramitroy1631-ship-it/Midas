# app/services/llm/ollama_provider.py
"""
Ollama provider — OpenAI-compatible endpoint.

Supports both plain structured generation and the ReAct tool-calling loop.
Tool support requires a model that supports function calling (e.g. llama3.1,
mistral-nemo, qwen2.5).  If the model does not support tool calls the ReAct
engine will immediately exit without observations and fall back to a plain
structured generation call — graceful degradation, no crash.
"""
from __future__ import annotations

import logging
from typing import Sequence

from langchain_core.tools import BaseTool
from langchain_openai import ChatOpenAI
from openai import OpenAI
from pydantic import BaseModel

from app.core.settings import settings

from .base import BaseLLM
from .react_engine import ReActEngine

logger = logging.getLogger("ollama_provider")


class OllamaProvider(BaseLLM):
    def __init__(self, model: str | None = None) -> None:
        self._model_name = model or settings.ollama_model_default

        # Raw OpenAI-compat client — for structured-output generation.
        self._client = OpenAI(
            base_url=settings.ollama_base_url,
            api_key=settings.ollama_api_key,
        )

        # LangChain chat model pointing at Ollama — for ReAct tool binding.
        self._chat = ChatOpenAI(
            model=self._model_name,
            base_url=settings.ollama_base_url,
            api_key=settings.ollama_api_key,
            temperature=0.7,
        )

    # ------------------------------------------------------------------
    # Mode 1 — structured output (no tools)
    # ------------------------------------------------------------------

    def generate(
        self,
        system_prompt: str,
        user_prompt: str,
        *,
        response_schema: type[BaseModel],
    ) -> BaseModel:
        response = self._client.beta.chat.completions.parse(
            model=self._model_name,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user",   "content": user_prompt},
            ],
            response_format=response_schema,
            temperature=0.7,
            max_tokens=7048,
        )
        usage = response.usage
        logger.info(
            f"LLM_CALL | provider=ollama | model={self._model_name} | "
            f"tokens={usage.total_tokens} | "
            f"prompt={usage.prompt_tokens} | "
            f"completion={usage.completion_tokens}"
        )
        return response.choices[0].message.parsed

    # ------------------------------------------------------------------
    # Mode 2 — ReAct loop → structured synthesis
    # ------------------------------------------------------------------

    def generate_with_tools(
        self,
        system_prompt: str,
        user_prompt: str,
        *,
        tools: Sequence[BaseTool],
        response_schema: type[BaseModel],
        max_steps: int = 8,
    ) -> BaseModel:
        llm_with_tools = self._chat.bind_tools(tools)
        engine = ReActEngine(
            llm_with_tools=llm_with_tools,
            tools=tools,
            max_steps=max_steps,
        )

        observations = engine.run(system_prompt, user_prompt)
        logger.info(
            f"ReAct complete | provider=ollama | "
            f"observations_len={len(observations)}"
        )

        enriched_prompt = _build_synthesis_prompt(user_prompt, observations)
        return self.generate(
            system_prompt=system_prompt,
            user_prompt=enriched_prompt,
            response_schema=response_schema,
        )


# ---------------------------------------------------------------------------
# Shared helper
# ---------------------------------------------------------------------------

def _build_synthesis_prompt(original_user_prompt: str, observations: str) -> str:
    return (
        f"{original_user_prompt}\n\n"
        "---\n"
        "The following real-time data was retrieved via tool calls. "
        "Incorporate it into your analysis. Do not ignore or contradict it.\n\n"
        f"{observations}"
    )