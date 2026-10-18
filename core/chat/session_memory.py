import time
import uuid
from dataclasses import dataclass, field
from typing import Any


@dataclass
class SessionState:
    session_id: uuid.UUID
    user_role: str
    mode: str
    context: dict[str, Any] = field(default_factory=dict)
    last_lead_id: uuid.UUID | None = None
    last_segment: str | None = None
    recent_queries: list[str] = field(default_factory=list)
    updated_at: float = field(default_factory=time.time)


class SessionMemoryStore:
    def __init__(self, ttl_sec: int) -> None:
        self._ttl_sec = ttl_sec
        self._sessions: dict[str, SessionState] = {}

    def get(self, session_id: uuid.UUID) -> SessionState | None:
        key = str(session_id)
        state = self._sessions.get(key)
        if not state:
            return None
        if time.time() - state.updated_at > self._ttl_sec:
            del self._sessions[key]
            return None
        return state

    def create(
        self,
        *,
        user_role: str,
        mode: str,
        context: dict[str, Any] | None = None,
        session_id: uuid.UUID | None = None,
    ) -> SessionState:
        sid = session_id or uuid.uuid4()
        state = SessionState(
            session_id=sid,
            user_role=user_role,
            mode=mode,
            context=context or {},
        )
        self._sessions[str(sid)] = state
        return state

    def touch(
        self,
        state: SessionState,
        *,
        query: str,
        context: dict[str, Any] | None = None,
    ) -> SessionState:
        state.recent_queries = ([query] + state.recent_queries)[:3]
        state.updated_at = time.time()
        if context:
            state.context.update(context)
            if context.get("lead_id"):
                state.last_lead_id = uuid.UUID(str(context["lead_id"]))
            if context.get("segment"):
                state.last_segment = str(context["segment"])
        self._sessions[str(state.session_id)] = state
        return state

    def clear(self, session_id: uuid.UUID) -> None:
        self._sessions.pop(str(session_id), None)
