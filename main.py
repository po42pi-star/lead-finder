import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from core.analytics.retrieval_log import RetrievalLogger
from core.config.settings import get_settings
from core.db.session import init_db
from core.dependencies import get_retrieval_cache
from handlers.rag_router import router as rag_router
from handlers.analytics_router import router as analytics_router
from handlers.chat_router import router as chat_router
from handlers.search_router import get_search_service, router as search_router

logging.basicConfig(
    level=get_settings().log_level,
    format="%(asctime)s %(levelname)s [%(name)s] %(message)s",
)


@asynccontextmanager
async def lifespan(app: FastAPI):
    settings = get_settings()
    retrieval_logger = RetrievalLogger(settings)
    await retrieval_logger.initialize()
    app.state.retrieval_logger = retrieval_logger
    try:
        await init_db(settings)
    except Exception as exc:
        logging.getLogger(__name__).warning("Database init failed: %s", exc)

    # Очищаем retrieval cache при старте
    try:
        cache = get_retrieval_cache()
        cache.invalidate_all()
        logging.getLogger(__name__).info("Retrieval cache cleared on startup")
    except Exception as exc:
        logging.getLogger(__name__).warning("Cache clear failed: %s", exc)

    yield
    await get_search_service().close()


app = FastAPI(
    title="AI Search Analytics",
    description="RAG knowledge base API for B2B lead qualification",
    version="0.1.0",
    lifespan=lifespan,
)
settings = get_settings()
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origin_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.include_router(rag_router)
app.include_router(search_router)
app.include_router(analytics_router)
app.include_router(chat_router)


@app.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok"}

