from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.api.deps import get_db
from app.schemas.analysis import JDAnalysisRequest, JDAnalysisResponse
from app.services.jd_analysis_service import JDAnalysisService

router = APIRouter(prefix="/analysis", tags=["analysis"])


@router.post("/jd", response_model=JDAnalysisResponse)
async def analyze_jd(payload: JDAnalysisRequest, db: Session = Depends(get_db)) -> JDAnalysisResponse:
    service = JDAnalysisService(db)
    return await service.analyze_and_store(payload)
