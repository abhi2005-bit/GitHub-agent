from __future__ import annotations

import json

import pytest

from app.agent.analyzer import Analyzer
from app.agent.planner import Planner
from app.agent.understander import Understander
from app.core.executor import Executor
from app.core.policy import PolicyEngine
from app.models.execution import ExecutionResult, StepExecutionResult
from app.models.plan import ActionType, AgentPlan, AgentStep
from app.models.project import Project, ProjectSource
from app.models.review import ReviewAnalysis
from app.models.tool import ToolResult
from app.models.understanding import Understanding, UnderstandingIntent
from app.tools.registry import ToolRegistry


class FakeLLM:
    def __init__(self, response: str) -> None:
        self.response = response
        self.prompts: list[str] = []

    def generate(self, prompt: str) -> str:
        self.prompts.append(prompt)
        return self.response

    def generate_structured(self, prompt: str, schema: dict, schema_name: str) -> str:
        return self.generate(prompt)


class FakeTool:
    name = "read_repository_file"
    description = "read"
    requires_approval = False

    def __init__(self, results: list[ToolResult]) -> None:
        self.results = iter(results)
        self.calls: list[dict] = []

    async def execute(self, **kwargs) -> ToolResult:
        self.calls.append(kwargs)
        return next(self.results)


def test_understander_extracts_unique_explicit_paths_and_rejects_bad_response() -> None:
    response = json.dumps({
        "intent": "review_code", "project_id": None, "entities": {},
        "constraints": {}, "desired_outcome": "Review code", "file_paths": [],
    })
    result = Understander(FakeLLM(response)).understand(
        "Review app/main.py and app\\agent\\planner.py, then app/main.py"
    )
    assert result.file_paths == ["app/main.py", "app/agent/planner.py"]
    assert result.intent == UnderstandingIntent.REVIEW_CODE

    with pytest.raises(ValueError, match="invalid JSON"):
        Understander(FakeLLM("not json")).understand("inspect this")
    with pytest.raises(ValueError, match="empty"):
        Understander(FakeLLM("{}")).understand(" ")


def test_planner_builds_unique_steps_and_rejects_traversal() -> None:
    registry = ToolRegistry()
    tool = FakeTool([])
    registry.register(tool)
    planner = Planner(registry)
    project = Project(id=9, name="demo", source=ProjectSource.GITHUB,
                      owner="org", repository="repo", branch="develop")
    understanding = Understanding(
        intent=UnderstandingIntent.REVIEW_CODE,
        desired_outcome="Review these files",
        file_paths=["app/main.py", "app/main.py", "app/agent/planner.py"],
    )
    plan = planner.create_plan(understanding, project)
    assert [step.id for step in plan.steps] == ["read_file_1", "read_file_2"]
    assert [step.tool_input for step in plan.steps] == [
        {"project_id": 9, "path": "app/main.py"},
        {"project_id": 9, "path": "app/agent/planner.py"},
    ]
    with pytest.raises(ValueError, match="repository-relative"):
        planner.create_plan(understanding.model_copy(update={"file_paths": ["../secret.py"]}), project)


def test_planner_routes_each_investigation_intent_to_its_real_tool() -> None:
    registry = ToolRegistry()
    for name in ("get_project_context", "get_repository_health", "search_open_issues", "investigate_ci"):
        registry.register(type("Tool", (), {"name": name, "description": name,
                                             "requires_approval": False})())
    planner = Planner(registry)
    project = Project(id=2, name="demo", source=ProjectSource.GITHUB,
                      owner="org", repository="repo")
    expected = {
        UnderstandingIntent.INSPECT_PROJECT: "get_project_context",
        UnderstandingIntent.INVESTIGATE_HEALTH: "get_repository_health",
        UnderstandingIntent.MANAGE_ISSUE: "search_open_issues",
        UnderstandingIntent.INVESTIGATE_CI: "investigate_ci",
    }
    for intent, tool_name in expected.items():
        understanding = Understanding(intent=intent, desired_outcome="Investigate")
        assert planner.create_plan(understanding, project).steps[0].tool_name == tool_name
    issue_request = Understanding(intent=UnderstandingIntent.MANAGE_ISSUE,
                                   desired_outcome="Find issues",
                                   entities={"issue_query": "authentication"})
    assert planner.create_plan(issue_request, project).steps[0].tool_input == {
        "project_id": 2, "query": "authentication"
    }


def test_planner_reports_missing_project_tool_and_rejects_absolute_paths() -> None:
    planner = Planner(ToolRegistry())
    request = Understanding(intent=UnderstandingIntent.INSPECT_PROJECT,
                            desired_outcome="Inspect")
    with pytest.raises(ValueError, match="project must be selected"):
        planner.create_plan(request)

    project = Project(id=1, name="demo", source=ProjectSource.GITHUB,
                      owner="org", repository="repo")
    with pytest.raises(ValueError, match="not registered"):
        planner.create_plan(request, project)

    registry = ToolRegistry()
    registry.register(FakeTool([]))
    planner = Planner(registry)
    for invalid_path in ("C:/secret.py", "/tmp/secret.py", "app//main.py", "app/../secret.py"):
        file_request = Understanding(intent=UnderstandingIntent.READ_REPOSITORY_FILE,
                                     desired_outcome="Read", file_paths=[invalid_path])
        with pytest.raises(ValueError, match="repository-relative"):
            planner.create_plan(file_request, project)


