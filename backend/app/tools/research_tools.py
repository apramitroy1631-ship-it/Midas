# app/tools/research_tools.py
"""External research tools.

Every tool here degrades instead of raising when its API key is absent: it
returns a structured `unavailable` observation so the ReAct loop keeps going
and the agent falls back on model knowledge. An unattended system must never
stall on missing optional config.
"""
from __future__ import annotations

import json
import logging
from typing import Literal

import requests
from langchain_core.tools import tool

from app.core.settings import settings

logger = logging.getLogger("tools.research")

_MAX_CONTENT_CHARS = 320


def _unavailable(tool_name: str, key_name: str, query: str) -> str:
    logger.warning("%s | %s not configured - degrading to model knowledge", tool_name, key_name)
    return json.dumps(
        {
            "unavailable": True,
            "reason": key_name + " is not configured on this deployment.",
            "guidance": (
                "Live retrieval is off. Proceed using your own knowledge, but mark any figure you "
                "produce as a benchmark estimate and record 'model-knowledge: no live search "
                "configured' in your sources."
            ),
            "query": query,
        }
    )


@tool
def web_search(
    query: str,
    topic: Literal["general", "news", "finance"] = "general",
    max_results: int = 5,
) -> str:
    """Search the live web for market data, industry statistics, growth rates, and trends.

    Use for: market sizing, CAGR figures, recent market shifts, regulatory context,
    and industry news. Do not use for competitor-specific lookups - use
    competitor_lookup for those.

    Args:
        query: A precise query including year, industry, and metric type.
               e.g. "warehouse automation software market size 2026 USD"
        topic: "general" for broad web, "news" for recent articles, "finance" for market data.
        max_results: How many results to return. 5 is usually enough.
    """
    if not settings.tavily_api_key or settings.tavily_api_key.startswith("your_"):
        return _unavailable("web_search", "TAVILY_API_KEY", query)

    try:
        from tavily import TavilyClient

        client = TavilyClient(api_key=settings.tavily_api_key)
        response = client.search(
            query=query,
            search_depth="advanced",
            topic=topic,
            max_results=max_results,
            include_answer=True,
            include_raw_content=False,
        )
        results = [
            {
                "title": r.get("title", ""),
                "url": r.get("url", ""),
                "score": r.get("score", 0),
                "content": (r.get("content") or "")[:_MAX_CONTENT_CHARS].strip(),
            }
            for r in response.get("results", [])
        ]
        logger.info("web_search | ok | query=%r | results=%d", query, len(results))
        return json.dumps({"answer": response.get("answer"), "results": results, "query": query})
    except Exception as exc:
        logger.error("web_search | error | %s", exc)
        return json.dumps({"error": str(exc), "query": query, "results": []})


@tool
def competitor_lookup(brand_or_product: str, industry: str = "") -> str:
    """Look up how a specific competitor brand or product positions itself publicly.

    Returns organic search results describing the competitor's messaging, pricing
    posture, and market positioning. Use one call per competitor.

    Args:
        brand_or_product: The competitor's brand or product name.
        industry: Optional industry qualifier to disambiguate common names.
    """
    query = (brand_or_product + " " + industry).strip() + " positioning pricing customers"

    if not settings.serper_api_key or settings.serper_api_key.startswith("your_"):
        return _unavailable("competitor_lookup", "SERPER_API_KEY", query)

    try:
        resp = requests.post(
            "https://google.serper.dev/search",
            headers={"X-API-KEY": settings.serper_api_key, "Content-Type": "application/json"},
            json={"q": query, "num": 6},
            timeout=20,
        )
        resp.raise_for_status()
        data = resp.json()
        organic = [
            {
                "title": r.get("title", ""),
                "link": r.get("link", ""),
                "snippet": (r.get("snippet") or "")[:_MAX_CONTENT_CHARS],
            }
            for r in data.get("organic", [])[:6]
        ]
        logger.info("competitor_lookup | ok | %s | results=%d", brand_or_product, len(organic))
        return json.dumps({"competitor": brand_or_product, "results": organic})
    except Exception as exc:
        logger.error("competitor_lookup | error | %s", exc)
        return json.dumps({"error": str(exc), "competitor": brand_or_product, "results": []})
