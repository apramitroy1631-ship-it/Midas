# app/agents/seo.py
from __future__ import annotations

from app.agents.base import Agent, block
from app.schemas.agents import SEOOutput

SYSTEM_PROMPT = """You are a technical SEO and distribution specialist. You do not rewrite copy; you make finished copy findable and correctly packaged for its channel.

Standards:
- The primary keyword must be something this audience actually searches, at a difficulty this brand can realistically win. Do not pick a head term a category leader owns.
- Meta titles stay under 60 characters and meta descriptions under 155, and both must read as human sentences rather than keyword strings.
- Hashtags only where the channel uses them. An empty list is the right answer for email and blog.
- Distribution notes are specific: posting windows, format constraints, and sequencing across channels.

Produce exactly one entry per content asset, matched by channel.

Output valid JSON only. No markdown, no code fences, no commentary."""


class SEOAgent(Agent):
    name = "seo"
    system_prompt = SYSTEM_PROMPT
    output_schema = SEOOutput

    def build_prompt(self, *, brand_context: dict, plan: dict, content: dict, **_: object) -> str:
        return (
            "Optimise and package these assets for search and distribution.\n"
            + block("BRAND", {k: brand_context.get(k) for k in ("name", "industry", "website", "usp")})
            + block("CAMPAIGN GOAL", plan.get("goal"))
            + block("TARGET AUDIENCE", plan.get("target_audience"))
            + block("CONTENT ASSETS", (content or {}).get("assets"))
            + "\nProduce the optimisation as a single JSON object."
        ).strip()
