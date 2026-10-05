from __future__ import annotations

from pydantic import BaseModel, Field

from app.models.plan import AgentPlan


class PolicyDecision(BaseModel):
    allowed: bool = True
    requires_approval: bool = False
    step_id: str | None = None
    reason: str | None = None


class PolicyEngine:
    """
    Evaluates whether an agent plan can be executed directly.
    """

    def evaluate(self, plan: AgentPlan) -> PolicyDecision:
        for step in plan.steps:
            if step.requires_approval:
                return PolicyDecision(
                    allowed=False,
                    requires_approval=True,
                    step_id=step.id,
                    reason=(
                        f"Step '{step.id}' requires approval "
                        "before execution."
                    ),
                )

        return PolicyDecision(
            allowed=True,
            requires_approval=False,
            step_id=None,
            reason=None,
        )