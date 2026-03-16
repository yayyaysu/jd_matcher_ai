from app.services.parser_service import compute_priority
from app.services.strategy_service import build_strategy_filename, compute_cluster_input_hash, map_resume_variant


def test_compute_priority_prefers_p0_for_high_fit_low_gap() -> None:
    assert compute_priority(82, "1-3", 1) == "P0"


def test_compute_priority_marks_low_fit_as_p2() -> None:
    assert compute_priority(55, "1-3", 1) == "P2"


def test_build_strategy_filename_includes_filters() -> None:
    assert build_strategy_filename("A", "TSMC", 80) == "strategy_A_TSMC_score80.md"


def test_compute_cluster_input_hash_is_stable() -> None:
    rows = [
        {
            "job_id": "job_1",
            "fit_score": 88,
            "must_have_keywords": '["python", "fastapi"]',
            "domain_keywords": '["semiconductor"]',
            "top_gaps": '["kafka"]',
            "recommended_resume_version": "V1",
        }
    ]
    first = compute_cluster_input_hash(
        cluster="A",
        resume_variant=map_resume_variant("A") or "A_resume",
        resume_hash="resume_hash",
        analysis_version=1,
        filter_company=None,
        filter_min_score=None,
        rows=rows,
    )
    second = compute_cluster_input_hash(
        cluster="A",
        resume_variant=map_resume_variant("A") or "A_resume",
        resume_hash="resume_hash",
        analysis_version=1,
        filter_company=None,
        filter_min_score=None,
        rows=rows,
    )
    assert first == second