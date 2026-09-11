# app/services/llm/simulator_provider.py
"""Offline simulator provider.

Produces schema-valid, prompt-derived output with no network call, so the graph,
the streaming layer, the persistence layer and the UI can all be exercised
without API credits. It is a development and demo aid, NOT a model: the copy it
writes is templated, and any number it emits is invented.

It is deliberately not a rubber stamp. The first QA pass raises a real critical
issue and the revision pass clears it, so the autonomous self-correction loop
runs for real rather than being skipped by an always-passing reviewer.

Switch to real inference by setting LLM_PROVIDER=openai (or anthropic) with a
funded key - nothing else in the system changes.
"""
from __future__ import annotations

import logging
import random
import re
from typing import Any, Sequence

from langchain_core.tools import BaseTool
from pydantic import BaseModel

from app.schemas.agents import (
    AnalyticsReport,
    ChannelPerformance,
    Competitor,
    ContentAsset,
    ContentOutput,
    LearningOutput,
    OrchestrationPlan,
    PlannedChannel,
    QAIssue,
    QAReport,
    ResearchOutput,
    SEOAsset,
    SEOOutput,
    StrategyOutput,
)

from .base import BaseLLM

logger = logging.getLogger("simulator_provider")

_CPM = {"linkedin": 33.0, "email": 2.0, "blog": 4.5, "x": 7.0, "instagram": 9.0, "tiktok": 10.0}
_CTR = {"linkedin": 0.55, "email": 2.4, "blog": 1.6, "x": 0.9, "instagram": 0.8, "tiktok": 1.1}


def _field(prompt: str, label: str) -> str:
    """Pull a labelled block back out of the prompt the agent built."""
    match = re.search(re.escape(label) + r":\s*\n(.+?)(?:\n\n[A-Z]|\Z)", prompt, re.S)
    return match.group(1).strip() if match else ""


def _json_value(prompt: str, key: str) -> str:
    match = re.search(r'"' + re.escape(key) + r'"\s*:\s*"([^"]{2,300})"', prompt)
    return match.group(1) if match else ""


def _brand(prompt: str) -> str:
    return _json_value(prompt, "name") or "the brand"


def _usp(prompt: str) -> str:
    return _json_value(prompt, "usp") or "a measurable operational advantage"


def _goal(prompt: str) -> str:
    goal = _field(prompt, "CAMPAIGN GOAL") or _field(prompt, "GOAL PURSUED")
    if not goal:
        match = re.search(r'OPERATOR GOAL:\s*"([^"]+)"', prompt)
        goal = match.group(1) if match else ""
    return goal.strip().strip('"') or "grow qualified pipeline from the core audience"


def _audience(prompt: str) -> str:
    aud = _field(prompt, "TARGET AUDIENCE") or _json_value(prompt, "target_audience")
    return aud.strip() or "operations decision-makers at mid-market companies"


def _channels(prompt: str) -> list[str]:
    found = re.findall(r'"channel"\s*:\s*"([a-z0-9_-]+)"', prompt, re.I)
    if not found:
        found = re.findall(r'"(linkedin|email|blog|x|instagram|tiktok)"', prompt, re.I)
    seen: list[str] = []
    for c in found:
        c = c.lower()
        if c not in seen:
            seen.append(c)
    return seen[:4] or ["linkedin", "email", "blog"]


def _budget(prompt: str) -> float:
    match = re.search(r"BUDGET \(USD\):\s*([\d,]+\.?\d*)", prompt)
    return float(match.group(1).replace(",", "")) if match else 5000.0


# ---------------------------------------------------------------------------
# Per-schema synthesis
# ---------------------------------------------------------------------------


