# app/tools/research/serper_competitor_lookup.py
"""Competitor intelligence tool for research agent using Serper.dev."""
import json
import logging
from typing import Optional

import httpx
from langchain_core.tools import tool

from app.core.settings import settings

logger = logging.getLogger("tools.serper_competitor_lookup")

SERPER_BASE_URL = "https://google.serper.dev"

# Module-level client — instantiated once, reused across calls
# Avoids rebuilding headers and connection pool on every tool invocation
_client: Optional[httpx.Client] = None


def _get_client() -> httpx.Client:
    global _client
    if _client is None:
        if not settings.serper_api_key:
            raise ValueError(
                "SERPER_API_KEY not set. "
                "Get a free key at https://serper.dev and add it to .env"
            )
        _client = httpx.Client(
            base_url=SERPER_BASE_URL,
            headers={
                "X-API-KEY":    settings.serper_api_key,
                "Content-Type": "application/json",
            },
            timeout=10.0,  # seconds — fail fast, don't hang the ReAct loop
        )
    return _client


def _search_overview(client: httpx.Client, company_name: str) -> dict:
    """
    General web search for company overview.
    Returns knowledge graph (if available) + top organic results.
    Knowledge graph contains: description, founded, HQ, CEO, employee count.
    """
    response = client.post(
        "/search",
        json={
            "q":   company_name,
            "num": 5,
        },
    )
    response.raise_for_status()
    data = response.json()

    knowledge_graph = data.get("knowledgeGraph", {})
    organic         = data.get("organic", [])[:3]  # top 3 only — rest is noise

    return {
        "description": knowledge_graph.get("description"),
        "founded":     knowledge_graph.get("attributes", {}).get("Founded"),
        "headquarters": knowledge_graph.get("attributes", {}).get("Headquarters"),
        "ceo":         knowledge_graph.get("attributes", {}).get("CEO"),
        "employees":   knowledge_graph.get("attributes", {}).get("Number of employees"),
        "website":     knowledge_graph.get("website"),
        "top_organic": [
            {
                "title":   r.get("title"),
                "snippet": r.get("snippet"),
                "link":    r.get("link"),
            }
            for r in organic
        ],
    }


def _search_news(client: httpx.Client, company_name: str) -> list[dict]:
    """
    Recent news search for the company.
    Surfaces funding rounds, product launches, leadership changes,
    strategic pivots — all critical for competitive intelligence.
    """
    response = client.post(
        "/news",
        json={
            "q":   f"{company_name}",
            "num": 5,
        },
    )
    response.raise_for_status()
    data = response.json()

    return [
        {
            "title":   r.get("title"),
            "source":  r.get("source"),
            "date":    r.get("date"),
            "snippet": r.get("snippet"),
            "link":    r.get("link"),
        }
        for r in data.get("news", [])[:5]
    ]


@tool
def serper_competitor_lookup(company_name: str) -> str:
    """
    Fetch structured competitor intelligence for a specific company
    using Google Search via Serper.dev. Returns company overview from
    the knowledge graph, top organic positioning signals, and recent
    news articles.

    Use this tool for:
    - Building a competitor profile (call once per competitor)
    - Understanding competitor market positioning and messaging
    - Identifying recent competitor moves: funding, launches, pivots
    - Gauging competitor market presence via organic search results

    Do NOT use for broad market research — use web_search for that.
    Call this tool separately for EACH competitor you want to profile.
    Aim to profile at least 3 competitors for a complete analysis.

    Args:
        company_name: Exact company name as commonly known.
                      Examples: "HubSpot", "Marketo", "Salesforce Marketing Cloud"
    """
    logger.info(f"serper_competitor_lookup | company={company_name!r}")

    try:
        client = _get_client()

        # Two targeted searches per competitor:
        # 1. General search  → knowledge graph + organic positioning signals
        # 2. News search     → recent strategic moves and signals
        overview = _search_overview(client, company_name)
        news     = _search_news(client, company_name)

        result = {
            "company":     company_name,
            "overview":    overview,
            "recent_news": news,
        }

        logger.info(
            f"serper_competitor_lookup | success | "
            f"company={company_name!r} | "
            f"has_knowledge_graph={bool(overview.get('description'))} | "
            f"news_count={len(news)}"
        )

        return json.dumps(result, ensure_ascii=False)

    except ValueError:
        raise  # re-raise config errors — surface immediately

    except httpx.TimeoutException:
        logger.error(f"serper_competitor_lookup | timeout | company={company_name!r}")
        return json.dumps({
            "error":       "Request timed out after 10s",
            "company":     company_name,
            "overview":    {},
            "recent_news": [],
        })

    except httpx.HTTPStatusError as e:
        logger.error(
            f"serper_competitor_lookup | http_error | "
            f"company={company_name!r} | "
            f"status={e.response.status_code}"
        )
        return json.dumps({
            "error":       f"Serper.dev returned HTTP {e.response.status_code}",
            "company":     company_name,
            "overview":    {},
            "recent_news": [],
        })

    except Exception as e:
        logger.error(
            f"serper_competitor_lookup | error | "
            f"company={company_name!r} | error={e}"
        )
        return json.dumps({
            "error":       str(e),
            "company":     company_name,
            "overview":    {},
            "recent_news": [],
        })