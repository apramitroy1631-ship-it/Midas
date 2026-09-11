# app/schemas/research.py
from pydantic import BaseModel, ConfigDict, Field


class Competitor(BaseModel):
    model_config = ConfigDict(strict=True)

    name: str = Field(
        ...,
        description=(
            "Full brand or product name of the competitor."
        ),
    )
    positioning: str = Field(
        ...,
        description=(
            "How this competitor positions itself in the market — including where their positioning "
            "leaves gaps or unmet needs that the brand can exploit. Do not just describe what they do; "
            "identify what they are failing to do for the target audience."
        ),
    )


class ResearchOutput(BaseModel):
    model_config = ConfigDict(strict=True)

    target_audience: str = Field(
        ...,
        min_length=10,
        max_length=500,
        description=(
            "A specific, actionable profile of the primary target audience: demographics, psychographics, "
            "key behaviours, and what motivates them to act. Must go beyond broad age/gender categories."
        ),
    )
    market_size: str = Field(
        ...,
        description=(
            "Total addressable market size in USD millions, grounded in a credible sector estimate. "
            "Example: '186000' for $186B. Must reflect realistic current data, not aspirational projections."
        ),
    )
    growth_rate: str = Field(
        ...,
        description=(
            "Realistic annual CAGR percentage for the relevant market segment, based on sector benchmarks. "
            "Consumer health/fitness tech typically ranges 8–25%. Do not inflate. Example: '14.5'."
        ),
    )
    key_insights: list[str] = Field(
        ...,
        min_length=3,
        description=(
            "Actionable insights that directly inform how to achieve the campaign goal with this audience. "
            "Each insight should reveal a specific opportunity, behaviour pattern, or market condition "
            "that shapes strategy. Generic category observations are not acceptable."
        ),
    )
    competitors: list[Competitor] = Field(
        ...,
        min_length=2,
        description=(
            "The most relevant direct and indirect competitors for this campaign's target audience and goal. "
            "Focus on competitors the target audience is most likely currently using or considering."
        ),
    )