def _plan(prompt: str) -> OrchestrationPlan:
    brand, goal, usp = _brand(prompt), _goal(prompt), _usp(prompt)
    self_directed = "none supplied" in prompt
    if self_directed:
        goal = "Convert existing evaluators into booked demos by leading with " + usp
    channels = ["linkedin", "email", "blog"]
    shares = [0.5, 0.3, 0.2]
    return OrchestrationPlan(
        goal=goal,
        goal_origin="self-directed" if self_directed else "operator",
        reasoning=(
            "The bet is specificity: " + brand + " wins when it leads with a number rather than a "
            "category claim. Research must confirm the figure holds outside the flagship deployment "
            "before any asset repeats it. Budget concentrates on the one channel where this audience "
            "already evaluates vendors, with email carrying the follow-up and the blog carrying proof."
        ),
        target_audience=_audience(prompt),
        channels=[
            PlannedChannel(
                channel=c,
                rationale=(
                    "This audience already evaluates vendors here, and the format supports the "
                    "operational detail the claim needs."
                ),
                budget_share=s,
            )
            for c, s in zip(channels, shares)
        ],
        research_focus=[
            "What is the current addressable market size and CAGR for this segment?",
            "Which two competitors does this audience most often shortlist, and what do they fail to offer?",
            "What objection kills this deal most often at the evaluation stage?",
            "What proof format does this buyer trust: case study, benchmark, or peer reference?",
        ],
        success_criteria=[
            "Every asset states a specific, sourced figure rather than a category claim.",
            "Every asset carries a next step that names what happens after the click.",
            "No asset repeats an angle listed as exhausted in brand memory.",
        ],
        risk_flags=[
            "Performance figures must be attributed, not stated as universal guarantees.",
        ],
    )


def _research(prompt: str) -> ResearchOutput:
    return ResearchOutput(
        target_audience=_audience(prompt)[:480],
        market_size="12400",
        growth_rate="11.8",
        key_insights=[
            "Evaluation stalls at internal justification, not at product comparison - buyers need a "
            "number they can defend to a CFO, not another feature list.",
            "This audience discounts any claim without a named deployment context behind it.",
            "Peer proof outperforms vendor proof: a named operator's account converts better than a "
            "benchmark chart from the vendor.",
            "The shortlist forms before first contact, so category-level awareness copy arrives too late.",
        ],
        competitors=[
            Competitor(
                name="Incumbent platform vendor",
                positioning=(
                    "Positions on breadth of integrations. Leaves a gap on time-to-value: buyers "
                    "report multi-quarter deployments with no interim proof point."
                ),
            ),
            Competitor(
                name="Low-cost regional challenger",
                positioning=(
                    "Positions on price. Leaves a gap on operational credibility - no published "
                    "deployment data, which this buyer treats as disqualifying."
                ),
            ),
        ],
        sources=["model-knowledge: simulator provider, no live search configured"],
    )


def _strategy(prompt: str) -> StrategyOutput:
    budget = _budget(prompt)
    channels = _channels(prompt) or ["linkedin", "email", "blog"]
    shares = [0.5, 0.3, 0.2][: len(channels)]
    shares = shares + [round((1 - sum(shares)) / max(1, len(channels) - len(shares)), 2)] * (
        len(channels) - len(shares)
    )
    return StrategyOutput(
        summary=(
            "Lead with one defensible number and make it easy to forward internally. The campaign "
            "concentrates spend where the shortlist actually forms, uses email to carry the proof "
            "asset to people already in evaluation, and uses the blog as the citable artefact both "
            "other channels point at. The key bet is that a single sourced figure outperforms a "
            "broader feature narrative with this buyer."
        ),
        objectives=[
            "Generate 40 qualified demo requests within 30 days at or below the forecast CAC.",
            "Reach 25% of the named target account list with at least two touches by week 4.",
        ],
        tactics=[
            "Allocate " + str(int(shares[0] * 100)) + "% of budget to " + channels[0]
            + " targeting operations titles at 200-2000 headcount firms, with the proof figure in the first line.",
            "Sequence a three-email follow-up to engaged readers, each carrying one objection-handling proof point.",
            "Publish the deployment breakdown as the citable artefact both paid channels link to.",
        ],
        channels=channels,
        budget_allocation=[
            c + ": $" + format(round(budget * s), ",") + " (" + str(int(s * 100)) + "%)"
            for c, s in zip(channels, shares)
        ],
    )


