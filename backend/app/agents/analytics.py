# app/agents/analytics.py
from __future__ import annotations

from app.agents.base import Agent, block
from app.schemas.agents import AnalyticsReport

SYSTEM_PROMPT = """You are a performance forecasting analyst. You produce a pre-flight forecast for a campaign that is about to run, using the budget split and channel benchmarks.

Standards:
- Use realistic CPM and CTR benchmarks for each channel and audience. B2B LinkedIn is not consumer TikTok.
- Arithmetic must be internally consistent: totals equal the sum of the breakdown, and each ctr equals clicks/impressions*100.
- Conversion rate must be grounded in the goal type, not optimism.
- This is a forecast, not a promise. Prefer the conservative end of a benchmark range.

Output valid JSON only. No markdown, no code fences, no commentary."""


class AnalyticsAgent(Agent):
    name = "analytics"
    system_prompt = SYSTEM_PROMPT
    output_schema = AnalyticsReport

    def build_prompt(self, *, plan: dict, strategy: dict, budget: float, **_: object) -> str:
        return (
            "Forecast this campaign's performance.\n\n"
            "TOTAL BUDGET (USD): " + format(budget, ",.2f") + "\n"
            + block("CAMPAIGN GOAL", plan.get("goal"))
            + block("TARGET AUDIENCE", plan.get("target_audience"))
            + block("CHANNELS AND BUDGET SHARES", plan.get("channels"))
            + block("BUDGET ALLOCATION", (strategy or {}).get("budget_allocation"))
            + block("TACTICS", (strategy or {}).get("tactics"))
            + "\nProduce the forecast as a single JSON object."
        ).strip()
