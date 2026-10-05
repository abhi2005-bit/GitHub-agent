from __future__ import annotations

from app.models.plan import ActionType, AgentPlan, AgentStep
from app.models.understanding import Understanding
from app.tools.registry import ToolRegistry


class Planner:
    """
    Deterministic planner for the DevPilot agent.

    The first version intentionally uses explicit rules instead of
    an LLM so that planning behavior is predictable and testable.
    """

    def __init__(self, tool_registry: ToolRegistry) -> None:
        self.tool_registry = tool_registry

    def create_plan(self, understanding: Understanding) -> AgentPlan:
        """
        Create an execution plan from a structured understanding.
        """

        if not understanding.intent:
            raise ValueError("Understanding intent cannot be empty.")

        if understanding.intent in (
            "inspect_project",
            "investigate_health",
            "manage_issue",
            "investigate_ci",
        ):
            return self._create_project_context_plan(understanding)

        raise ValueError(
            f"Unable to create a plan for intent: "
            f"'{understanding.intent}'"
        )

    def _create_project_context_plan(
        self,
        understanding: Understanding,
    ) -> AgentPlan:
        """
        Create a deterministic plan for gathering project context.
        """

        tool_name = "get_project_context"
        project_id = understanding.project_id

        if project_id is None:
            raise ValueError(
                "A numeric project ID is required."
            )

        if not self.tool_registry.has(tool_name):
            raise ValueError(
                f"Required tool '{tool_name}' is not registered."
            )

        tool = self.tool_registry.get(tool_name)

        return AgentPlan(
            goal=understanding.desired_outcome,
            steps=[
                AgentStep(
                    id="step_1",
                    action=ActionType.OBSERVE,
                    description=(
                        "Gather engineering context for the requested project."
                    ),
                    tool_name=tool.name,
                    tool_input={
                        "project_id": project_id,
                    },
                    requires_approval=tool.requires_approval,
                ),
                AgentStep(
                    id="step_2",
                    action=ActionType.ANALYZE,
                    description=(
                        "Analyze the collected project context and identify "
                        "relevant engineering signals."
                    ),
                    tool_name=None,
                    requires_approval=False,
                ),
            ],
        )