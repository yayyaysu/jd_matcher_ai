from __future__ import annotations

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.api.deps import get_db
from app.schemas.strategy import StrategyGenerateRequest, StrategyGenerateResponse, StrategyListResponse
from app.services.strategy_service import StrategyService

router = APIRouter(prefix="/strategy", tags=["strategy"])


@router.post("/generate", response_model=StrategyGenerateResponse)
async def generate_strategy(payload: StrategyGenerateRequest, db: Session = Depends(get_db)) -> StrategyGenerateResponse:
    service = StrategyService(db)
    result = await service.generate_strategies(
        cluster=payload.cluster,
        filter_company=payload.filter_company,
        filter_min_score=payload.filter_min_score,
        force=payload.force,
    )
    return StrategyGenerateResponse(**result)


@router.get("", response_model=StrategyListResponse)
def list_strategy(
    cluster: str | None = None,
    filter_company: str | None = None,
    filter_min_score: int | None = Query(default=None, ge=0, le=100),
    limit: int = Query(default=20, ge=1, le=100),
    db: Session = Depends(get_db),
) -> StrategyListResponse:
    service = StrategyService(db)
    return StrategyListResponse(
        **service.list_strategies(
            cluster=cluster,
            filter_company=filter_company,
            filter_min_score=filter_min_score,
            limit=limit,
        )
    )