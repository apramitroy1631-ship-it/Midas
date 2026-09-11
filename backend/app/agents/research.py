# app/agents/research.py
from __future__ import annotations

from datetime import date

from app.agents.base import Agent, block
from app.schemas.agents import ResearchOutput
from app.tools import RESEARCH_TOOLS

SYSTEM_PROMPT = """You are a senior market research analyst. You produce grounded, decision-ready research for a specific brand and a specific campaign goal.

Standards:
- Market sizing comes from real sector benchmarks, not aspiration.
- Growth rates reflect realistic CAGR for the segment. Do not inflate to make the opportunity look better.
- Competitive intelligence names the exploitable gap, not just the positioning.
- Every insight must be usable by a strategist tomorrow. Generic category observations are worthless here.
- If a tool reports itself unavailable, continue from your own knowledge, mark figures as benchmark estimates, and say so in `sources`. Never fabricate a citation.

You answer the Campaign Director's research questions specifically. Those questions are the assignment.

Output valid JSON only. No markdown, no code fences, no commentary."""


class ResearchAgent(Agent):
    name = "research"
    system_prompt = SYSTEM_PROMPT
    output_schema = ResearchOutput
    tools = RESEARCH_TOOLS
    max_tool_steps = 6

    def build_prompt(self, *, brand_context: dict, plan: dict, budget: float, **_: object) -> str:
        return (
            "Conduct the market research this campaign plan depends on.\n\n"
            "TODAY: " + date.today().isoformat() + "\n"
            "BUDGET (USD): " + format(budget, ",.2f") + "\n"
            + block("BRAND", brand_context)
            + block("CAMPAIGN GOAL", plan.get("goal"))
            + block("TARGET AUDIENCE", plan.get("target_audience"))
            + block("QUESTIONS YOU MUST ANSWER (from the Campaign Director)", plan.get("research_focus"))
            + block("PLANNED CHANNELS", plan.get("channels"))
            + "\nUse your tools where they help, then produce your analysis as a single JSON object."
        ).strip()
