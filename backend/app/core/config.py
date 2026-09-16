# app/core/config.py
"""Agent -> provider/model routing.

Cheap models handle the high-volume drafting work; the orchestrator and QA
agents get the stronger model because their judgement gates the whole run.
A tenant can override any of this via `tenant.model_overrides`.
"""

AGENT_MODEL_MAP = {
    "orchestrator": {"provider": "gemini", "model": "gemini-1.5-pro"},
    "research":     {"provider": "gemini", "model": "gemini-1.5-flash"},
    "strategy":     {"provider": "gemini", "model": "gemini-1.5-flash"},
    "content":      {"provider": "gemini", "model": "gemini-1.5-flash"},
    "seo":          {"provider": "gemini", "model": "gemini-1.5-flash"},
    "qa":           {"provider": "gemini", "model": "gemini-1.5-pro"},
    "analytics":    {"provider": "gemini", "model": "gemini-1.5-flash"},
}
