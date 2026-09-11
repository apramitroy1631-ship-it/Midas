# app/tools/research/web_search.py
"""Web search tool for research agent."""
import json
import logging
from typing import Literal, Optional

from langchain_core.tools import tool
from tavily import TavilyClient

from app.core.settings import settings

logger = logging.getLogger("tools.web_search")

_MAX_CONTENT_CHARS = 300  # ~75 tokens per result — enough context, no bloat


def _trim_results(results: list[dict]) -> list[dict]:
    """Strip noise from raw Tavily results before feeding to LLM."""
    trimmed = []
    for r in results:
        trimmed.append({
            "title":           r.get("title", ""),
            "url":             r.get("url", ""),
            "relevance_score": r.get("score", r.get("relevance_score", 0)),
            # Truncate content — LLM only needs a snippet, not the full scrape
            "content": r.get("content", "")[:_MAX_CONTENT_CHARS].strip(),
        })
    return trimmed

# Module-level client — instantiated once, reused across calls
# Avoids re-authenticating on every tool invocation
_client: Optional[TavilyClient] = None


def _get_client() -> TavilyClient:
    global _client
    if _client is None:
        if not settings.tavily_api_key:
            raise ValueError(
                "TAVILY_API_KEY not set. "
                "Get a key at https://tavily.com and add it to .env"
            )
        _client = TavilyClient(api_key=settings.tavily_api_key)
    return _client


@tool
def web_search(
    query: str,
    topic: Literal["general", "news", "finance"] = "general",
    max_results: int = 5,
) -> str:
    """
    Search the web for current market data, industry statistics, growth
    rates, trend information, and news. Returns AI-extracted summaries
    with source URLs and relevance scores.

    Use this tool for:
    - Market size and valuation figures
    - Industry growth rate data
    - Recent market trends and shifts
    - Regulatory or macro environment context
    - Recent competitor or industry news (topic="news")
    - Financial market data (topic="finance")

    Do NOT use for competitor-specific research.

    Args:
        query: Specific search query. Be precise — include year,
               industry, and metric type for best results.
               Example: "marketing automation software market size 2024 USD"
        topic: Search index to use.
               "general" — broad web (default)
               "news"    — recent news articles only
               "finance" — financial data and market reports
        max_results: Number of results to return. Default 5 is usually
                     sufficient. Increase to 10 for broad topics.
    """
    logger.info(f"web_search | query={query!r} | topic={topic} | max_results={max_results}")

    try:
        client = _get_client()

        response = client.search(
            query=query,
            search_depth="advanced",   # advanced = AI extraction, not just snippets
            topic=topic,               # search index: general / news / finance
            max_results=max_results,
            include_answer=True,       # Tavily's own AI summary of results
            include_raw_content=False, # raw HTML — not needed, wastes tokens
        )

        # Shape the response for LLM consumption
        # Keep only what the LLM needs — strip noise
        results = {
            "answer":  response.get("answer"),  # Tavily's synthesized answer
            "topic":   topic,                   # so LLM knows which index was used
            "results": _trim_results(response.get("results", [])),
            "query": query,
        }

        logger.info(
            f"web_search | success | "
            f"topic={topic} | "
            f"results={len(results['results'])} | "
            f"has_answer={bool(results['answer'])}"
        )

        return json.dumps(results, ensure_ascii=False)

    except ValueError:
        raise   # re-raise config errors — these need to surface immediately

    except Exception as e:
        # Tool errors must NOT crash the ReAct loop
        # Return structured error so LLM can reason about it
        # and decide whether to retry or continue without this data
        logger.error(f"web_search | error | query={query!r} | error={e}")
        return json.dumps({
            "error":   str(e),
            "query":   query,
            "topic":   topic,
            "results": [],
            "answer":  None,
        })