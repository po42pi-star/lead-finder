import logging

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException

# from core.analytics.retrieval_log import RetrievalLogger  # Disabled
from core.config.settings import Settings, get_settings
from core.dependencies import (
    get_chroma_store,
    get_document_loader,
    get_embedding_service,
    get_intent_classifier,
    get_markdown_chunker,
    get_retrieval_cache,
    get_retrieval_pipeline,
)
from core.rag.models import (
    CollectionsResponse,
    CollectionStats,
    IngestRequest,
    IngestResponse,
    SearchRequest,
    SearchResponse,
)
from services.rag_service import RagService

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/rag", tags=["rag"])


# def get_retrieval_logger(settings: Settings = Depends(get_settings)) -> RetrievalLogger:
    # return RetrievalLogger(settings)  # Disabled


def get_rag_service(
    settings: Settings = Depends(get_settings),
) -> RagService:
    # Create RetrievalLogger directly
    from core.analytics.retrieval_log import RetrievalLogger
    retrieval_logger = RetrievalLogger(settings)
    
    return RagService(
        settings=settings,
        loader=get_document_loader(),
        chunker=get_markdown_chunker(),
        embeddings=get_embedding_service(),
        chroma=get_chroma_store(),
        cache=get_retrieval_cache(),
        pipeline=get_retrieval_pipeline(),
        retrieval_logger=retrieval_logger,
    )


@router.post("/ingest", response_model=IngestResponse)
async def ingest(
    request: IngestRequest,
    background_tasks: BackgroundTasks,
    service: RagService = Depends(get_rag_service),
) -> IngestResponse:
    files_count = service.count_files(request.path)
    background_tasks.add_task(
        _run_ingest_background,
        service,
        request.path,
        request.force_rebuild,
    )
    return IngestResponse(
        status="accepted",
        message="Ingestion started in background",
        files_queued=files_count,
    )


async def _run_ingest_background(
    service: RagService,
    path: str,
    force_rebuild: bool,
) -> None:
    try:
        result = await service.ingest(path, force_rebuild)
        logger.info("Background ingest finished: %s", result.message)
    except Exception as exc:
        logger.exception("Background ingest failed: %s", exc)


@router.post("/search", response_model=SearchResponse)
async def search(
    request: SearchRequest,
    service: RagService = Depends(get_rag_service),
) -> SearchResponse:
    try:
        return await service.search(request)
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except Exception as exc:
        logger.exception("RAG search failed")
        raise HTTPException(status_code=503, detail="RAG search unavailable") from exc


@router.get("/collections", response_model=CollectionsResponse)
async def collections(
    service: RagService = Depends(get_rag_service),
) -> CollectionsResponse:
    stats = service.collections_stats()
    return CollectionsResponse(
        collections=[
            CollectionStats(
                name=stats["name"],
                chunk_count=stats["chunk_count"],
                categories=stats["categories"],
            )
        ]
    )


@router.post("/diag")
async def diag(
    request: SearchRequest,
    service: RagService = Depends(get_rag_service),
):
    intent = await service._pipeline._intent_classifier.classify(
        request.query, request.user_role, request.category_override
    )
    return {
        "query": request.query,
        "category": intent.category.value if intent.category else None,
        "intent": intent.intent.value if intent.intent else None,
        
    }
