"""Analysis tab rendering."""

from pathlib import Path

import streamlit as st

import config
from config import ANALYSIS_PATH
from prompts.prompt import (
    INTERVIEW_PREP_PROMPT,
    MATCH_SCORE_PROMPT,
    RESUME_IMPROVEMENT_PROMPT,
)
from streamlit_ui.components import (
    render_interview_prep,
    render_match_analysis,
    render_resume_improvements,
)
from streamlit_ui.helpers import (
    run_json_prompt,
    safe_filename,
    safe_filename_from_url,
    save_result,
    show_error,
)
from streamlit_ui.tabs._shared import (
    build_jd_resume_result,
    extract_jd_resume_from_upload,
)
from utils.history import save_history


def render_combined_analysis_tab():
    st.header("Full JD + Resume Analysis")
    st.caption(
        "Runs match score, interview prep, and resume improvement in one workflow."
    )
    jd_url = st.text_input(
        "Job description URL",
        value="https://careers.qualcomm.com/careers/job/446718764455",
        key="analysis_jd_url",
    )
    uploaded_pdf = st.file_uploader(
        "Upload resume PDF",
        type=["pdf"],
        key="analysis_resume_pdf",
        max_upload_size=config.MAX_RESUME_UPLOAD_MB,
    )
    save_output = st.checkbox(
        f"Save full analysis to {ANALYSIS_PATH}", value=True, key="save_full_analysis"
    )
    if st.button("Run Full Analysis", type="primary"):
        if not jd_url or not uploaded_pdf:
            st.warning("Enter a JD URL and upload a resume PDF.")
            return
        try:
            jd_text, resume_text = extract_jd_resume_from_upload(jd_url, uploaded_pdf)
            with st.spinner("Analyzing match..."):
                match_analysis = run_json_prompt(
                    MATCH_SCORE_PROMPT, resume_text=resume_text, jd_text=jd_text
                )
            with st.spinner("Generating interview prep..."):
                prep = run_json_prompt(
                    INTERVIEW_PREP_PROMPT, resume_text=resume_text, jd_text=jd_text
                )
            with st.spinner("Generating resume improvements..."):
                improvements = run_json_prompt(
                    RESUME_IMPROVEMENT_PROMPT, resume_text=resume_text, jd_text=jd_text
                )
            result = build_jd_resume_result(jd_url, uploaded_pdf, jd_text, resume_text)
            result["match_analysis"] = match_analysis
            result["interview_prep"] = prep
            result["resume_improvements"] = improvements
            if save_output:
                result = save_result(
                    ANALYSIS_PATH,
                    f"analysis_{safe_filename(Path(uploaded_pdf.name).stem)}_{safe_filename_from_url(jd_url)}.json",
                    result,
                )
            save_history(
                "jd_resume_analysis",
                f"{uploaded_pdf.name} + {safe_filename_from_url(jd_url)}",
                result,
            )
            render_match_analysis(result)
            render_interview_prep(result)
            render_resume_improvements(result)
        except Exception as exc:
            show_error(exc, operation="analysis")
