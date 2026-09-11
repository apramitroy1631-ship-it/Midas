

# app/config.py
# Agent → provider/model mapping. Factory reads this to resolve LLM per agent.

AGENT_MODEL_MAP = {
    "research": {
        "provider": "openai",
        "model": "gpt-4o-mini",
    },
    "strategy": {
        "provider": "openai",
        "model": "gpt-4o-mini",
    },
    "content": {
        "provider": "openai",
        "model": "gpt-4o-mini",
    },
    "qa": {
        "provider": "openai",
        "model": "gpt-4o-mini",
    },
    "analytics": {
        "provider": "openai",
        "model": "gpt-4o-mini",
    },
}