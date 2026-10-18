import logging
from functools import lru_cache

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import Response
from sqlalchemy.ext.asyncio import AsyncSession

from core.config.settings import Settings, get_settings
from core.db.session import get_async_session
from core.search.schemas import (
    ExportRequest,
    FiltersMetaResponse,
    SearchMoreRequest,
    SearchRunRequest,
    SearchRunResponse,
)
from services.search_service import SearchService

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/search", tags=["search"])


@lru_cache
def get_search_service() -> SearchService:
    return SearchService(get_settings())


@router.get("/filters", response_model=FiltersMetaResponse)
async def filters_meta(
    service: SearchService = Depends(get_search_service),
) -> FiltersMetaResponse:
    return service.filters_meta()


@router.post("/run", response_model=SearchRunResponse)
async def run_search(
    request: SearchRunRequest,
    db: AsyncSession = Depends(get_async_session),
    service: SearchService = Depends(get_search_service),
) -> SearchRunResponse:
    try:
        return await service.run_search(db, request)
    except Exception as exc:
        logger.exception("Search run failed")
        raise HTTPException(status_code=503, detail="Search unavailable") from exc


@router.post("/more", response_model=SearchRunResponse)
async def load_more(
    request: SearchMoreRequest,
    db: AsyncSession = Depends(get_async_session),
    service: SearchService = Depends(get_search_service),
) -> SearchRunResponse:
    try:
        return await service.load_more(db, request)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.post("/export")
async def export_leads(
    request: ExportRequest,
    db: AsyncSession = Depends(get_async_session),
    service: SearchService = Depends(get_search_service),
) -> Response:
    content, media_type, filename = await service.export(db, request)
    return Response(
        content=content,
        media_type=media_type,
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )
