"""Extraction tab rendering."""

from pathlib import Path

import streamlit as st

import config
from config import JSON_PATH
from services.extraction import (
    extract_job_description as scrape_job_description,
    extract_resume_bytes,
)
from streamlit_ui.components import render_json_extraction
from streamlit_ui.helpers import (
    safe_filename,
    safe_filename_from_url,
    show_error,
    write_json_file,
)


def render_jd_resume_json_tab():
    st.header("Extract JD + Resume JSON")
    st.caption(
        "Extract text from a job description URL and a resume PDF, then save both in one JSON file."
    )
    jd_url = st.text_input(
        "Job description URL",
        value="https://careers.qualcomm.com/careers/job/446718764455",
        key="json_jd_url",
    )
    uploaded_pdf = st.file_uploader(
        "Upload resume PDF",
        type=["pdf"],
        key="json_resume_pdf",
        max_upload_size=config.MAX_RESUME_UPLOAD_MB,
    )
    save_json = st.checkbox(
        f"Save JSON to {JSON_PATH}", value=True, key="save_jd_resume_json"
    )
    extract_json = st.button("Extract to JSON", type="primary")
    if extract_json and jd_url and uploaded_pdf:
        try:
            with st.spinner("Scraping job description..."):
                jd_text = scrape_job_description(jd_url)
            with st.spinner("Extracting resume text..."):
                resume_text = extract_resume_bytes(
                    uploaded_pdf.getbuffer(), uploaded_pdf.name
                )
            resume_name = safe_filename(Path(uploaded_pdf.name).stem)
            jd_name = safe_filename_from_url(jd_url)
            result = {
                "jd": {"url": jd_url, "text": jd_text},
                "resume": {"filename": uploaded_pdf.name, "text": resume_text},
                "output_path": None,
            }
            if save_json:
                output_filename = f"extracted_{resume_name}_{jd_name}.json"
                output_path = write_json_file(JSON_PATH, output_filename, result)
                result["output_path"] = str(output_path)
            render_json_extraction(result)
        except Exception as exc:
            show_error(exc, operation="extraction")
    elif extract_json:
        if not jd_url:
            st.warning("Enter a job description URL.")
        elif not uploaded_pdf:
            st.warning("Upload a resume PDF.")
