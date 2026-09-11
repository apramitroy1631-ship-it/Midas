# app/agents/analytics_agent.py
import json
from typing import Any, Dict

from app.schemas.analytics import AnalyticsReport
from app.services.llm.llm_factory import LLMFactory

SYSTEM_PROMPT = """You are a digital marketing analytics expert specialising in pre-launch campaign projection modelling.

Given a campaign's budget, channels, content, and goal, produce a realistic pre-launch forecast.
Base your estimates on industry-standard benchmarks for each channel type. Be conservative, not optimistic.

Benchmark reference ranges (adjust based on audience, creative quality, and sector):
- Instagram/TikTok paid social: CPM $6-12, CTR 0.5-1.5%
- Influencer partnerships: CPM $5-15 (engagement-based), CTR 1-3%
- Email marketing: open rate 20-35%, CTR 2-4%
- Health/fitness content/blogs: CPM $3-8, CTR 0.3-0.8%
- App Store Optimisation: impression-to-install rate 2-5% (organic)

Distribute the budget across channels proportionally based on their expected ROI for the stated goal.
Conversion rate reflects goal completions (e.g. installs, sign-ups) as a percentage of total clicks.

Output valid JSON only — no markdown, no code fences, no commentary. Return exactly one JSON object."""


def _build_user_prompt(
    content: Dict[str, Any],
    strategy: Dict[str, Any],
    goal: str,
    target_audience: str,
    budget: float,
) -> str:
    return f"""Generate a pre-launch analytics forecast for this campaign.

CAMPAIGN GOAL: {goal}
TARGET AUDIENCE: {target_audience}
TOTAL BUDGET (USD): ${budget:,.2f}

CHANNELS IN USE: {json.dumps(strategy.get("channels", []))}

CONTENT ASSETS:
{json.dumps(content.get("assets", []), indent=2)}

Forecast the expected performance if this campaign launches today.
Distribute the budget intelligently across the channels based on what will most efficiently achieve the goal.
Ensure aggregated totals are arithmetically consistent with the channel-level breakdown.

Produce your forecast as a single JSON object.""".strip()


class AnalyticsAgent:
    def __init__(self) -> None:
        self.llm = LLMFactory.get_llm(agent_type="analytics")

    def run(
        self,
        content: Dict[str, Any] | None,
        strategy: Dict[str, Any] | None = None,
        goal: str = "",
        target_audience: str = "",
        budget: float = 0.0,
    ) -> AnalyticsReport:
        if not content or not content.get("assets"):
            # Return zero-state if content is missing — avoids LLM hallucinating channels
            from app.schemas.analytics import ChannelPerformance
            return AnalyticsReport(
                total_impressions=0,
                total_clicks=0,
                overall_ctr=0.0,
                conversion_rate=0.0,
                channel_breakdown=[
                    ChannelPerformance(channel_name="no_content", impressions=0, clicks=0, ctr=0.0)
                ],
            )

        result: AnalyticsReport = self.llm.generate(
            system_prompt=SYSTEM_PROMPT,
            user_prompt=_build_user_prompt(
                content or {},
                strategy or {},
                goal,
                target_audience,
                budget,
            ),
            response_schema=AnalyticsReport,
        )
        return result