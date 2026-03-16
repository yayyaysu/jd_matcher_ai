from __future__ import annotations

import sys
from pathlib import Path

import httpx
import streamlit as st

UI_ROOT = Path(__file__).resolve().parents[1]
if str(UI_ROOT) not in sys.path:
    sys.path.insert(0, str(UI_ROOT))

from helpers import MAX_JOB_LIMIT, api_request, fetch_companies, fetch_jobs, get_strategy_payload

st.set_page_config(page_title="Strategy", layout="wide")
st.title("Strategy")
st.caption("Generate resume strategy from filtered jobs.")

company_options = ["All", *fetch_companies()]

filter_col1, filter_col2, filter_col3, filter_col4 = st.columns(4)
selected_cluster = filter_col1.selectbox("Cluster", ["All", "A", "B", "C1", "C2"])
selected_company = filter_col2.selectbox("Company", company_options)
selected_score = filter_col3.slider("Minimum Score", min_value=0, max_value=100, value=70)
selected_applied = filter_col4.selectbox("Applied Status", ["All", "Applied", "Not Applied"])

preview_jobs: list[dict] = []
preview_error: str | None = None
try:
    preview_jobs = fetch_jobs(
        company=selected_company,
        cluster=selected_cluster,
        min_score=selected_score,
        applied_status=selected_applied,
        limit=MAX_JOB_LIMIT,
    )
except httpx.HTTPStatusError as exc:
    preview_error = f"API returned {exc.response.status_code}: {exc.response.text}"
except Exception as exc:
    preview_error = f"Request failed: {exc}"

summary_col1, summary_col2 = st.columns([2, 3])
summary_col1.metric("Matching Jobs", len(preview_jobs))
if preview_error:
    summary_col2.error(preview_error)
elif not preview_jobs:
    summary_col2.info("No jobs match current filters.")
else:
    summary_col2.caption("Strategy generation will use the current cluster, company, and minimum score filters.")

if selected_applied != "All":
    st.warning(
        "Applied Status is currently used for job preview in the UI. The existing strategy API does not enforce this filter server-side."
    )

generate_payload = get_strategy_payload(
    cluster=selected_cluster,
    company=selected_company,
    min_score=selected_score,
    applied_status=selected_applied,
)

action_col1, action_col2 = st.columns(2)
if action_col1.button("Generate Strategy", type="primary", use_container_width=True):
    try:
        result = api_request("POST", "/strategy/generate", json=generate_payload)
        items = result.get("items", [])
        if not items:
            st.info("No jobs match current filters.")
        else:
            st.success(f"Generated {len(items)} strategy result(s).")
            st.caption(f"Index file: {result.get('index_filename')}")
            for item in items:
                with st.container(border=True):
                    header_col1, header_col2, header_col3 = st.columns(3)
                    header_col1.metric("Cluster", item.get("cluster", "-"))
                    header_col2.metric("Resume Variant", item.get("resume_variant", "-"))
                    header_col3.metric("Source", item.get("source", "-"))
                    st.markdown(item.get("section_md", ""))
    except httpx.HTTPStatusError as exc:
        st.error(f"API returned {exc.response.status_code}: {exc.response.text}")
    except Exception as exc:
        st.error(f"Request failed: {exc}")

if action_col2.button("Load Existing Strategies", use_container_width=True):
    try:
        params = {
            "cluster": None if selected_cluster == "All" else selected_cluster,
            "filter_company": None if selected_company == "All" else selected_company,
            "filter_min_score": selected_score,
            "limit": 20,
        }
        params = {key: value for key, value in params.items() if value is not None}
        result = api_request("GET", "/strategy", params=params)
        items = result.get("items", [])
        if not items:
            st.info("No jobs match current filters.")
        else:
            for item in items:
                with st.container(border=True):
                    st.markdown(
                        f"**Cluster {item.get('cluster', '-')} | {item.get('resume_variant', '-')} | {item.get('generated_at', '-') }**"
                    )
                    st.markdown(item.get("section_md", ""))
    except httpx.HTTPStatusError as exc:
        st.error(f"API returned {exc.response.status_code}: {exc.response.text}")
    except Exception as exc:
        st.error(f"Request failed: {exc}")

if preview_jobs:
    st.divider()
    st.subheader("Jobs Included in Preview")
    for job in preview_jobs[:20]:
        analysis = job.get("analysis") or {}
        workflow = job.get("workflow") or {}
        st.write(
            f"- {job.get('company') or '-'} | {job.get('role_title') or '-'} | "
            f"Cluster {analysis.get('cluster') or '-'} | Fit {analysis.get('fit_score') if analysis.get('fit_score') is not None else '-'} | "
            f"Applied {'Yes' if workflow.get('applied') else 'No'}"
        )