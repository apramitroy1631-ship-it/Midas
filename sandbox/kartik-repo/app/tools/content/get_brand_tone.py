# app/tools/content/get_brand_tone.py
"""Brand tone tool for content agent."""
import json
import logging

from langchain_core.tools import tool

from app.db.repositories.brand_repo import get_by_id

logger = logging.getLogger("tools.get_brand_tone")


@tool
def get_brand_tone(brand_id: str) -> str:
    """
    Fetch brand voice and copy alignment data: tone of voice, unique
    selling proposition, target audience profile, and industry context.

    Always call this tool alongside get_brand_guidelines before writing
    any copy. Together they provide everything needed for on-brand content.

    Use the returned data to:
    - Match headline and body copy tone exactly (professional/playful/bold etc.)
    - Lead with the USP in headlines and calls-to-action
    - Write directly to the target audience — their language, pain points
    - Use industry-appropriate vocabulary and references throughout

    Args:
        brand_id: The brand's UUID from the campaign context.
    """
    logger.info(f"get_brand_tone | brand_id={brand_id}")

    try:
        brand = get_by_id(brand_id)

        if brand is None:
            logger.warning(f"get_brand_tone | not found | brand_id={brand_id}")
            return json.dumps({
                "error":        f"Brand {brand_id} not found",
                "tone_profile": None,
            })

        result = {
            "brand_id":   brand_id,
            "brand_name": brand.get("name"),
            "tone_profile": {
                "tone":            brand.get("tone", ""),
                "usp":             brand.get("usp", ""),
                "target_audience": brand.get("target_audience", ""),
                "industry":        brand.get("industry", ""),
                "description":     brand.get("description", ""),
            },
        }

        logger.info(
            f"get_brand_tone | success | "
            f"brand_id={brand_id} | "
            f"tone={result['tone_profile']['tone']!r}"
        )

        return json.dumps(result, ensure_ascii=False)

    except Exception as e:
        logger.error(f"get_brand_tone | error | brand_id={brand_id} | error={e}")
        return json.dumps({
            "error":        str(e),
            "brand_id":     brand_id,
            "tone_profile": None,
        })