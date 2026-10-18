from enum import Enum
from typing import Any
from uuid import UUID

from pydantic import BaseModel, Field


class SortOption(str, Enum):
    SCORE_DESC = "score_desc"
    NAME_ASC = "name_asc"
    REGION_ASC = "region_asc"
    UPDATED_DESC = "updated_desc"


class GroupOption(str, Enum):
    NONE = "none"
    SEGMENT = "segment"
    REGION = "region"


class ExtraFields(BaseModel):
    geography: str = ""
    keywords: str = ""
    adjacent_industries: str = ""
    exclude_keywords: str = ""
    min_turnover_mln: str = ""
    activity_period: str = ""
    project_types: str = ""
    technical_requirements: str = ""
    contact_channels: str = ""
    search_comment: str = ""


class SearchFilters(BaseModel):
    checkboxes: list[str] = Field(default_factory=list)
    extra: ExtraFields = Field(default_factory=ExtraFields)


class SearchRunRequest(BaseModel):
    user_role: str = Field(min_length=1, max_length=32)
    filters: SearchFilters
    sort_by: SortOption = SortOption.SCORE_DESC
    group_by: GroupOption = GroupOption.NONE


class SearchMoreRequest(BaseModel):
    session_id: UUID
    exclude_lead_ids: list[UUID] = Field(default_factory=list)
    sort_by: SortOption = SortOption.SCORE_DESC
    group_by: GroupOption = GroupOption.NONE


class ScoreBreakdownItem(BaseModel):
    delta: int
    reason: str
    matched: bool = True


class LeadCard(BaseModel):
    lead_id: UUID
    company_name: str
    inn: str | None = None
    segment: str
    region: str | None = None
    score: int
    score_breakdown: list[ScoreBreakdownItem]
    turnover_mln: float | None = None
    employees: int | None = None
    website: str | None = None
    contact_name: str | None = None
    contact_phone: str | None = None
    contact_email: str | None = None
    source: str
    updated_at: str | None = None


class LeadGroup(BaseModel):
    key: str
    title: str
    leads: list[LeadCard]


class SearchRunResponse(BaseModel):
    session_id: UUID
    leads: list[LeadCard]
    groups: list[LeadGroup] | None = None
    shown_count: int
    total_count: int
    has_more: bool


class FiltersMetaResponse(BaseModel):
    checkbox_groups: list[dict[str, Any]]
    extra_fields: list[dict[str, Any]]
    sort_options: list[dict[str, str]]
    group_options: list[dict[str, str]]


class ExportRequest(BaseModel):
    session_id: UUID
    lead_ids: list[UUID] | None = None
    format: str = Field(default="csv", pattern="^(csv|xlsx)$")
