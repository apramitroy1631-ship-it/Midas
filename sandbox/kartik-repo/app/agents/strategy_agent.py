# app/agents/strategy_agent.py
import json
import logging
from datetime import date
from typing import Any, Dict

from app.schemas.strategy import StrategyOutput
from app.services.llm.llm_factory import LLMFactory
from app.tools import STRATEGY_TOOLS

logger = logging.getLogger("agents.strategy")

SYSTEM_PROMPT = """You are a CMO designing a data-driven growth strategy for a specific campaign.

Your strategy must directly serve the stated campaign goal, target audience, and budget.
Output valid JSON only — no markdown, no code fences, no commentary. Return exactly one JSON object.

Quality standards:
- Objectives must be measurable and achievable within the stated budget — not aspirational
- Tactics must be concrete, executable actions — not vague directions
- Every recommended channel must earn its place based on where the target audience actually is
- All timeframes must be future-relative from today — never reference dates already passed
- Strategy must follow logically from the research; do not ignore competitive gaps identified
- Tactics must never violate brand content restrictions — always check guidelines before recommending"""


def _build_user_prompt(
    research: Dict[str, Any],
    brand_context: Dict[str, Any],
    goal: str,
    target_audience: str,
    budget: float,
) -> str:
    brand_id = brand_context.get("id", brand_context.get("_id", ""))
    return f"""Design a campaign growth strategy using the inputs below.

TODAY'S DATE: {date.today().isoformat()}

BRAND ID: {brand_id}

BRAND CONTEXT:
{json.dumps(brand_context, indent=2)}

CAMPAIGN GOAL:
{goal}

TARGET AUDIENCE:
{target_audience}

BUDGET (USD): ${budget:,.2f}

MARKET RESEARCH:
{json.dumps(research, indent=2)}

Use your tools where needed, then produce your strategy as a single JSON object.""".strip()


class StrategyAgent:
    def __init__(self) -> None:
        self.llm = LLMFactory.get_llm(agent_type="strategy")

    def run(
        self,
        research: Dict[str, Any] | None,
        brand_context: Dict[str, Any] | None = None,
        goal: str = "",
        target_audience: str = "",
        budget: float = 0.0,
    ) -> StrategyOutput:
        brand_context = brand_context or {}
        logger.info(
            "StrategyAgent.run | brand=%s | goal=%s",
            brand_context.get("name", "?"), goal[:80],
        )
        result: StrategyOutput = self.llm.generate_with_tools(
            system_prompt=SYSTEM_PROMPT,
            user_prompt=_build_user_prompt(
                research or {},
                brand_context,
                goal,
                target_audience,
                budget,
            ),
            tools=STRATEGY_TOOLS,
            response_schema=StrategyOutput,
            max_steps=4,
        )
        logger.info("StrategyAgent.run | complete")
        return result