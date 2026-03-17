from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, Field


class JobCreateRequest(BaseModel):
    jd_text: str = Field(..., min_length=20)
    url: str | None = None
    company: str | None = None
    role_title: str | None = None
    notes: str | None = None
    auto_analyze: bool = False


class WorkflowSnapshot(BaseModel):
    priority: str
    status: str
    next_action: str
    applied: bool
    applied_date: datetime | None = None
    notes: str | None = None
    updated_at: datetime | None = None


class JobAnalysisSnapshot(BaseModel):
    job_id: str
    company: str
    role_title: str
    cluster: str
    fit_score: int
    cluster_reason: str
    must_have_keywords: list[str]
    nice_to_have_keywords: list[str]
    domain_keywords: list[str]
    gap_keywords: list[str] = Field(default_factory=list)
    years_required: str
    top_gaps: list[str]
    screening_risks: list[str]
    recommended_resume_version: str
    resume_tweak_suggestions: list[str]
    analysis_version: int
    resume_hash: str | None = None
    priority: str
    cache_hit: bool = False
    source: str
    workflow_status: str
    next_action: str


class JobRecord(BaseModel):
    job_id: str
    company: str | None = None
    role_title: str | None = None
    url: str | None = None
    jd_text: str
    created_at: datetime
    analysis: JobAnalysisSnapshot | None = None
    workflow: WorkflowSnapshot | None = None


class JobCreateResponse(BaseModel):
    job: JobRecord


class JobListResponse(BaseModel):
    items: list[JobRecord]
    total: int


class JobAnalyzeRequest(BaseModel):
    job_id: str | None = None
    job_ids: list[str] | None = None
    force: bool = False


class JobAnalyzeResponse(BaseModel):
    items: list[JobAnalysisSnapshot]
    total: int
    generated_count: int
    cache_hits: int


class WorkflowUpdateRequest(BaseModel):
    status: str | None = None
    next_action: str | None = None
    applied: bool | None = None
    notes: str | None = None
    priority: str | None = None


class WorkflowUpdateResponse(BaseModel):
    job_id: str
    workflow: WorkflowSnapshot


class DeleteJobResponse(BaseModel):
    deleted: bool
    job_id: str