# app/agents/content_agent.py
import json
import logging
from typing import Any, Dict

from app.schemas.content import ContentOutput
from app.services.llm.llm_factory import LLMFactory
from app.tools import CONTENT_TOOLS

logger = logging.getLogger("agents.content")

SYSTEM_PROMPT = """You are a performance marketing copywriter who writes channel-native campaign content.

Quality standards:
- Every asset must feel native to its channel — a TikTok script reads nothing like an email
- The USP is the hook — lead with what makes the brand different, not a generic pain point any competitor could claim
- Respect all brand content restrictions without exception
- CTAs must be specific and create genuine urgency — not generic instructions

Output valid JSON only — no markdown, no code fences, no commentary. Return exactly one JSON object."""


def _build_user_prompt(
    strategy: Dict[str, Any],
    brand_context: Dict[str, Any],
    goal: str,
    target_audience: str,
    budget: float,
) -> str:
    brand_id = brand_context.get("id", brand_context.get("_id", ""))
    return f"""Write campaign content assets for each channel in the strategy below.

BRAND ID: {brand_id}

BRAND CONTEXT:
{json.dumps(brand_context, indent=2)}

CAMPAIGN GOAL:
{goal}

TARGET AUDIENCE:
{target_audience}

BUDGET (USD): ${budget:,.2f}

STRATEGY:
{json.dumps(strategy, indent=2)}

Use your tools where needed, then produce one content asset per channel as a single JSON object.""".strip()


class ContentAgent:
    def __init__(self) -> None:
        self.llm = LLMFactory.get_llm(agent_type="content")

    def run(
        self,
        strategy: Dict[str, Any] | None,
        brand_context: Dict[str, Any] | None = None,
        goal: str = "",
        target_audience: str = "",
        budget: float = 0.0,
    ) -> ContentOutput:
        brand_context = brand_context or {}
        logger.info(
            "ContentAgent.run | brand=%s | goal=%s",
            brand_context.get("name", "?"), goal[:80],
        )
        result: ContentOutput = self.llm.generate_with_tools(
            system_prompt=SYSTEM_PROMPT,
            user_prompt=_build_user_prompt(
                strategy or {},
                brand_context,
                goal,
                target_audience,
                budget,
            ),
            tools=CONTENT_TOOLS,
            response_schema=ContentOutput,
            max_steps=4,
        )
        logger.info("ContentAgent.run | complete")
        return result