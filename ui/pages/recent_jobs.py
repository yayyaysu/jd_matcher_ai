from __future__ import annotations

import sys
from pathlib import Path

import httpx
import streamlit as st

UI_ROOT = Path(__file__).resolve().parents[1]
if str(UI_ROOT) not in sys.path:
    sys.path.insert(0, str(UI_ROOT))

from helpers import MAX_JOB_LIMIT, api_request, fetch_companies, fetch_jobs, get_public_job_row, refresh_data

st.set_page_config(page_title="Recent Jobs", layout="wide")
st.title("Recent Jobs")
st.caption("Job dashboard for browsing, filtering, and taking action on saved jobs.")

company_options = ["All", *fetch_companies()]

filter_col1, filter_col2, filter_col3, filter_col4 = st.columns(4)
selected_company = filter_col1.selectbox("Company", company_options)
selected_cluster = filter_col2.selectbox("Cluster", ["All", "A", "B", "C1", "C2"])
selected_score = filter_col3.slider("Minimum Fit Score", min_value=0, max_value=100, value=0)
selected_applied = filter_col4.selectbox("Applied Status", ["All", "Applied", "Not Applied"])

try:
    jobs = fetch_jobs(
        company=selected_company,
        cluster=selected_cluster,
        min_score=selected_score,
        applied_status=selected_applied,
        limit=MAX_JOB_LIMIT,
    )
except httpx.HTTPStatusError as exc:
    st.error(f"API returned {exc.response.status_code}: {exc.response.text}")
    jobs = []
except Exception as exc:
    st.error(f"Request failed: {exc}")
    jobs = []

summary_col1, summary_col2, summary_col3 = st.columns(3)
summary_col1.metric("Visible Jobs", len(jobs))
summary_col2.metric("Applied", sum(1 for job in jobs if (job.get("workflow") or {}).get("applied")))
summary_col3.metric("Not Applied", sum(1 for job in jobs if not (job.get("workflow") or {}).get("applied")))

if jobs:
    st.dataframe([get_public_job_row(job) for job in jobs], use_container_width=True, hide_index=True)
else:
    st.info("No jobs match current filters.")

st.divider()
st.subheader("Job Actions")

for index, job in enumerate(jobs):
    analysis = job.get("analysis") or {}
    workflow = job.get("workflow") or {}
    title = " | ".join(
        [
            job.get("company") or "Unknown Company",
            job.get("role_title") or "Unknown Role",
            f"Cluster {analysis.get('cluster') or '-'}",
            f"Fit {analysis.get('fit_score') if analysis.get('fit_score') is not None else '-'}",
        ]
    )
    with st.container(border=True):
        head_col1, head_col2 = st.columns([3, 2])
        head_col1.markdown(f"**{title}**")
        head_col2.write(
            f"Priority: {workflow.get('priority') or '-'} | Applied: {'Yes' if workflow.get('applied') else 'No'}"
        )

        action_col1, action_col2, action_col3 = st.columns(3)
        if action_col1.button("Run Parser", key=f"run-parser-{job['job_id']}-{index}", use_container_width=True):
            try:
                api_request("POST", "/jobs/analyze", json={"job_id": job["job_id"], "force": True})
                st.success("Parser completed.")
                refresh_data()
            except httpx.HTTPStatusError as exc:
                st.error(f"API returned {exc.response.status_code}: {exc.response.text}")
            except Exception as exc:
                st.error(f"Request failed: {exc}")

        toggle_label = "Mark Not Applied" if workflow.get("applied") else "Mark Applied"
        if action_col2.button(toggle_label, key=f"toggle-applied-{job['job_id']}-{index}", use_container_width=True):
            try:
                api_request(
                    "PATCH",
                    f"/jobs/{job['job_id']}/workflow",
                    json={"applied": not bool(workflow.get("applied"))},
                )
                st.success("Applied status updated.")
                refresh_data()
            except httpx.HTTPStatusError as exc:
                st.error(f"API returned {exc.response.status_code}: {exc.response.text}")
            except Exception as exc:
                st.error(f"Request failed: {exc}")

        confirm_key = f"confirm-delete-{job['job_id']}"
        if action_col3.button("Delete Job", key=f"delete-job-{job['job_id']}-{index}", use_container_width=True):
            st.session_state[confirm_key] = True

        if st.session_state.get(confirm_key):
            st.warning("Delete this job and its related analysis/workflow records?")
            confirm_col1, confirm_col2 = st.columns(2)
            if confirm_col1.button("Confirm Delete", key=f"confirm-delete-action-{job['job_id']}-{index}", use_container_width=True):
                try:
                    api_request("DELETE", f"/jobs/{job['job_id']}")
                    st.session_state.pop(confirm_key, None)
                    st.success("Job deleted.")
                    refresh_data()
                except httpx.HTTPStatusError as exc:
                    st.error(f"API returned {exc.response.status_code}: {exc.response.text}")
                except Exception as exc:
                    st.error(f"Request failed: {exc}")
            if confirm_col2.button("Cancel", key=f"cancel-delete-{job['job_id']}-{index}", use_container_width=True):
                st.session_state.pop(confirm_key, None)
                st.rerun()

        detail_col1, detail_col2 = st.columns(2)
        detail_col1.markdown("**Summary**")
        detail_col1.write(f"Created: {job.get('created_at', '-')}")
        detail_col1.write(f"Company: {job.get('company') or '-'}")
        detail_col1.write(f"Role Title: {job.get('role_title') or '-'}")
        detail_col1.write(f"Applied: {'Yes' if workflow.get('applied') else 'No'}")
        detail_col2.markdown("**Analysis**")
        detail_col2.write(f"Cluster: {analysis.get('cluster') or '-'}")
        detail_col2.write(f"Fit Score: {analysis.get('fit_score') if analysis.get('fit_score') is not None else '-'}")
        detail_col2.write(f"Priority: {workflow.get('priority') or '-'}")

        if analysis:
            keyword_col1, keyword_col2 = st.columns(2)
            keyword_col1.markdown("**Must-have Keywords**")
            keyword_col1.write(analysis.get("must_have_keywords", []))
            keyword_col2.markdown("**Top Gaps**")
            keyword_col2.write(analysis.get("top_gaps", []))

        if job.get("url"):
            st.caption(job["url"])