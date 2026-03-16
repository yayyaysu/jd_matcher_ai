from __future__ import annotations

import logging

from sqlalchemy import desc, select
from sqlalchemy.orm import Session

from app.db.models.analysis_record import AnalysisRecord
from app.schemas.analysis import JDAnalysisRequest, JDAnalysisResponse
from app.schemas.history import HistoryListResponse, HistoryRecord
from app.services.cache_service import CacheService
from app.services.match_service import analyze_jd_text

logger = logging.getLogger(__name__)


class JDAnalysisService:
    def __init__(self, db: Session) -> None:
        self.db = db
        self.cache_service = CacheService()

    async def analyze_and_store(self, payload: JDAnalysisRequest) -> JDAnalysisResponse:
        cached = await self.cache_service.get_analysis(payload.jd_text)
        if cached:
            logger.info("Cache hit for /analysis/jd")
            cached["cache_hit"] = True
            return JDAnalysisResponse(**cached)

        logger.info("Cache miss for /analysis/jd; running analysis")
        analyzed = analyze_jd_text(payload.jd_text)

        response_payload = {
            "cluster": analyzed["cluster"],
            "score": analyzed["score"],
            "matched_keywords": analyzed["matched_keywords"],
            "missing_keywords": analyzed["missing_keywords"],
            "cache_hit": False,
        }

        record = AnalysisRecord(
            jd_text=payload.jd_text,
            matched_keywords=analyzed["matched_keywords"],
            missing_keywords=analyzed["missing_keywords"],
            score=analyzed["score"],
            cluster=analyzed["cluster"],
        )
        self.db.add(record)
        self.db.commit()
        logger.info("Analysis persisted to MySQL")

        await self.cache_service.set_analysis(payload.jd_text, response_payload)
        return JDAnalysisResponse(**response_payload)

    def get_recent_history(self, limit: int) -> HistoryListResponse:
        stmt = select(AnalysisRecord).order_by(desc(AnalysisRecord.created_at)).limit(limit)
        rows = self.db.execute(stmt).scalars().all()

        items = [
            HistoryRecord(
                id=row.id,
                jd_text=row.jd_text,
                matched_keywords=row.matched_keywords,
                missing_keywords=row.missing_keywords,
                score=row.score,
                cluster=row.cluster,
                created_at=row.created_at,
            )
            for row in rows
        ]
        return HistoryListResponse(items=items, total=len(items))
