# app/graph/nodes/research_node.py
from app.agents.research_agent import ResearchAgent
from app.graph.node_wrapper import node_logger


@node_logger("research")
def research_node(state):
    agent = ResearchAgent()
    research_output = agent.run(
        brand_context=state.get("brand_context", {}),
        goal=state.get("goal", ""),
        target_audience=state.get("target_audience", ""),
        budget=state.get("budget", 0.0),
    )
    state["research"] = research_output.model_dump()
    return state