"""Applications tab rendering."""

from pathlib import Path

import streamlit as st

import config
from config import APPLICATIONS_PATH
from prompts.prompt import COVER_LETTER_PROMPT
from streamlit_ui.components import render_cover_letter
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


def render_cover_letter_tab():
    st.header("Cover Letter Generator")
    jd_url = st.text_input(
        "Job description URL",
        value="https://careers.qualcomm.com/careers/job/446718764455",
        key="cover_jd_url",
    )
    uploaded_pdf = st.file_uploader(
        "Upload resume PDF",
        type=["pdf"],
        key="cover_resume_pdf",
        max_upload_size=config.MAX_RESUME_UPLOAD_MB,
    )
    save_output = st.checkbox(
        f"Save messages to {APPLICATIONS_PATH}", value=True, key="save_cover_letter"
    )
    if st.button("Generate Application Messages", type="primary"):
        if not jd_url or not uploaded_pdf:
            st.warning("Enter a JD URL and upload a resume PDF.")
            return
        try:
            jd_text, resume_text = extract_jd_resume_from_upload(jd_url, uploaded_pdf)
            with st.spinner("Writing tailored application messages..."):
                messages = run_json_prompt(
                    COVER_LETTER_PROMPT, resume_text=resume_text, jd_text=jd_text
                )
            result = build_jd_resume_result(
                jd_url,
                uploaded_pdf,
                jd_text,
                resume_text,
                "application_messages",
                messages,
            )
            if save_output:
                result = save_result(
                    APPLICATIONS_PATH,
                    f"application_{safe_filename(Path(uploaded_pdf.name).stem)}_{safe_filename_from_url(jd_url)}.json",
                    result,
                )
            save_history(
                "cover_letter",
                f"{uploaded_pdf.name} + {safe_filename_from_url(jd_url)}",
                result,
            )
            render_cover_letter(result)
        except Exception as exc:
            show_error(exc, operation="applications")
