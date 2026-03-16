from __future__ import annotations

import csv
from datetime import datetime
from pathlib import Path

from sqlalchemy import and_, select
from sqlalchemy.orm import Session

from app.core.config import settings
from app.db.models.job_analysis import JobAnalysis
from app.db.models.jobs import Job
from app.db.models.resume_strategy import ResumeStrategy
from app.db.models.workflow import Workflow


class ExportService:
    def __init__(self, db: Session) -> None:
        self.db = db

    def export_all(self) -> dict[str, str]:
        jobs_csv = self._export_jobs_csv()
        dash_md = self._export_dash_md()
        resume_versions_md = self._export_resume_versions_md()
        return {
            "jobs_csv": jobs_csv,
            "dash_md": dash_md,
            "resume_versions_md": resume_versions_md,
        }

    def _export_jobs_csv(self) -> str:
        output_path = settings.resolve_output_path("jobs.csv")
        stmt = (
            select(Job, JobAnalysis, Workflow)
            .outerjoin(
                JobAnalysis,
                and_(Job.id == JobAnalysis.job_id, JobAnalysis.analysis_version == settings.analysis_version),
            )
            .outerjoin(Workflow, Workflow.job_id == Job.id)
            .order_by(Job.created_at.desc())
        )
        rows = self.db.execute(stmt).all()
        with output_path.open("w", newline="", encoding="utf-8") as handle:
            writer = csv.writer(handle)
            writer.writerow(
                [
                    "job_id",
                    "company",
                    "role_title",
                    "url",
                    "jd_text",
                    "created_at",
                    "cluster",
                    "fit_score",
                    "years_required",
                    "recommended_resume_version",
                    "top_gaps",
                    "priority",
                    "status",
                    "next_action",
                    "applied",
                    "applied_date",
                ]
            )
            for job, analysis, workflow in rows:
                writer.writerow(
                    [
                        job.id,
                        job.company,
                        job.role_title,
                        job.url,
                        job.jd_text,
                        job.created_at,
                        analysis.cluster if analysis else None,
                        analysis.fit_score if analysis else None,
                        analysis.years_required if analysis else None,
                        analysis.recommended_resume_version if analysis else None,
                        analysis.top_gaps if analysis else None,
                        workflow.priority if workflow else None,
                        workflow.status if workflow else None,
                        workflow.next_action if workflow else None,
                        workflow.applied if workflow else None,
                        workflow.applied_date if workflow else None,
                    ]
                )
        return str(output_path)

    def _export_dash_md(self) -> str:
        output_path = settings.resolve_output_path("dash.md")
        stmt = (
            select(Job, JobAnalysis, Workflow)
            .join(
                JobAnalysis,
                and_(Job.id == JobAnalysis.job_id, JobAnalysis.analysis_version == settings.analysis_version),
            )
            .join(Workflow, Workflow.job_id == Job.id)
            .where(Workflow.priority == "P0")
            .order_by(JobAnalysis.fit_score.desc())
        )
        rows = self.db.execute(stmt).all()
        today = datetime.now().strftime("%Y-%m-%d")
        lines = [f"# P0 shortlist ({today})", ""]
        if not rows:
            lines.append("No P0 jobs found.")
        else:
            for job, analysis, workflow in rows:
                lines.append(
                    f"- {job.company} | {job.role_title} | {job.url} | Cluster {analysis.cluster} | Fit {analysis.fit_score} | {workflow.next_action}"
                )
        output_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
        return str(output_path)

    def _export_resume_versions_md(self) -> str:
        output_path = settings.resolve_output_path("resume_versions.md")
        rows = self.db.execute(
            select(ResumeStrategy).order_by(ResumeStrategy.generated_at.desc(), ResumeStrategy.id.desc())
        ).scalars().all()
        lines = ["# Resume Strategy Outputs", ""]
        if not rows:
            lines.append("No generated strategy files yet.")
        else:
            for row in rows:
                lines.append(
                    f"- Cluster {row.cluster} | {row.resume_variant} | {row.output_filename or 'N/A'} | generated_at={row.generated_at}"
                )
        output_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
        return str(output_path)