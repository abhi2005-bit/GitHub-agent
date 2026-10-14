from __future__ import annotations

from typing import Any

from app.core.project_context import ProjectContext
from app.integrations.github_client import GitHubClient
from app.models.project import ProjectSource
from app.models.tool import ToolResult


class _GitHubProjectTool:
    """Shared project resolution for read-only GitHub investigation tools."""

    requires_approval = False

    def __init__(self, project_context: ProjectContext, github_client: GitHubClient) -> None:
        self.project_context = project_context
        self.github_client = github_client

    def _project(self, raw_project_id: Any):
        if raw_project_id is None or isinstance(raw_project_id, bool):
            raise ValueError("project_id must be a valid positive integer.")
        try:
            project_id = int(raw_project_id)
        except (TypeError, ValueError) as exc:
            raise ValueError("project_id must be a valid positive integer.") from exc
        if project_id <= 0:
            raise ValueError("project_id must be a valid positive integer.")
        project = self.project_context.get_project(project_id)
        if project.source != ProjectSource.GITHUB:
            raise ValueError("This investigation is supported for GitHub projects only.")
        if not project.owner or not project.repository:
            raise ValueError("The registered GitHub project needs an owner and repository name.")
        return project

    @staticmethod
    def _failure(exc: Exception) -> ToolResult:
        return ToolResult(success=False, data=None, error=str(exc))


class RepositoryHealthTool(_GitHubProjectTool):
    name = "get_repository_health"
    description = "Reads repository status signals from GitHub metadata."

    async def execute(self, **kwargs: Any) -> ToolResult:
        try:
            project = self._project(kwargs.get("project_id"))
            health = await self.github_client.get_repository_health(
                project.owner, project.repository
            )
        except (ValueError, RuntimeError) as exc:
            return self._failure(exc)
        return ToolResult(success=True, data={
            "repository": f"{project.owner}/{project.repository}",
            "configured_branch": project.branch,
            "signals": health,
            "scope": "GitHub repository metadata; no source analysis or CI checks were run.",
        })


class OpenIssueSearchTool(_GitHubProjectTool):
    name = "search_open_issues"
    description = "Searches open GitHub issues without modifying repository data."

    async def execute(self, **kwargs: Any) -> ToolResult:
        try:
            project = self._project(kwargs.get("project_id"))
            query = kwargs.get("query")
            if query is not None and not isinstance(query, str):
                raise ValueError("Issue query must be text.")
            issues = await self.github_client.search_open_issues(
                project.owner, project.repository, query=query
            )
        except (ValueError, RuntimeError) as exc:
            return self._failure(exc)
        return ToolResult(success=True, data={
            "repository": f"{project.owner}/{project.repository}",
            "query": query,
            "returned_count": len(issues),
            "issues": issues,
            "read_only": True,
        })


class CIInvestigationTool(_GitHubProjectTool):
    name = "investigate_ci"
    description = "Lists recent GitHub Actions runs on the registered branch."

    async def execute(self, **kwargs: Any) -> ToolResult:
        try:
            project = self._project(kwargs.get("project_id"))
            runs = await self.github_client.list_workflow_runs(
                project.owner, project.repository, project.branch
            )
        except (ValueError, RuntimeError) as exc:
            return self._failure(exc)
        return ToolResult(success=True, data={
            "repository": f"{project.owner}/{project.repository}",
            "branch": project.branch,
            "count": len(runs),
            "workflow_runs": runs,
            "read_only": True,
        })
