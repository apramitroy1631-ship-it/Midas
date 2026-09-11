# app/services/llm/base.py
"""
Abstract base for all LLM providers.

Two generation modes:
  generate()            → structured output only (no tools, used by QA / Analytics)
  generate_with_tools() → ReAct loop first, then structured output synthesis
"""
from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Sequence, TypeVar

from langchain_core.tools import BaseTool
from pydantic import BaseModel

T = TypeVar("T", bound=BaseModel)


class BaseLLM(ABC):
    # ------------------------------------------------------------------
    # Mode 1 — plain structured generation (no tools)
    # ------------------------------------------------------------------

    @abstractmethod
    def generate(
        self,
        system_prompt: str,
        user_prompt: str,
        *,
        response_schema: type[BaseModel],
    ) -> BaseModel:
        """
        Call the LLM once and parse the response into `response_schema`.
        No tool invocation — use for QA, Analytics, and any agent that
        does not need live data retrieval.
        """

    # ------------------------------------------------------------------
    # Mode 2 — ReAct tool loop → structured synthesis
    # ------------------------------------------------------------------

    @abstractmethod
    def generate_with_tools(
        self,
        system_prompt: str,
        user_prompt: str,
        *,
        tools: Sequence[BaseTool],
        response_schema: type[BaseModel],
        max_steps: int = 8,
    ) -> BaseModel:
        """
        Run a ReAct (Reason + Act) loop with the provided tools, then
        synthesise all observations into a structured `response_schema`.

        Steps:
          1. Bind tools to the LLM chat model.
          2. Drive the ReAct engine until the LLM stops calling tools.
          3. Call `generate()` once more with all observations appended
             to the user prompt, to produce the final typed output.
        """