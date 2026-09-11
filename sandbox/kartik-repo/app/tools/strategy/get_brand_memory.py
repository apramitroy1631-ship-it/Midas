# app/tools/strategy/get_brand_memory.py
"""Brand memory tool for strategy agent."""
import json
import logging

from langchain_core.tools import tool

from app.db.repositories.brand_repo import get_by_id

logger = logging.getLogger("tools.get_brand_memory")


@tool
def get_brand_memory(brand_id: str) -> str:
    """
    Fetch complete brand memory from the database: past campaign IDs,
    latest insights gathered from previous campaigns, and brand
    guidelines (visual style, preferred channels, content restrictions).

    Always call this tool FIRST before forming any strategy.
    The brand memory contains critical constraints and learnings that
    must inform every strategic decision.

    Use the returned data to:
    - Respect content_restrictions absolutely — never violate these
    - Align strategy with preferred_channels
    - Build on latest_insights from past campaigns
    - Understand brand maturity via past_campaigns count

    Args:
        brand_id: The brand's UUID from the campaign context.
    """
    logger.info(f"get_brand_memory | brand_id={brand_id}")

    try:
        brand = get_by_id(brand_id)

        if brand is None:
            logger.warning(f"get_brand_memory | not found | brand_id={brand_id}")
            return json.dumps({
                "error":  f"Brand {brand_id} not found",
                "memory": None,
            })

        # Return memory + core brand fields strategy needs
        # Exclude internal fields (_id, created_at etc) — waste of tokens
        result = {
            "brand_id":        brand_id,
            "name":            brand.get("name"),
            "industry":        brand.get("industry"),
            "tone":            brand.get("tone"),
            "usp":             brand.get("usp"),
            "target_audience": brand.get("target_audience"),
            "memory": {
                "past_campaigns":    brand.get("memory", {}).get("past_campaigns", []),
                "latest_insights":   brand.get("memory", {}).get("latest_insights", []),
                "brand_guidelines":  brand.get("memory", {}).get("brand_guidelines", {}),
            },
        }

        logger.info(
            f"get_brand_memory | success | "
            f"brand_id={brand_id} | "
            f"past_campaigns={len(result['memory']['past_campaigns'])} | "
            f"insights={len(result['memory']['latest_insights'])}"
        )

        return json.dumps(result, ensure_ascii=False)

    except Exception as e:
        logger.error(f"get_brand_memory | error | brand_id={brand_id} | error={e}")
        return json.dumps({
            "error":    str(e),
            "brand_id": brand_id,
            "memory":   None,
        })