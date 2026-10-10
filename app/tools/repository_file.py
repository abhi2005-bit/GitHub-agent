from __future__ import annotations

from typing import Any

from app.core.project_context import ProjectContext
from app.integrations.github_client import GitHubClient
from app.models.project import ProjectSource
from app.models.tool import ToolResult


class ReadRepositoryFileTool:
    """
    Reads a text file from a registered GitHub repository.
    """

    name = "read_repository_file"

    description = (
        "Reads the contents of a text file from a registered GitHub "
        "project using its project ID and repository-relative file path."
    )

    requires_approval = False

    def __init__(
        self,
        project_context: ProjectContext,
        github_client: GitHubClient,
    ) -> None:
        self.project_context = project_context
        self.github_client = github_client

    async def execute(self, **kwargs: Any) -> ToolResult:
        """
        Retrieve the requested file and return its contents.
        """

        # 1. Validate the project ID.
        raw_project_id = kwargs.get("project_id")

        if raw_project_id is None:
            return ToolResult(
                success=False,
                data=None,
                error="project_id is required.",
            )

        try:
            if isinstance(raw_project_id, bool):
                raise ValueError

            project_id = int(raw_project_id)

            if project_id <= 0:
                raise ValueError

        except (TypeError, ValueError):
            return ToolResult(
                success=False,
                data=None,
                error="project_id must be a positive integer.",
            )

        # 2. Validate the file path.
        raw_path = kwargs.get("path")

        if not isinstance(raw_path, str) or not raw_path.strip():
            return ToolResult(
                success=False,
                data=None,
                error="A non-empty file path is required.",
            )

        path = raw_path.strip()

        # 3. Resolve the registered project.
        try:
            project = self.project_context.get_project(project_id)

        except ValueError as exc:
            return ToolResult(
                success=False,
                data=None,
                error=str(exc),
            )

        # 4. Ensure this is a properly configured GitHub project.
        if project.source != ProjectSource.GITHUB:
            return ToolResult(
                success=False,
                data=None,
                error="File reading is currently supported for GitHub projects only.",
            )

        if not project.owner or not project.repository:
            return ToolResult(
                success=False,
                data=None,
                error=(
                    "The registered GitHub project must have "
                    "an owner and repository name."
                ),
            )

        # 5. Fetch the file from GitHub.
        try:
            content = await self.github_client.get_file_contents(
                owner=project.owner,
                repository=project.repository,
                path=path,
                branch=project.branch,
            )

        except (RuntimeError, ValueError) as exc:
            return ToolResult(
                success=False,
                data=None,
                error=str(exc),
            )

        # 6. Return the actual file contents.
        return ToolResult(
            success=True,
            data={
                "project_id": project.id,
                "repository": f"{project.owner}/{project.repository}",
                "branch": project.branch,
                "path": path,
                "content": content,
            },
            error=None,
        )