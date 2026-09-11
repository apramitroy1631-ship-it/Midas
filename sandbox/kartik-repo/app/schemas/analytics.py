# app/schemas/analytics.py
from pydantic import BaseModel, ConfigDict, Field


class ChannelPerformance(BaseModel):
    model_config = ConfigDict(strict=True, extra="forbid")

    channel_name: str = Field(
        ...,
        description="Name of the marketing channel, matching exactly what is defined in the strategy.",
    )
    impressions: int = Field(
        ...,
        ge=0,
        description=(
            "Estimated total impressions for this channel based on the budget allocated to it "
            "and industry-standard CPM benchmarks for the channel type and audience."
        ),
    )
    clicks: int = Field(
        ...,
        ge=0,
        description=(
            "Estimated total clicks derived from impressions and a realistic CTR benchmark "
            "for this channel and audience. Must be less than or equal to impressions."
        ),
    )
    ctr: float = Field(
        ...,
        ge=0,
        le=100,
        description=(
            "Click-through rate as a percentage: (clicks / impressions) * 100. "
            "Must be arithmetically consistent with the impressions and clicks values above."
        ),
    )


class AnalyticsReport(BaseModel):
    model_config = ConfigDict(strict=True, extra="forbid")

    total_impressions: int = Field(
        ...,
        ge=0,
        description="Sum of impressions across all channels. Must equal the sum of all channel_breakdown impressions.",
    )
    total_clicks: int = Field(
        ...,
        ge=0,
        description="Sum of clicks across all channels. Must equal the sum of all channel_breakdown clicks.",
    )
    overall_ctr: float = Field(
        ...,
        ge=0,
        le=100,
        description=(
            "Overall click-through rate: (total_clicks / total_impressions) * 100. "
            "Must be arithmetically consistent with total_impressions and total_clicks."
        ),
    )
    conversion_rate: float = Field(
        ...,
        ge=0,
        le=100,
        description=(
            "Estimated percentage of clicks that result in a goal completion (e.g. app install, sign-up). "
            "Must be grounded in realistic benchmarks for the campaign goal and channel mix — "
            "typically 1–5% for app installs, 5–15% for email sign-ups."
        ),
    )
    channel_breakdown: list[ChannelPerformance] = Field(
        ...,
        min_length=1,
        description=(
            "Per-channel performance forecast. Must include one entry per channel in the strategy. "
            "Aggregated totals above must be consistent with the sum of values here."
        ),
    )