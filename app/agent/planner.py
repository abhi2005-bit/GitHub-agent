from __future__ import annotations

from app.models.plan import ActionType, AgentPlan, AgentStep
from app.models.project import Project
from app.models.understanding import Understanding
from app.tools.registry import ToolRegistry


class Planner:
    """
    Deterministic planner for the DevPilot agent.

    Creates an execution plan using the user's understanding
    and the selected project.
    """

    def __init__(self, tool_registry: ToolRegistry) -> None:
        self.tool_registry = tool_registry

    def create_plan(
        self,
        understanding: Understanding,
        project: Project | None = None,
    ) -> AgentPlan:
        """
        Create an execution plan from a structured understanding
        and an optional selected project.
        """

        if understanding.intent in (
            "inspect_project",
            "investigate_health",
            "manage_issue",
            "investigate_ci",
        ):
            if project is None:
                raise ValueError(
                    "A project must be selected for this request."
                )

            return self._create_project_context_plan(
                understanding=understanding,
                project=project,
            )

        raise ValueError(
            f"Unable to create a plan for intent: "
            f"'{understanding.intent.value}'"
        )

    def _create_project_context_plan(
        self,
        understanding: Understanding,
        project: Project,
    ) -> AgentPlan:
        """
        Create a plan for gathering engineering context
        from the selected project.
        """

        tool_name = "get_project_context"

        # Use the selected project's ID as the source of truth.
        project_id = project.id

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
                        "Gather engineering context for the selected project."
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