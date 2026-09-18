# app/main.py
from __future__ import annotations

import asyncio
import logging
import os
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.core.logging import setup_logging
from app.core.settings import settings

# LangSmith env must be set before any LangGraph/LangChain import.
os.environ["LANGSMITH_TRACING"] = str(settings.langsmith_tracing).lower()
os.environ["LANGSMITH_ENDPOINT"] = settings.langsmith_endpoint
if settings.langsmith_api_key:
    os.environ["LANGSMITH_API_KEY"] = settings.langsmith_api_key
os.environ["LANGCHAIN_PROJECT"] = settings.langsmith_project

from app.api.routes_auth import router as auth_router  # noqa: E402
from app.api.routes_autopilot import router as autopilot_router  # noqa: E402
from app.api.routes_brands import router as brands_router  # noqa: E402
from app.api.routes_logs import router as logs_router  # noqa: E402
from app.api.routes_runs import router as runs_router  # noqa: E402
from app.api.routes_schedules import router as schedules_router  # noqa: E402
from app.api.routes_tenants import admin_router, router as tenant_router  # noqa: E402
from app.core.log_capture import start_log_capture  # noqa: E402
from app.db.mongo import ensure_indexes  # noqa: E402
from app.services.autopilot import scheduler_loop  # noqa: E402
from app.services.scheduled_campaigns import scheduler_loop as schedules_scheduler_loop  # noqa: E402

setup_logging()
start_log_capture()
logger = logging.getLogger("main")


@asynccontextmanager
async def lifespan(app: FastAPI):
    try:
        ensure_indexes()
    except Exception:
        logger.exception("Mongo unreachable at startup - the API will start but runs will fail")

    task: asyncio.Task | None = None
    if settings.autopilot_enabled:
        task = asyncio.create_task(scheduler_loop(), name="autopilot-scheduler")
    else:
        logger.info("autopilot | disabled by AUTOPILOT_ENABLED=false")

    # Per-campaign scheduling (date range + weekdays, set from New Campaign) is
    # independent of the tenant-wide autopilot toggle above - it only ever runs
    # what an operator explicitly scheduled, so it's always on.
    schedules_task = asyncio.create_task(schedules_scheduler_loop(), name="schedules-scheduler")

    yield

    for t in (task, schedules_task):
        if t is not None:
            t.cancel()
            try:
                await t
            except asyncio.CancelledError:
                pass


app = FastAPI(
    title="MIDAS - Marketing Intelligence & Decision Automation System",
    version="1.0.0",
    description=(
        "A hierarchical agent system that plans, researches, writes, reviews, and publishes "
        "marketing content with no human in the loop. Authenticate with X-API-Key. "
        "Architected multi-tenant (see app/db/scoped.py) though this deployment is operated "
        "for a single company."
    ),
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(admin_router)
app.include_router(auth_router)
app.include_router(tenant_router)
app.include_router(brands_router)
app.include_router(runs_router)
app.include_router(autopilot_router)
app.include_router(logs_router)
app.include_router(schedules_router)


@app.get("/health", tags=["Meta"])
def health() -> dict:
    from app.db.mongo import get_client

    try:
        get_client().admin.command("ping")
        db_ok = True
    except Exception:
        db_ok = False

    return {
        "status": "ok" if db_ok else "degraded",
        "database": "up" if db_ok else "down",
        "autopilot": settings.autopilot_enabled,
        "llm_provider": settings.llm_provider,
        "live_search": bool(settings.tavily_api_key and not settings.tavily_api_key.startswith("your_")),
    }
