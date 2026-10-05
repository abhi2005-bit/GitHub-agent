from __future__ import annotations

from app.tools.base import AgentTool


class ToolRegistry:
    """
    Stores and manages the tools available to the agent.
    """

    def __init__(self) -> None:
        self._tools: dict[str, AgentTool] = {}

    def register(self, tool: AgentTool) -> None:
        """
        Add a tool to the registry.
        """

        if tool.name in self._tools:
            raise ValueError(
                f"Tool '{tool.name}' is already registered."
            )

        self._tools[tool.name] = tool

    def get(self, name: str) -> AgentTool:
        """
        Retrieve a tool by its name.
        """

        if name not in self._tools:
            raise KeyError(
                f"Tool '{name}' is not registered."
            )

        return self._tools[name]

    def has(self, name: str) -> bool:
        """
        Check whether a tool exists in the registry.
        """

        return name in self._tools

    def list_tools(self) -> list[AgentTool]:
        """
        Return all registered tools.
        """

        return list(self._tools.values())
    