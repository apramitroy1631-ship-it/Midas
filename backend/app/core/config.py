# app/core/config.py
"""Agent -> provider/model routing.

Routed to Groq (free tier, generous daily request limits, no per-project
20/day wall like Gemini's free tier) so local testing isn't blocked by quota
every few runs. Gemini's free-tier cap (20 requests/day/model) got exhausted
fast just from iterating on this pipeline — Groq's free tier holds up far
better for that. Swap back to Gemini/OpenAI/Anthropic per-agent, or once
billing is attached to a paid key, by changing the "provider"/"model" pairs
below; `llm_factory.py` looks up providers by name and doesn't care which
mix is used.

A tenant can override any of this via `tenant.model_overrides`.
"""

AGENT_MODEL_MAP = {
    "orchestrator": {"provider": "groq", "model": "openai/gpt-oss-120b"},
    "research":     {"provider": "groq", "model": "openai/gpt-oss-120b"},
    "strategy":     {"provider": "groq", "model": "openai/gpt-oss-120b"},
    "content":      {"provider": "groq", "model": "openai/gpt-oss-120b"},
    "seo":          {"provider": "groq", "model": "openai/gpt-oss-20b"},
    "qa":           {"provider": "groq", "model": "openai/gpt-oss-120b"},
    "analytics":    {"provider": "groq", "model": "openai/gpt-oss-20b"},
}
