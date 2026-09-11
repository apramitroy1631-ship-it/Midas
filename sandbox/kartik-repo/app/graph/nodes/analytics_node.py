# app/graph/nodes/analytics_node.py
from app.agents.analytics_agent import AnalyticsAgent
from app.graph.node_wrapper import node_logger


@node_logger("analytics")
def analytics_node(state):
    agent = AnalyticsAgent()
    report = agent.run(
        content=state.get("content"),
        strategy=state.get("strategy", {}),
        goal=state.get("goal", ""),
        target_audience=state.get("target_audience", ""),
        budget=state.get("budget", 0.0),
    )
    state["analytics"] = report.model_dump()
    return state