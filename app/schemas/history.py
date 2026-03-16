from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel


class HistoryRecord(BaseModel):
    id: int
    jd_text: str
    matched_keywords: list[str]
    missing_keywords: list[str]
    score: float
    cluster: str
    created_at: datetime


class HistoryListResponse(BaseModel):
    items: list[HistoryRecord]
    total: int
