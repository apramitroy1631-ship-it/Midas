# app/services/llm/react_engine.py
"""
ReAct (Reasoning + Acting) engine.

Implements a provider-agnostic Thought → Action → Observation loop using
LangChain's tool-calling interface.  Agents pass their tool registry and
the engine drives the LLM until it either:

  1. Produces a final answer (no tool calls in response), OR
  2. Exhausts the allowed step budget (safety ceiling).

The engine is intentionally stateless — all context lives in the message
history it accumulates during a single `run()` call.

Usage
-----
    engine  = ReActEngine(llm_with_tools, tools=RESEARCH_TOOLS, max_steps=6)
    summary = engine.run(system_prompt, user_prompt)
    # summary is a plain string — pass it to the final structured generation step.
"""
from __future__ import annotations

import json
import logging
from typing import Any, Sequence

from langchain_core.messages import (
    AIMessage,
    BaseMessage,
    HumanMessage,
    SystemMessage,
    ToolMessage,
)
from langchain_core.tools import BaseTool

logger = logging.getLogger("react_engine")

# Hard ceiling — prevents infinite loops if the LLM keeps calling tools.
_DEFAULT_MAX_STEPS = 8


class ReActEngine:
    """
    Provider-agnostic ReAct loop.

    Parameters
    ----------
    llm_with_tools:
        A LangChain chat model already bound to tools via `.bind_tools(...)`.
    tools:
        The same list of LangChain `@tool` functions — used to dispatch calls.
    max_steps:
        Maximum tool-calling rounds before the loop is aborted and whatever
        observations we have are passed to the final synthesis step.
    """

    def __init__(
        self,
        llm_with_tools: Any,
        tools: Sequence[BaseTool],
        max_steps: int = _DEFAULT_MAX_STEPS,
    ) -> None:
        self._llm = llm_with_tools
        self._tool_map: dict[str, BaseTool] = {t.name: t for t in tools}
        self._max_steps = max_steps

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def run(self, system_prompt: str, user_prompt: str) -> str:
        """
        Execute the ReAct loop.

        Returns a plain-text summary of all observations gathered — ready
        to be handed to a final structured-generation call.
        """
        messages: list[BaseMessage] = [
            SystemMessage(content=system_prompt),
            HumanMessage(content=user_prompt),
        ]

        observations: list[str] = []
        steps = 0

        while steps < self._max_steps:
            steps += 1
            logger.info(f"ReActEngine | step={steps}/{self._max_steps}")

            ai_message: AIMessage = self._llm.invoke(messages)
            messages.append(ai_message)

            tool_calls = getattr(ai_message, "tool_calls", None) or []

            if not tool_calls:
                # LLM decided it has enough information — exit loop.
                logger.info("ReActEngine | no tool calls — loop complete")
                # Capture any final text the model produced.
                if ai_message.content:
                    observations.append(str(ai_message.content))
                break

            # ---------- dispatch each tool call ----------
            for call in tool_calls:
                tool_name = call["name"]
                tool_args = call["args"]
                call_id   = call["id"]

                logger.info(
                    f"ReActEngine | tool_call | name={tool_name} | args={tool_args}"
                )

                tool_fn = self._tool_map.get(tool_name)
                if tool_fn is None:
                    result = json.dumps({
                        "error": f"Unknown tool '{tool_name}'. "
                                 f"Available: {list(self._tool_map)}"
                    })
                    logger.warning(
                        f"ReActEngine | unknown tool | name={tool_name}"
                    )
                else:
                    try:
                        raw = tool_fn.invoke(tool_args)
                        result = raw if isinstance(raw, str) else json.dumps(raw)
                        logger.info(
                            f"ReActEngine | tool_result | "
                            f"name={tool_name} | "
                            f"result_len={len(result)}"
                        )
                    except Exception as exc:
                        result = json.dumps({"error": str(exc)})
                        logger.error(
                            f"ReActEngine | tool_error | "
                            f"name={tool_name} | error={exc}"
                        )

                observations.append(f"[{tool_name}] → {result}")
                messages.append(
                    ToolMessage(content=result, tool_call_id=call_id)
                )

        else:
            logger.warning(
                f"ReActEngine | max_steps={self._max_steps} reached — "
                "forcing synthesis with collected observations"
            )

        return self._format_observations(observations)

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _format_observations(observations: list[str]) -> str:
        if not observations:
            return "No tool observations were collected."
        joined = "\n\n".join(observations)
        return f"TOOL OBSERVATIONS:\n{joined}"