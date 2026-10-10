from __future__ import annotations

from typing import Any

from app.core.project_context import ProjectContext
from app.integrations.github_client import GitHubClient
from app.models.project import ProjectSource
from app.models.tool import ToolResult


class ProjectContextTool:
    """
    Retrieves project metadata and, for GitHub projects,
    live repository information and file listings.
    """

    name = "get_project_context"

    description = (
        "Retrieves registered project metadata, live GitHub repository "
        "information, and repository file paths."
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
        Retrieve project metadata and GitHub repository information.
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
                error="project_id must be a valid positive integer.",
            )

        # 2. Retrieve the registered project.
        try:
            project = self.project_context.get_project(project_id)

        except ValueError as exc:
            return ToolResult(
                success=False,
                data=None,
                error=str(exc),
            )

        # 3. Prepare the locally registered project metadata.
        context: dict[str, Any] = {
            "project": {
                "id": project.id,
                "name": project.name,
                "source": project.source.value,
                "repository": project.repository,
                "owner": project.owner,
                "branch": project.branch,
            }
        }

        # 4. Fetch live data for GitHub projects.
        if project.source == ProjectSource.GITHUB:
            if not project.owner or not project.repository:
                return ToolResult(
                    success=False,
                    data=None,
                    error=(
                        "GitHub project must have an owner "
                        "and repository name."
                    ),
                )

            try:
                # Fetch actual repository metadata.
                github_data = await self.github_client.get_repository(
                    owner=project.owner,
                    repository=project.repository,
                )

                # Fetch the file tree for the registered branch.
                files = await self.github_client.list_repository_files(
                    owner=project.owner,
                    repository=project.repository,
                    branch=project.branch,
                )

            except RuntimeError as exc:
                return ToolResult(
                    success=False,
                    data=None,
                    error=str(exc),
                )

            # 5. Keep the GitHub metadata relevant to DevPilot.
            github_fields = (
                "full_name",
                "description",
                "private",
                "html_url",
                "default_branch",
                "stargazers_count",
            )

            context["github"] = {
                field: github_data[field]
                for field in github_fields
                if field in github_data
            }

            # 6. Include file paths without unnecessary API fields.
            context["repository_tree"] = {
                "count": len(files),
                "entries": [
                    {
                        "path": item["path"],
                        "type": item["type"],
                    }
                    for item in files
                ],
            }

        # 7. Return the combined result.
        return ToolResult(
            success=True,
            data=context,
            error=None,
        )