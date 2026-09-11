from typing import TypedDict, Optional, List, Dict


class CampaignState(TypedDict):
    """State for the campaign graph."""

    campaign_id: str
    brand_context: Optional[Dict]

    # Campaign intent — passed in at graph.invoke() time
    goal: Optional[str]
    target_audience: Optional[str]
    budget: Optional[float]

    research: Optional[dict]  # ResearchOutput.model_dump()
    strategy: Optional[dict]  # StrategyOutput.model_dump()
    content: Optional[dict]   # ContentOutput.model_dump()
    qa_report: Optional[dict]  # QAReport.model_dump()
    analytics: Optional[dict]  # AnalyticsReport.model_dump()

    validation_errors: Optional[List[str]]
    status: Optional[str]