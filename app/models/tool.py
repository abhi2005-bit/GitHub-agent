from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field


class ToolDefinition(BaseModel):
    name: str = Field(
        min_length=1,
        max_length=100,
    )

    description: str = Field(
        min_length=1,
        max_length=500,
    )

    requires_approval: bool = False


class ToolResult(BaseModel):
    success: bool = True
    data: Any | None = None
    error: str | None = None