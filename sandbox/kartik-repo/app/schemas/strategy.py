# app/schemas/strategy.py
from pydantic import BaseModel, ConfigDict, Field


class StrategyOutput(BaseModel):
    model_config = ConfigDict(strict=True)

    summary: str = Field(
        ...,
        description=(
            "A concise executive summary (3–5 sentences) of the campaign strategy: what the approach is, "
            "why it will work for this specific audience and goal, and what the key bet is. "
            "Must be grounded in the research findings — not a generic marketing statement."
        ),
    )
    objectives: list[str] = Field(
        ...,
        min_length=2,
        description=(
            "Specific, measurable objectives tied directly to the campaign goal. Each objective must include "
            "a metric and a future-relative timeframe (e.g. 'within 30 days', 'by week 4'). "
            "Objectives must be achievable within the stated budget. No vague aspirations."
        ),
    )
    tactics: list[str] = Field(
        ...,
        min_length=3,
        description=(
            "Concrete, executable actions the campaign will take — not directions or principles. "
            "Each tactic should imply where budget is being spent and what outcome it drives. "
            "Example: 'Allocate 40% of budget to TikTok paid ads targeting 22–30 fitness enthusiasts "
            "using interest-based and lookalike audiences' — not 'use social media'."
        ),
    )
    channels: list[str] = Field(
        ...,
        min_length=1,
        description=(
            "The specific marketing channels selected for this campaign, matching the tactics described. "
            "Each channel must earn its place — only include channels where the target audience is "
            "meaningfully reachable and the budget can drive measurable results."
        ),
    )