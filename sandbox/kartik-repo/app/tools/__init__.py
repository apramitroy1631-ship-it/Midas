# app/tools/__init__.py
"""
Tool registries — one per agent.

Each agent imports only its own registry. This is the hard boundary:
  ResearchAgent  → RESEARCH_TOOLS  (external APIs)
  StrategyAgent  → STRATEGY_TOOLS  (internal MongoDB)
  ContentAgent   → CONTENT_TOOLS   (internal MongoDB)

An agent cannot accidentally call a tool outside its registry.
If the LLM hallucinates a tool name not in the list, OllamaProvider
returns a structured error and the LLM reasons around it.
"""
from app.tools.research.web_search                  import web_search
from app.tools.research.serper_competitor_lookup     import serper_competitor_lookup
from app.tools.strategy.get_brand_memory             import get_brand_memory
from app.tools.strategy.get_past_campaigns           import get_past_campaigns
from app.tools.content.get_brand_guidelines          import get_brand_guidelines
from app.tools.content.get_brand_tone                import get_brand_tone

RESEARCH_TOOLS = [web_search, serper_competitor_lookup]
STRATEGY_TOOLS = [get_brand_memory, get_past_campaigns, get_brand_guidelines]
CONTENT_TOOLS  = [get_brand_guidelines, get_brand_tone]

__all__ = [
    "RESEARCH_TOOLS",
    "STRATEGY_TOOLS",
    "CONTENT_TOOLS",
]