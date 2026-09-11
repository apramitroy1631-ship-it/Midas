import time
import logging

logger = logging.getLogger("campaign_graph")


def node_logger(node_name):
    def decorator(func):
        def wrapper(state):
            logger.info(f"NODE_START | {node_name}")
            start = time.time()

            result = func(state)

            duration = round(time.time() - start, 3)
            logger.info(
                f"NODE_END | {node_name} | duration={duration}s"
            )

            return result
        return wrapper
    return decorator