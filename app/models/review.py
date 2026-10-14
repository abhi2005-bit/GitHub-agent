from __future__ import annotations

from enum import Enum

from pydantic import BaseModel, ConfigDict, Field, model_validator


class ReviewSeverity(str, Enum):
    CRITICAL = "Critical"
    HIGH = "High"
    MEDIUM = "Medium"
    LOW = "Low"


class ReviewCategory(str, Enum):
    BUG = "Bug"
    SECURITY = "Security"
    RELIABILITY = "Reliability"
    MAINTAINABILITY = "Maintainability"


class FindingStatus(str, Enum):
    CONFIRMED = "confirmed"
    PLAUSIBLE = "plausible"
    SUGGESTION = "suggestion"


class ReviewFinding(BaseModel):
    model_config = ConfigDict(extra="forbid")

    severity: ReviewSeverity
    category: ReviewCategory
    status: FindingStatus
    file_path: str = Field(min_length=1)
    line_start: int | None = Field(default=None, ge=1)
    line_end: int | None = Field(default=None, ge=1)
    evidence: str = Field(min_length=1)
    explanation: str = Field(min_length=1)
    impact: str = Field(min_length=1)
    remediation: str = Field(min_length=1)
    confidence: float = Field(ge=0, le=1)

    @model_validator(mode="after")
    def valid_line_range(self) -> "ReviewFinding":
        if self.line_end is not None and self.line_start is None:
            raise ValueError("line_end requires line_start.")
        if (
            self.line_start is not None
            and self.line_end is not None
            and self.line_end < self.line_start
        ):
            raise ValueError("line_end must be at or after line_start.")
        return self


class ReviewAnalysis(BaseModel):
    model_config = ConfigDict(extra="forbid")

    summary: str = Field(min_length=1)
    findings: list[ReviewFinding] = Field(default_factory=list)
    positive_observations: list[str] = Field(default_factory=list)
    limitations: list[str] = Field(default_factory=list)
