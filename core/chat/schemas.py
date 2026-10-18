from enum import Enum
from typing import Any
from uuid import UUID

from pydantic import BaseModel, Field


class ChatMode(str, Enum):
    SEARCH = "search"
    HELP = "help"


class ChatContext(BaseModel):
    lead_id: UUID | str | None = None
    segment: str | None = None
    score: int | None = None
    page: str | None = None
    company_name: str | None = None


class ChatMessageRequest(BaseModel):
    query: str = Field(min_length=1, max_length=500)
    mode: ChatMode = ChatMode.SEARCH
    user_role: str = Field(min_length=1, max_length=32)
    session_id: UUID | None = None
    context: ChatContext = Field(default_factory=ChatContext)


class ChatSource(BaseModel):
    doc_id: str
    section: str
    score: float


class QuickAction(BaseModel):
    id: str
    label: str
    action_type: str


class ChatMessageResponse(BaseModel):
    session_id: UUID
    interaction_id: UUID
    answer: str
    sources: list[ChatSource]
    cache_hit: bool
    fallback_used: bool
    suggested_followups: list[str] = Field(default_factory=list)
    quick_actions: list[QuickAction] = Field(default_factory=list)
    escalation_used: bool = False


class ChatSuggestionsRequest(BaseModel):
    mode: ChatMode = ChatMode.SEARCH
    user_role: str = "rop"
    context: ChatContext = Field(default_factory=ChatContext)


class ChatSuggestionsResponse(BaseModel):
    suggestions: list[str]


class ChatFeedbackRequest(BaseModel):
    interaction_id: UUID
    feedback: str = Field(pattern="^(positive|negative)$")
    reason: str | None = None


class ChatClearSessionRequest(BaseModel):
    session_id: UUID
