from app.graph.node_wrapper import node_logger

@node_logger("publish")
def publish_node(state):
    state["status"] = "published"
    return state