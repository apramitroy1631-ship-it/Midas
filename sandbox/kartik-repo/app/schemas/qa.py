# app/schemas/qa.py
from pydantic import BaseModel, ConfigDict, Field


class QAReport(BaseModel):
    model_config = ConfigDict(strict=True, extra="forbid")

    passed: bool = Field(
        ...,
        description=(
            "True only if there are zero critical issues. "
            "Copy quality issues (weak hooks, buried USP) do NOT set this to false — "
            "only hard violations do: content restriction breaches, missing CTAs entirely, "
            "assets on wrong channels. If there are only recommendations, set passed=True."
        ),
    )
    critical_issues: list[str] = Field(
        default_factory=list,
        description=(
            "Hard-stop violations that must block publishing. Only include: "
            "(1) content restriction violations — e.g. before/after imagery, unverified health claims; "
            "(2) missing CTA entirely — asset has no next step at all; "
            "(3) asset targeted at completely wrong channel — e.g. a 2000-word essay for TikTok. "
            "Each entry must name the channel and describe the specific violation. "
            "Do NOT include copy quality feedback here."
        ),
    )
    recommendations: list[str] = Field(
        default_factory=list,
        description=(
            "Copy quality improvements that should be addressed but do not block publishing. "
            "Includes: weak hooks, generic copy, buried USP, vague CTAs that exist but could be sharper, "
            "tone mismatches, missing brand differentiator in body copy. "
            "Each entry must name the channel and give a specific, actionable fix a copywriter "
            "could act on immediately. Example: 'TikTok — rewrite headline to lead with the "
            "24-hour adaptive plan angle instead of the generic HRV question.'"
        ),
    )