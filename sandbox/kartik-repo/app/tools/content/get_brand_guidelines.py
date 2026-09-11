# app/tools/content/get_brand_guidelines.py
"""Brand guidelines tool for content agent."""
import json
import logging

from langchain_core.tools import tool

from app.db.repositories.brand_repo import get_by_id

logger = logging.getLogger("tools.get_brand_guidelines")


@tool
def get_brand_guidelines(brand_id: str) -> str:
    """
    Fetch brand guidelines: visual style direction, preferred publishing
    channels, and content restrictions that must never be violated.

    Always call this tool BEFORE writing any copy or content assets.
    Content restrictions are hard rules — violating them means the
    campaign will fail QA and be rejected entirely.

    Use the returned data to:
    - Write copy aligned with the visual_style tone and aesthetic
    - Only produce content formats suited to preferred_channels
    - Strictly avoid anything listed in content_restrictions
    - Match content length and format to each channel's conventions

    Args:
        brand_id: The brand's UUID from the campaign context.
    """
    logger.info(f"get_brand_guidelines | brand_id={brand_id}")

    try:
        brand = get_by_id(brand_id)

        if brand is None:
            logger.warning(f"get_brand_guidelines | not found | brand_id={brand_id}")
            return json.dumps({
                "error":      f"Brand {brand_id} not found",
                "guidelines": None,
            })

        guidelines = brand.get("memory", {}).get("brand_guidelines", {})

        result = {
            "brand_id":   brand_id,
            "brand_name": brand.get("name"),
            "guidelines": {
                "visual_style":         guidelines.get("visual_style", ""),
                "preferred_channels":   guidelines.get("preferred_channels", []),
                "content_restrictions": guidelines.get("content_restrictions", []),
            },
        }

        logger.info(
            f"get_brand_guidelines | success | "
            f"brand_id={brand_id} | "
            f"channels={result['guidelines']['preferred_channels']} | "
            f"restrictions={len(result['guidelines']['content_restrictions'])}"
        )

        return json.dumps(result, ensure_ascii=False)

    except Exception as e:
        logger.error(
            f"get_brand_guidelines | error | brand_id={brand_id} | error={e}"
        )
        return json.dumps({
            "error":      str(e),
            "brand_id":   brand_id,
            "guidelines": None,
        })