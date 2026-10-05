import pytest

from app.tools.engineering import ProjectContextTool
from app.tools.registry import ToolRegistry


def test_register_and_get_tool():
    registry = ToolRegistry()
    tool = ProjectContextTool()

    registry.register(tool)

    assert registry.get("get_project_context") is tool


def test_has_tool():
    registry = ToolRegistry()
    registry.register(ProjectContextTool())

    assert registry.has("get_project_context") is True
    assert registry.has("unknown_tool") is False


def test_list_tools():
    registry = ToolRegistry()
    registry.register(ProjectContextTool())

    tools = registry.list_tools()

    assert len(tools) == 1
    assert tools[0].name == "get_project_context"


def test_duplicate_tool_registration_fails():
    registry = ToolRegistry()

    registry.register(ProjectContextTool())

    with pytest.raises(ValueError):
        registry.register(ProjectContextTool())


def test_get_missing_tool_fails():
    registry = ToolRegistry()

    with pytest.raises(KeyError):
        registry.get("unknown_tool")