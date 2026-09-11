import logging
import sys

_FORMAT = "%(asctime)s | %(levelname)s | %(name)s | %(message)s"


def setup_logging():
    logging.basicConfig(
        level=logging.INFO,
        format=_FORMAT,
        handlers=[logging.StreamHandler(sys.stdout)],
    )
    # Ensure these loggers always use our handler (uvicorn can override root config)
    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(logging.Formatter(_FORMAT))
    for name in ("campaign_graph", "ollama_provider"):
        log = logging.getLogger(name)
        log.setLevel(logging.INFO)
        log.addHandler(handler)
        log.propagate = False