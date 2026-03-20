from __future__ import annotations

import asyncio
from collections.abc import Generator

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from app.api.deps import get_db
from app.db.base import Base
from app.db.models.job_analysis import JobAnalysis
from app.db.models.jobs import Job
from app.db.models.workflow import Workflow
from app.main import app
from app.services.job_service import JobService
from app.services.parser_service import ParserService


@pytest.fixture
def db_session() -> Generator[Session, None, None]:
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    Base.metadata.create_all(bind=engine)

    session = TestingSessionLocal()
    try:
        yield session
    finally:
        session.close()
        Base.metadata.drop_all(bind=engine)


def test_delete_job_removes_all_analysis_versions(db_session: Session) -> None:
    job = Job(id="job_delete", company="TSMC", role_title="Backend Engineer", jd_text="x" * 40)
    workflow = Workflow(
        job_id=job.id,
        priority="P1",
        status="Backlog",
        next_action="Run parser analysis",
        applied=False,
    )
    analysis_v1 = JobAnalysis(
        job_id=job.id,
        analysis_version=1,
        cluster="A",
        fit_score=80,
        years_required="1-3",
        cluster_reason="Strong backend match",
        must_have_keywords='["python"]',
        nice_to_have_keywords='[]',
        domain_keywords='[]',
        top_gaps='[]',
        screening_risks='[]',
        recommended_resume_version="V1",
        resume_tweak_suggestions='[]',
        resume_hash="resume_a",
    )
    analysis_v2 = JobAnalysis(
        job_id=job.id,
        analysis_version=2,
        cluster="A",
        fit_score=82,
        years_required="1-3",
        cluster_reason="Updated backend match",
        must_have_keywords='["python", "fastapi"]',
        nice_to_have_keywords='[]',
        domain_keywords='[]',
        top_gaps='[]',
        screening_risks='[]',
        recommended_resume_version="V2",
        resume_tweak_suggestions='[]',
        resume_hash="resume_b",
    )
    db_session.add_all([job, workflow, analysis_v1, analysis_v2])
    db_session.commit()

    deleted = JobService(db_session).delete_job(job.id)

    remaining_analyses = db_session.execute(
        select(JobAnalysis).where(JobAnalysis.job_id == job.id)
    ).scalars().all()

    assert deleted is True
    assert db_session.get(Job, job.id) is None
    assert db_session.get(Workflow, job.id) is None
    assert remaining_analyses == []


def test_parser_analyze_job_returns_token_usage(db_session: Session, monkeypatch: pytest.MonkeyPatch) -> None:
    job = Job(id="job_tokens", company=None, role_title=None, jd_text="x" * 60)
    db_session.add(job)
    db_session.commit()

    class DummyCache:
        @staticmethod
        def build_parser_key(job_id: str, resume_hash: str, analysis_version: int) -> str:
            return f"parser_cache:{job_id}:{resume_hash}:{analysis_version}"

        async def get_json(self, key: str) -> dict | None:
            return None

        async def set_json(self, key: str, payload: dict, ttl_seconds: int | None = None) -> None:
            return None

    parser_payload = {
        "company": "NVIDIA",
        "role_title": "Platform Engineer",
        "cluster": "A",
        "fit_score": 88,
        "cluster_reason": "Good backend fit",
        "must_have_keywords": ["python", "fastapi"],
        "nice_to_have_keywords": ["kafka"],
        "domain_keywords": ["ai"],
        "years_required": "1-3",
        "gap_keywords": ["kafka"],
        "top_gaps": ["kafka"],
        "screening_risks": [],
        "recommended_resume_version": "V2",
        "resume_tweak_suggestions": ["Highlight APIs"],
    }

    monkeypatch.setattr("app.services.parser_service.load_resume_payload", lambda: ("resume text", "resume_hash"))
    monkeypatch.setattr(
        ParserService,
        "_generate_analysis",
        lambda self, jd_text, resume_text: (
            parser_payload,
            {"input_tokens": 120, "output_tokens": 45, "total_tokens": 165},
        ),
    )

    service = ParserService(db_session)
    service.cache = DummyCache()

    result = asyncio.run(service.analyze_job(job.id, force=True))

    assert result["token_usage"] == {"input_tokens": 120, "output_tokens": 45, "total_tokens": 165}
    assert result["company"] == "NVIDIA"


def test_add_job_response_includes_token_usage(db_session: Session, monkeypatch: pytest.MonkeyPatch) -> None:
    def override_get_db() -> Generator[Session, None, None]:
        yield db_session

    async def fake_analyze_job(self, job_id: str, force: bool = False) -> dict:
        return {
            "token_usage": {"input_tokens": 90, "output_tokens": 20, "total_tokens": 110}
        }

    app.dependency_overrides[get_db] = override_get_db
    monkeypatch.setattr(ParserService, "analyze_job", fake_analyze_job)

    try:
        with TestClient(app) as client:
            response = client.post(
                "/jobs/add",
                json={
                    "jd_text": "Senior backend engineer with Python, FastAPI, MySQL and Redis experience.",
                    "company": "TSMC",
                    "role_title": "Backend Engineer",
                    "auto_analyze": True,
                },
            )
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 200
    assert response.json()["token_usage"] == {"input_tokens": 90, "output_tokens": 20, "total_tokens": 110}