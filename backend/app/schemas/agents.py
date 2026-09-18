# app/schemas/agents.py
"""Typed contracts for every agent in the pipeline.

Every one of these is used as an OpenAI structured-output schema, so the
constraints live in field *descriptions* rather than in JSON-Schema keywords
(`minItems`, `minLength` and friends are rejected by strict structured output).
The models still validate on the way back, which is what stops a hallucinated
shape from propagating into the graph state.
"""
from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field

# ---------------------------------------------------------------------------
# Orchestrator — the manager agent that plans the run
# ---------------------------------------------------------------------------


class PlannedChannel(BaseModel):
    model_config = ConfigDict(extra="forbid")

    channel: str = Field(
        ...,
        description="Exact channel name, e.g. 'linkedin', 'email', 'blog', 'x', 'instagram'.",
    )
    rationale: str = Field(
        ...,
        description="Why this channel earns budget for THIS goal and audience. One sentence, specific.",
    )
    budget_share: float = Field(
        ...,
        description="Fraction of the campaign budget assigned to this channel, 0.0-1.0. Shares must sum to ~1.0.",
    )


class OrchestrationPlan(BaseModel):
    """The manager agent's delegation decision for one run."""

    model_config = ConfigDict(extra="forbid")

    goal: str = Field(
        ...,
        description=(
            "The campaign goal this run will pursue, restated precisely and measurably. "
            "If the operator supplied a goal, sharpen it. If none was supplied, choose the "
            "highest-leverage goal available from brand memory and current positioning, and "
            "do not repeat an angle listed as exhausted."
        ),
    )
    goal_origin: str = Field(
        ...,
        description="Either 'operator' if a goal was supplied, or 'self-directed' if you chose it.",
    )
    reasoning: str = Field(
        ...,
        description=(
            "3-5 sentences explaining the plan: what the key bet is, why this audience, and what "
            "specifically you are doing differently from the brand's past campaigns."
        ),
    )
    target_audience: str = Field(
        ...,
        description="The precise audience segment this run targets. Sharper than the brand default.",
    )
    channels: list[PlannedChannel] = Field(
        ...,
        description="Two to four channels. Each must be somewhere this audience is genuinely reachable.",
    )
    research_focus: list[str] = Field(
        ...,
        description=(
            "Three to five specific questions the research agent must answer for this plan to "
            "hold up. These are delegation instructions, not generic topics."
        ),
    )
    success_criteria: list[str] = Field(
        ...,
        description=(
            "Two to four measurable criteria that define whether this run succeeded. "
            "The QA agent will be handed these to judge the finished content against."
        ),
    )
    risk_flags: list[str] = Field(
        ...,
        description=(
            "Anything about this brand, claim set, or regulatory context that the QA agent must "
            "treat as blocking. Empty list if genuinely none."
        ),
    )


# ---------------------------------------------------------------------------
# Research
# ---------------------------------------------------------------------------


class Competitor(BaseModel):
    model_config = ConfigDict(extra="forbid")

    name: str = Field(..., description="Full brand or product name of the competitor.")
    positioning: str = Field(
        ...,
        description=(
            "How this competitor positions itself AND where that positioning leaves a gap this "
            "brand can exploit. Identify what they fail to do for the audience, not just what they do."
        ),
    )


class MarketFacts(BaseModel):
    """Durable market research for a brand — audience, sizing, competitors.

    Reused across runs instead of re-deriving the same analysis from scratch
    every time. Written by the Learning agent, read by the Research agent.
    """

    model_config = ConfigDict(extra="forbid")

    target_audience: str = Field(default="", description="The brand's confirmed audience profile.")
    market_size: str = Field(default="", description="Confirmed TAM in USD millions, e.g. '186000' for $186B.")
    growth_rate: str = Field(default="", description="Confirmed annual CAGR percentage, e.g. '14.5'.")
    competitors: list["Competitor"] = Field(
        default_factory=list, description="Confirmed competitors and their positioning gaps."
    )
    researched_at: str = Field(
        default="", description="ISO date these facts were last confirmed or updated. Empty if never set."
    )


