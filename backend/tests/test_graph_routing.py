# tests/test_graph_routing.py
"""The self-correction loop's decision logic, tested as pure functions.

These are the three decisions that make the pipeline run unattended: whether
a QA result ships, loops back for a revision, or falls through to
arbitration, and what arbitration itself keeps versus drops. None of it
needs a live LLM or database — it's dict-in, dict/string-out — so it is
tested directly rather than through a full graph run.
"""
from langgraph.graph import END

from app.graph.builder import _after_arbitrate, _after_qa
from app.graph.nodes import arbitrate_node, revise_node


def _qa(passed: bool, issues: list[dict] | None = None) -> dict:
    return {"passed": passed, "issues": issues or []}


def _critical(channel: str, issue: str = "problem") -> dict:
    return {"channel": channel, "severity": "critical", "issue": issue, "fix": "fix it"}


def _advisory(channel: str) -> dict:
    return {"channel": channel, "severity": "advisory", "issue": "minor", "fix": "polish"}


# --- _after_qa --------------------------------------------------------------


def test_clean_pass_publishes():
    state = {"qa_report": _qa(True), "revisions": 0, "max_revisions": 2}
    assert _after_qa(state) == "publish"


def test_advisory_only_still_publishes():
    """Advisory issues never block — only critical ones do."""
    state = {"qa_report": _qa(True, [_advisory("email")]), "revisions": 0, "max_revisions": 2}
    assert _after_qa(state) == "publish"


def test_critical_issue_with_budget_remaining_revises():
    state = {
        "qa_report": _qa(False, [_critical("linkedin")]),
        "revisions": 0,
        "max_revisions": 2,
    }
    assert _after_qa(state) == "revise"


def test_critical_issue_with_budget_spent_arbitrates():
    state = {
        "qa_report": _qa(False, [_critical("linkedin")]),
        "revisions": 2,
        "max_revisions": 2,
    }
    assert _after_qa(state) == "arbitrate"


def test_passed_flag_true_but_critical_issue_present_still_blocks():
    """A malformed agent response (passed=True alongside a critical issue)
    must not slip through — the router checks the issues list itself."""
    state = {
        "qa_report": _qa(True, [_critical("linkedin")]),
        "revisions": 0,
        "max_revisions": 2,
    }
    assert _after_qa(state) == "revise"


def test_zero_revision_budget_goes_straight_to_arbitration():
    state = {
        "qa_report": _qa(False, [_critical("linkedin")]),
        "revisions": 0,
        "max_revisions": 0,
    }
    assert _after_qa(state) == "arbitrate"


# --- revise_node --------------------------------------------------------------


def test_revise_node_increments_the_counter():
    state = {"revisions": 0, "qa_report": _qa(False, [_critical("email")])}
    result = revise_node(state)
    assert result == {"revisions": 1, "status": "revising"}


# --- arbitrate_node -----------------------------------------------------------


def test_arbitrate_drops_only_the_failing_channels():
    state = {
        "qa_report": _qa(False, [_critical("email")]),
        "content": {
            "assets": [
                {"channel": "email", "headline": "bad"},
                {"channel": "linkedin", "headline": "fine"},
            ]
        },
        "revisions": 2,
    }
    result = arbitrate_node(state)
    assert result["status"] == "partial"
    assert result["dropped_channels"] == ["email"]
    assert [a["channel"] for a in result["content"]["assets"]] == ["linkedin"]


def test_arbitrate_is_case_and_whitespace_insensitive_on_channel_match():
    """A single asset whose only channel is the (differently-cased,
    padded) critical one has nothing left to keep — this falls through to
    the same 'abandoned' branch as test_arbitrate_abandons_when_nothing_survives,
    which is what proves the match itself is case/whitespace-insensitive."""
    state = {
        "qa_report": _qa(False, [_critical(" Email ")]),
        "content": {"assets": [{"channel": "email", "headline": "x"}]},
        "revisions": 2,
    }
    result = arbitrate_node(state)
    assert result["status"] == "abandoned"
    assert result["dropped_channels"] == ["email"]
    assert "content" not in result


def test_arbitrate_abandons_when_nothing_survives():
    state = {
        "qa_report": _qa(False, [_critical("email"), _critical("linkedin")]),
        "content": {
            "assets": [
                {"channel": "email", "headline": "bad"},
                {"channel": "linkedin", "headline": "also bad"},
            ]
        },
        "revisions": 2,
    }
    result = arbitrate_node(state)
    assert result["status"] == "abandoned"
    assert "error" in result


# --- _after_arbitrate ---------------------------------------------------------


def test_after_arbitrate_abandoned_ends_the_run():
    assert _after_arbitrate({"status": "abandoned"}) == END


def test_after_arbitrate_partial_still_publishes():
    assert _after_arbitrate({"status": "partial"}) == "publish"
