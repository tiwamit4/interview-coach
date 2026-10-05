"""Interview prep tab rendering."""

from pathlib import Path

import streamlit as st

import config
from config import PREP_PATH
from prompts.prompt import INTERVIEW_PREP_PROMPT
from streamlit_ui.components import render_interview_prep
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


def render_interview_prep_tab():
    st.header("Tailored Interview Prep")
    jd_url = st.text_input(
        "Job description URL",
        value="https://careers.qualcomm.com/careers/job/446718764455",
        key="prep_jd_url",
    )
    uploaded_pdf = st.file_uploader(
        "Upload resume PDF",
        type=["pdf"],
        key="prep_resume_pdf",
        max_upload_size=config.MAX_RESUME_UPLOAD_MB,
    )
    save_output = st.checkbox(
        f"Save prep to {PREP_PATH}", value=True, key="save_interview_prep"
    )
    if st.button("Generate Interview Prep", type="primary"):
        if not jd_url or not uploaded_pdf:
            st.warning("Enter a JD URL and upload a resume PDF.")
            return
        try:
            jd_text, resume_text = extract_jd_resume_from_upload(jd_url, uploaded_pdf)
            with st.spinner("Generating tailored interview prep..."):
                prep = run_json_prompt(
                    INTERVIEW_PREP_PROMPT, resume_text=resume_text, jd_text=jd_text
                )
            result = build_jd_resume_result(
                jd_url, uploaded_pdf, jd_text, resume_text, "interview_prep", prep
            )
            if save_output:
                result = save_result(
                    PREP_PATH,
                    f"prep_{safe_filename(Path(uploaded_pdf.name).stem)}_{safe_filename_from_url(jd_url)}.json",
                    result,
                )
            save_history(
                "interview_prep",
                f"{uploaded_pdf.name} + {safe_filename_from_url(jd_url)}",
                result,
            )
            render_interview_prep(result)
        except Exception as exc:
            show_error(exc, operation="interview_prep")
