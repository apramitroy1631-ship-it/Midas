# app/core/settings.py
from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    app_name: str = "Multi Agents Marketing and Growth System"

    # OpenAI (optional if using Ollama)
    openai_api_key: str = ""
    openai_model_default: str = "gpt-4o-mini"

    # Anthropic
    anthropic_api_key: str = ""
    anthropic_model_default: str = "claude-3-sonnet"

    # Default provider/model when agent not in AGENT_MODEL_MAP
    llm_provider: str = "ollama"  # "ollama" | "openai" | "anthropic"
    ollama_model_default: str = "llama3.1"

    # Ollama (OpenAI-compatible endpoint)
    ollama_base_url: str = "http://localhost:11434/v1"
    ollama_api_key: str = "ollama"

    # Infra
    database_url: str = "sqlite:///./app.db"
    redis_url: str = "redis://localhost:6379/0"

    # MongoDB (brand data)
    mongodb_uri: str = "mongodb://localhost:27017"
    mongodb_db_name: str = "marketing_growth"

    # Tavily (search for research tools)
    tavily_api_key: str = ""

    # Serper (Google Search API – https://serper.dev/api-keys)
    serper_api_key: str = ""

    # LangSmith tracing (LangChain/LangGraph)
    langsmith_tracing: bool = False
    langsmith_endpoint: str = "https://api.smith.langchain.com"
    langsmith_api_key: str = ""
    langsmith_project: str = "Market and Growth"

    class Config:
        env_file = ".env"

settings = Settings()