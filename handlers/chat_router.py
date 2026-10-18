import json
import logging
from functools import lru_cache

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession

from core.chat.schemas import (
    ChatClearSessionRequest,
    ChatFeedbackRequest,
    ChatMessageRequest,
    ChatMessageResponse,
    ChatMode,
    ChatContext,
    ChatSuggestionsResponse,
)
from core.config.settings import Settings, get_settings
from core.db.session import get_async_session
from services.chat_service import ChatService

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/chat", tags=["chat"])


@lru_cache
def get_chat_service() -> ChatService:
    return ChatService(get_settings())


@router.get("/suggestions", response_model=ChatSuggestionsResponse)
async def suggestions(
    mode: ChatMode = ChatMode.SEARCH,
    user_role: str = "rop",
    lead_id: str | None = None,
    segment: str | None = None,
    score: int | None = None,
    page: str | None = None,
    service: ChatService = Depends(get_chat_service),
) -> ChatSuggestionsResponse:
    from uuid import UUID

    context = ChatContext(
        lead_id=UUID(lead_id) if lead_id else None,
        segment=segment,
        score=score,
        page=page,
    )
    return service.get_suggestions(mode, user_role, context)


@router.post("/message", response_model=ChatMessageResponse)
async def send_message(
    request: ChatMessageRequest,
    db: AsyncSession = Depends(get_async_session),
    service: ChatService = Depends(get_chat_service),
) -> ChatMessageResponse:
    try:
        return await service.send_message(db, request)
    except Exception as exc:
        logger.exception("Chat message failed")
        raise HTTPException(status_code=503, detail="Chat unavailable") from exc


@router.post("/stream")
async def stream_message(
    request: ChatMessageRequest,
    db: AsyncSession = Depends(get_async_session),
    service: ChatService = Depends(get_chat_service),
    settings: Settings = Depends(get_settings),
):
    if not settings.chat_stream_enabled:
        raise HTTPException(status_code=400, detail="Streaming disabled")

    async def event_generator():
        try:
            async for token, done_response in service.stream_message(db, request):
                if done_response is not None:
                    payload = json.dumps(
                        {"done": True, "response": done_response.model_dump(mode="json")},
                        ensure_ascii=False,
                    )
                    yield f"data: {payload}\n\n"
                elif token:
                    payload = json.dumps({"token": token}, ensure_ascii=False)
                    yield f"data: {payload}\n\n"
        except Exception as exc:
            logger.exception("Chat stream failed")
            payload = json.dumps({"error": str(exc)}, ensure_ascii=False)
            yield f"data: {payload}\n\n"

    return StreamingResponse(event_generator(), media_type="text/event-stream")


@router.post("/feedback")
async def feedback(
    request: ChatFeedbackRequest,
    db: AsyncSession = Depends(get_async_session),
    service: ChatService = Depends(get_chat_service),
) -> dict[str, bool]:
    ok = await service.submit_feedback(db, request)
    if not ok:
        raise HTTPException(status_code=404, detail="Interaction not found")
    return {"ok": True}


@router.post("/session/clear")
async def clear_session(
    request: ChatClearSessionRequest,
    service: ChatService = Depends(get_chat_service),
) -> dict[str, bool]:
    service.clear_session(request.session_id)
    return {"ok": True}
