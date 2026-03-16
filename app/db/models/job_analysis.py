from __future__ import annotations

from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Integer, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class JobAnalysis(Base):
    __tablename__ = "job_analysis"

    job_id: Mapped[str] = mapped_column(String(255), ForeignKey("jobs.id"), primary_key=True)
    analysis_version: Mapped[int] = mapped_column(Integer, primary_key=True)
    cluster: Mapped[str] = mapped_column(Text, nullable=False)
    fit_score: Mapped[int] = mapped_column(Integer, nullable=False)
    years_required: Mapped[str] = mapped_column(Text, nullable=False)
    cluster_reason: Mapped[str] = mapped_column(Text, nullable=False)
    must_have_keywords: Mapped[str] = mapped_column(Text, nullable=False)
    nice_to_have_keywords: Mapped[str] = mapped_column(Text, nullable=False)
    domain_keywords: Mapped[str] = mapped_column(Text, nullable=False)
    top_gaps: Mapped[str] = mapped_column(Text, nullable=False)
    screening_risks: Mapped[str] = mapped_column(Text, nullable=False)
    recommended_resume_version: Mapped[str] = mapped_column(Text, nullable=False)
    resume_tweak_suggestions: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), nullable=False)
    resume_hash: Mapped[str | None] = mapped_column(Text, nullable=True)