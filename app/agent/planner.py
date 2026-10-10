from __future__ import annotations

from app.models.plan import ActionType, AgentPlan, AgentStep
from app.models.project import Project
from app.models.understanding import Understanding, UnderstandingIntent
from app.tools.registry import ToolRegistry


class Planner:
    """
    Creates deterministic execution plans for DevPilot.
    """

    def __init__(self, tool_registry: ToolRegistry) -> None:
        self.tool_registry = tool_registry

    def create_plan(
        self,
        understanding: Understanding,
        project: Project | None = None,
    ) -> AgentPlan:
        """
        Create a plan based on the user's intent and selected project.
        """

        project_intents = {
            UnderstandingIntent.INSPECT_PROJECT,
            UnderstandingIntent.INVESTIGATE_HEALTH,
            UnderstandingIntent.MANAGE_ISSUE,
            UnderstandingIntent.INVESTIGATE_CI,
        }

        if understanding.intent in project_intents:
            if project is None:
                raise ValueError(
                    "A project must be selected for this request."
                )

            return self._create_project_context_plan(
                understanding=understanding,
                project=project,
            )

        if (
            understanding.intent
            == UnderstandingIntent.READ_REPOSITORY_FILE
        ):
            if project is None:
                raise ValueError(
                    "A project must be selected to read a repository file."
                )

            return self._create_file_read_plan(
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
        """Create a plan to retrieve project context."""

        tool_name = "get_project_context"

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
                        "Retrieve project metadata and repository context."
                    ),
                    tool_name=tool.name,
                    tool_input={
                        "project_id": project.id,
                    },
                    requires_approval=tool.requires_approval,
                ),
                AgentStep(
                    id="step_2",
                    action=ActionType.ANALYZE,
                    description=(
                        "Analyze the collected project context."
                    ),
                    tool_name=None,
                    requires_approval=False,
                ),
            ],
        )

    def _create_file_read_plan(
        self,
        understanding: Understanding,
        project: Project,
    ) -> AgentPlan:
        """Create a plan to read a specific repository file."""

        path = understanding.entities.get("path")

        if not isinstance(path, str) or not path.strip():
            raise ValueError(
                "A repository-relative file path is required."
            )

        tool_name = "read_repository_file"

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
                    description=f"Read repository file: {path.strip()}",
                    tool_name=tool.name,
                    tool_input={
                        "project_id": project.id,
                        "path": path.strip(),
                    },
                    requires_approval=tool.requires_approval,
                )
            ],
        )