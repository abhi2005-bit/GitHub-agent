from __future__ import annotations

import pytest

from app.core.executor import Executor
from app.models.execution import ExecutionResult
from app.models.plan import AgentPlan, AgentStep, ActionType
from app.models.tool import ToolResult
from app.tools.base import AgentTool
from app.tools.registry import ToolRegistry


class FakeTool:
    name = "fake_tool"
    description = "A fake tool for testing."
    requires_approval = False

    async def execute(self, **kwargs) -> ToolResult:
        return ToolResult(
            success=True,
            data={"message": "hello"},
        )


class FailingTool:
    name = "failing_tool"
    description = "A fake failing tool."
    requires_approval = False

    async def execute(self, **kwargs) -> ToolResult:
        return ToolResult(
            success=False,
            error="Something went wrong",
        )


@pytest.mark.asyncio
async def test_executor_successful_tool():
    registry = ToolRegistry()
    registry.register(FakeTool())

    executor = Executor(registry)

    plan = AgentPlan(
        goal="Test fake tool",
        steps=[
            AgentStep(
                id="step_1",
                action=ActionType.OBSERVE,
                description="Run fake tool",
                tool_name="fake_tool",
                tool_input={"project_id": 1},
            )
        ],
    )

    result = await executor.execute(plan)

    assert isinstance(result, ExecutionResult)
    assert result.success is True
    assert len(result.step_results) == 1

    step_result = result.step_results[0]

    assert step_result.step_id == "step_1"
    assert step_result.success is True
    assert step_result.tool_result is not None
    assert step_result.tool_result.data == {"message": "hello"}


@pytest.mark.asyncio
async def test_executor_skips_step_without_tool():
    registry = ToolRegistry()
    executor = Executor(registry)

    plan = AgentPlan(
        goal="Test skipped step",
        steps=[
            AgentStep(
                id="step_1",
                action=ActionType.ANALYZE,
                description="Analyze project",
            )
        ],
    )

    result = await executor.execute(plan)

    assert result.success is True
    assert len(result.step_results) == 1

    step_result = result.step_results[0]

    assert step_result.step_id == "step_1"
    assert step_result.success is True
    assert step_result.tool_result is None
    assert step_result.error == "Step skipped because no tool is configured."


@pytest.mark.asyncio
async def test_executor_handles_unknown_tool():
    registry = ToolRegistry()
    executor = Executor(registry)

    plan = AgentPlan(
        goal="Test unknown tool",
        steps=[
            AgentStep(
                id="step_1",
                action=ActionType.OBSERVE,
                description="Run missing tool",
                tool_name="does_not_exist",
            )
        ],
    )

    result = await executor.execute(plan)

    assert result.success is False
    assert len(result.step_results) == 1

    step_result = result.step_results[0]

    assert step_result.step_id == "step_1"
    assert step_result.success is False
    assert step_result.tool_result is None
    assert "does_not_exist" in step_result.error


@pytest.mark.asyncio
async def test_executor_handles_tool_failure():
    registry = ToolRegistry()
    registry.register(FailingTool())

    executor = Executor(registry)

    plan = AgentPlan(
        goal="Test failing tool",
        steps=[
            AgentStep(
                id="step_1",
                action=ActionType.ACT,
                description="Run failing tool",
                tool_name="failing_tool",
            )
        ],
    )

    result = await executor.execute(plan)

    assert result.success is False
    assert len(result.step_results) == 1

    step_result = result.step_results[0]

    assert step_result.step_id == "step_1"
    assert step_result.success is False
    assert step_result.tool_result is not None
    assert step_result.tool_result.success is False
    assert step_result.error == "Something went wrong"