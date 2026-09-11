# app/tools/strategy/get_past_campaigns.py
"""Past campaigns tool for strategy agent."""
import json
import logging

from langchain_core.tools import tool

from app.db.repositories.campaign_repo import list_by_brand_id

logger = logging.getLogger("tools.get_past_campaigns")

_MAX_LIMIT = 10  # hard ceiling — prevent context window abuse


@tool
def get_past_campaigns(brand_id: str, limit: int = 5) -> str:
    """
    Fetch recent campaign history for a brand: goals, strategies used,
    channels, QA outcomes, and whether each campaign passed or failed.

    Always call this tool AFTER get_brand_memory to build a complete
    picture before forming strategy. Use this to ensure strategic
    continuity — avoid repeating what failed, build on what worked.

    Use the returned data to:
    - Identify which strategies previously succeeded (qa_passed=True)
    - Avoid repeating failed strategic approaches (qa_passed=False)
    - Understand which channels have been used and their outcomes
    - Spot patterns in goals and audience targeting over time

    Args:
        brand_id: The brand's UUID from the campaign context.
        limit: Number of recent campaigns to fetch. Default 5 gives
               enough history without overwhelming context. Max 10.
    """
    logger.info(f"get_past_campaigns | brand_id={brand_id} | limit={limit}")

    # Enforce hard ceiling regardless of what LLM passes
    limit = min(limit, _MAX_LIMIT)

    try:
        campaigns = list_by_brand_id(brand_id)[:limit]

        if not campaigns:
            logger.info(f"get_past_campaigns | no history | brand_id={brand_id}")
            return json.dumps({
                "brand_id":       brand_id,
                "campaign_count": 0,
                "campaigns":      [],
                "note": (
                    "No previous campaigns found. "
                    "This is the brand's first campaign — "
                    "form strategy from brand memory alone."
                ),
            })

        # Return only strategically relevant fields
        # Full campaign docs are 50-200KB — way too large for context window
        summaries = [
            {
                "campaign_id":      c.get("id"),
                "goal":             c.get("goal"),
                "target_audience":  c.get("target_audience"),
                "budget":           c.get("budget"),
                "status":           c.get("status"),
                "channels_used":    c.get("strategy", {}).get("channels", []),
                "strategy_summary": c.get("strategy", {}).get("summary"),
                "qa_passed":        c.get("qa_report", {}).get("passed"),
                "qa_issues":        c.get("qa_report", {}).get("issues", []),
                "created_at":       c.get("created_at"),
            }
            for c in campaigns
        ]

        result = {
            "brand_id":       brand_id,
            "campaign_count": len(summaries),
            "campaigns":      summaries,
        }

        logger.info(
            f"get_past_campaigns | success | "
            f"brand_id={brand_id} | "
            f"found={len(summaries)}"
        )

        return json.dumps(result, ensure_ascii=False, default=str)

    except Exception as e:
        logger.error(
            f"get_past_campaigns | error | brand_id={brand_id} | error={e}"
        )
        return json.dumps({
            "error":     str(e),
            "brand_id":  brand_id,
            "campaigns": [],
        })