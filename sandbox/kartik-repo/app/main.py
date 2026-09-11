# app/main.py
import os

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.core.logging import setup_logging
from app.core.settings import settings

# Wire LangSmith env vars for LangChain/LangGraph tracing (must be set before graph imports)
os.environ["LANGSMITH_TRACING"] = str(settings.langsmith_tracing).lower()
os.environ["LANGSMITH_ENDPOINT"] = settings.langsmith_endpoint
if settings.langsmith_api_key:
    os.environ["LANGSMITH_API_KEY"] = settings.langsmith_api_key
os.environ["LANGCHAIN_PROJECT"] = settings.langsmith_project

from app.api.routes_brand import router as brand_router
from app.api.routes_campaign import router as campaign_router
from app.api.routes_stream import router as stream_router

setup_logging()

app = FastAPI(title="Multi Agents Marketing and Growth System")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.include_router(brand_router)
app.include_router(campaign_router)
app.include_router(stream_router)

@app.get("/health")
def health():
    return {"status": "ok"}