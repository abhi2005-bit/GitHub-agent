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

        if understanding.intent in {
            UnderstandingIntent.READ_REPOSITORY_FILE,
            UnderstandingIntent.REVIEW_CODE,
        }:
            if project is None:
                raise ValueError(
                    "A project must be selected for this request."
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
        """Create a plan to read one or more repository files."""

        # Prefer the explicitly extracted file paths.
        paths = understanding.file_paths.copy()

        # Support older single-file requests.
        if not paths:
            path = understanding.entities.get("path")

            if isinstance(path, str) and path.strip():
                paths = [path]

        if not paths:
            raise ValueError(
                "At least one repository-relative file path is required."
            )

        # Validate paths and remove duplicates while preserving order.
        unique_paths: list[str] = []
        seen_paths: set[str] = set()

        for path in paths:
            if not isinstance(path, str) or not path.strip():
                raise ValueError(
                    f"Invalid file path: '{path}'. "
                    "Must be a non-empty string."
                )

            path = path.strip().replace("\\", "/")

            if (
                path.startswith("/")
                or (len(path) >= 2 and path[1] == ":")
                or ".." in path.split("/")
            ):
                raise ValueError(
                    f"Invalid file path: '{path}'. "
                    "Must be a repository-relative path."
                )

            if path not in seen_paths:
                unique_paths.append(path)
                seen_paths.add(path)

        tool_name = "read_repository_file"

        if not self.tool_registry.has(tool_name):
            raise ValueError(
                f"Required tool '{tool_name}' is not registered."
            )

        tool = self.tool_registry.get(tool_name)

        # Create one execution step for each file.
        steps: list[AgentStep] = []

        for index, path in enumerate(unique_paths, start=1):
            steps.append(
                AgentStep(
                    id=f"read_file_{index}",
                    action=ActionType.OBSERVE,
                    description=f"Read repository file: {path}",
                    tool_name=tool.name,
                    tool_input={
                        "project_id": project.id,
                        "path": path,
                    },
                    requires_approval=tool.requires_approval,
                )
            )

        return AgentPlan(
            goal=understanding.desired_outcome,
            steps=steps,
        )