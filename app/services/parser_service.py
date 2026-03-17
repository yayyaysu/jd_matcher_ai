from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import settings
from app.db.models.job_analysis import JobAnalysis
from app.db.models.jobs import Job
from app.db.models.workflow import Workflow
from app.prompts.schemas import PARSER_SCHEMA
from app.services.cache_service import CacheService
from app.services.openai_client import OpenAIClient
from app.services.resume_service import load_resume_payload
from app.schemas.ai import ParserAIResult

PROMPT_PATH = settings.prompt_dir / "parser_prompt.txt"


def load_prompt() -> str:
    return PROMPT_PATH.read_text(encoding="utf-8")


def build_user_content(jd_text: str, resume_text: str) -> str:
    return (
        "Resume (current):\n"
        f"{resume_text}\n\n"
        "Job description:\n"
        f"{jd_text}\n"
    )


def compute_priority(fit_score: int, years_required: str, top_gaps_len: int) -> str:
    if fit_score >= 75 and years_required in {"0", "1-3", "3-5"} and top_gaps_len <= 2:
        return "P0"
    if fit_score < 60 or years_required == "5+":
        return "P2"
    if 60 <= fit_score <= 74 or top_gaps_len == 3:
        return "P1"
    return "P2"


def _parse_json_list(value: str | None) -> list[str]:
    if not value:
        return []
    try:
        parsed = json.loads(value)
    except json.JSONDecodeError:
        return []
    if not isinstance(parsed, list):
        return []
    return [str(item) for item in parsed if item]


def _serialize_list(value: list[str]) -> str:
    return json.dumps(value, ensure_ascii=False)


class ParserService:
    def __init__(self, db: Session) -> None:
        self.db = db
        self.cache = CacheService()

    async def analyze_job(self, job_id: str, force: bool = False) -> dict[str, Any]:
        job = self.db.get(Job, job_id)
        if job is None:
            raise ValueError(f"Job not found: {job_id}")

        resume_text, resume_hash = load_resume_payload()
        cache_key = self.cache.build_parser_key(job.id, resume_hash, settings.analysis_version)
        analysis_row = self.db.get(JobAnalysis, (job.id, settings.analysis_version))
        payload: dict[str, Any] | None = None
        source = "openai"

        if not force:
            payload = await self.cache.get_json(cache_key)
            if payload is not None:
                source = "redis"
            elif analysis_row is not None and analysis_row.resume_hash == resume_hash:
                payload = self._row_to_payload(analysis_row, job)
                source = "database"
                await self.cache.set_json(cache_key, payload)

        if payload is None:
            payload = self._generate_analysis(job.jd_text, resume_text)

        validated = ParserAIResult.model_validate(payload)
        payload = validated.model_dump()

        job.company = job.company or payload.get("company") or None
        job.role_title = job.role_title or payload.get("role_title") or None

        priority = compute_priority(
            int(payload["fit_score"]),
            payload["years_required"],
            len(payload.get("top_gaps", [])),
        )

        if analysis_row is None:
            analysis_row = JobAnalysis(job_id=job.id, analysis_version=settings.analysis_version)
            self.db.add(analysis_row)

        analysis_row.cluster = payload["cluster"]
        analysis_row.fit_score = int(payload["fit_score"])
        analysis_row.years_required = payload["years_required"]
        analysis_row.cluster_reason = payload["cluster_reason"]
        analysis_row.must_have_keywords = _serialize_list(payload["must_have_keywords"])
        analysis_row.nice_to_have_keywords = _serialize_list(payload["nice_to_have_keywords"])
        analysis_row.domain_keywords = _serialize_list(payload["domain_keywords"])
        analysis_row.top_gaps = _serialize_list(payload["top_gaps"])
        analysis_row.screening_risks = _serialize_list(payload["screening_risks"])
        analysis_row.recommended_resume_version = payload["recommended_resume_version"]
        analysis_row.resume_tweak_suggestions = _serialize_list(payload["resume_tweak_suggestions"])
        analysis_row.resume_hash = resume_hash

        workflow = self.db.get(Workflow, job.id)
        if workflow is None:
            workflow = Workflow(
                job_id=job.id,
                priority=priority,
                status="Backlog",
                next_action=self._priority_next_action(priority),
                notes=None,
                applied=False,
            )
            self.db.add(workflow)
        else:
            workflow.priority = priority
            if not workflow.applied:
                workflow.next_action = self._priority_next_action(priority)

        self.db.commit()
        self.db.refresh(job)
        self.db.refresh(analysis_row)
        self.db.refresh(workflow)

        result = self._row_to_payload(analysis_row, job)
        result.update(
            {
                "priority": priority,
                "cache_hit": source in {"redis", "database"},
                "source": source,
                "job_id": job.id,
                "workflow_status": workflow.status,
                "next_action": workflow.next_action,
            }
        )
        await self.cache.set_json(cache_key, result)
        return result

    async def analyze_jobs(self, job_ids: list[str] | None = None, force: bool = False) -> dict[str, Any]:
        if job_ids:
            ids = job_ids
        else:
            ids = list(self.db.execute(select(Job.id).order_by(Job.created_at.desc())).scalars().all())

        items: list[dict[str, Any]] = []
        generated_count = 0
        cache_hits = 0
        for job_id in ids:
            result = await self.analyze_job(job_id, force=force)
            items.append(result)
            if result["cache_hit"]:
                cache_hits += 1
            else:
                generated_count += 1

        return {
            "items": items,
            "total": len(items),
            "generated_count": generated_count,
            "cache_hits": cache_hits,
        }

    def _generate_analysis(self, jd_text: str, resume_text: str) -> dict[str, Any]:
        client = OpenAIClient()
        return client.generate_json(
            model=settings.parser_model,
            system_prompt=load_prompt(),
            user_content=build_user_content(jd_text, resume_text),
            schema=PARSER_SCHEMA,
            schema_name="job_analysis",
            pipeline_type="parser",
            max_output_tokens=900,
        )

    @staticmethod
    def _priority_next_action(priority: str) -> str:
        if priority == "P0":
            return "Apply ASAP"
        if priority == "P1":
            return "Consider applying"
        return "Low priority"

    def _row_to_payload(self, row: JobAnalysis, job: Job | None = None) -> dict[str, Any]:
        top_gaps = _parse_json_list(row.top_gaps)
        return {
            "company": (job.company if job else None) or "",
            "role_title": (job.role_title if job else None) or "",
            "cluster": row.cluster,
            "fit_score": row.fit_score,
            "cluster_reason": row.cluster_reason,
            "must_have_keywords": _parse_json_list(row.must_have_keywords),
            "nice_to_have_keywords": _parse_json_list(row.nice_to_have_keywords),
            "domain_keywords": _parse_json_list(row.domain_keywords),
            "years_required": row.years_required,
            "gap_keywords": top_gaps,
            "top_gaps": top_gaps,
            "screening_risks": _parse_json_list(row.screening_risks),
            "recommended_resume_version": row.recommended_resume_version,
            "resume_tweak_suggestions": _parse_json_list(row.resume_tweak_suggestions),
            "analysis_version": row.analysis_version,
            "resume_hash": row.resume_hash,
        }