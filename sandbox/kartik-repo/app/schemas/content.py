# app/schemas/content.py
from pydantic import BaseModel, ConfigDict, Field


class ContentAsset(BaseModel):
    model_config = ConfigDict(strict=True, extra="forbid")

    headline: str = Field(
        ...,
        description=(
            "The primary hook or headline for this asset. Must be channel-appropriate in length and style: "
            "punchy and scroll-stopping for social, benefit-led for email subject lines, "
            "keyword-aware for app store or blog. Must reflect the brand's tone and differentiator."
        ),
    )
    body: str = Field(
        ...,
        description=(
            "The main copy body. Length and style must match the channel: short and energetic for "
            "TikTok/Instagram, narrative and trust-building for email, informational for blog, "
            "benefit-dense for app store. The brand identity and USP must come through naturally — "
            "not bolted on. Generic copy that could belong to any brand is not acceptable."
        ),
    )
    call_to_action: str = Field(
        ...,
        description=(
            "A specific, action-driving CTA tailored to the channel and campaign goal. "
            "Must create genuine urgency or clear next step — not a generic 'Learn more' or 'Click here'. "
            "Example: 'Download free — your plan adapts tomorrow' or 'Join 10,000 on the waitlist'."
        ),
    )
    channel: str = Field(
        ...,
        description=(
            "The exact marketing channel this asset is designed for, matching one of the channels "
            "defined in the strategy. Must be one of the strategy's planned channels."
        ),
    )


class ContentOutput(BaseModel):
    model_config = ConfigDict(strict=True, extra="forbid")

    assets: list[ContentAsset] = Field(
        ...,
        min_length=1,
        description=(
            "One content asset per channel defined in the strategy. "
            "Each asset must be distinctly native to its channel — not a reskin of the same copy."
        ),
    )