from __future__ import annotations

from app.core.policy import PolicyEngine
from app.models.plan import ActionType, AgentPlan, AgentStep


def test_policy_allows_plan_without_approval():
    engine = PolicyEngine()

    plan = AgentPlan(
        goal="Check project health",
        steps=[
            AgentStep(
                id="step_1",
                action=ActionType.OBSERVE,
                description="Get project context",
                tool_name="get_project_context",
                tool_input={"project_id": 1},
                requires_approval=False,
            )
        ],
    )

    decision = engine.evaluate(plan)

    assert decision.allowed is True
    assert decision.requires_approval is False
    assert decision.step_id is None
    assert decision.reason is None


def test_policy_blocks_plan_requiring_approval():
    engine = PolicyEngine()

    plan = AgentPlan(
        goal="Update project",
        steps=[
            AgentStep(
                id="step_1",
                action=ActionType.ACT,
                description="Update project",
                tool_name="update_project",
                tool_input={"project_id": 1},
                requires_approval=True,
            )
        ],
    )

    decision = engine.evaluate(plan)

    assert decision.allowed is False
    assert decision.requires_approval is True
    assert decision.step_id == "step_1"
    assert decision.reason is not None


def test_policy_checks_all_steps():
    engine = PolicyEngine()

    plan = AgentPlan(
        goal="Inspect and update project",
        steps=[
            AgentStep(
                id="step_1",
                action=ActionType.OBSERVE,
                description="Inspect project",
                tool_name="get_project_context",
                requires_approval=False,
            ),
            AgentStep(
                id="step_2",
                action=ActionType.ACT,
                description="Update project",
                tool_name="update_project",
                requires_approval=True,
            ),
        ],
    )

    decision = engine.evaluate(plan)

    assert decision.allowed is False
    assert decision.requires_approval is True
    assert decision.step_id == "step_2"