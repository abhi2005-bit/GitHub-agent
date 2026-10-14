from __future__ import annotations

import pytest

from app.core.policy import PolicyEngine
from app.core.runner import AgentRunner
from app.models.agent import AgentState
from app.models.execution import ExecutionResult
from app.models.plan import ActionType, AgentPlan, AgentStep
from app.models.project import Project, ProjectSource
from app.models.understanding import Understanding, UnderstandingIntent


class FakeUnderstander:
    def understand(self, goal):
        return Understanding(intent=UnderstandingIntent.INVESTIGATE_HEALTH,
                             desired_outcome=goal)


class FakePlanner:
    def __init__(self, plan):
        self.plan = plan

    def create_plan(self, understanding, project):
        return self.plan


class FakeProjectContext:
    def get_project(self, project_id):
        return Project(id=project_id, name="demo", source=ProjectSource.GITHUB,
                       owner="org", repository="repo")


class FakeExecutor:
    def __init__(self, result):
        self.result = result
        self.calls = 0

    async def execute(self, plan):
        self.calls += 1
        return self.result


class FakeAnalyzer:
    def __init__(self, error=None):
        self.error = error

    def analyze(self, goal, execution_result, intent):
        if self.error:
            raise RuntimeError(self.error)
        return "Analysis completed from supplied evidence."


class ReviewUnderstander(FakeUnderstander):
    def understand(self, goal):
        return Understanding(intent=UnderstandingIntent.REVIEW_CODE,
                             desired_outcome=goal, file_paths=["app.py"])


class StaticPlan:
    def create_plan(self, understanding, project):
        return _plan()


class ReviewExecutor:
    async def execute(self, plan):
        from app.models.execution import StepExecutionResult
        from app.models.tool import ToolResult
        return ExecutionResult(success=True, step_results=[StepExecutionResult(
            step_id="read", success=True,
            tool_result=ToolResult(success=True, data={
                "path": "app.py", "content": "PRIVATE_REPOSITORY_SOURCE",
            }),
        )])


def _plan(requires_approval=False):
    return AgentPlan(goal="inspect", steps=[AgentStep(
        id="step_1", action=ActionType.OBSERVE, description="inspect",
        tool_name="inspect", requires_approval=requires_approval,
    )])


@pytest.mark.asyncio
async def test_runner_blocks_policy_before_execution() -> None:
    executor = FakeExecutor(ExecutionResult(success=True, step_results=[]))
    runner = AgentRunner(FakeUnderstander(), FakePlanner(_plan(True)), PolicyEngine(),
                         executor, FakeProjectContext(), FakeAnalyzer())
    result = await runner.run("inspect repository", project_id=1)
    assert result.state == AgentState.FAILED
    assert "requires approval" in result.error
    assert executor.calls == 0


@pytest.mark.asyncio
async def test_runner_uses_execution_outcome_and_reports_analysis_failure() -> None:
    failed_execution = ExecutionResult(success=False, step_results=[], error="tool failed")
    runner = AgentRunner(FakeUnderstander(), FakePlanner(_plan()), PolicyEngine(),
                         FakeExecutor(failed_execution), FakeProjectContext(), FakeAnalyzer())
    result = await runner.run("inspect repository", project_id=1)
    assert result.state == AgentState.FAILED
    assert result.error == "tool failed"

    broken_analyzer = AgentRunner(FakeUnderstander(), FakePlanner(_plan()), PolicyEngine(),
                                  FakeExecutor(ExecutionResult(success=True, step_results=[])),
                                  FakeProjectContext(), FakeAnalyzer("invalid model response"))
    analysis_result = await broken_analyzer.run("inspect repository", project_id=1)
    assert analysis_result.state == AgentState.FAILED
    assert analysis_result.error == "invalid model response"


@pytest.mark.asyncio
async def test_runner_completes_success_and_does_not_copy_review_source_to_transcript() -> None:
    runner = AgentRunner(FakeUnderstander(), FakePlanner(_plan()), PolicyEngine(),
                         FakeExecutor(ExecutionResult(success=True, step_results=[])),
                         FakeProjectContext(), FakeAnalyzer())
    result = await runner.run("inspect repository", project_id=1)
    assert result.state == AgentState.COMPLETED

    review_runner = AgentRunner(ReviewUnderstander(), StaticPlan(), PolicyEngine(),
                                ReviewExecutor(), FakeProjectContext(), FakeAnalyzer())
    review = await review_runner.run("Review app.py", project_id=1)
    transcript = "\n".join(message.content for message in review.messages)
    assert review.state == AgentState.COMPLETED
    assert "PRIVATE_REPOSITORY_SOURCE" not in transcript
    assert "File retrieved for review: app.py" in transcript