class ResearchOutput(BaseModel):
    model_config = ConfigDict(extra="forbid")

    target_audience: str = Field(
        ...,
        description=(
            "A specific, actionable audience profile: demographics, psychographics, behaviours, "
            "and what actually motivates them to act. Go well beyond age/gender bands. 10-500 chars."
        ),
    )
    market_size: str = Field(
        ...,
        description="Total addressable market in USD millions, grounded in a credible sector estimate. e.g. '186000' for $186B.",
    )
    growth_rate: str = Field(
        ...,
        description="Realistic annual CAGR percentage for the segment, based on sector benchmarks. Do not inflate. e.g. '14.5'.",
    )
    key_insights: list[str] = Field(
        ...,
        description=(
            "At least three insights that each reveal a specific opportunity, behaviour pattern, or "
            "market condition that shapes strategy for THIS goal. Generic category observations are not acceptable."
        ),
    )
    competitors: list[Competitor] = Field(
        ...,
        description="At least two competitors the target audience is most likely already using or considering.",
    )
    sources: list[str] = Field(
        ...,
        description=(
            "URLs or named sources backing the figures above. If live search was unavailable, say so "
            "explicitly with an entry like 'model-knowledge: no live search configured'."
        ),
    )


# ---------------------------------------------------------------------------
# Strategy
# ---------------------------------------------------------------------------


class StrategyOutput(BaseModel):
    model_config = ConfigDict(extra="forbid")

    summary: str = Field(
        ...,
        description=(
            "A 3-5 sentence executive summary: what the approach is, why it works for this audience "
            "and goal, and what the key bet is. Must be grounded in the research findings."
        ),
    )
    objectives: list[str] = Field(
        ...,
        description=(
            "At least two measurable objectives, each with a metric and a relative timeframe "
            "('within 30 days', 'by week 4'), achievable within the stated budget."
        ),
    )
    tactics: list[str] = Field(
        ...,
        description=(
            "At least three concrete executable actions, each implying where budget goes and what "
            "outcome it drives. 'Allocate 40% of budget to LinkedIn thought-leadership ads targeting "
            "ops leaders at 200-2000 headcount logistics firms' - not 'use social media'."
        ),
    )
    channels: list[str] = Field(
        ...,
        description="The channels selected, matching the tactics and the orchestrator's plan.",
    )
    budget_allocation: list[str] = Field(
        ...,
        description="One line per channel: 'linkedin: $2000 (40%)'. Must sum to the campaign budget.",
    )


# ---------------------------------------------------------------------------
# Content
# ---------------------------------------------------------------------------


class ContentAsset(BaseModel):
    model_config = ConfigDict(extra="forbid")

    headline: str = Field(
        ...,
        description=(
            "The primary hook. Channel-appropriate in length and style: punchy for social, "
            "benefit-led for email subject lines, keyword-aware for blog. Must carry the brand's tone."
        ),
    )
    body: str = Field(
        ...,
        description=(
            "Main copy. Length and style must match the channel. The brand identity and USP must come "
            "through naturally, not bolted on. Copy that could belong to any brand is not acceptable."
        ),
    )
    call_to_action: str = Field(
        ...,
        description=(
            "A specific CTA tailored to channel and goal, creating a genuine next step. "
            "Not 'Learn more' or 'Click here'."
        ),
    )
    channel: str = Field(..., description="Exact channel this asset targets, from the strategy's channel list.")


class ContentOutput(BaseModel):
    model_config = ConfigDict(extra="forbid")

    assets: list[ContentAsset] = Field(
        ...,
        description=(
            "One asset per channel in the strategy. Each must be natively written for its channel, "
            "not a reskin of the same copy."
        ),
    )
    revision_notes: str = Field(
        ...,
        description=(
            "If this is a revision, state exactly what you changed and which QA issue each change "
            "addresses. If this is the first draft, write 'initial draft'."
        ),
    )


# ---------------------------------------------------------------------------
# SEO / distribution
# ---------------------------------------------------------------------------


class SEOAsset(BaseModel):
    model_config = ConfigDict(extra="forbid")

    channel: str = Field(..., description="Channel this optimisation applies to, matching a content asset.")
    primary_keyword: str = Field(..., description="The single keyword or phrase this asset should rank or index for.")
    secondary_keywords: list[str] = Field(..., description="Three to six supporting terms, semantically related.")
    meta_title: str = Field(..., description="Under 60 characters, keyword-leading, still readable as a human sentence.")
    meta_description: str = Field(..., description="Under 155 characters, benefit-led, contains the primary keyword once.")
    slug: str = Field(..., description="Lowercase hyphenated URL slug. No stop words.")
    hashtags: list[str] = Field(..., description="Channel-appropriate hashtags, or an empty list where they do not apply.")


