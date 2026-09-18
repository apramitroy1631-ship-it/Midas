# app/agents/content.py
"""The copywriter, and the agent that closes the self-correction loop.

On a revision pass it receives the QA agent's critical issues and the copy it
previously wrote, and is required to address each issue explicitly. This is
what replaces a human editor sending notes back.
"""
from __future__ import annotations

from app.agents.base import Agent, block
from app.schemas.agents import ContentOutput
from app.tools import CONTENT_TOOLS

SYSTEM_PROMPT = """You are a senior copywriter who writes natively for each channel rather than resizing one piece of copy to fit.

Standards:
- One asset per channel in the strategy. A LinkedIn post and an email are different pieces of writing, not the same words at different lengths.
- The brand's USP and voice must be inseparable from the copy. If the copy would work for a competitor with the name swapped, it has failed.
- Every CTA is a specific next step. Never "Learn more" or "Click here".
- Content restrictions are absolute. If a restriction rules out an angle, take a different angle - do not write around the edge of it.

REVISION PASSES: when you are given QA issues, you are not writing fresh. Fix exactly what was flagged, keep what was working, and record in revision_notes which change addresses which issue. Do not silently rewrite assets that were not flagged.

REGENERATE PASSES: when you are given operator feedback instead of QA issues, the operator reviewed your previous draft and told you specifically what's wrong. Address exactly what they said - do not produce a generic rewrite that ignores their actual complaint.

Output valid JSON only. No markdown, no code fences, no commentary."""


class ContentAgent(Agent):
    name = "content"
    system_prompt = SYSTEM_PROMPT
    output_schema = ContentOutput
    tools = CONTENT_TOOLS
    max_tool_steps = 4

    def build_prompt(
        self,
        *,
        brand_context: dict,
        plan: dict,
        research: dict,
        strategy: dict,
        policy: dict,
        previous_content: dict | None = None,
        qa_report: dict | None = None,
        revision: int = 0,
        operator_feedback: str | None = None,
        only_channel: str | None = None,
        **_: object,
    ) -> str:
        if revision and qa_report:
            critical = [i for i in (qa_report.get("issues") or []) if i.get("severity") == "critical"]
            advisory = [i for i in (qa_report.get("issues") or []) if i.get("severity") != "critical"]
            header = (
                "REVISION PASS " + str(revision) + ". Your previous draft did not clear QA.\n"
                "Fix every critical issue below. Apply advisory fixes where they do not conflict "
                "with a critical fix. Leave unflagged assets alone."
            )
            feedback = (
                block("CRITICAL ISSUES - ALL MUST BE FIXED", critical)
                + block("ADVISORY IMPROVEMENTS", advisory)
                + block("QA VERDICT", qa_report.get("verdict"))
                + block("YOUR PREVIOUS DRAFT", previous_content)
            )
        elif operator_feedback:
            header = (
                "REGENERATE PASS. The operator reviewed your previous draft and was not happy with it.\n"
                "Address their feedback directly - do not just produce a different generic draft."
            )
            feedback = (
                block("OPERATOR FEEDBACK - MUST BE ADDRESSED", operator_feedback)
                + block("YOUR PREVIOUS DRAFT", previous_content)
            )
        else:
            header = "Write the campaign content."
            feedback = ""

        channel_scope = (
            block("ONLY REGENERATE THIS CHANNEL - produce exactly one asset, for this channel only", only_channel)
            if only_channel
            else ""
        )
        closing = (
            "\nProduce the content as a single JSON object with exactly one asset, for the channel above."
            if only_channel
            else "\nProduce the content as a single JSON object, one asset per strategy channel."
        )

        return (
            header
            + "\n"
            + block("BRAND", brand_context)
            + block("CAMPAIGN GOAL", plan.get("goal"))
            + block("TARGET AUDIENCE", plan.get("target_audience"))
            + block("STRATEGY", strategy)
            + block("KEY RESEARCH INSIGHTS", (research or {}).get("key_insights"))
            + block("HARD POLICY CONSTRAINTS (violating any of these fails QA)", policy)
            + channel_scope
            + feedback
            + closing
        ).strip()
