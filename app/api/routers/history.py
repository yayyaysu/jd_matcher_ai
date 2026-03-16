from __future__ import annotations

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.api.deps import get_db
from app.schemas.history import HistoryListResponse
from app.services.jd_analysis_service import JDAnalysisService

router = APIRouter(prefix="/history", tags=["history"])


@router.get("", response_model=HistoryListResponse)
async def get_history(
    limit: int = Query(default=20, ge=1, le=200),
    db: Session = Depends(get_db),
) -> HistoryListResponse:
    service = JDAnalysisService(db)
    return service.get_recent_history(limit)
