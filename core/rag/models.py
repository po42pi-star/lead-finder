from datetime import date
from enum import Enum
from typing import Any

from pydantic import BaseModel, Field, field_validator


class DocumentCategory(str, Enum):
    PRODUCT = "product"
    SALES = "sales"
    SEGMENTS = "segments"
    COMPANY = "company"
    SYSTEM = "system"


class AudienceRole(str, Enum):
    MANAGER = "manager"
    ROP = "rop"
    ANALYST = "analyst"
    CLIENT = "client"
    DESIGNER = "designer"
    INSPECTOR = "inspector"
    ADMIN = "admin"


class Priority(str, Enum):
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"


class IntentType(str, Enum):
    SEARCH = "search"
    HELP = "help"
    TECHNICAL = "technical"


class UserRole(str, Enum):
    MANAGER = "manager"
    ROP = "rop"
    ANALYST = "analyst"
    CLIENT = "client"
    DESIGNER = "designer"
    INSPECTOR = "inspector"
    ADMIN = "admin"


class DocumentMetadata(BaseModel):
    doc_id: str
    category: DocumentCategory
    audience: list[AudienceRole]
    tags: list[str] = Field(default_factory=list)
    version: str = "1.0"
    last_updated: date | None = None
    related_docs: list[str] = Field(default_factory=list)
    priority: Priority = Priority.MEDIUM
    extra: dict[str, Any] = Field(default_factory=dict)

    @field_validator("audience", mode="before")
    @classmethod
    def normalize_audience(cls, value: Any) -> list[Any]:
        if isinstance(value, str):
            return [item.strip() for item in value.split(",") if item.strip()]
        return value


class ChunkMetadata(DocumentMetadata):
    chunk_id: str
    section_title: str
    char_start: int
    char_end: int
    source_file: str
    is_table: bool = False
    text: str = ""


class IntentResult(BaseModel):
    category: DocumentCategory | None = None
    audience: list[AudienceRole] = Field(default_factory=list)
    intent: IntentType = IntentType.SEARCH


class RetrievedChunk(BaseModel):
    chunk_id: str
    doc_id: str
    section_title: str
    text: str
    score: float
    priority: Priority
    category: DocumentCategory
    is_table: bool = False


class IngestRequest(BaseModel):
    path: str = Field(default="", max_length=5000)
    force_rebuild: bool = False


class IngestResponse(BaseModel):
    status: str
    message: str
    files_queued: int = 0


class SearchRequest(BaseModel):
    query: str = Field(min_length=1, max_length=5000)
    user_role: UserRole
    category_override: DocumentCategory | None = None


class SourceItem(BaseModel):
    doc_id: str
    section: str
    score: float


class SearchResponse(BaseModel):
    answer: str
    sources: list[SourceItem]
    cache_hit: bool


class CollectionStats(BaseModel):
    name: str
    chunk_count: int
    categories: dict[str, int]


class CollectionsResponse(BaseModel):
    collections: list[CollectionStats]
