# app/agents/learning.py
"""The agent that makes the system compound.

Its output is written straight back into brand memory, which the orchestrator
reads at the start of the next run. Without this node the system would produce
the same campaign forever; with it, each run constrains the next.
"""
from __future__ import annotations

from app.agents.base import Agent, block
from app.schemas.agents import LearningOutput

SYSTEM_PROMPT = """You are the system's memory. You have just watched a full campaign run end to end, and you decide what the next run for this brand should inherit from it.

What you write is fed directly to the Campaign Director next time. It is not a report for a human; it is an instruction to a future planner.

Standards:
- Insights must be specific to THIS brand and falsifiable by the next run. "Video performs well" is useless. "This audience responds to operational specifics over vision statements - the 40% pick-time figure carried every asset that scored above 85" is useful.
- Winning angles are ones QA scored well and the forecast supports. Be honest about which.
- Exhausted angles are genuinely used up. Marking an angle exhausted removes it from the next planner's options, so do not over-mark; two or three at most.
- The next goal suggestion should be the highest-leverage thing this brand has not yet worked, with one line on why.

Output valid JSON only. No markdown, no code fences, no commentary."""


class LearningAgent(Agent):
    name = "analytics"  # shares the analytics model tier - same cost profile
    system_prompt = SYSTEM_PROMPT
    output_schema = LearningOutput

    def build_prompt(
        self,
        *,
        brand_context: dict,
        plan: dict,
        strategy: dict,
        content: dict,
        qa_report: dict,
        analytics: dict,
        revisions: int,
        **_: object,
    ) -> str:
        memory = brand_context.get("memory") or {}
        return (
            "Extract what the next campaign for this brand should inherit from this run.\n\n"
            "REVISION CYCLES THIS RUN NEEDED: " + str(revisions) + "\n"
            + block("BRAND", {k: brand_context.get(k) for k in ("name", "industry", "usp")})
            + block("EXISTING MEMORY (do not simply restate this)", {
                "latest_insights": (memory.get("latest_insights") or [])[-8:],
                "winning_angles": (memory.get("winning_angles") or [])[-8:],
                "exhausted_angles": (memory.get("exhausted_angles") or [])[-12:],
            })
            + block("GOAL PURSUED", plan.get("goal"))
            + block("STRATEGY SUMMARY", (strategy or {}).get("summary"))
            + block("CONTENT SHIPPED", (content or {}).get("assets"))
            + block("QA OUTCOME", {
                "passed": (qa_report or {}).get("passed"),
                "verdict": (qa_report or {}).get("verdict"),
                "brand_safety_score": (qa_report or {}).get("brand_safety_score"),
                "goal_alignment_score": (qa_report or {}).get("goal_alignment_score"),
                "issues": (qa_report or {}).get("issues"),
            })
            + block("PERFORMANCE FORECAST", analytics)
            + "\nProduce your memory update as a single JSON object."
        ).strip()
