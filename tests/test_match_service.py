from app.services.match_service import analyze_jd_text


def test_backend_jd_prefers_backend_cluster() -> None:
    result = analyze_jd_text(
        "We need a backend engineer with Python, FastAPI, MySQL, Redis, Docker, SQL and microservices experience."
    )

    assert result["cluster"] == "backend engineer"
    assert result["score"] > 60
    assert "python" in result["matched_keywords"]
    assert "mysql" in result["matched_keywords"]


def test_data_jd_prefers_data_engineer_cluster() -> None:
    result = analyze_jd_text(
        "Looking for a data engineer with Python, SQL, Airflow, Spark, Kafka and ETL pipeline experience."
    )

    assert result["cluster"] == "data engineer"
    assert result["score"] > 60
    assert "airflow" in result["matched_keywords"]