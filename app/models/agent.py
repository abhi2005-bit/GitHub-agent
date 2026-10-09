from __future__ import annotations

from datetime import datetime, timezone
from enum import Enum
from uuid import UUID, uuid4

from pydantic import BaseModel, Field


class AgentState(str, Enum):
    """
    Represents the current lifecycle state of an agent run.
    """

    IDLE = "idle"
    THINKING = "thinking"
    ACTING = "acting"
    COMPLETED = "completed"
    FAILED = "failed"


class AgentMessage(BaseModel):
    """
    Represents a single message exchanged during an agent run.
    """

    role: str = Field(
        description="Who produced the message: user, agent, tool, or system."
    )

    content: str = Field(
        min_length=1,
        description="Message content."
    )

    created_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc)
    )


class AgentRun(BaseModel):
    """
    Represents one complete execution of the agent.
    """

    id: UUID = Field(
        default_factory=uuid4
    )

    goal: str = Field(
        min_length=1,
        max_length=1000
    )
    project_id: int | None = None

    state: AgentState = AgentState.IDLE

    messages: list[AgentMessage] = Field(
        default_factory=list
    )

    iterations: int = 0

    created_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc)
    )

    updated_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc)
    )

    error: str | None = None