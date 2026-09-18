# app/agents/research.py
from __future__ import annotations

from datetime import date

from app.agents.base import Agent, block
from app.schemas.agents import ResearchOutput
from app.tools import RESEARCH_TOOLS

MARKET_FACTS_FRESH_DAYS = 30

SYSTEM_PROMPT = """You are a senior market research analyst. You produce grounded, decision-ready research for a specific brand and a specific campaign goal.

Standards:
- Check EXISTING MARKET FACTS first. If they are marked fresh and still fit this goal's audience angle, REUSE them directly for target_audience, market_size, growth_rate, and competitors instead of re-deriving from scratch - cite them in `sources` as 'brand memory: confirmed <researched_at date>'. Only re-research those fields if they are missing, marked stale, or clearly do not fit this specific goal.
- key_insights must still be produced fresh every run - they are about what shapes strategy for THIS goal, not the durable facts above.
- Market sizing comes from real sector benchmarks, not aspiration.
- Growth rates reflect realistic CAGR for the segment. Do not inflate to make the opportunity look better.
- Competitive intelligence names the exploitable gap, not just the positioning.
- Every insight must be usable by a strategist tomorrow. Generic category observations are worthless here.
- If a tool reports itself unavailable, continue from your own knowledge, mark figures as benchmark estimates, and say so in `sources`. Never fabricate a citation.

You answer the Campaign Director's research questions specifically. Those questions are the assignment.

Output valid JSON only. No markdown, no code fences, no commentary."""


def _market_facts_freshness(memory: dict) -> tuple[dict, str]:
    """How old the brand's stored market facts are, in a form the model doesn't
    have to compute itself - it just gets told fresh/stale and the day count."""
    facts = memory.get("market_facts") or {}
    researched_at = facts.get("researched_at") or ""
    if not researched_at:
        return facts, "none on file - research this from scratch"
    try:
        age_days = (date.today() - date.fromisoformat(researched_at[:10])).days
    except ValueError:
        return facts, "date unparseable - treat as none on file"
    if age_days <= MARKET_FACTS_FRESH_DAYS:
        return facts, f"FRESH - {age_days} days old, reuse unless it clearly doesn't fit this goal"
    return facts, f"STALE - {age_days} days old, re-research rather than trust these"


class ResearchAgent(Agent):
    name = "research"
    system_prompt = SYSTEM_PROMPT
    output_schema = ResearchOutput
    tools = RESEARCH_TOOLS
    max_tool_steps = 6

    def build_prompt(self, *, brand_context: dict, plan: dict, budget: float, **_: object) -> str:
        memory = brand_context.get("memory") or {}
        facts, freshness = _market_facts_freshness(memory)
        return (
            "Conduct the market research this campaign plan depends on.\n\n"
            "TODAY: " + date.today().isoformat() + "\n"
            "BUDGET (USD): " + format(budget, ",.2f") + "\n"
            + block("EXISTING MARKET FACTS (" + freshness + ")", facts)
            + block("BRAND", brand_context)
            + block("CAMPAIGN GOAL", plan.get("goal"))
            + block("TARGET AUDIENCE", plan.get("target_audience"))
            + block("QUESTIONS YOU MUST ANSWER (from the Campaign Director)", plan.get("research_focus"))
            + block("PLANNED CHANNELS", plan.get("channels"))
            + "\nUse your tools where they help, then produce your analysis as a single JSON object."
        ).strip()
