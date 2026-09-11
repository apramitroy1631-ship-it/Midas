# tests/test_agent_schemas.py
"""The typed contracts between agents.

Every schema in app/schemas/agents.py sets extra="forbid" deliberately: a
provider (real model or the simulator) that drifts from the contract must
fail loudly at the boundary, not propagate a malformed dict deeper into the
graph. These tests pin that behaviour so a future edit can't loosen it by
accident.
"""
import pytest
from pydantic import ValidationError

from app.schemas.agents import (
    ChannelPerformance,
    QAIssue,
    QAReport,
    ResearchOutput,
)


def test_qa_report_accepts_a_well_formed_response():
    report = QAReport(
        passed=False,
        verdict="Needs work.",
        brand_safety_score=80,
        goal_alignment_score=70,
        issues=[
            QAIssue(channel="email", severity="critical", issue="x", fix="y"),
        ],
    )
    assert report.passed is False
    assert report.issues[0].severity == "critical"


def test_qa_report_rejects_an_unknown_field():
    """A model that invents a field (e.g. 'confidence') must fail validation
    rather than have the extra data silently dropped or ignored."""
    with pytest.raises(ValidationError):
        QAReport(
            passed=True,
            verdict="ok",
            brand_safety_score=90,
            goal_alignment_score=90,
            issues=[],
            confidence=0.9,  # not part of the contract
        )


def test_qa_report_rejects_a_missing_required_field():
    with pytest.raises(ValidationError):
        QAReport(passed=True, verdict="ok", brand_safety_score=90, issues=[])  # missing goal_alignment_score


def test_channel_performance_rejects_wrong_types():
    with pytest.raises(ValidationError):
        ChannelPerformance(channel_name="email", impressions="a lot", clicks=10, ctr=1.0)


def test_research_output_round_trips_through_model_dump():
    """Confirms the shape agents.run() returns is exactly what graph nodes
    store back into state — model_dump() must not drop or rename fields."""
    original = ResearchOutput(
        target_audience="Ops directors at mid-market logistics firms evaluating automation vendors.",
        market_size="12400",
        growth_rate="11.8",
        key_insights=["a", "b", "c"],
        competitors=[],
        sources=["model-knowledge: no live search configured"],
    )
    restored = ResearchOutput(**original.model_dump())
    assert restored == original
