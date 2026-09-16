# app/core/settings.py
"""Process-wide configuration, loaded from environment / .env."""
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    app_name: str = "MIDAS - Marketing Intelligence & Decision Automation System"

    # --- Control plane ---
    # Master key for tenant provisioning (POST /v1/admin/tenants). Never hand this to a tenant.
    admin_api_key: str = "midas-admin-change-me"

    # --- LLM providers ---
    openai_api_key: str = ""
    openai_model_default: str = "gpt-4o-mini"
    anthropic_api_key: str = ""
    anthropic_model_default: str = "claude-sonnet-5"

    gemini_api_key: str = ""
    gemini_model_default: str = "gemini-1.5-flash"

    llm_provider: str = "openai"  # fallback when an agent is not in AGENT_MODEL_MAP
    ollama_base_url: str = "http://localhost:11434/v1"
    ollama_api_key: str = "ollama"
    ollama_model_default: str = "llama3.1:8b-instruct-q8_0"

    # --- Storage ---
    mongodb_uri: str = "mongodb://localhost:27017"
    mongodb_db_name: str = "buildx"

    # --- Research tools (optional: agents degrade to model knowledge without them) ---
    tavily_api_key: str = ""
    serper_api_key: str = ""

    # --- Autonomy ---
    # Global kill switch for the background scheduler. Individual tenants opt in
    # separately via their own autopilot settings.
    autopilot_enabled: bool = True
    # How often the scheduler wakes to look for tenants that are due a run.
    autopilot_sweep_seconds: int = 60
    # Hard ceiling on agent self-revision cycles, whatever a tenant configures.
    max_revision_cycles: int = 3

    # --- Observability ---
    langsmith_tracing: bool = False
    langsmith_endpoint: str = "https://api.smith.langchain.com"
    langsmith_api_key: str = ""
    langsmith_project: str = "MIDAS"


settings = Settings()
