# app/api/routes_stream.py
"""
SSE streaming endpoint for watching the campaign graph run agent-by-agent.

Added for the testing-dashboard sandbox — does not touch the existing
POST /brands/{brand_id}/campaigns/ (blocking) endpoint or its behavior.
Uses LangGraph's native `.stream()` (not `.invoke()`), which yields a dict
keyed by node name every time a node finishes, so the client sees each
agent light up in real time instead of waiting for the whole run.
"""
import json
import uuid

from fastapi import APIRouter
from sse_starlette.sse import EventSourceResponse

from app.graph.builder import build_campaign_graph
from app.schemas.campaign import CampaignCreate
from app.services.brand_service import BrandService
from app.db.repositories.campaign_repo import create as campaign_repo_create

router = APIRouter(prefix="/brands/{brand_id}/campaigns", tags=["Campaigns (streaming)"])

# Friendly labels for the timeline UI
NODE_LABELS = {
    "research": "Research Agent",
    "strategy": "Strategy Agent",
    "content": "Content Agent",
    "qa": "QA Agent",
    "publish": "Publish",
    "analytics": "Analytics Agent",
}


def _event(event: str, data: dict) -> dict:
    return {"event": event, "data": json.dumps(data)}


@router.post("/stream")
async def stream_campaign(brand_id: str, payload: CampaignCreate):
    """
    Same inputs as POST /brands/{brand_id}/campaigns/, but returns
    Server-Sent Events instead of a single blocking JSON response.

    Events emitted:
      start          -> {campaign_id}
      node_complete  -> {node, label, output}   (one per finished agent)
      done           -> {campaign_id, status, result}
      error          -> {message}
    """
    payload.brand_id = brand_id
    graph = build_campaign_graph()
    brand_service = BrandService()
    campaign_id = str(uuid.uuid4())

    async def event_generator():
        brand_context = brand_service.get_by_id(brand_id)
        yield _event("start", {"campaign_id": campaign_id})

        state = {
            "campaign_id": campaign_id,
            "brand_context": brand_context.model_dump(),
            "goal": payload.goal,
            "target_audience": payload.target_audience,
            "budget": payload.budget,
            "research": None,
            "strategy": None,
            "content": None,
            "qa_report": None,
            "analytics": None,
        }

        final_result = {}
        try:
            # graph.stream() yields {node_name: node_output_delta} after each node
            for step in graph.stream(state):
                for node_name, node_output in step.items():
                    final_result.update(node_output or {})
                    yield _event(
                        "node_complete",
                        {
                            "node": node_name,
                            "label": NODE_LABELS.get(node_name, node_name),
                            "output": node_output,
                        },
                    )
        except Exception as exc:  # surface failures to the UI instead of hanging
            yield _event("error", {"message": str(exc)})
            return

        qa_report = final_result.get("qa_report") or {}
        critical_issues = qa_report.get("critical_issues", [])
        status = "failed" if critical_issues else "completed"

        record = {
            "campaign_id": campaign_id,
            "brand_id": brand_id,
            "status": status,
            "goal": payload.goal,
            "target_audience": payload.target_audience,
            "budget": payload.budget,
            "brand_context": brand_context.model_dump(),
            "research": final_result.get("research"),
            "strategy": final_result.get("strategy"),
            "content": final_result.get("content"),
            "qa_report": final_result.get("qa_report"),
            "analytics": final_result.get("analytics"),
        }
        campaign_repo_create(record)

        yield _event("done", {"campaign_id": campaign_id, "status": status, "result": record})

    return EventSourceResponse(event_generator())
