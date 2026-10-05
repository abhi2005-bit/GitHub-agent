from __future__ import annotations

from pydantic import BaseModel, Field

from app.models.tool import ToolResult


class StepExecutionResult(BaseModel):
    """Represents the result of executing a single step in an agent plan."""

    step_id: str = Field(
        max_length=100,
        min_length=1,
    )

    success: bool = True

    tool_result: ToolResult | None = None

    error: str | None = None


class ExecutionResult(BaseModel):
    """Represents the result of executing an entire agent plan."""

    success: bool = True

    step_results: list[StepExecutionResult]

    error: str | None = None