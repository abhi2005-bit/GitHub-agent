from __future__ import annotations

import pytest

from app.core.policy import PolicyDecision
from app.core.runner import AgentRunner
from app.models.agent import AgentState
from app.models.execution import ExecutionResult, StepExecutionResult
from app.models.plan import AgentPlan, AgentStep, ActionType
from app.models.tool import ToolResult


class FakePlanner:
    def create_plan(self, goal: str) -> AgentPlan:
        return AgentPlan(
            goal=goal,
            steps=[
                AgentStep(
                    id="step_1",
                    action=ActionType.OBSERVE,
                    description="Observe project",
                    tool_name="fake_tool",
                    tool_input={"project_id": 1},
                )
            ],
        )


class FailingPlanner:
    def create_plan(self, goal: str) -> AgentPlan:
        raise ValueError("Unable to create plan")


class FakePolicy:
    def evaluate(self, plan: AgentPlan) -> PolicyDecision:
        return PolicyDecision(
            allowed=True,
            requires_approval=False,
        )


class BlockingPolicy:
    def evaluate(self, plan: AgentPlan) -> PolicyDecision:
        return PolicyDecision(
            allowed=False,
            requires_approval=True,
            step_id="step_1",
            reason="Step 'step_1' requires approval before execution.",
        )


class FakeExecutor:
    async def execute(self, plan: AgentPlan) -> ExecutionResult:
        return ExecutionResult(
            success=True,
            step_results=[
                StepExecutionResult(
                    step_id="step_1",
                    success=True,
                    tool_result=ToolResult(
                        success=True,
                        data={"message": "success"},
                    ),
                )
            ],
        )


class FailingExecutor:
    async def execute(self, plan: AgentPlan) -> ExecutionResult:
        return ExecutionResult(
            success=False,
            step_results=[
                StepExecutionResult(
                    step_id="step_1",
                    success=False,
                    tool_result=ToolResult(
                        success=False,
                        error="Tool failed",
                    ),
                    error="Tool failed",
                )
            ],
            error="Tool failed",
        )


class TrackingExecutor:
    def __init__(self) -> None:
        self.called = False

    async def execute(self, plan: AgentPlan) -> ExecutionResult:
        self.called = True

        return ExecutionResult(
            success=True,
            step_results=[],
        )


@pytest.mark.asyncio
async def test_runner_completes_successfully():
    runner = AgentRunner(
        planner=FakePlanner(),
        policy_engine=FakePolicy(),
        executor=FakeExecutor(),
    )

    run = await runner.run("Check project 1 health")

    assert run.state == AgentState.COMPLETED
    assert run.error is None
    assert run.iterations == 1

    assert len(run.messages) == 4

    assert run.messages[0].role == "user"
    assert run.messages[0].content == "Check project 1 health"

    assert run.messages[1].content == "Agent run started."

    assert "Plan created with 1 step(s)." in run.messages[2].content

    assert run.messages[3].content == "Agent execution completed successfully."


@pytest.mark.asyncio
async def test_runner_fails_when_planner_raises_exception():
    runner = AgentRunner(
        planner=FailingPlanner(),
        policy_engine=FakePolicy(),
        executor=FakeExecutor(),
    )

    run = await runner.run("Check project 1 health")

    assert run.state == AgentState.FAILED
    assert run.error == "Unable to create plan"
    assert run.iterations == 0

    assert len(run.messages) == 3

    assert "Agent run failed: Unable to create plan" in run.messages[-1].content


@pytest.mark.asyncio
async def test_runner_fails_when_executor_returns_failure():
    runner = AgentRunner(
        planner=FakePlanner(),
        policy_engine=FakePolicy(),
        executor=FailingExecutor(),
    )

    run = await runner.run("Check project 1 health")

    assert run.state == AgentState.FAILED
    assert run.error == "Tool failed"
    assert run.iterations == 1

    assert len(run.messages) == 4

    assert run.messages[0].role == "user"
    assert run.messages[0].content == "Check project 1 health"

    assert run.messages[1].content == "Agent run started."

    assert "Plan created with 1 step(s)." in run.messages[2].content

    assert "Agent execution failed: Tool failed" in run.messages[3].content


@pytest.mark.asyncio
async def test_runner_blocks_execution_when_policy_rejects_plan():
    executor = TrackingExecutor()

    runner = AgentRunner(
        planner=FakePlanner(),
        policy_engine=BlockingPolicy(),
        executor=executor,
    )

    run = await runner.run("Update project 1")

    assert run.state == AgentState.FAILED

    assert run.error == (
        "Step 'step_1' requires approval before execution."
    )

    assert run.iterations == 0

    assert executor.called is False

    assert len(run.messages) == 4

    assert "Plan created with 1 step(s)." in run.messages[2].content

    assert (
        "Agent execution blocked by policy:"
        in run.messages[3].content
    )


@pytest.mark.asyncio
async def test_runner_updates_timestamps():
    runner = AgentRunner(
        planner=FakePlanner(),
        policy_engine=FakePolicy(),
        executor=FakeExecutor(),
    )

    run = await runner.run("Check project 1 health")

    assert run.created_at is not None
    assert run.updated_at is not None
    assert run.updated_at >= run.created_at