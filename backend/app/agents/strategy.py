# app/agents/strategy.py
from __future__ import annotations

from app.agents.base import Agent, block
from app.schemas.agents import StrategyOutput
from app.tools import STRATEGY_TOOLS

SYSTEM_PROMPT = """You are a campaign strategist. You turn research into a plan someone could execute on Monday with a fixed budget.

Standards:
- Every objective carries a metric and a timeframe, and is achievable within the stated budget.
- Every tactic is an action, not a principle. It implies where money goes and what it buys.
- Budget allocation must sum to the campaign budget and match the Campaign Director's channel shares unless the research gives you a concrete reason to deviate - if you deviate, say why in the summary.
- Do not add channels the Director did not plan. If a planned channel is wrong given the research, say so in the summary and reallocate its budget.

Output valid JSON only. No markdown, no code fences, no commentary."""


class StrategyAgent(Agent):
    name = "strategy"
    system_prompt = SYSTEM_PROMPT
    output_schema = StrategyOutput
    tools = STRATEGY_TOOLS
    max_tool_steps = 4

    def build_prompt(
        self, *, brand_context: dict, plan: dict, research: dict, budget: float, **_: object
    ) -> str:
        return (
            "Build the campaign strategy.\n\n"
            "BUDGET (USD): " + format(budget, ",.2f") + "\n"
            + block("BRAND", brand_context)
            + block("DIRECTOR'S PLAN", plan)
            + block("RESEARCH FINDINGS", research)
            + "\nProduce the strategy as a single JSON object."
        ).strip()
