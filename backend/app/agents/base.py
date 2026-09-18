# app/agents/base.py
from __future__ import annotations

import json
import logging
from typing import Any, Sequence

from langchain_core.tools import BaseTool
from pydantic import BaseModel

from app.services.llm.llm_factory import LLMFactory
from app.services.llm.usage import attributed_to

logger = logging.getLogger("agents")


class Agent:
    """Shared plumbing for every specialist.

    Subclasses declare `name`, `system_prompt`, `output_schema`, and optionally
    `tools`, then implement `build_prompt()`. Everything else - model resolution
    from tenant overrides, tool-loop vs plain generation, usage attribution -
    is handled here so the agents stay readable as prompts plus contracts.
    """

    name: str = "agent"
    system_prompt: str = ""
    output_schema: type[BaseModel]
    tools: Sequence[BaseTool] = ()
    max_tool_steps: int = 6

    def __init__(self, model_overrides: dict[str, Any] | None = None) -> None:
        self._llm = LLMFactory.get_llm(self.name, model_overrides)

    def build_prompt(self, **kwargs: Any) -> str:  # pragma: no cover - overridden
        raise NotImplementedError

    def run(self, *, use_tools: bool = True, **kwargs: Any) -> BaseModel:
        prompt = self.build_prompt(**kwargs)
        logger.info("%s | start", self.name)
        with attributed_to(self.name):
            if self.tools and use_tools:
                result = self._llm.generate_with_tools(
                    system_prompt=self.system_prompt,
                    user_prompt=prompt,
                    tools=list(self.tools),
                    response_schema=self.output_schema,
                    max_steps=self.max_tool_steps,
                )
            else:
                result = self._llm.generate(
                    system_prompt=self.system_prompt,
                    user_prompt=prompt,
                    response_schema=self.output_schema,
                )
        logger.info("%s | complete", self.name)
        return result


def block(title: str, payload: Any) -> str:
    """Render a labelled JSON block for a prompt, skipping empty sections."""
    if payload in (None, "", [], {}):
        return ""
    if isinstance(payload, (dict, list)):
        rendered = json.dumps(payload, indent=2, default=str)
    else:
        rendered = str(payload)
    return "\n" + title + ":\n" + rendered + "\n"
