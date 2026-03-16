from __future__ import annotations

import os
from datetime import datetime
from typing import Any

import httpx
import streamlit as st

API_BASE_URL = os.getenv("API_BASE_URL", "http://localhost:8000").rstrip("/")
MAX_JOB_LIMIT = 200


def api_request(method: str, path: str, **kwargs: Any) -> dict[str, Any]:
    with httpx.Client(timeout=60.0) as client:
        response = client.request(method, f"{API_BASE_URL}{path}", **kwargs)
    response.raise_for_status()
    return response.json()


@st.cache_data(ttl=20, show_spinner=False)
def fetch_companies() -> list[str]:
    try:
        payload = api_request("GET", "/jobs", params={"limit": MAX_JOB_LIMIT})
    except Exception:
        return []
    companies = sorted(
        {
            str(item.get("company")).strip()
            for item in payload.get("items", [])
            if item.get("company") and str(item.get("company")).strip()
        }
    )
    return companies


def build_job_filters(
    *,
    company: str,
    cluster: str,
    min_score: int,
    applied_status: str,
    limit: int = MAX_JOB_LIMIT,
) -> dict[str, Any]:
    params: dict[str, Any] = {"limit": min(limit, MAX_JOB_LIMIT)}
    if company != "All":
        params["company"] = company
    if cluster != "All":
        params["cluster"] = cluster
    if min_score > 0:
        params["min_score"] = min_score
    if applied_status == "Applied":
        params["applied"] = True
    elif applied_status == "Not Applied":
        params["applied"] = False
    return params


def fetch_jobs(
    *,
    company: str = "All",
    cluster: str = "All",
    min_score: int = 0,
    applied_status: str = "All",
    limit: int = MAX_JOB_LIMIT,
) -> list[dict[str, Any]]:
    params = build_job_filters(
        company=company,
        cluster=cluster,
        min_score=min_score,
        applied_status=applied_status,
        limit=limit,
    )
    payload = api_request("GET", "/jobs", params=params)
    return payload.get("items", [])


def refresh_data() -> None:
    fetch_companies.clear()
    st.rerun()


def format_created_at(value: str | None) -> str:
    if not value:
        return ""
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00")).strftime("%Y-%m-%d")
    except Exception:
        return str(value)


def get_public_job_row(job: dict[str, Any]) -> dict[str, Any]:
    analysis = job.get("analysis") or {}
    workflow = job.get("workflow") or {}
    return {
        "Company": job.get("company") or "-",
        "Role Title": job.get("role_title") or "-",
        "Cluster": analysis.get("cluster") or "-",
        "Fit Score": analysis.get("fit_score") if analysis.get("fit_score") is not None else "-",
        "Priority": workflow.get("priority") or "-",
        "Applied": "Yes" if workflow.get("applied") else "No",
        "Created Date": format_created_at(job.get("created_at")),
    }


def get_strategy_payload(cluster: str, company: str, min_score: int, applied_status: str) -> dict[str, Any]:
    payload: dict[str, Any] = {
        "cluster": "all" if cluster == "All" else cluster,
        "filter_company": None if company == "All" else company,
        "filter_min_score": min_score,
        "applied": applied_status,
    }
    return payload