def _content(prompt: str) -> ContentOutput:
    revision = "REVISION PASS" in prompt
    brand, usp = _brand(prompt), _usp(prompt)
    channels = _channels(prompt) or ["linkedin", "email", "blog"]

    assets = []
    for channel in channels:
        if channel == "email":
            headline = "The number your CFO will ask for"
            body = (
                "You already know what " + brand + " does. What you probably need is the figure you "
                "can put in a business case: " + usp + " Across deployed customers that has held "
                "within a predictable band, and the breakdown of how it is measured is linked below. "
                "No demo required to read it."
            )
            cta = "Read the deployment breakdown, then book time if the maths holds"
        elif channel == "blog":
            headline = "How we measure the number we lead with"
            body = (
                "Vendors quote improvement figures without saying what was measured, over what "
                "period, against what baseline. This is the full methodology behind " + usp + " - "
                "the baseline, the measurement window, and the two conditions under which the figure "
                "does not hold. It is written to be forwarded to whoever has to approve the spend."
            )
            cta = "See the full methodology and the conditions where it does not apply"
        else:
            headline = usp.rstrip(".") + " - here is the measurement behind it"
            body = (
                "Most operations teams do not lose the evaluation on features. They lose it at the "
                "internal justification step, because nobody can defend the vendor's number. So here "
                "is ours, with the baseline and the measurement window attached. Take it to your CFO "
                "before you take a call with us."
            )
            cta = "Get the one-page proof before you book anything"

        if revision:
            body = body + " Figures reflect deployed customer averages and are not guarantees."

        assets.append(
            ContentAsset(headline=headline, body=body, call_to_action=cta, channel=channel)
        )

    return ContentOutput(
        assets=assets,
        revision_notes=(
            "Added the attribution qualifier to every asset so the performance figure reads as a "
            "deployed-customer average rather than a universal guarantee, addressing the critical "
            "QA issue. Headlines and CTAs left unchanged - they were not flagged."
            if revision
            else "initial draft"
        ),
    )


def _seo(prompt: str) -> SEOOutput:
    channels = _channels(prompt) or ["linkedin", "email", "blog"]
    per_asset = []
    for channel in channels:
        keyword = "warehouse automation roi" if channel != "email" else "warehouse automation business case"
        per_asset.append(
            SEOAsset(
                channel=channel,
                primary_keyword=keyword,
                secondary_keywords=[
                    "pick time reduction",
                    "amr deployment benchmark",
                    "warehouse robotics payback period",
                    "3pl automation case study",
                ],
                meta_title="Warehouse Automation ROI: The Measured Numbers",
                meta_description=(
                    "The baseline, measurement window, and limits behind our warehouse automation ROI "
                    "figure - written to be forwarded to finance."
                ),
                slug="warehouse-automation-roi-methodology",
                hashtags=["#WarehouseOps", "#Logistics", "#Automation"] if channel in ("linkedin", "x", "instagram") else [],
            )
        )
    return SEOOutput(
        per_asset=per_asset,
        distribution_notes=[
            "LinkedIn: post Tuesday-Thursday 08:00-09:30 local to the target region; lead with the figure in line one, no link in the first 140 characters.",
            "Email: send Tuesday 06:30 local; single CTA, proof asset above the fold.",
            "Blog: publish before the paid channels run so both have a live artefact to cite.",
        ],
    )


def _qa(prompt: str) -> QAReport:
    """First pass flags a real policy violation; the revision pass clears it.

    This keeps the self-correction loop honest in offline mode instead of
    letting a permanently-passing reviewer skip it.
    """
    revision = "This is revision" in prompt
    channels = _channels(prompt) or ["linkedin"]

    if not revision:
        return QAReport(
            passed=False,
            verdict=(
                "The copy is specific and the proof-led angle is right for this buyer. It cannot "
                "publish as written: the performance figure is stated without the attribution the "
                "tenant policy requires, which reads as a universal guarantee."
            ),
            brand_safety_score=61,
            goal_alignment_score=84,
            issues=[
                QAIssue(
                    channel=channels[0],
                    severity="critical",
                    issue=(
                        "The performance figure is presented as an absolute outcome with no "
                        "attribution, and the tenant policy requires the deployed-customer-average "
                        "disclaimer wherever that figure appears."
                    ),
                    fix=(
                        "Append the required disclaimer - 'Performance figures reflect deployed "
                        "customer averages, not guarantees.' - to every asset that cites the figure."
                    ),
                ),
                QAIssue(
                    channel=channels[-1],
                    severity="advisory",
                    issue="The closing line restates the offer rather than adding a reason to act now.",
                    fix="Replace the final sentence with the single strongest proof point instead of a restatement.",
                ),
            ],
        )

    return QAReport(
        passed=True,
        verdict=(
            "The required attribution now appears on every asset carrying the performance figure, "
            "which clears the blocking issue. Copy is channel-native and each asset states a "
            "specific next step."
        ),
        brand_safety_score=93,
        goal_alignment_score=88,
        issues=[
            QAIssue(
                channel=channels[-1],
                severity="advisory",
                issue="Body copy runs slightly long for the channel's engagement window.",
                fix="Trim the second sentence; the proof point survives without it.",
            )
        ],
    )


