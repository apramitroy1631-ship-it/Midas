# app/services/llm/openai_provider.py
"""
OpenAI provider — supports both plain structured generation and
the ReAct tool-calling loop via `generate_with_tools()`.
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
from .retry import with_retry
from .usage import record as record_usage

logger = logging.getLogger("openai_provider")


class OpenAIProvider(BaseLLM):
    def __init__(self, model: str | None = None) -> None:
        self._model_name = model or settings.openai_model_default

        # Raw OpenAI client — used for structured-output generation (mode 1).
        self._client = OpenAI(api_key=settings.openai_api_key)

        # LangChain chat model — used for tool-binding in ReAct (mode 2).
        self._chat = ChatOpenAI(
            model=self._model_name,
            api_key=settings.openai_api_key,
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
        response = with_retry(
            lambda: self._client.beta.chat.completions.parse(
                model=self._model_name,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user",   "content": user_prompt},
                ],
                temperature=0.7,
                max_tokens=7048,
                response_format=response_schema,
            ),
            label=f"openai:{self._model_name}",
        )
        usage = response.usage
        record_usage(self._model_name, usage.prompt_tokens, usage.completion_tokens)
        logger.info(
            f"LLM_CALL | provider=openai | model={self._model_name} | "
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
            f"ReAct complete | provider=openai | "
            f"observations_len={len(observations)}"
        )

        # Synthesise: append all gathered observations to the original
        # user prompt and ask for one final structured response.
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