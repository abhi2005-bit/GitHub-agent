import pytest

from app.tools.engineering import ProjectContextTool


@pytest.mark.asyncio
async def test_get_project_context_success():
    tool = ProjectContextTool()

    result = await tool.execute(project_id=123)

    assert result.success is True
    assert result.error is None
    assert result.data is not None


@pytest.mark.asyncio
async def test_get_project_context_requires_project_id():
    tool = ProjectContextTool()

    result = await tool.execute()

    assert result.success is False
    assert result.error == "project_id is required."


@pytest.mark.asyncio
async def test_get_project_context_rejects_invalid_project_id():
    tool = ProjectContextTool()

    result = await tool.execute(project_id="abc")

    assert result.success is False
    assert result.error == "project_id must be a valid integer."


@pytest.mark.asyncio
async def test_get_project_context_contains_expected_sections():
    tool = ProjectContextTool()

    result = await tool.execute(project_id=123)

    assert result.success is True

    data = result.data

    assert "project" in data
    assert "health" in data
    assert "issues" in data
    assert "cicd" in data
    assert "github" in data
    assert "signals" in data

    assert data["project"]["id"] == 123
    assert data["project"]["name"] == "Demo Engineering Project"

    assert "open" in data["issues"]
    assert "failed_runs" in data["cicd"]
    assert "success_rate" in data["cicd"]