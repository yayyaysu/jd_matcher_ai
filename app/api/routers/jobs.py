from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.api.deps import get_db
from app.schemas.jobs import (
    DeleteJobResponse,
    JobAnalyzeRequest,
    JobAnalyzeResponse,
    JobCreateRequest,
    JobCreateResponse,
    JobListResponse,
    WorkflowUpdateRequest,
    WorkflowUpdateResponse,
)
from app.services.job_service import JobService
from app.services.parser_service import ParserService

router = APIRouter(prefix="/jobs", tags=["jobs"])


@router.post("/add", response_model=JobCreateResponse)
async def add_job(payload: JobCreateRequest, db: Session = Depends(get_db)) -> JobCreateResponse:
    job_service = JobService(db)
    token_usage = None
    job = job_service.add_job(
        jd_text=payload.jd_text,
        url=payload.url,
        company=payload.company,
        role_title=payload.role_title,
        notes=payload.notes,
    )
    if payload.auto_analyze:
        parser_service = ParserService(db)
        analysis_result = await parser_service.analyze_job(job.id)
        token_usage = analysis_result.get("token_usage")
    return JobCreateResponse(job=job_service.get_job_snapshot(job.id), token_usage=token_usage)


@router.post("/analyze", response_model=JobAnalyzeResponse)
async def analyze_jobs(payload: JobAnalyzeRequest, db: Session = Depends(get_db)) -> JobAnalyzeResponse:
    parser_service = ParserService(db)
    job_ids = payload.job_ids or ([payload.job_id] if payload.job_id else None)
    try:
        result = await parser_service.analyze_jobs(job_ids=job_ids, force=payload.force)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    return JobAnalyzeResponse(**result)


@router.post("/analyze/{job_id}", response_model=JobAnalyzeResponse)
async def analyze_single_job(job_id: str, force: bool = False, db: Session = Depends(get_db)) -> JobAnalyzeResponse:
    parser_service = ParserService(db)
    try:
        result = await parser_service.analyze_jobs(job_ids=[job_id], force=force)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    return JobAnalyzeResponse(**result)


@router.get("", response_model=JobListResponse)
def list_jobs(
    cluster: str | None = None,
    status: str | None = None,
    priority: str | None = None,
    company: str | None = None,
    applied: bool | None = None,
    min_score: int | None = Query(default=None, ge=0, le=100),
    limit: int = Query(default=50, ge=1, le=200),
    db: Session = Depends(get_db),
) -> JobListResponse:
    service = JobService(db)
    return JobListResponse(**service.list_jobs(
        cluster=cluster,
        status=status,
        priority=priority,
        company=company,
        applied=applied,
        min_score=min_score,
        limit=limit,
    ))


@router.patch("/{job_id}/workflow", response_model=WorkflowUpdateResponse)
def update_workflow(job_id: str, payload: WorkflowUpdateRequest, db: Session = Depends(get_db)) -> WorkflowUpdateResponse:
    service = JobService(db)
    try:
        workflow = service.update_workflow(
            job_id,
            status=payload.status,
            next_action=payload.next_action,
            applied=payload.applied,
            notes=payload.notes,
            priority=payload.priority,
        )
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    return WorkflowUpdateResponse(
        job_id=job_id,
        workflow={
            "priority": workflow.priority,
            "status": workflow.status,
            "next_action": workflow.next_action,
            "applied": workflow.applied,
            "applied_date": workflow.applied_date,
            "notes": workflow.notes,
            "updated_at": workflow.updated_at,
        },
    )


@router.delete("/{job_id}", response_model=DeleteJobResponse)
def delete_job(job_id: str, db: Session = Depends(get_db)) -> DeleteJobResponse:
    service = JobService(db)
    deleted = service.delete_job(job_id)
    if not deleted:
        raise HTTPException(status_code=404, detail=f"Job not found: {job_id}")
    return DeleteJobResponse(deleted=True, job_id=job_id)