@pytest.mark.asyncio
async def test_executor_records_all_outcomes_and_policy_blocks_approval() -> None:
    registry = ToolRegistry()
    tool = FakeTool([
        ToolResult(success=False, error="not found"),
        ToolResult(success=True, data={"ok": True}),
    ])
    registry.register(tool)
    plan = AgentPlan(goal="read", steps=[
        AgentStep(id="one", action=ActionType.OBSERVE, description="first",
                  tool_name=tool.name, tool_input={"path": "a.py"}),
        AgentStep(id="two", action=ActionType.OBSERVE, description="second",
                  tool_name=tool.name, tool_input={"path": "b.py"}),
    ])
    result = await Executor(registry).execute(plan)
    assert result.success is False
    assert result.error == "not found"
    assert [item.success for item in result.step_results] == [False, True]
    assert len(tool.calls) == 2

    approved_plan = plan.model_copy(update={
        "steps": [plan.steps[0].model_copy(update={"requires_approval": True})]
    })
    decision = PolicyEngine().evaluate(approved_plan)
    assert decision.allowed is False
    assert decision.step_id == "one"


@pytest.mark.asyncio
async def test_executor_records_missing_tools_and_tool_exceptions() -> None:
    registry = ToolRegistry()
    plan = AgentPlan(goal="run", steps=[
        AgentStep(id="missing", action=ActionType.OBSERVE, description="missing", tool_name="unknown"),
        AgentStep(id="unconfigured", action=ActionType.ANALYZE, description="not implemented"),
    ])
    result = await Executor(registry).execute(plan)
    assert result.success is False
    assert len(result.step_results) == 2
    assert all(not item.success for item in result.step_results)


def _review_payload(**updates) -> str:
    payload = {
        "summary": "One concrete issue was found.",
        "findings": [{
            "severity": "Medium", "category": "Reliability", "status": "confirmed",
            "file_path": "app.py", "line_start": 2, "line_end": None,
            "evidence": "open(path)", "explanation": "The file handle is not managed.",
            "impact": "Repeated calls can leak descriptors.", "remediation": "Use a context manager.",
            "confidence": 0.95,
        }],
        "positive_observations": [], "limitations": ["Runtime behavior was not tested."],
    }
    payload.update(updates)
    return json.dumps(payload)


def test_analyzer_validates_ast_source_and_finding_evidence() -> None:
    llm = FakeLLM(_review_payload())
    result = ExecutionResult(success=True, step_results=[StepExecutionResult(
        step_id="read1", success=True,
        tool_result=ToolResult(success=True, data={"path": "app.py", "content": "def f():\n    open(path)\n"}),
    )])
    report = Analyzer(llm).analyze("Review app.py", result, UnderstandingIntent.REVIEW_CODE)
    assert "`app.py`:2" in report
    assert "Python AST parsing passed" in report
    assert "Runtime behavior was not tested" in report
    assert "open(path)" in llm.prompts[0]

    invalid_llm = FakeLLM(_review_payload(findings=[{
        "severity": "High", "category": "Security", "status": "confirmed",
        "file_path": "app.py", "line_start": 99, "line_end": None,
        "evidence": "open(path)", "explanation": "bad", "impact": "bad",
        "remediation": "bad", "confidence": 1,
    }]))
    limited = Analyzer(invalid_llm).analyze("Review app.py", result, UnderstandingIntent.REVIEW_CODE)
    assert "Findings withheld" in limited
    assert "outside 'app.py'" in limited


def test_review_model_rejects_invalid_severity_and_unknown_fields() -> None:
    with pytest.raises(Exception):
        ReviewAnalysis.model_validate({"summary": "x", "findings": [{"severity": "Blocker"}]})


def test_analyzer_reports_ast_failure_and_bounds_general_evidence() -> None:
    result = ExecutionResult(success=True, step_results=[StepExecutionResult(
        step_id="read", success=True,
        tool_result=ToolResult(success=True, data={"path": "broken.py", "content": "def f(:\n"}),
    )])
    review = Analyzer(FakeLLM(json.dumps({
        "summary": "Syntax is invalid.", "findings": [],
        "positive_observations": [], "limitations": [],
    })))
    report = review.analyze("Review broken.py", result, UnderstandingIntent.REVIEW_CODE)
    assert "Python AST parsing failed" in report

    llm = FakeLLM("General report")
    analyzer = Analyzer(llm)
    huge = ExecutionResult(success=True, step_results=[StepExecutionResult(
        step_id="data", success=True,
        tool_result=ToolResult(success=True, data={"content": "x" * 10_000}),
    )])
    analyzer.analyze("summarize", huge, UnderstandingIntent.UNKNOWN)
    assert '"evidence_truncated": true' in llm.prompts[0].lower()


def test_understander_extracts_issue_search_topic_deterministically() -> None:
    response = json.dumps({
        "intent": "manage_issue", "project_id": None, "entities": {},
        "constraints": {}, "desired_outcome": "Find open issues", "file_paths": [],
    })
    understanding = Understander(FakeLLM(response)).understand(
        "Find open issues relating to authentication."
    )
    assert understanding.entities["issue_query"] == "authentication"

