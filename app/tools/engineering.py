from __future__ import annotations

from typing import Any

from app.models.tool import ToolResult


class ProjectContextTool:
    """
    Provides the current engineering context for a project.
    """

    name = "get_project_context"

    description = (
        "Retrieves the current engineering context for a project, "
        "including health, issues, CI/CD, GitHub activity, and signals."
    )

    requires_approval = False

    async def execute(self, **kwargs: Any) -> ToolResult:
        project_id = kwargs.get("project_id")

        if project_id is None:
            return ToolResult(
                success=False,
                data=None,
                error="project_id is required.",
            )

        try:
            project_id = int(project_id)
        except (TypeError, ValueError):
            return ToolResult(
                success=False,
                data=None,
                error="project_id must be a valid integer.",
            )

        context = {
            "project": {
                "id": project_id,
                "name": "Demo Engineering Project",
            },
            "health": {
                "score": 68,
                "status": "warning",
            },
            "issues": {
                "total": 18,
                "open": 11,
                "critical": 2,
                "stale": 3,
            },
            "cicd": {
                "total_runs": 20,
                "failed_runs": 6,
                "success_rate": 70.0,
            },
            "github": {
                "commits": 32,
                "open_pull_requests": 4,
            },
            "signals": [
                {
                    "type": "risk",
                    "title": "CI reliability declining",
                    "severity": "high",
                },
                {
                    "type": "warning",
                    "title": "Several issues are stale",
                    "severity": "medium",
                },
            ],
        }

        return ToolResult(
            success=True,
            data=context,
            error=None,
        )


project_context_tool = ProjectContextTool()