from __future__ import annotations

from enum import Enum

from pydantic import BaseModel, Field


class UnderstandingIntent(str, Enum):
    INSPECT_PROJECT = "inspect_project"
    INVESTIGATE_HEALTH = "investigate_health"
    MANAGE_ISSUE = "manage_issue"
    INVESTIGATE_CI = "investigate_ci"
    READ_REPOSITORY_FILE = "read_repository_file"
    UNKNOWN = "unknown"


class Understanding(BaseModel):
    """
    Structured representation of a user's engineering request.
    """

    intent: UnderstandingIntent
    project_id: int | None = None
    entities: dict[str, str] = Field(default_factory=dict)
    constraints: dict[str, str] = Field(default_factory=dict)
    desired_outcome: str