from __future__ import annotations

import sys
from pathlib import Path

import httpx
import streamlit as st

UI_ROOT = Path(__file__).resolve().parents[1]
if str(UI_ROOT) not in sys.path:
    sys.path.insert(0, str(UI_ROOT))

from helpers import api_request, refresh_data

st.set_page_config(page_title="Add Job", layout="wide")
st.title("Add Job")
st.caption("Paste a job description, save it, and optionally run parser immediately.")

meta_col1, meta_col2 = st.columns(2)
company = meta_col1.text_input("Company")
role_title = meta_col2.text_input("Role Title")
url = meta_col1.text_input("Job URL")
notes = meta_col2.text_input("Notes")
auto_analyze = st.checkbox("Analyze immediately after adding", value=True)
jd_text = st.text_area("Job Description", height=360, placeholder="Paste the full JD here...")

if st.button("Add Job", type="primary", use_container_width=True):
    if not jd_text.strip():
        st.error("Please paste a job description first.")
    else:
        try:
            result = api_request(
                "POST",
                "/jobs/add",
                json={
                    "jd_text": jd_text.strip(),
                    "url": url or None,
                    "company": company or None,
                    "role_title": role_title or None,
                    "notes": notes or None,
                    "auto_analyze": auto_analyze,
                },
            )
            refresh_data()
            st.success("Job added successfully.")
            job = result.get("job", {})
            analysis = job.get("analysis") or {}
            workflow = job.get("workflow") or {}
            summary_col1, summary_col2, summary_col3 = st.columns(3)
            summary_col1.metric("Company", job.get("company") or "-")
            summary_col2.metric("Cluster", analysis.get("cluster") or "Pending")
            summary_col3.metric("Priority", workflow.get("priority") or "Pending")
            st.subheader("Saved Job")
            st.write(job.get("role_title") or "-")
            st.write(job.get("url") or "")
            if analysis:
                st.markdown("**Parser summary**")
                st.write(f"Fit Score: {analysis.get('fit_score', '-')}")
                st.write(f"Recommended Resume Version: {analysis.get('recommended_resume_version', '-')}")
                st.write("Top Gaps")
                st.write(analysis.get("top_gaps", []))
        except httpx.HTTPStatusError as exc:
            st.error(f"API returned {exc.response.status_code}: {exc.response.text}")
        except Exception as exc:
            st.error(f"Request failed: {exc}")