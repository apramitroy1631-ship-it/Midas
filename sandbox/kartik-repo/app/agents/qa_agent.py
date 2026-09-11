# app/agents/qa_agent.py
import json
import logging
from typing import Any, Dict

from app.schemas.qa import QAReport
from app.services.llm.llm_factory import LLMFactory

logger = logging.getLogger("agents.qa")

SYSTEM_PROMPT = """You are a senior campaign QA reviewer checking marketing content before it goes live.

Classify every finding into one of two buckets:

CRITICAL — blocks publishing:
- Content restriction violation
- Asset has no CTA at all
- Asset format completely wrong for the channel

RECOMMENDATIONS — quality improvements, does not block publishing:
- Generic copy, weak hook, buried USP
- CTA exists but could be sharper
- Tone or brand voice could be stronger

Set "passed" to true if there are zero critical issues.
Output valid JSON only — no markdown, no code fences, no commentary. Return exactly one JSON object."""

def _extract_restrictions(brand_context: Dict[str, Any]) -> list:
    """
    Content restrictions live inside memory.brand_guidelines, not at the
    top level of brand_context. This helper navigates the correct path.
    """
    memory = brand_context.get("memory") or {}
    if isinstance(memory, dict):
        guidelines = memory.get("brand_guidelines") or {}
    else:
        # BrandMemory pydantic object
        guidelines = getattr(memory, "brand_guidelines", {}) or {}

    if isinstance(guidelines, dict):
        return guidelines.get("content_restrictions", [])

    # BrandGuidelines pydantic object
    return getattr(guidelines, "content_restrictions", [])


def _build_user_prompt(
    content: Dict[str, Any],
    brand_context: Dict[str, Any],
    strategy: Dict[str, Any],
    goal: str,
    target_audience: str,
) -> str:
    return f"""Review the following campaign content before it goes live.

BRAND NAME: {brand_context.get("name", "")}
BRAND USP: {brand_context.get("usp", "")}
BRAND TONE: {brand_context.get("tone", "")}
CONTENT RESTRICTIONS: {json.dumps(_extract_restrictions(brand_context))}

CAMPAIGN GOAL: {goal}
TARGET AUDIENCE: {target_audience}

PLANNED CHANNELS: {json.dumps(strategy.get("channels", []))}

CONTENT ASSETS:
{json.dumps(content.get("assets", []), indent=2)}

For each asset evaluate:
1. Does it clearly belong to this brand without the brand name visible?
2. Does the USP come through naturally — not forced?
3. Is the format and tone native to the channel?
4. Does it violate any content restriction?
5. Does the CTA drive a specific action toward the campaign goal?

For any issue: name the channel, state the problem, explain why it matters.
Produce your review as a single JSON object.""".strip()


class QAAgent:
    def __init__(self) -> None:
        self.llm = LLMFactory.get_llm(agent_type="qa")

    def run(
        self,
        content: Dict[str, Any] | None,
        brand_context: Dict[str, Any] | None = None,
        strategy: Dict[str, Any] | None = None,
        goal: str = "",
        target_audience: str = "",
    ) -> QAReport:
        if not content or not content.get("assets"):
            return QAReport(
                passed=False,
                critical_issues=["No content assets were generated."],
                recommendations=["Re-run the content agent with a valid strategy."],
            )

        logger.info(
            "QAAgent.run | brand=%s | assets=%d",
            (brand_context or {}).get("name", "?"),
            len(content.get("assets", [])),
        )

        result: QAReport = self.llm.generate(
            system_prompt=SYSTEM_PROMPT,
            user_prompt=_build_user_prompt(
                content,
                brand_context or {},
                strategy or {},
                goal,
                target_audience,
            ),
            response_schema=QAReport,
        )

        logger.info(
            "QAAgent.run | passed=%s | critical_issues=%d | recommendations=%d",
            result.passed,
            len(result.critical_issues),
            len(result.recommendations),
        )
        return result