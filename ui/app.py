from __future__ import annotations

import streamlit as st

from helpers import API_BASE_URL, api_request

st.set_page_config(page_title="JD Matcher UI", layout="wide")
st.title("JD Matcher")
st.caption("Job dashboard and strategy workspace for the FastAPI backend")


with st.sidebar:
    st.subheader("API")
    st.code(API_BASE_URL)
    if st.button("Check Health", use_container_width=True):
        try:
            result = api_request("GET", "/health")
            st.success(result.get("status", "ok"))
        except Exception as exc:
            st.error(str(exc))

st.markdown(
    """
### Pages

- Use **Add Job** to save a new job description and optionally run parser immediately.
- Use **Recent Jobs** as the job dashboard for filtering, parser reruns, delete, and applied toggles.
- Use **Strategy** to preview matching jobs and generate markdown strategy output.
"""
)

st.info("Open the pages from the left sidebar.")