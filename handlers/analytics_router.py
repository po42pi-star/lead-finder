import logging
from functools import lru_cache
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import Response
from sqlalchemy.ext.asyncio import AsyncSession

from core.analytics.schemas import (
    AnalyticsExportRequest,
    AnalyticsReport,
    AnalyticsRunRequest,
    AnalyticsRunResponse,
    MarkInWorkRequest,
    MarkQuestionUsedRequest,
)
from core.config.settings import Settings, get_settings
from core.db.session import get_async_session
from services.analytics_service import AnalyticsService

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/analytics", tags=["analytics"])


@lru_cache
def get_analytics_service() -> AnalyticsService:
    return AnalyticsService(get_settings())


@router.post("/run", response_model=AnalyticsRunResponse)
async def run_analytics(
    request: AnalyticsRunRequest,
    db: AsyncSession = Depends(get_async_session),
    service: AnalyticsService = Depends(get_analytics_service),
) -> AnalyticsRunResponse:
    try:
        return await service.run(db, request)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:
        logger.exception("Analytics run failed")
        raise HTTPException(status_code=503, detail="Analytics unavailable") from exc


@router.get("/report/{report_id}", response_model=AnalyticsReport)
async def get_report(
    report_id: UUID,
    db: AsyncSession = Depends(get_async_session),
    service: AnalyticsService = Depends(get_analytics_service),
) -> AnalyticsReport:
    report = await service.get_report(db, report_id)
    if not report:
        raise HTTPException(status_code=404, detail="Report not found")
    return report


@router.get("/leads", response_model=AnalyticsRunResponse)
async def list_lead_reports(
    lead_ids: list[UUID] = Query(..., max_length=5),
    db: AsyncSession = Depends(get_async_session),
    service: AnalyticsService = Depends(get_analytics_service),
) -> AnalyticsRunResponse:
    reports = await service.list_for_leads(db, lead_ids)
    return AnalyticsRunResponse(reports=reports)


@router.post("/in-work")
async def mark_in_work(
    request: MarkInWorkRequest,
    db: AsyncSession = Depends(get_async_session),
    service: AnalyticsService = Depends(get_analytics_service),
) -> dict[str, int]:
    count = await service.mark_in_work(db, request)
    return {"updated": count}


@router.post("/questions/{question_id}/used-in-call")
async def mark_question_used(
    question_id: UUID,
    request: MarkQuestionUsedRequest,
    db: AsyncSession = Depends(get_async_session),
    service: AnalyticsService = Depends(get_analytics_service),
) -> dict[str, bool]:
    ok = await service.mark_question_used(db, question_id, request.used)
    if not ok:
        raise HTTPException(status_code=404, detail="Question not found")
    return {"ok": True}


@router.post("/export")
async def export_analytics(
    request: AnalyticsExportRequest,
    db: AsyncSession = Depends(get_async_session),
    service: AnalyticsService = Depends(get_analytics_service),
) -> Response:
    content, media_type, filename = await service.export_reports(db, request)
    return Response(
        content=content,
        media_type=media_type,
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )
