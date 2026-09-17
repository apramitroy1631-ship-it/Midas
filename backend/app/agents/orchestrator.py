# app/agents/orchestrator.py
"""The manager agent.

Sits above the specialists and decides what this run is actually for: it
sharpens (or invents) the goal, picks channels and budget split, and writes the
delegation brief the downstream agents are bound by. Nothing below it chooses
its own scope.
"""
from __future__ import annotations

from datetime import date

from app.agents.base import Agent, block
from app.schemas.agents import OrchestrationPlan
from app.tools import ORCHESTRATOR_TOOLS

SYSTEM_PROMPT = """You are the Campaign Director of an autonomous marketing system. You do not write copy. You decide what the campaign is, who it is for, and where the budget goes, then you delegate.

You are operating with no human in the loop. There is nobody to ask, and nobody will review your plan before the specialists act on it. Commit to a decision and make it specific enough to execute.

How you work:
- Read brand memory FIRST. Repeating an angle listed as exhausted is a failure of your job.
- If no goal was supplied, choose one. Pick the highest-leverage goal available given the brand's positioning, the gaps in its past campaigns, and what its memory says worked. Do not pick a safe generic goal.
- Channels must be earned, not listed. Two to four, each somewhere this specific audience is genuinely reachable at this budget. If a CHANNEL OVERRIDE is given, that list is a hard constraint from the operator, not your call to make — use exactly it, however many channels that is, and give each its full budget_share (100% if it's one channel).
- Your research_focus entries are orders to the research agent. Make them answerable questions, not topics.
- Your success_criteria are what the QA agent will judge the finished content against. Write them so that a piece of content either clearly meets them or clearly does not.

Output valid JSON only. No markdown, no code fences, no commentary."""


class OrchestratorAgent(Agent):
    name = "orchestrator"
    system_prompt = SYSTEM_PROMPT
    output_schema = OrchestrationPlan
    tools = ORCHESTRATOR_TOOLS
    max_tool_steps = 4

    def build_prompt(
        self,
        *,
        brand_context: dict,
        goal: str | None,
        target_audience: str | None,
        channels: list[str] | None = None,
        budget: float,
        policy: dict,
        **_: object,
    ) -> str:
        channel_line = (
            "CHANNEL OVERRIDE (mandatory, exhaustive — use exactly these channels and no others): "
            + str(list(channels)) + "\n"
            if channels
            else ""
        )
        goal_line = (
            'OPERATOR GOAL: "' + goal + '"\nSharpen this into something measurable. Do not replace it.'
            if goal
            else (
                "OPERATOR GOAL: none supplied.\n"
                "You must choose the goal yourself. Use get_brand_memory and get_past_campaigns on "
                "brand_id '" + str(brand_context.get("id", "")) + "' to see what has already been "
                "tried, then pick the highest-leverage goal that has not been worked."
            )
        )

        return (
            "Plan a marketing campaign run.\n\n"
            "TODAY: " + date.today().isoformat() + "\n"
            "BUDGET (USD): " + format(budget, ",.2f") + "\n\n"
            + channel_line
            + goal_line
            + "\n"
            + block("BRAND", brand_context)
            + block("AUDIENCE HINT FROM OPERATOR", target_audience)
            + block("TENANT POLICY (hard constraints you must plan within)", policy)
            + "\nProduce the delegation plan as a single JSON object."
        ).strip()
