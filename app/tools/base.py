from __future__ import annotations

from typing import Any, Protocol

from app.models.tool import ToolResult


class AgentTool(Protocol):
    """
    Contract that every agent tool must follow.
    """

    name: str
    description: str
    requires_approval: bool

    async def execute(self, **kwargs: Any) -> ToolResult:
        """
        Execute the tool and return a structured result.
        """
        ...