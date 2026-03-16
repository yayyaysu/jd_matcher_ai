from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

from app.db.session import SessionLocal
from app.services.export_service import ExportService
from app.services.job_service import JobService
from app.services.parser_service import ParserService
from app.services.strategy_service import StrategyService


def _read_jd_text(args: argparse.Namespace) -> str:
    if args.jd_text:
        return args.jd_text.strip()
    if args.file:
        return Path(args.file).read_text(encoding="utf-8").strip()
    raise ValueError("Provide either --jd-text or --file")


def _print_json(payload: Any) -> None:
    print(json.dumps(payload, ensure_ascii=False, indent=2, default=str))


async def _run_async_command(args: argparse.Namespace) -> int:
    with SessionLocal() as db:
        job_service = JobService(db)

        if args.command == "add-jd":
            job = job_service.add_job(
                jd_text=_read_jd_text(args),
                url=args.url,
                company=args.company,
                role_title=args.role_title,
                notes=args.notes,
            )
            if args.auto_analyze:
                parser_service = ParserService(db)
                await parser_service.analyze_job(job.id)
            _print_json(job_service.get_job_snapshot(job.id))
            return 0

        if args.command == "delete-jd":
            deleted = job_service.delete_job(args.job_id)
            _print_json({"deleted": deleted, "job_id": args.job_id})
            return 0 if deleted else 1

        if args.command == "list-jobs":
            _print_json(
                job_service.list_jobs(
                    cluster=args.cluster,
                    status=args.status,
                    priority=args.priority,
                    company=args.company,
                    applied=args.applied,
                    min_score=args.min_score,
                    limit=args.limit,
                )
            )
            return 0

        if args.command == "run-parser":
            parser_service = ParserService(db)
            job_ids = args.job_ids if args.job_ids else None
            _print_json(await parser_service.analyze_jobs(job_ids=job_ids, force=args.force))
            return 0

        if args.command == "run-strategist":
            strategy_service = StrategyService(db)
            _print_json(
                await strategy_service.generate_strategies(
                    cluster=args.cluster,
                    filter_company=args.company,
                    filter_min_score=args.min_score,
                    force=args.force,
                )
            )
            return 0

        if args.command == "export":
            export_service = ExportService(db)
            _print_json(export_service.export_all())
            return 0

    return 1


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="JD Matcher v2 CLI")
    subparsers = parser.add_subparsers(dest="command", required=True)

    add_job = subparsers.add_parser("add-jd", help="Add a job description")
    add_job.add_argument("--jd-text")
    add_job.add_argument("--file")
    add_job.add_argument("--url")
    add_job.add_argument("--company")
    add_job.add_argument("--role-title")
    add_job.add_argument("--notes")
    add_job.add_argument("--auto-analyze", action="store_true")

    delete_job = subparsers.add_parser("delete-jd", help="Delete a job")
    delete_job.add_argument("job_id")

    list_jobs = subparsers.add_parser("list-jobs", help="List jobs")
    list_jobs.add_argument("--cluster")
    list_jobs.add_argument("--status")
    list_jobs.add_argument("--priority")
    list_jobs.add_argument("--company")
    list_jobs.add_argument("--applied", action=argparse.BooleanOptionalAction, default=None)
    list_jobs.add_argument("--min-score", type=int)
    list_jobs.add_argument("--limit", type=int, default=20)

    run_parser = subparsers.add_parser("run-parser", help="Run parser analysis")
    run_parser.add_argument("job_ids", nargs="*")
    run_parser.add_argument("--force", action="store_true")

    run_strategist = subparsers.add_parser("run-strategist", help="Generate strategy markdown")
    run_strategist.add_argument("--cluster", default="all")
    run_strategist.add_argument("--company")
    run_strategist.add_argument("--min-score", type=int)
    run_strategist.add_argument("--force", action="store_true")

    subparsers.add_parser("export", help="Export CSV and markdown outputs")
    return parser


def main() -> int:
    import asyncio

    parser = build_parser()
    args = parser.parse_args()
    return asyncio.run(_run_async_command(args))


if __name__ == "__main__":
    raise SystemExit(main())