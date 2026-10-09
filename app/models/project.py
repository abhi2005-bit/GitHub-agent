from __future__ import annotations

from enum import Enum

from pydantic import BaseModel, Field


class ProjectSource(str, Enum):
    GITHUB = "github"
    LOCAL = "local"


class Project(BaseModel):
    """
    Represents a project connected to DevPilot.
    """

    id: int
    name: str = Field(min_length=1, max_length=200)

    source: ProjectSource

    repository: str | None = None
    owner: str | None = None
    branch: str = "main"