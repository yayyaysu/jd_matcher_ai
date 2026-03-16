from __future__ import annotations

from datetime import datetime
from typing import Any
from uuid import uuid4

from sqlalchemy import and_, select
from sqlalchemy.orm import Session

from app.core.config import settings
from app.db.models.job_analysis import JobAnalysis
from app.db.models.jobs import Job
from app.db.models.workflow import Workflow
from app.services.parser_service import compute_priority


def _parse_json_list(value: str | None) -> list[str]:
    import json

    if not value:
        return []
    try:
        data = json.loads(value)
    except json.JSONDecodeError:
        return []
    if not isinstance(data, list):
        return []
    return [str(item) for item in data if item]


class JobService:
    def __init__(self, db: Session) -> None:
        self.db = db

    def add_job(
        self,
        *,
        jd_text: str,
        url: str | None = None,
        company: str | None = None,
        role_title: str | None = None,
        notes: str | None = None,
    ) -> Job:
        job = Job(
            id=f"job_{uuid4().hex[:12]}",
            company=(company or None),
            role_title=(role_title or None),
            url=(url or None),
            jd_text=jd_text.strip(),
        )
        workflow = Workflow(
            job_id=job.id,
            priority="P2",
            status="Backlog",
            next_action="Run parser analysis",
            notes=(notes or None),
            applied=False,
        )
        self.db.add(job)
        self.db.add(workflow)
        self.db.commit()
        self.db.refresh(job)
        return job

    def delete_job(self, job_id: str) -> bool:
        workflow = self.db.get(Workflow, job_id)
        analysis = self.db.get(JobAnalysis, (job_id, settings.analysis_version))
        job = self.db.get(Job, job_id)
        if job is None:
            return False
        if workflow is not None:
            self.db.delete(workflow)
        if analysis is not None:
            self.db.delete(analysis)
        self.db.delete(job)
        self.db.commit()
        return True

    def update_workflow(
        self,
        job_id: str,
        *,
        status: str | None = None,
        next_action: str | None = None,
        applied: bool | None = None,
        notes: str | None = None,
        priority: str | None = None,
    ) -> Workflow:
        job = self.db.get(Job, job_id)
        if job is None:
            raise ValueError(f"Job not found: {job_id}")

        workflow = self.db.get(Workflow, job_id)
        if workflow is None:
            workflow = Workflow(
                job_id=job_id,
                priority=priority or "P2",
                status=status or "Backlog",
                next_action=next_action or "Run parser analysis",
                notes=notes,
                applied=bool(applied),
            )
            self.db.add(workflow)
        else:
            if status is not None:
                workflow.status = status
            if next_action is not None:
                workflow.next_action = next_action
            if notes is not None:
                workflow.notes = notes
            if priority is not None:
                workflow.priority = priority
            if applied is not None:
                workflow.applied = applied
                workflow.applied_date = datetime.utcnow() if applied else None
                if applied:
                    workflow.status = "Applied"
                    workflow.next_action = "Already applied"

        self.db.commit()
        self.db.refresh(workflow)
        return workflow

    def list_jobs(
        self,
        *,
        cluster: str | None = None,
        status: str | None = None,
        priority: str | None = None,
        company: str | None = None,
        applied: bool | None = None,
        min_score: int | None = None,
        limit: int = 50,
    ) -> dict[str, Any]:
        stmt = (
            select(Job, JobAnalysis, Workflow)
            .outerjoin(
                JobAnalysis,
                and_(Job.id == JobAnalysis.job_id, JobAnalysis.analysis_version == settings.analysis_version),
            )
            .outerjoin(Workflow, Workflow.job_id == Job.id)
            .order_by(Job.created_at.desc())
            .limit(limit)
        )

        if cluster and cluster.lower() != "all":
            stmt = stmt.where(JobAnalysis.cluster == cluster)
        if status:
            stmt = stmt.where(Workflow.status == status)
        if priority:
            stmt = stmt.where(Workflow.priority == priority)
        if company:
            stmt = stmt.where(Job.company.ilike(f"%{company}%"))
        if applied is not None:
            stmt = stmt.where(Workflow.applied == applied)
        if min_score is not None:
            stmt = stmt.where(JobAnalysis.fit_score >= min_score)

        rows = self.db.execute(stmt).all()
        items = [self._serialize_row(job, analysis, workflow) for job, analysis, workflow in rows]
        return {"items": items, "total": len(items)}

    def get_job_snapshot(self, job_id: str) -> dict[str, Any]:
        stmt = (
            select(Job, JobAnalysis, Workflow)
            .outerjoin(
                JobAnalysis,
                and_(Job.id == JobAnalysis.job_id, JobAnalysis.analysis_version == settings.analysis_version),
            )
            .outerjoin(Workflow, Workflow.job_id == Job.id)
            .where(Job.id == job_id)
        )
        row = self.db.execute(stmt).first()
        if row is None:
            raise ValueError(f"Job not found: {job_id}")
        job, analysis, workflow = row
        return self._serialize_row(job, analysis, workflow)

    def _serialize_row(self, job: Job, analysis: JobAnalysis | None, workflow: Workflow | None) -> dict[str, Any]:
        analysis_payload = None
        if analysis is not None:
            priority = workflow.priority if workflow is not None else compute_priority(
                analysis.fit_score,
                analysis.years_required,
                len(_parse_json_list(analysis.top_gaps)),
            )
            analysis_payload = {
                "company": job.company or "",
                "role_title": job.role_title or "",
                "cluster": analysis.cluster,
                "fit_score": analysis.fit_score,
                "cluster_reason": analysis.cluster_reason,
                "must_have_keywords": _parse_json_list(analysis.must_have_keywords),
                "nice_to_have_keywords": _parse_json_list(analysis.nice_to_have_keywords),
                "domain_keywords": _parse_json_list(analysis.domain_keywords),
                "years_required": analysis.years_required,
                "top_gaps": _parse_json_list(analysis.top_gaps),
                "screening_risks": _parse_json_list(analysis.screening_risks),
                "recommended_resume_version": analysis.recommended_resume_version,
                "resume_tweak_suggestions": _parse_json_list(analysis.resume_tweak_suggestions),
                "analysis_version": analysis.analysis_version,
                "resume_hash": analysis.resume_hash,
                "priority": priority,
                "cache_hit": False,
                "source": "database",
                "job_id": job.id,
                "workflow_status": workflow.status if workflow else "Backlog",
                "next_action": workflow.next_action if workflow else "Run parser analysis",
            }

        workflow_payload = None
        if workflow is not None:
            workflow_payload = {
                "priority": workflow.priority,
                "status": workflow.status,
                "next_action": workflow.next_action,
                "applied": workflow.applied,
                "applied_date": workflow.applied_date,
                "notes": workflow.notes,
                "updated_at": workflow.updated_at,
            }

        return {
            "job_id": job.id,
            "company": job.company,
            "role_title": job.role_title,
            "url": job.url,
            "jd_text": job.jd_text,
            "created_at": job.created_at,
            "analysis": analysis_payload,
            "workflow": workflow_payload,
        }