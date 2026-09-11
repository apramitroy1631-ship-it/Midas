# app/agents/qa.py
"""The QA agent is the gate that stands in for a human reviewer.

Because nothing downstream of it is checked by a person, it is deliberately the
strictest agent in the system and runs on the strongest model. Its `passed`
verdict decides whether content publishes or goes back for revision.
"""
from __future__ import annotations

from app.agents.base import Agent, block
from app.schemas.agents import QAReport

SYSTEM_PROMPT = """You are the final reviewer. Nothing you approve is seen by a human before it is published, so you are the only thing standing between a bad asset and the brand's audience. Review accordingly.

Mark an issue `critical` only when it genuinely must block publication:
- it breaches a brand content restriction or a tenant policy constraint
- it makes a factual, health, financial, or performance claim the research does not support
- it uses a banned phrase or omits a required disclaimer
- an asset has no call to action at all
- an asset is written for the wrong channel in a way that cannot run
- it fails one of the Campaign Director's stated success criteria

Mark everything else `advisory`: weak hooks, generic copy, a buried USP, a vague-but-present CTA, tone drift.

Rules you must follow:
- `passed` is true if and only if there are zero critical issues. Advisory issues never set it false.
- Every issue names its channel, quotes or points at the specific offending copy, and gives a fix a copywriter can act on directly.
- Do not invent critical issues to look diligent. Blocking clean content wastes a revision cycle and the budget that goes with it.
- Do not pass content you have doubts about because it is a revision. A third weak draft is still a fail.
- Score brand_safety and goal_alignment honestly on 0-100. These are tracked over time.

Output valid JSON only. No markdown, no code fences, no commentary."""


class QAAgent(Agent):
    name = "qa"
    system_prompt = SYSTEM_PROMPT
    output_schema = QAReport

    def build_prompt(
        self,
        *,
        brand_context: dict,
        plan: dict,
        strategy: dict,
        content: dict,
        research: dict,
        policy: dict,
        revision: int = 0,
        **_: object,
    ) -> str:
        restrictions = ((brand_context.get("memory") or {}).get("brand_guidelines") or {}).get(
            "content_restrictions", []
        )
        pass_note = (
            "\nThis is revision " + str(revision) + ". Judge it on its merits, not on effort spent.\n"
            if revision
            else ""
        )
        return (
            "Review this campaign content for publication.\n"
            + pass_note
            + block("BRAND", {k: brand_context.get(k) for k in ("name", "industry", "tone", "usp")})
            + block("BRAND CONTENT RESTRICTIONS (absolute)", restrictions)
            + block("TENANT POLICY (absolute)", policy)
            + block("CAMPAIGN GOAL", plan.get("goal"))
            + block("SUCCESS CRITERIA YOU ARE JUDGING AGAINST", plan.get("success_criteria"))
            + block("RISK FLAGS FROM THE DIRECTOR", plan.get("risk_flags"))
            + block("STRATEGY CHANNELS", (strategy or {}).get("channels"))
            + block("RESEARCH THE CLAIMS MUST BE CONSISTENT WITH", research)
            + block("CONTENT UNDER REVIEW", content)
            + "\nProduce your report as a single JSON object."
        ).strip()
