import uuid
from datetime import datetime
from decimal import Decimal

from sqlalchemy import JSON, DateTime, ForeignKey, Integer, Numeric, String, Text, Uuid, func
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


class Base(DeclarativeBase):
    pass


class SearchSessionORM(Base):
    __tablename__ = "search_sessions"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    user_role: Mapped[str] = mapped_column(String(32), nullable=False)
    filters: Mapped[dict] = mapped_column(JSON, nullable=False)
    comment: Mapped[str | None] = mapped_column(Text)
    total_found: Mapped[int] = mapped_column(Integer, default=0)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    leads: Mapped[list["LeadORM"]] = relationship(back_populates="session")


class LeadORM(Base):
    __tablename__ = "leads"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    session_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("search_sessions.id", ondelete="CASCADE"), nullable=False
    )
    company_name: Mapped[str] = mapped_column(String(512), nullable=False)
    inn: Mapped[str | None] = mapped_column(String(12))
    ogrn: Mapped[str | None] = mapped_column(String(15))
    segment: Mapped[str] = mapped_column(String(64), nullable=False)
    region: Mapped[str | None] = mapped_column(String(256))
    source: Mapped[str] = mapped_column(String(64), nullable=False)
    score: Mapped[int] = mapped_column(Integer, nullable=False)
    score_breakdown: Mapped[list] = mapped_column(JSON, default=list)
    turnover_mln: Mapped[Decimal | None] = mapped_column(Numeric(14, 2))
    employees: Mapped[int | None] = mapped_column(Integer)
    website: Mapped[str | None] = mapped_column(String(512))
    contact_name: Mapped[str | None] = mapped_column(String(256))
    contact_phone: Mapped[str | None] = mapped_column(String(64))
    contact_email: Mapped[str | None] = mapped_column(String(256))
    okved_codes: Mapped[list] = mapped_column(JSON, default=list)
    raw_data: Mapped[dict] = mapped_column(JSON, default=dict)
    updated_at_source: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    status: Mapped[str] = mapped_column(String(32), default="new")
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    session: Mapped[SearchSessionORM] = relationship(back_populates="leads")
    analytics_reports: Mapped[list["AnalyticsReportORM"]] = relationship(back_populates="lead")


class AnalyticsReportORM(Base):
    __tablename__ = "analytics_reports"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    lead_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("leads.id", ondelete="CASCADE"), nullable=False
    )
    user_role: Mapped[str] = mapped_column(String(32), nullable=False)
    company_name: Mapped[str] = mapped_column(String(512), nullable=False)
    segment: Mapped[str] = mapped_column(String(64), nullable=False)
    score: Mapped[int] = mapped_column(Integer, nullable=False)
    region: Mapped[str | None] = mapped_column(String(256))
    report: Mapped[dict] = mapped_column(JSON, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    lead: Mapped[LeadORM] = relationship(back_populates="analytics_reports")
    question_sets: Mapped[list["QuestionSetORM"]] = relationship(back_populates="analytics_report")


class QuestionSetORM(Base):
    __tablename__ = "question_sets"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    lead_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("leads.id", ondelete="CASCADE"), nullable=False
    )
    analytics_report_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid, ForeignKey("analytics_reports.id", ondelete="SET NULL")
    )
    segment: Mapped[str] = mapped_column(String(64), nullable=False)
    questions: Mapped[list] = mapped_column(JSON, default=list)
    generated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    used_in_call: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    analytics_report: Mapped[AnalyticsReportORM | None] = relationship(back_populates="question_sets")
    question_logs: Mapped[list["QuestionLogORM"]] = relationship(back_populates="question_set")


class QuestionLogORM(Base):
    __tablename__ = "question_logs"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    question_set_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("question_sets.id", ondelete="CASCADE"), nullable=False
    )
    lead_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("leads.id", ondelete="CASCADE"), nullable=False
    )
    question_text: Mapped[str] = mapped_column(Text, nullable=False)
    methodology_tag: Mapped[str | None] = mapped_column(String(64))
    category: Mapped[str | None] = mapped_column(String(64))
    source: Mapped[str | None] = mapped_column(String(256))
    used_in_call: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    question_set: Mapped[QuestionSetORM] = relationship(back_populates="question_logs")


class ChatSessionORM(Base):
    __tablename__ = "chat_sessions"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    user_role: Mapped[str] = mapped_column(String(32), nullable=False)
    mode: Mapped[str] = mapped_column(String(16), nullable=False)
    context: Mapped[dict] = mapped_column(JSON, default=dict)
    last_lead_id: Mapped[uuid.UUID | None] = mapped_column(Uuid)
    last_segment: Mapped[str | None] = mapped_column(String(64))
    recent_queries: Mapped[list] = mapped_column(JSON, default=list)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    interactions: Mapped[list["ChatInteractionORM"]] = relationship(back_populates="session")


class ChatInteractionORM(Base):
    __tablename__ = "chat_interactions"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    session_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("chat_sessions.id", ondelete="CASCADE"), nullable=False
    )
    interaction_type: Mapped[str] = mapped_column(String(32), default="chatbot")
    user_role: Mapped[str] = mapped_column(String(32), nullable=False)
    mode: Mapped[str] = mapped_column(String(16), nullable=False)
    lead_id: Mapped[uuid.UUID | None] = mapped_column(Uuid)
    page: Mapped[str | None] = mapped_column(String(64))
    query: Mapped[str] = mapped_column(Text, nullable=False)
    answer: Mapped[str | None] = mapped_column(Text)
    retrieved_docs: Mapped[list] = mapped_column(JSON, default=list)
    sources: Mapped[list] = mapped_column(JSON, default=list)
    answer_length: Mapped[int] = mapped_column(Integer, default=0)
    cache_hit: Mapped[bool] = mapped_column(default=False)
    fallback_used: Mapped[bool] = mapped_column(default=False)
    retrieval_score_max: Mapped[float | None] = mapped_column()
    feedback: Mapped[str | None] = mapped_column(String(16))
    feedback_reason: Mapped[str | None] = mapped_column(String(128))
    quick_action_clicked: Mapped[str | None] = mapped_column(String(64))
    escalation_used: Mapped[bool] = mapped_column(default=False)
    latency_ms: Mapped[int] = mapped_column(Integer, default=0)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    session: Mapped[ChatSessionORM] = relationship(back_populates="interactions")


class RagFeedbackORM(Base):
    __tablename__ = "rag_feedback"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    interaction_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid, ForeignKey("chat_interactions.id", ondelete="SET NULL")
    )
    user_role: Mapped[str] = mapped_column(String(32), nullable=False)
    query: Mapped[str] = mapped_column(Text, nullable=False)
    feedback: Mapped[str] = mapped_column(String(16), nullable=False)
    reason: Mapped[str | None] = mapped_column(String(128))
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
