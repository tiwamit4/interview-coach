"""Resume optimizer tab rendering."""

from pathlib import Path

import streamlit as st

import config
from config import RESUME_IMPROVEMENTS_PATH
from prompts.prompt import RESUME_IMPROVEMENT_PROMPT
from streamlit_ui.components import render_resume_improvements
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


def render_resume_improvement_tab():
    st.header("Resume Improvement Suggestions")
    jd_url = st.text_input(
        "Job description URL",
        value="https://careers.qualcomm.com/careers/job/446718764455",
        key="improve_jd_url",
    )
    uploaded_pdf = st.file_uploader(
        "Upload resume PDF",
        type=["pdf"],
        key="improve_resume_pdf",
        max_upload_size=config.MAX_RESUME_UPLOAD_MB,
    )
    save_output = st.checkbox(
        f"Save improvements to {RESUME_IMPROVEMENTS_PATH}",
        value=True,
        key="save_resume_improvements",
    )
    if st.button("Improve Resume for JD", type="primary"):
        if not jd_url or not uploaded_pdf:
            st.warning("Enter a JD URL and upload a resume PDF.")
            return
        try:
            jd_text, resume_text = extract_jd_resume_from_upload(jd_url, uploaded_pdf)
            with st.spinner("Generating resume improvements..."):
                improvements = run_json_prompt(
                    RESUME_IMPROVEMENT_PROMPT, resume_text=resume_text, jd_text=jd_text
                )
            result = build_jd_resume_result(
                jd_url,
                uploaded_pdf,
                jd_text,
                resume_text,
                "resume_improvements",
                improvements,
            )
            if save_output:
                result = save_result(
                    RESUME_IMPROVEMENTS_PATH,
                    f"resume_improvements_{safe_filename(Path(uploaded_pdf.name).stem)}_{safe_filename_from_url(jd_url)}.json",
                    result,
                )
            save_history(
                "resume_improvement",
                f"{uploaded_pdf.name} + {safe_filename_from_url(jd_url)}",
                result,
            )
            render_resume_improvements(result)
        except Exception as exc:
            show_error(exc, operation="resume_optimizer")
