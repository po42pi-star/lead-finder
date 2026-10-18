from datetime import datetime
from enum import Enum
from typing import Any
from uuid import UUID

from pydantic import BaseModel, Field


class ConfidenceLevel(str, Enum):
    OK = "ok"
    WARNING = "warning"
    ERROR = "error"


class AnalyticsItem(BaseModel):
    text: str
    confidence: ConfidenceLevel = ConfidenceLevel.OK
    source: str | None = None


class AnalyticsBlock(BaseModel):
    title: str
    items: list[AnalyticsItem] = Field(default_factory=list)
    summary: str | None = None


class RecommendedQuestion(BaseModel):
    question_id: UUID
    text: str
    source: str
    methodology_tag: str | None = None
    category: str | None = None
    used_in_call: datetime | None = None


class AnalyticsReport(BaseModel):
    report_id: UUID
    lead_id: UUID
    company_name: str
    segment: str
    score: int
    region: str | None = None
    mandatory: dict[str, AnalyticsBlock]
    optional: dict[str, Any]
    question_set_id: UUID | None = None
    questions: list[RecommendedQuestion] = Field(default_factory=list)
    created_at: datetime


class AnalyticsRunRequest(BaseModel):
    lead_ids: list[UUID] = Field(min_length=1, max_length=5)
    user_role: str = Field(min_length=1, max_length=32)


class AnalyticsRunResponse(BaseModel):
    reports: list[AnalyticsReport]


class MarkInWorkRequest(BaseModel):
    lead_ids: list[UUID] = Field(min_length=1)


class MarkQuestionUsedRequest(BaseModel):
    used: bool = True


class AnalyticsExportRequest(BaseModel):
    report_ids: list[UUID] = Field(min_length=1)
    format: str = Field(default="csv", pattern="^(csv|xlsx)$")
