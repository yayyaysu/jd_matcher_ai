from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, Field


class KeywordCount(BaseModel):
    keyword: str
    count: int


class ClusterSummary(BaseModel):
    top_must_haves: list[KeywordCount]
    top_domains: list[KeywordCount]
    top_gaps: list[KeywordCount]


class StrategyGenerateRequest(BaseModel):
    cluster: str | None = Field(default="all")
    filter_company: str | None = None
    filter_min_score: int | None = Field(default=None, ge=0, le=100)
    force: bool = False


class StrategyResult(BaseModel):
    id: int | None = None
    cluster: str
    resume_variant: str
    summary: ClusterSummary
    section_md: str
    resume_hash: str | None = None
    analysis_version: int | None = None
    cluster_input_hash: str
    filter_company: str | None = None
    filter_min_score: int | None = None
    output_filename: str
    generated_at: datetime | None = None
    used_cache: bool
    source: str
    no_matching: bool = False


class StrategyGenerateResponse(BaseModel):
    items: list[StrategyResult]
    total: int
    index_filename: str


class StrategyListResponse(BaseModel):
    items: list[StrategyResult]
    total: int