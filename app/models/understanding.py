from __future__ import annotations

from enum import Enum

from pydantic import BaseModel, Field


class UnderstandingIntent(str, Enum):
    """
    Supported intents that DevPilot can currently understand.
    """

    INSPECT_PROJECT = "inspect_project"
    INVESTIGATE_HEALTH = "investigate_health"
    MANAGE_ISSUE = "manage_issue"
    INVESTIGATE_CI = "investigate_ci"
    UNKNOWN = "unknown"


class Understanding(BaseModel):
    """
    Structured representation of what the user wants
    the agent to accomplish.
    """

    intent: UnderstandingIntent
    project_id: int | None = None
    entities: dict[str, str] = Field(default_factory=dict)
    constraints: dict[str, str] = Field(default_factory=dict)
    desired_outcome: str