from __future__ import annotations

import hashlib
import json
import re
from collections import Counter
from pathlib import Path
from typing import Any, Iterable

from sqlalchemy import and_, select
from sqlalchemy.orm import Session

from app.core.config import settings
from app.db.models.job_analysis import JobAnalysis
from app.db.models.jobs import Job
from app.db.models.resume_strategy import ResumeStrategy
from app.prompts.schemas import STRATEGIST_SCHEMA
from app.services.cache_service import CacheService
from app.services.openai_client import OpenAIClient
from app.services.resume_service import load_resume_payload

PROMPT_PATH = Path(__file__).resolve().parents[1] / "prompts" / "strategist_prompt.txt"


def load_prompt() -> str:
    return PROMPT_PATH.read_text(encoding="utf-8")


def _truncate_text(text: str, max_chars: int = 3000) -> str:
    if len(text) <= max_chars:
        return text
    head = text[: int(max_chars * 0.6)]
    tail = text[-int(max_chars * 0.3) :]
    return f"{head}\n...\n{tail}"


def _parse_json_list(value: str | None) -> list[str]:
    if not value:
        return []
    try:
        data = json.loads(value)
    except json.JSONDecodeError:
        return []
    if isinstance(data, list):
        return [str(item) for item in data if item]
    return []


def aggregate_keywords(rows: Iterable[dict[str, Any]]) -> dict[str, Any]:
    must_have_counter: Counter[str] = Counter()
    domain_counter: Counter[str] = Counter()
    gaps_counter: Counter[str] = Counter()

    for row in rows:
        must_have_counter.update(_parse_json_list(row.get("must_have_keywords")))
        domain_counter.update(_parse_json_list(row.get("domain_keywords")))
        gaps_counter.update(_parse_json_list(row.get("top_gaps")))

    return {
        "top_must_haves": [
            {"keyword": keyword, "count": count}
            for keyword, count in must_have_counter.most_common(15)
        ],
        "top_domains": [
            {"keyword": keyword, "count": count}
            for keyword, count in domain_counter.most_common(10)
        ],
        "top_gaps": [
            {"keyword": keyword, "count": count}
            for keyword, count in gaps_counter.most_common(8)
        ],
    }


def map_resume_variant(cluster: str) -> str | None:
    return {
        "A": "A_resume",
        "B": "B_resume",
        "C1": "C1_resume",
        "C2": "C2_resume",
    }.get(cluster)


def compute_cluster_input_hash(
    *,
    cluster: str,
    resume_variant: str,
    resume_hash: str,
    analysis_version: int,
    filter_company: str | None,
    filter_min_score: int | None,
    rows: Iterable[dict[str, Any]],
) -> str:
    normalized_rows: list[dict[str, Any]] = []
    for row in rows:
        normalized_rows.append(
            {
                "job_id": row["job_id"],
                "fit_score": row["fit_score"],
                "must_have_keywords": sorted(_parse_json_list(row.get("must_have_keywords"))),
                "domain_keywords": sorted(_parse_json_list(row.get("domain_keywords"))),
                "top_gaps": sorted(_parse_json_list(row.get("top_gaps"))),
                "recommended_resume_version": row.get("recommended_resume_version"),
            }
        )
    normalized_rows.sort(key=lambda item: item["job_id"])
    payload = {
        "cluster": cluster,
        "resume_variant": resume_variant,
        "resume_hash": resume_hash,
        "analysis_version": analysis_version,
        "filter_company": filter_company,
        "filter_min_score": filter_min_score,
        "rows": normalized_rows,
    }
    dumped = json.dumps(payload, ensure_ascii=False, sort_keys=True)
    return hashlib.sha256(dumped.encode("utf-8")).hexdigest()


def _list_with_counts(items: list[dict[str, int]]) -> str:
    return "\n".join([f"- {item['keyword']} ({item['count']})" for item in items])


def _list_plain(items: list[str]) -> str:
    return "\n".join([f"- {item}" for item in items])


