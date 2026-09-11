# app/tools/__init__.py
"""Per-agent tool registries.

Each agent gets only its own registry, which is the hard boundary on what it
can reach. A hallucinated tool name outside the registry comes back as a
structured error the ReAct loop reasons around, rather than an exception.
"""
from app.tools.memory_tools import (
    get_brand_guidelines,
    get_brand_memory,
    get_past_campaigns,
    get_published_assets,
)
from app.tools.research_tools import competitor_lookup, web_search

ORCHESTRATOR_TOOLS = [get_brand_memory, get_past_campaigns]
RESEARCH_TOOLS = [web_search, competitor_lookup]
STRATEGY_TOOLS = [get_brand_memory, get_past_campaigns, get_brand_guidelines]
CONTENT_TOOLS = [get_brand_guidelines, get_published_assets]

__all__ = [
    "ORCHESTRATOR_TOOLS",
    "RESEARCH_TOOLS",
    "STRATEGY_TOOLS",
    "CONTENT_TOOLS",
]
