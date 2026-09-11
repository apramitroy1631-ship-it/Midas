# app/services/llm/anthropic_provider.py
"""
Anthropic (Claude) provider.

Supports both plain structured generation and the ReAct tool-calling loop.
Uses langchain-anthropic for tool binding in mode 2, and the raw anthropic
SDK for structured JSON extraction in mode 1.
"""
from __future__ import annotations

import json
import logging
from typing import Sequence

from langchain_anthropic import ChatAnthropic
from langchain_core.tools import BaseTool
from pydantic import BaseModel

from app.core.settings import settings

from .base import BaseLLM
from .react_engine import ReActEngine

logger = logging.getLogger("anthropic_provider")


class AnthropicProvider(BaseLLM):
    def __init__(self, model: str | None = None) -> None:
        self._model_name = model or settings.anthropic_model_default

        # LangChain chat model — used for both structured output and tool binding.
        # Anthropic does not have an OpenAI-compat structured-output endpoint,
        # so we use JSON-mode prompting + manual pydantic parsing in mode 1.
        self._chat = ChatAnthropic(
            model=self._model_name,
            api_key=settings.anthropic_api_key,
            temperature=0.7,
            max_tokens=7048,
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
        from langchain_core.messages import HumanMessage, SystemMessage

        schema_hint = json.dumps(response_schema.model_json_schema(), indent=2)
        augmented_system = (
            f"{system_prompt}\n\n"
            "Return ONLY a valid JSON object that conforms to this schema "
            "(no markdown, no code fences):\n"
            f"{schema_hint}"
        )

        response = self._chat.invoke([
            SystemMessage(content=augmented_system),
            HumanMessage(content=user_prompt),
        ])

        raw_text: str = response.content
        # Strip accidental markdown fences if the model adds them.
        if raw_text.startswith("```"):
            raw_text = raw_text.split("```")[1]
            if raw_text.startswith("json"):
                raw_text = raw_text[4:]

        parsed = response_schema.model_validate_json(raw_text.strip())
        logger.info(
            f"LLM_CALL | provider=anthropic | model={self._model_name} | "
            f"response_len={len(raw_text)}"
        )
        return parsed

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
            f"ReAct complete | provider=anthropic | "
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