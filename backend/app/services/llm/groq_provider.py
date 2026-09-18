# app/services/llm/groq_provider.py
"""
Groq provider — OpenAI-compatible endpoint, used as a free, high-throughput
alternative to Gemini's free tier (20 requests/day/model) for local testing.

Same shape as gemini_provider.py: rather than trust Groq's OpenAI-compatible
`.beta.chat.completions.parse()` structured-output support (inconsistent across
models), mode 1 asks for JSON via the system prompt and parses it by hand.
"""
from __future__ import annotations

import logging
from typing import Sequence

from langchain_core.tools import BaseTool
from langchain_openai import ChatOpenAI
from pydantic import BaseModel

from app.core.settings import settings

from .base import BaseLLM
from .react_engine import ReActEngine
from .retry import with_retry
from .usage import record as record_usage

logger = logging.getLogger("groq_provider")

GROQ_BASE_URL = "https://api.groq.com/openai/v1"


def _text_of(content: object) -> str:
    """Mirrors gemini_provider._text_of — LangChain message content isn't
    always a plain string across providers."""
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        parts = []
        for item in content:
            if isinstance(item, str):
                parts.append(item)
            elif isinstance(item, dict):
                parts.append(item.get("text", ""))
        return "".join(parts)
    return str(content)


class GroqProvider(BaseLLM):
    def __init__(self, model: str | None = None) -> None:
        self._model_name = model or settings.groq_model_default

        self._chat = ChatOpenAI(
            model=self._model_name,
            base_url=GROQ_BASE_URL,
            api_key=settings.groq_api_key,
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
        import json

        from langchain_core.messages import HumanMessage, SystemMessage

        schema_hint = json.dumps(response_schema.model_json_schema(), indent=2)
        augmented_system = (
            f"{system_prompt}\n\n"
            "Return ONLY a valid JSON object that conforms to this schema "
            "(no markdown, no code fences, no commentary):\n"
            f"{schema_hint}"
        )

        response = with_retry(
            lambda: self._chat.invoke([
                SystemMessage(content=augmented_system),
                HumanMessage(content=user_prompt),
            ]),
            label=f"groq:{self._model_name}",
        )

        raw_text = _text_of(response.content)
        if raw_text.startswith("```"):
            raw_text = raw_text.split("```")[1]
            if raw_text.startswith("json"):
                raw_text = raw_text[4:]

        parsed = response_schema.model_validate_json(raw_text.strip())

        usage = getattr(response, "usage_metadata", None) or {}
        record_usage(
            self._model_name,
            usage.get("input_tokens", 0),
            usage.get("output_tokens", 0),
        )
        logger.info(
            f"LLM_CALL | provider=groq | model={self._model_name} | "
            f"tokens={usage.get('total_tokens', 0)}"
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
            f"ReAct complete | provider=groq | "
            f"observations_len={len(observations)}"
        )

        enriched_prompt = _build_synthesis_prompt(user_prompt, observations)
        return self.generate(
            system_prompt=system_prompt,
            user_prompt=enriched_prompt,
            response_schema=response_schema,
        )


def _build_synthesis_prompt(original_user_prompt: str, observations: str) -> str:
    return (
        f"{original_user_prompt}\n\n"
        "---\n"
        "The following real-time data was retrieved via tool calls. "
        "Incorporate it into your analysis. Do not ignore or contradict it.\n\n"
        f"{observations}"
    )