class SEOOutput(BaseModel):
    model_config = ConfigDict(extra="forbid")

    per_asset: list[SEOAsset] = Field(..., description="One entry per content asset, matched by channel.")
    distribution_notes: list[str] = Field(
        ...,
        description="Posting-time, format, and sequencing guidance specific to each channel.",
    )


# ---------------------------------------------------------------------------
# QA — the gate that replaces the human reviewer
# ---------------------------------------------------------------------------


class QAIssue(BaseModel):
    model_config = ConfigDict(extra="forbid")

    channel: str = Field(..., description="Which asset this issue belongs to.")
    severity: str = Field(..., description="Exactly one of: 'critical' or 'advisory'.")
    issue: str = Field(..., description="The specific defect, quoting the offending copy where possible.")
    fix: str = Field(
        ...,
        description=(
            "A concrete instruction the content agent can act on directly in a revision pass. "
            "Not 'improve the hook' but 'rewrite the headline to lead with the 40% pick-time figure'."
        ),
    )


class QAReport(BaseModel):
    model_config = ConfigDict(extra="forbid")

    passed: bool = Field(
        ...,
        description=(
            "True only if there are zero critical issues. Copy-quality problems are advisory and do "
            "not set this to false. Set false only for: brand/content restriction breaches, "
            "forbidden or unverifiable claims, a missing CTA entirely, an asset on the wrong channel, "
            "or a failure against the orchestrator's stated success criteria."
        ),
    )
    verdict: str = Field(..., description="Two sentences: what is strong, and what (if anything) blocks publication.")
    brand_safety_score: int = Field(..., description="0-100. How safely this content represents the brand.")
    goal_alignment_score: int = Field(..., description="0-100. How well the content serves the stated campaign goal.")
    issues: list[QAIssue] = Field(..., description="Every issue found, critical and advisory. Empty list if clean.")


# ---------------------------------------------------------------------------
# Analytics + learning
# ---------------------------------------------------------------------------


class ChannelPerformance(BaseModel):
    model_config = ConfigDict(extra="forbid")

    channel_name: str = Field(..., description="Channel name, matching the strategy exactly.")
    impressions: int = Field(..., description="Estimated impressions from the channel's budget and standard CPM benchmarks.")
    clicks: int = Field(..., description="Estimated clicks from impressions and a realistic CTR benchmark. Never exceeds impressions.")
    ctr: float = Field(..., description="(clicks / impressions) * 100. Must be arithmetically consistent with the two fields above.")


class AnalyticsReport(BaseModel):
    model_config = ConfigDict(extra="forbid")

    total_impressions: int = Field(..., description="Sum of channel impressions. Must equal the breakdown total.")
    total_clicks: int = Field(..., description="Sum of channel clicks. Must equal the breakdown total.")
    overall_ctr: float = Field(..., description="(total_clicks / total_impressions) * 100.")
    conversion_rate: float = Field(
        ...,
        description="Estimated percentage of clicks completing the goal. Ground in benchmarks: 1-5% app installs, 5-15% email signups.",
    )
    projected_cac_usd: float = Field(..., description="Budget divided by projected conversions.")
    channel_breakdown: list[ChannelPerformance] = Field(..., description="One entry per strategy channel.")


class LearningOutput(BaseModel):
    """What the system writes back into brand memory. This is the improvement loop."""

    model_config = ConfigDict(extra="forbid")

    insights: list[str] = Field(
        ...,
        description=(
            "Two to four durable lessons from this run that should change how the NEXT run for this "
            "brand is planned. Must be specific to this brand, not marketing platitudes."
        ),
    )
    winning_angles: list[str] = Field(
        ...,
        description="Angles or hooks from this run worth reusing, based on QA scores and forecast performance.",
    )
    exhausted_angles: list[str] = Field(
        ...,
        description="Angles now used up for this brand, which the orchestrator should avoid repeating next run.",
    )
    next_goal_suggestion: str = Field(
        ...,
        description="The single highest-leverage campaign goal this brand should pursue next, and one line on why.",
    )
    market_facts: MarketFacts = Field(
        ...,
        description=(
            "The brand's durable market facts. If EXISTING MARKET FACTS were provided and this run's "
            "research did not materially change them, return them UNCHANGED (including the original "
            "researched_at date). If this run's research meaningfully corrected or updated them (or none "
            "existed yet), return the new values with researched_at set to today."
        ),
    )
