from __future__ import annotations
from typing import Any
from enum import Enum

from pydantic import BaseModel, Field


class ActionType(str, Enum):
    """
    Defines the broad category of an agent action.
    """

    OBSERVE = "observe"
    ANALYZE = "analyze"
    ACT = "act"


class AgentStep(BaseModel):
    id: str = Field(
        min_length=1,
        max_length=100,
    )

    action: ActionType

    description: str = Field(
        min_length=1,
        max_length=500,
    )

    tool_name: str | None = None

    tool_input:dict[str, Any]|None= None

    requires_approval: bool = False
    


class AgentPlan(BaseModel):
    """
    Represents the complete plan generated for an agent goal.
    """

    goal: str = Field(
        min_length=1,
        max_length=1000,
    )

    steps: list[AgentStep] = Field(
        min_length=1,
    )