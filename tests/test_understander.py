from __future__ import annotations

from app.agent.understander import Understander


def test_understander_extracts_project_id():
    understander = Understander()

    result = understander.understand("Check project 12 health")

    assert result.project_id == 12


def test_understander_identifies_health_intent():
    understander = Understander()

    result = understander.understand("Check project 12 health")

    assert result.intent == "investigate_health"


def test_understander_identifies_issue_intent():
    understander = Understander()

    result = understander.understand("Find the bug in project 12")

    assert result.intent == "manage_issue"
    assert result.project_id == 12


def test_understander_identifies_ci_intent():
    understander = Understander()

    result = understander.understand("Investigate the CI pipeline")

    assert result.intent == "investigate_ci"
    assert result.project_id is None


def test_understander_handles_project_without_specific_intent():
    understander = Understander()

    result = understander.understand("Inspect project 12")

    assert result.intent == "inspect_project"
    assert result.project_id == 12


def test_understander_handles_unknown_intent():
    understander = Understander()

    result = understander.understand("Tell me something about software")

    assert result.intent == "unknown"
    assert result.project_id is None


def test_understander_preserves_desired_outcome():
    understander = Understander()

    goal = "Check project 12 health"

    result = understander.understand(goal)

    assert result.desired_outcome == goal