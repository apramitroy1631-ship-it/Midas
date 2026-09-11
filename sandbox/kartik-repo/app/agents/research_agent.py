# app/agents/research_agent.py
import json
import logging
from datetime import date
from typing import Any, Dict

from app.schemas.research import ResearchOutput
from app.services.llm.llm_factory import LLMFactory
from app.tools import RESEARCH_TOOLS

logger = logging.getLogger("agents.research")

SYSTEM_PROMPT = """You are a senior market research analyst with deep expertise in digital marketing and consumer behaviour.

Your task is to produce rigorous, grounded market research tailored to a specific brand and campaign goal.
Output valid JSON only — no markdown, no code fences, no commentary. Return exactly one JSON object.

Quality standards:
- Market sizing must be grounded in real sector benchmarks, not aspirational estimates
- Growth rates must reflect realistic CAGR figures for the sector
- Competitive intelligence must identify exploitable gaps, not just surface positioning
- Insights must be directly tied to the campaign goal, not generic category observations
- All analysis must be forward-looking from today's date"""


def _build_user_prompt(
    brand_context: Dict[str, Any],
    goal: str,
    target_audience: str,
    budget: float,
) -> str:
    return f"""Conduct market research to support the following campaign.

TODAY'S DATE: {date.today().isoformat()}

BRAND CONTEXT:
{json.dumps(brand_context, indent=2)}

CAMPAIGN GOAL:
{goal}

TARGET AUDIENCE:
{target_audience}

BUDGET (USD): {budget:,.2f}

Use your tools where needed, then produce your analysis as a single JSON object.""".strip()


class ResearchAgent:
    def __init__(self) -> None:
        self.llm = LLMFactory.get_llm(agent_type="research")

    def run(
        self,
        brand_context: Dict[str, Any],
        goal: str = "",
        target_audience: str = "",
        budget: float = 0.0,
    ) -> ResearchOutput:
        logger.info(
            "ResearchAgent.run | brand=%s | goal=%s",
            brand_context.get("name", "?"), goal[:80],
        )
        result: ResearchOutput = self.llm.generate_with_tools(
            system_prompt=SYSTEM_PROMPT,
            user_prompt=_build_user_prompt(brand_context, goal, target_audience, budget),
            tools=RESEARCH_TOOLS,
            response_schema=ResearchOutput,
            max_steps=6,
        )
        logger.info("ResearchAgent.run | complete")
        return result