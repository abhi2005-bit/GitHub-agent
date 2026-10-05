import pytest

from app.agent.planner import Planner
from app.tools.engineering import ProjectContextTool
from app.tools.registry import ToolRegistry


@pytest.fixture
def planner() -> Planner:
    registry = ToolRegistry()
    registry.register(ProjectContextTool())

    return Planner(registry)


def test_planner_creates_project_context_plan(planner: Planner):
    plan = planner.create_plan(
        "Check the health of project 123"
    )

    assert plan.goal == "Check the health of project 123"
    assert len(plan.steps) == 2


def test_first_step_is_project_context_observation(planner: Planner):
    plan = planner.create_plan(
        "Check project status for project 123"
    )

    step = plan.steps[0]

    assert step.id == "step_1"
    assert step.action.value == "observe"
    assert step.tool_name == "get_project_context"
    assert step.tool_input == {"project_id": 123}
    assert step.requires_approval is False


def test_second_step_is_analysis(planner: Planner):
    plan = planner.create_plan(
        "Analyze project health for project 123"
    )

    step = plan.steps[1]

    assert step.id == "step_2"
    assert step.action.value == "analyze"
    assert step.tool_name is None
    assert step.tool_input is None
    assert step.requires_approval is False


def test_project_id_is_required(planner: Planner):
    with pytest.raises(
        ValueError,
        match="A numeric project ID is required",
    ):
        planner.create_plan(
            "Check project health"
        )


def test_empty_goal_is_rejected(planner: Planner):
    with pytest.raises(
        ValueError,
        match="Goal cannot be empty",
    ):
        planner.create_plan("")


def test_unknown_goal_is_rejected(planner: Planner):
    with pytest.raises(
        ValueError,
        match="Unable to create a plan",
    ):
        planner.create_plan(
            "Tell me a joke"
        )


def test_missing_required_tool_is_rejected():
    registry = ToolRegistry()
    planner = Planner(registry)

    with pytest.raises(
        ValueError,
        match="Required tool 'get_project_context' is not registered",
    ):
        planner.create_plan(
            "Check project health for project 123"
        )
