from __future__ import annotations

from datetime import datetime

from sqlalchemy import DateTime, Float, Integer, String, Text, func
from sqlalchemy.dialects.mysql import JSON as MySQLJSON
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.types import JSON

from app.db.base import Base


class AnalysisRecord(Base):
    __tablename__ = "analysis_records"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    jd_text: Mapped[str] = mapped_column(Text, nullable=False)
    matched_keywords: Mapped[list[str]] = mapped_column(MySQLJSON().with_variant(JSON, "sqlite"), nullable=False)
    missing_keywords: Mapped[list[str]] = mapped_column(MySQLJSON().with_variant(JSON, "sqlite"), nullable=False)
    score: Mapped[float] = mapped_column(Float, nullable=False)
    cluster: Mapped[str] = mapped_column(String(50), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), nullable=False)
