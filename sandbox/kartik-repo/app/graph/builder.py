# app/graph/builder.py
import logging

from langgraph.graph import END, StateGraph

from app.graph.nodes.analytics_node import analytics_node
from app.graph.nodes.content_node import content_node
from app.graph.nodes.publish_node import publish_node
from app.graph.nodes.qa_node import qa_node
from app.graph.nodes.research_node import research_node
from app.graph.nodes.strategy_node import strategy_node
from app.graph.state import CampaignState

logger = logging.getLogger("campaign_graph")


def _qa_router(state: CampaignState) -> str:
    """
    Route after QA:
    - zero critical_issues → publish (recommendations are logged but don't block)
    - any critical_issues  → END (hard violations block publishing)
    """
    qa_report = state.get("qa_report") or {}
    critical_issues = qa_report.get("critical_issues", [])

    if not critical_issues:
        recommendations = qa_report.get("recommendations", [])
        if recommendations:
            logger.info(
                "QA router | no critical issues | recommendations=%d → publish",
                len(recommendations),
            )
        else:
            logger.info("QA router | clean pass → publish")
        return "publish"

    logger.warning(
        "QA router | critical_issues=%d → halting pipeline",
        len(critical_issues),
    )
    return END


def build_campaign_graph():
    graph = StateGraph(CampaignState)

    graph.add_node("research", research_node)
    graph.add_node("strategy", strategy_node)
    graph.add_node("content", content_node)
    graph.add_node("qa", qa_node)
    graph.add_node("publish", publish_node)
    graph.add_node("analytics", analytics_node)

    graph.set_entry_point("research")

    graph.add_edge("research", "strategy")
    graph.add_edge("strategy", "content")
    graph.add_edge("content", "qa")

    # Conditional — only hard violations block publishing
    graph.add_conditional_edges(
        "qa",
        _qa_router,
        {
            "publish": "publish",
            END: END,
        },
    )

    graph.add_edge("publish", "analytics")
    graph.set_finish_point("analytics")

    return graph.compile()