def render_strategy_markdown(
    *,
    cluster: str,
    resume_variant: str,
    top_must_haves: list[dict[str, int]],
    top_domains: list[dict[str, int]],
    top_gaps: list[dict[str, int]],
    positioning_sentence: str,
    keyword_additions: list[str],
    bullets: list[str],
    checklist: list[str],
    notes: list[str] | None,
) -> str:
    summary_md = (
        f"## Cluster {cluster}\n\n"
        "## Cluster Summary\n"
        "Top must-have keywords:\n"
        f"{_list_with_counts(top_must_haves)}\n\n"
        "Top domain keywords:\n"
        f"{_list_with_counts(top_domains)}\n\n"
        "Top gaps:\n"
        f"{_list_with_counts(top_gaps)}\n"
    )
    variant_md = (
        f"## Resume Variant: {resume_variant}\n"
        f"Positioning sentence: {positioning_sentence}\n\n"
        "Keyword additions:\n"
        f"{_list_plain(keyword_additions)}\n\n"
        "Ready-to-paste bullets:\n"
        f"{_list_plain(bullets)}\n\n"
        "Checklist:\n"
        f"{_list_plain(checklist)}\n"
    )
    notes_md = ""
    if notes:
        notes_md = f"\n## Notes\n{_list_plain(notes)}\n"
    return f"{summary_md}\n{variant_md}{notes_md}".strip() + "\n"


def _sanitize_filename_token(token: str) -> str:
    cleaned = re.sub(r"[^A-Za-z0-9]+", "_", token)
    cleaned = cleaned.strip("_")
    return cleaned or "NA"


def build_strategy_filename(cluster: str, company: str | None = None, min_score: int | None = None) -> str:
    parts = [f"strategy_{cluster}"]
    if company:
        parts.append(_sanitize_filename_token(company))
    if min_score is not None:
        parts.append(f"score{min_score}")
    return "_".join(parts) + ".md"


def build_index_filename(company: str | None = None, min_score: int | None = None) -> str:
    parts = ["strategy_INDEX"]
    if company:
        parts.append(_sanitize_filename_token(company))
    if min_score is not None:
        parts.append(f"score{min_score}")
    return "_".join(parts) + ".md"


