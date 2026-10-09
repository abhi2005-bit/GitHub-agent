from __future__ import annotations

from typing import Any

from app.core.project_context import ProjectContext
from app.models.tool import ToolResult


class ProjectContextTool:
    """
    Retrieves metadata for a project registered with DevPilot.
    """

    name = "get_project_context"

    description = (
        "Retrieves registered project metadata, including its ID, name, "
        "source, repository, owner, and branch."
    )

    requires_approval = False

    def __init__(self, project_context: ProjectContext) -> None:
        self.project_context = project_context

    async def execute(self, **kwargs: Any) -> ToolResult:
        """
        Retrieve project metadata using the supplied project ID.
        """

        raw_project_id = kwargs.get("project_id")

        # Validate that a project ID was provided.
        if raw_project_id is None:
            return ToolResult(
                success=False,
                data=None,
                error="project_id is required.",
            )

        # Validate the project ID.
        try:
            if isinstance(raw_project_id, bool):
                raise ValueError

            project_id = int(raw_project_id)

        except (TypeError, ValueError):
            return ToolResult(
                success=False,
                data=None,
                error="project_id must be a valid integer.",
            )

        # Retrieve the registered project.
        try:
            project = self.project_context.get_project(project_id)

        except ValueError as exc:
            return ToolResult(
                success=False,
                data=None,
                error=str(exc),
            )

        # Build the context from actual project metadata.
        context = {
            "project": {
                "id": project.id,
                "name": project.name,
                "source": project.source.value,
                "repository": project.repository,
                "owner": project.owner,
                "branch": project.branch,
            }
        }

        return ToolResult(
            success=True,
            data=context,
            error=None,
        )