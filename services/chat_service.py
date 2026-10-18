import logging
import time
import uuid
from collections.abc import AsyncIterator
from datetime import datetime, timezone

from sqlalchemy.ext.asyncio import AsyncSession

from core.chat.modes import resolve_categories
from core.chat.quick_actions import build_quick_actions
from core.chat.schemas import (
    ChatContext,
    ChatFeedbackRequest,
    ChatMessageRequest,
    ChatMessageResponse,
    ChatMode,
    ChatSource,
    ChatSuggestionsResponse,
)
from core.chat.session_memory import SessionMemoryStore
from core.chat.suggestions import build_suggestions
from core.config.settings import Settings
from core.db.models import ChatInteractionORM, ChatSessionORM, RagFeedbackORM
from core.dependencies import get_retrieval_pipeline
from core.rag.models import UserRole

logger = logging.getLogger(__name__)

FALLBACK_MESSAGE = """К сожалению, я не нашёл точного ответа в базе. Попробуйте:
1. Перефразировать вопрос короче
2. Выбрать одну из подсказок ниже
3. Обратиться к РОПу для сложных вопросов"""


class ChatService:
    def __init__(self, settings: Settings) -> None:
        self._settings = settings
        self._memory = SessionMemoryStore(settings.chat_session_ttl_sec)
        self._pipeline = get_retrieval_pipeline()

    def get_suggestions(
        self,
        mode: ChatMode,
        user_role: str,
        context: ChatContext,
    ) -> ChatSuggestionsResponse:
        return ChatSuggestionsResponse(
            suggestions=build_suggestions(mode, user_role, context),
        )

    def clear_session(self, session_id: uuid.UUID) -> None:
        self._memory.clear(session_id)

    async def send_message(
        self,
        db: AsyncSession,
        request: ChatMessageRequest,
    ) -> ChatMessageResponse:
        started = time.perf_counter()
        answer, meta = await self._process_message(request)
        meta["latency_ms"] = int((time.perf_counter() - started) * 1000)
        interaction = await self._persist_interaction(db, request, answer, meta)
        await db.commit()
        return self._build_response(request, answer, meta, interaction.id)

    async def stream_message(
        self,
        db: AsyncSession,
        request: ChatMessageRequest,
    ) -> AsyncIterator[tuple[str, ChatMessageResponse | None]]:
        started = time.perf_counter()
        enriched_query, meta = self._prepare_request(request)
        chunks, cache_hit, retrieval_meta = await self._retrieve(
            enriched_query, request, meta["use_cache"]
        )
        meta.update(retrieval_meta)
        meta["cache_hit"] = cache_hit
        meta["chunks"] = chunks
        max_score = max((c.score for c in chunks), default=0.0)
        meta["max_score"] = max_score

        tokens: list[str] = []
        if self._should_fallback(chunks, max_score):
            meta["fallback_used"] = True
            meta["escalation_used"] = True
            tokens = [FALLBACK_MESSAGE]
            yield FALLBACK_MESSAGE, None
        else:
            context = self._pipeline._format_context(chunks)
            stream = await self._pipeline.generate_answer(
                enriched_query,
                context,
                system_prompt=self._system_prompt(request),
                stream=True,
            )
            async for token in stream:
                tokens.append(token)
                yield token, None
            meta["fallback_used"] = False
            meta["escalation_used"] = False

        answer = "".join(tokens)
        meta["latency_ms"] = int((time.perf_counter() - started) * 1000)
        interaction = await self._persist_interaction(db, request, answer, meta)
        await db.commit()
        response = self._build_response(request, answer, meta, interaction.id)
        yield "", response

    async def submit_feedback(
        self,
        db: AsyncSession,
        request: ChatFeedbackRequest,
    ) -> bool:
        interaction = await db.get(ChatInteractionORM, request.interaction_id)
        if not interaction:
            return False
        interaction.feedback = request.feedback
        interaction.feedback_reason = request.reason
        db.add(
            RagFeedbackORM(
                id=uuid.uuid4(),
                interaction_id=interaction.id,
                user_role=interaction.user_role,
                query=interaction.query,
                feedback=request.feedback,
                reason=request.reason,
            )
        )
        await db.commit()
        return True

    async def _process_message(self, request: ChatMessageRequest) -> tuple[str, dict]:
        started = time.perf_counter()
        enriched_query, meta = self._prepare_request(request)
        chunks, cache_hit, retrieval_meta = await self._retrieve(
            enriched_query, request, meta["use_cache"]
        )
        meta.update(retrieval_meta)
        meta["cache_hit"] = cache_hit
        meta["chunks"] = chunks

        max_score = max((c.score for c in chunks), default=0.0)
        meta["max_score"] = max_score

        if self._should_fallback(chunks, max_score):
            meta["fallback_used"] = True
            meta["escalation_used"] = True
            return FALLBACK_MESSAGE, meta

        context = self._pipeline._format_context(chunks)
        answer = await self._pipeline.generate_answer(
            enriched_query,
            context,
            system_prompt=self._system_prompt(request),
        )
        meta["fallback_used"] = False
        meta["escalation_used"] = False
        meta["latency_ms"] = int((time.perf_counter() - started) * 1000)
        return answer if isinstance(answer, str) else str(answer), meta

    def _prepare_request(self, request: ChatMessageRequest) -> tuple[str, dict]:
        ctx_dict = request.context.model_dump(exclude_none=True)
        state = None
        if request.session_id:
            state = self._memory.get(request.session_id)
        if not state:
            state = self._memory.create(
                user_role=request.user_role,
                mode=request.mode.value,
                context=ctx_dict,
                session_id=request.session_id,
            )
        else:
            state = self._memory.touch(state, query=request.query, context=ctx_dict)

        enriched = self._enrich_query(request.query, state, request.context)
        use_cache = request.context.lead_id is None
        return enriched, {
            "session_id": state.session_id,
            "use_cache": use_cache,
        }

    def _enrich_query(
        self,
        query: str,
        state,
        context: ChatContext,
    ) -> str:
        parts = [query]
        if context.company_name:
            parts.append(f"Компания: {context.company_name}")
        elif state.last_lead_id and context.lead_id is None:
            parts.append(f"Контекст лида: lead_id={state.last_lead_id}")
        if context.segment or state.last_segment:
            parts.append(f"Сегмент: {context.segment or state.last_segment}")
        if context.score is not None:
            parts.append(f"Скоринг: {context.score}")
        if state.recent_queries:
            parts.append(f"Предыдущие вопросы: {'; '.join(state.recent_queries[1:3])}")
        return "\n".join(parts)

    async def _retrieve(
        self,
        query: str,
        request: ChatMessageRequest,
        use_cache: bool,
    ):
        try:
            role = UserRole(request.user_role)
        except ValueError:
            role = UserRole.MANAGER
        categories = resolve_categories(request.mode, request.query, request.context)
        return await self._pipeline.retrieve_for_chat(
            query,
            role,
            categories,
            use_cache=use_cache,
        )

    def _should_fallback(self, chunks, max_score: float) -> bool:
        if not chunks:
            return True
        return max_score < self._settings.chat_fallback_score_threshold

    def _system_prompt(self, request: ChatMessageRequest) -> str:
        role_hint = {
            "rop": (
                "Ты общаешься с РОПом. Давай детали, метрики, аргументы с цифрами. "
                "Можешь предлагать стратегии и ссылаться на методологии (SPIN, MEDDIC, BANT)."
            ),
            "manager": (
                "Ты общаешься с менеджером по продажам. Отвечай кратко, по делу, "
                "без лишней теории. Давай готовые фразы для разговора с клиентом."
            ),
            "admin": (
                "Ты общаешься с администратором системы. Можешь давать технические детали, "
                "ссылаться на конфигурацию и интеграции."
            ),
        }.get(request.user_role, "Отвечай кратко и по делу.")

        mode_hint = (
            "Режим: справка по системе. Отвечай только инструкциями по интерфейсу. "
            "Не предлагай звонить клиенту, не давай продажных советов."
            if request.mode == ChatMode.HELP
            else (
                "Режим: поиск и аналитика лидов. Помогай с квалификацией, подготовкой к звонку, "
                "отработкой возражений. Используй сегментную специфику."
            )
        )

        return (
            "Ты — ассистент компании НЕВАТОМ. Твоя единственная база знаний — переданный ниже контекст. "
            "Если в контексте нет ответа — скажи об этом прямо, не выдумывай.\n\n"
            "Правила форматирования:\n"
            "- Используй Markdown: заголовки, списки, жирный текст.\n"
            "- Если отвечаешь на вопрос про продукт — укажи модельный ряд и ключевые параметры.\n"
            "- Если отвечаешь на вопрос про продажи — дай готовую фразу для разговора.\n\n"
            "- Не добавляй блок «Источники» и не упоминай doc_id — интерфейс показывает источники сам.\n\n"
            f"{role_hint}\n\n{mode_hint}"
        )

    async def _persist_interaction(
        self,
        db: AsyncSession,
        request: ChatMessageRequest,
        answer: str,
        meta: dict,
    ) -> ChatInteractionORM:
        session_id = meta.get("session_id") or request.session_id or uuid.uuid4()
        lead_id = _as_uuid(request.context.lead_id)
        db_session = await db.get(ChatSessionORM, session_id)
        if not db_session:
            db_session = ChatSessionORM(
                id=session_id,
                user_role=request.user_role,
                mode=request.mode.value,
                context=request.context.model_dump(mode="json", exclude_none=True),
                last_lead_id=lead_id,
                last_segment=request.context.segment,
                recent_queries=[request.query],
            )
            db.add(db_session)

        chunks = meta.get("chunks", [])
        sources = [
            {"doc_id": c.doc_id, "section": c.section_title, "score": c.score}
            for c in chunks
        ]
        interaction = ChatInteractionORM(
            id=uuid.uuid4(),
            session_id=session_id,
            user_role=request.user_role,
            mode=request.mode.value,
            lead_id=lead_id,
            page=request.context.page,
            query=request.query,
            answer=answer,
            retrieved_docs=[c.doc_id for c in chunks],
            sources=sources,
            answer_length=len(answer),
            cache_hit=meta.get("cache_hit", False),
            fallback_used=meta.get("fallback_used", False),
            retrieval_score_max=meta.get("max_score"),
            escalation_used=meta.get("escalation_used", False),
            latency_ms=meta.get("latency_ms", 0),
        )
        db.add(interaction)
        return interaction

    def _build_response(
        self,
        request: ChatMessageRequest,
        answer: str,
        meta: dict,
        interaction_id: uuid.UUID,
    ) -> ChatMessageResponse:
        chunks = meta.get("chunks", [])
        sources = [
            ChatSource(doc_id=c.doc_id, section=c.section_title, score=c.score)
            for c in chunks
        ]
        query = request.query.lower()
        has_questions = "вопрос" in query or "задать" in query
        followups = build_suggestions(request.mode, request.user_role, request.context)[:3]
        return ChatMessageResponse(
            session_id=meta.get("session_id") or request.session_id or uuid.uuid4(),
            interaction_id=interaction_id,
            answer=answer,
            sources=sources,
            cache_hit=meta.get("cache_hit", False),
            fallback_used=meta.get("fallback_used", False),
            suggested_followups=followups,
            quick_actions=build_quick_actions(
                request.mode,
                request.user_role,
                request.context,
                has_questions=has_questions,
            ),
            escalation_used=meta.get("escalation_used", False),
        )


def _as_uuid(value: uuid.UUID | str | None) -> uuid.UUID | None:
    """lead_id приходит с фронтенда строкой; колонка UUID в SQLite принимает только UUID."""
    if value is None or isinstance(value, uuid.UUID):
        return value
    try:
        return uuid.UUID(str(value))
    except ValueError:
        return None