class StrategyService:
    def __init__(self, db: Session) -> None:
        self.db = db
        self.cache = CacheService()

    async def generate_strategies(
        self,
        *,
        cluster: str | None,
        filter_company: str | None,
        filter_min_score: int | None,
        force: bool = False,
    ) -> dict[str, Any]:
        resume_text, resume_hash = load_resume_payload()
        clusters = self._get_target_clusters(cluster, resume_hash, filter_company, filter_min_score)
        items: list[dict[str, Any]] = []
        for target_cluster in clusters:
            result = await self._build_strategy(
                cluster=target_cluster,
                resume_text=resume_text,
                resume_hash=resume_hash,
                filter_company=filter_company,
                filter_min_score=filter_min_score,
                force=force,
            )
            if result is not None:
                items.append(result)

        index_filename = build_index_filename(filter_company, filter_min_score)
        self._write_index_file(items, index_filename)
        return {
            "items": items,
            "total": len(items),
            "index_filename": index_filename,
        }

    def list_strategies(
        self,
        *,
        cluster: str | None,
        filter_company: str | None,
        filter_min_score: int | None,
        limit: int = 20,
    ) -> dict[str, Any]:
        stmt = select(ResumeStrategy).order_by(ResumeStrategy.generated_at.desc(), ResumeStrategy.id.desc()).limit(limit)
        if cluster and cluster.lower() != "all":
            stmt = stmt.where(ResumeStrategy.cluster == cluster)
        if filter_company:
            stmt = stmt.where(ResumeStrategy.filter_company == filter_company)
        if filter_min_score is not None:
            stmt = stmt.where(ResumeStrategy.filter_min_score == filter_min_score)

        rows = self.db.execute(stmt).scalars().all()
        items = [self._serialize_strategy_row(row) for row in rows]
        return {"items": items, "total": len(items)}

    async def _build_strategy(
        self,
        *,
        cluster: str,
        resume_text: str,
        resume_hash: str,
        filter_company: str | None,
        filter_min_score: int | None,
        force: bool,
    ) -> dict[str, Any] | None:
        resume_variant = map_resume_variant(cluster)
        if resume_variant is None:
            return None

        rows = self._fetch_analysis_rows(cluster, resume_hash, filter_company, filter_min_score)
        output_filename = build_strategy_filename(cluster, filter_company, filter_min_score)
        if not rows:
            section_md = self._render_no_matching_markdown(cluster, filter_company, filter_min_score)
            self._write_markdown(output_filename, section_md)
            return {
                "cluster": cluster,
                "resume_variant": resume_variant,
                "section_md": section_md,
                "used_cache": True,
                "source": "empty",
                "cluster_input_hash": "",
                "summary": {"top_must_haves": [], "top_domains": [], "top_gaps": []},
                "output_filename": output_filename,
                "no_matching": True,
            }

        summary = aggregate_keywords(rows)
        cluster_input_hash = compute_cluster_input_hash(
            cluster=cluster,
            resume_variant=resume_variant,
            resume_hash=resume_hash,
            analysis_version=settings.analysis_version,
            filter_company=filter_company,
            filter_min_score=filter_min_score,
            rows=rows,
        )
        cache_key = self.cache.build_strategy_key(
            cluster,
            resume_hash,
            settings.analysis_version,
            cluster_input_hash,
            filter_company,
            filter_min_score,
        )

        source = "openai"
        cached_payload: dict[str, Any] | None = None
        if not force:
            cached_payload = await self.cache.get_json(cache_key)
            if cached_payload is not None:
                source = "redis"
            else:
                cached_row = self._fetch_cached_strategy(
                    cluster,
                    resume_variant,
                    resume_hash,
                    cluster_input_hash,
                    filter_company,
                    filter_min_score,
                )
                if cached_row is not None:
                    cached_payload = self._serialize_strategy_row(cached_row)
                    cached_payload["section_md"] = cached_row.resume_plan_md
                    source = "database"
                    await self.cache.set_json(cache_key, cached_payload)

        if cached_payload is None:
            plan = self._generate_strategy(cluster, resume_variant, summary, resume_text)
            section_md = render_strategy_markdown(
                cluster=cluster,
                resume_variant=resume_variant,
                top_must_haves=summary["top_must_haves"],
                top_domains=summary["top_domains"],
                top_gaps=summary["top_gaps"],
                positioning_sentence=plan["positioning_sentence"],
                keyword_additions=plan["keyword_additions"],
                bullets=plan["bullets"],
                checklist=plan["actionable_checklist"],
                notes=plan.get("notes") or [],
            )
            row = ResumeStrategy(
                resume_variant=resume_variant,
                cluster=cluster,
                cluster_summary=json.dumps(summary, ensure_ascii=False),
                resume_plan_md=section_md,
                resume_hash=resume_hash,
                analysis_version=settings.analysis_version,
                cluster_input_hash=cluster_input_hash,
                filter_company=filter_company,
                filter_min_score=filter_min_score,
                output_filename=output_filename,
            )
            self.db.add(row)
            self.db.commit()
            self.db.refresh(row)
            cached_payload = self._serialize_strategy_row(row)
            cached_payload["section_md"] = section_md
            await self.cache.set_json(cache_key, cached_payload)

        self._write_markdown(output_filename, cached_payload["section_md"])
        cached_payload.update(
            {
                "used_cache": source in {"redis", "database"},
                "source": source,
                "cluster_input_hash": cluster_input_hash,
                "summary": summary,
                "output_filename": output_filename,
                "no_matching": False,
            }
        )
        return cached_payload

    def _generate_strategy(
        self,
        cluster: str,
        resume_variant: str,
        summary: dict[str, Any],
        resume_text: str,
    ) -> dict[str, Any]:
        client = OpenAIClient()
        result = client.generate_json(
            model=settings.strategist_model,
            system_prompt=load_prompt(),
            user_content=json.dumps(
                {
                    "resume": _truncate_text(resume_text, max_chars=3000),
                    "cluster": cluster,
                    "resume_variant": resume_variant,
                    "top_must_haves": summary["top_must_haves"],
                    "top_domains": summary["top_domains"],
                    "top_gaps": summary["top_gaps"],
                },
                ensure_ascii=False,
            ),
            schema=STRATEGIST_SCHEMA,
            schema_name="resume_strategy",
            max_output_tokens=2400,
        )
        result["resume_variant"] = resume_variant
        return result

    def _fetch_analysis_rows(
        self,
        cluster: str,
        resume_hash: str,
        filter_company: str | None,
        filter_min_score: int | None,
    ) -> list[dict[str, Any]]:
        stmt = (
            select(JobAnalysis, Job.company)
            .join(Job, Job.id == JobAnalysis.job_id)
            .where(
                JobAnalysis.cluster == cluster,
                JobAnalysis.resume_hash == resume_hash,
                JobAnalysis.analysis_version == settings.analysis_version,
            )
        )
        if filter_company:
            stmt = stmt.where(Job.company == filter_company)
        if filter_min_score is not None:
            stmt = stmt.where(JobAnalysis.fit_score >= filter_min_score)
        rows = self.db.execute(stmt).all()
        payloads: list[dict[str, Any]] = []
        for analysis, company in rows:
            payloads.append(
                {
                    "job_id": analysis.job_id,
                    "company": company,
                    "cluster": analysis.cluster,
                    "fit_score": analysis.fit_score,
                    "must_have_keywords": analysis.must_have_keywords,
                    "domain_keywords": analysis.domain_keywords,
                    "top_gaps": analysis.top_gaps,
                    "recommended_resume_version": analysis.recommended_resume_version,
                }
            )
        return payloads

    def _get_target_clusters(
        self,
        cluster: str | None,
        resume_hash: str,
        filter_company: str | None,
        filter_min_score: int | None,
    ) -> list[str]:
        if cluster and cluster.lower() != "all":
            return [cluster]

        stmt = select(JobAnalysis.cluster).distinct().where(
            JobAnalysis.resume_hash == resume_hash,
            JobAnalysis.analysis_version == settings.analysis_version,
        )
        if filter_min_score is not None or filter_company:
            stmt = stmt.join(Job, Job.id == JobAnalysis.job_id)
        if filter_company:
            stmt = stmt.where(Job.company == filter_company)
        if filter_min_score is not None:
            stmt = stmt.where(JobAnalysis.fit_score >= filter_min_score)

        rows = self.db.execute(stmt.order_by(JobAnalysis.cluster.asc())).all()
        return [row[0] for row in rows if map_resume_variant(row[0])]

    def _fetch_cached_strategy(
        self,
        cluster: str,
        resume_variant: str,
        resume_hash: str,
        cluster_input_hash: str,
        filter_company: str | None,
        filter_min_score: int | None,
    ) -> ResumeStrategy | None:
        stmt = select(ResumeStrategy).where(
            ResumeStrategy.cluster == cluster,
            ResumeStrategy.resume_variant == resume_variant,
            ResumeStrategy.resume_hash == resume_hash,
            ResumeStrategy.analysis_version == settings.analysis_version,
            ResumeStrategy.cluster_input_hash == cluster_input_hash,
        )
        if filter_company is None:
            stmt = stmt.where(ResumeStrategy.filter_company.is_(None))
        else:
            stmt = stmt.where(ResumeStrategy.filter_company == filter_company)
        if filter_min_score is None:
            stmt = stmt.where(ResumeStrategy.filter_min_score.is_(None))
        else:
            stmt = stmt.where(ResumeStrategy.filter_min_score == filter_min_score)
        return self.db.execute(
            stmt.order_by(ResumeStrategy.generated_at.desc(), ResumeStrategy.id.desc()).limit(1)
        ).scalar_one_or_none()

    @staticmethod
    def _render_no_matching_markdown(cluster: str, company: str | None, min_score: int | None) -> str:
        filters: list[str] = []
        if company:
            filters.append(f"company={company}")
        if min_score is not None:
            filters.append(f"min_score={min_score}")
        filter_text = ", ".join(filters) if filters else "none"
        return f"## Cluster {cluster}\n\nNo matching jobs for current filters.\n\nFilters: {filter_text}\n"

    @staticmethod
    def _serialize_strategy_row(row: ResumeStrategy) -> dict[str, Any]:
        summary = json.loads(row.cluster_summary)
        return {
            "id": row.id,
            "cluster": row.cluster,
            "resume_variant": row.resume_variant,
            "summary": summary,
            "section_md": row.resume_plan_md,
            "resume_hash": row.resume_hash,
            "analysis_version": row.analysis_version,
            "cluster_input_hash": row.cluster_input_hash,
            "filter_company": row.filter_company,
            "filter_min_score": row.filter_min_score,
            "output_filename": row.output_filename,
            "generated_at": row.generated_at,
        }

    def _write_markdown(self, filename: str, content: str) -> None:
        settings.resolve_output_path(filename).write_text(content, encoding="utf-8")

    def _write_index_file(self, items: list[dict[str, Any]], filename: str) -> None:
        lines = ["# Strategy Index", ""]
        if not items:
            lines.append("No strategies generated.")
        else:
            for item in items:
                lines.append(
                    f"- Cluster {item['cluster']} | {item['resume_variant']} | {item['output_filename']} | source={item['source']}"
                )
        settings.resolve_output_path(filename).write_text("\n".join(lines) + "\n", encoding="utf-8")