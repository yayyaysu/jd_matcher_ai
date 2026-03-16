from __future__ import annotations

from datetime import datetime

from sqlalchemy import DateTime, Integer, Text, func
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class ResumeStrategy(Base):
    __tablename__ = "resume_strategy"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    resume_variant: Mapped[str] = mapped_column(Text, nullable=False)
    cluster: Mapped[str] = mapped_column(Text, nullable=False)
    cluster_summary: Mapped[str] = mapped_column(Text, nullable=False)
    resume_plan_md: Mapped[str] = mapped_column(Text, nullable=False)
    resume_hash: Mapped[str] = mapped_column(Text, nullable=False)
    analysis_version: Mapped[int] = mapped_column(Integer, nullable=False)
    cluster_input_hash: Mapped[str] = mapped_column(Text, nullable=False)
    filter_company: Mapped[str | None] = mapped_column(Text, nullable=True)
    filter_min_score: Mapped[int | None] = mapped_column(Integer, nullable=True)
    output_filename: Mapped[str | None] = mapped_column(Text, nullable=True)
    generated_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), nullable=False)