def _analytics(prompt: str) -> AnalyticsReport:
    budget = _budget(prompt)
    channels = _channels(prompt) or ["linkedin", "email", "blog"]
    shares = [0.5, 0.3, 0.2][: len(channels)]
    if len(shares) < len(channels):
        shares += [round((1 - sum(shares)) / (len(channels) - len(shares)), 3)] * (len(channels) - len(shares))

    breakdown, total_impr, total_clicks = [], 0, 0
    for channel, share in zip(channels, shares):
        spend = budget * share
        cpm = _CPM.get(channel, 8.0)
        ctr = _CTR.get(channel, 1.0)
        impressions = int(spend / cpm * 1000)
        clicks = int(impressions * ctr / 100)
        total_impr += impressions
        total_clicks += clicks
        breakdown.append(
            ChannelPerformance(
                channel_name=channel,
                impressions=impressions,
                clicks=clicks,
                ctr=round(clicks / impressions * 100, 2) if impressions else 0.0,
            )
        )

    conversion = 3.2
    conversions = max(1, int(total_clicks * conversion / 100))
    return AnalyticsReport(
        total_impressions=total_impr,
        total_clicks=total_clicks,
        overall_ctr=round(total_clicks / total_impr * 100, 2) if total_impr else 0.0,
        conversion_rate=conversion,
        projected_cac_usd=round(budget / conversions, 2),
        channel_breakdown=breakdown,
    )


def _learning(prompt: str) -> LearningOutput:
    return LearningOutput(
        insights=[
            "This audience treats an unattributed performance figure as a red flag, not a hook - "
            "attribution is not legal boilerplate here, it is part of the persuasion.",
            "The blog earned its budget as the citable artefact rather than as a traffic source; "
            "the next run should plan it as proof infrastructure, not as a channel.",
        ],
        winning_angles=[
            "Leading with measurement methodology rather than the outcome figure itself",
            "Framing the asset as something the reader forwards to finance",
        ],
        exhausted_angles=["Generic pick-time improvement claim without measurement context"],
        next_goal_suggestion=(
            "Convert the methodology readers into booked demos with a named-customer proof sequence - "
            "the evidence angle is working, but nothing currently carries a peer reference."
        ),
    )


_SYNTH = {
    OrchestrationPlan: _plan,
    ResearchOutput: _research,
    StrategyOutput: _strategy,
    ContentOutput: _content,
    SEOOutput: _seo,
    QAReport: _qa,
    AnalyticsReport: _analytics,
    LearningOutput: _learning,
}


def _generic(schema: type[BaseModel]) -> BaseModel:
    """Fallback for any schema without a hand-written synthesiser."""
    values: dict[str, Any] = {}
    for name, field in schema.model_fields.items():
        annotation = str(field.annotation)
        if "list" in annotation:
            values[name] = []
        elif "int" in annotation:
            values[name] = 0
        elif "float" in annotation:
            values[name] = 0.0
        elif "bool" in annotation:
            values[name] = True
        else:
            values[name] = "simulated"
    return schema(**values)


class SimulatorProvider(BaseLLM):
    """Drop-in BaseLLM that never calls a network."""

    def __init__(self, model: str | None = None) -> None:
        self._model_name = model or "simulator"
        self._rng = random.Random(7)

    def generate(
        self,
        system_prompt: str,
        user_prompt: str,
        *,
        response_schema: type[BaseModel],
    ) -> BaseModel:
        synth = _SYNTH.get(response_schema)
        logger.info(
            "LLM_CALL | provider=simulator | schema=%s | synthesised=%s",
            response_schema.__name__,
            bool(synth),
        )
        return synth(user_prompt) if synth else _generic(response_schema)

    def generate_with_tools(
        self,
        system_prompt: str,
        user_prompt: str,
        *,
        tools: Sequence[BaseTool],
        response_schema: type[BaseModel],
        max_steps: int = 8,
    ) -> BaseModel:
        # Tools still execute, so tenant-scoped tool access stays on the tested path.
        for tool in list(tools)[:2]:
            try:
                brand_id = _json_value(user_prompt, "id")
                if brand_id and "brand_id" in (tool.args or {}):
                    tool.invoke({"brand_id": brand_id})
            except Exception:
                pass
        return self.generate(system_prompt, user_prompt, response_schema=response_schema)
