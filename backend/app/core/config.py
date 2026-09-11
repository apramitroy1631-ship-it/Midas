# app/core/config.py
"""Agent -> provider/model routing.

Cheap models handle the high-volume drafting work; the orchestrator and QA
agents get the stronger model because their judgement gates the whole run.
A tenant can override any of this via `tenant.model_overrides`.
"""

AGENT_MODEL_MAP = {
    "orchestrator": {"provider": "openai", "model": "gpt-4o"},
    "research":     {"provider": "openai", "model": "gpt-4o-mini"},
    "strategy":     {"provider": "openai", "model": "gpt-4o-mini"},
    "content":      {"provider": "openai", "model": "gpt-4o-mini"},
    "seo":          {"provider": "openai", "model": "gpt-4o-mini"},
    "qa":           {"provider": "openai", "model": "gpt-4o"},
    "analytics":    {"provider": "openai", "model": "gpt-4o-mini"},
}
