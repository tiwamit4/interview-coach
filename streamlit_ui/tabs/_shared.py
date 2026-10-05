"""Streamlit progress indicators and uploaded-file presentation adapters."""

import streamlit as st

import config
from services.extraction import (
    extract_job_description as scrape_job_description,
    extract_resume_bytes,
)
from services.uploads import validate_upload_size


def extract_jd_resume_from_upload(jd_url, uploaded_pdf):
    validate_upload_size(
        len(uploaded_pdf.getbuffer()), config.MAX_RESUME_UPLOAD_BYTES, "resume"
    )
    with st.spinner("Scraping job description..."):
        jd_text = scrape_job_description(jd_url)
    with st.spinner("Extracting resume text..."):
        resume_text = extract_resume_bytes(uploaded_pdf.getbuffer(), uploaded_pdf.name)
    return (jd_text, resume_text)


def build_jd_resume_result(
    jd_url, uploaded_pdf, jd_text, resume_text, payload_key=None, payload=None
):
    result = {
        "jd": {"url": jd_url, "text": jd_text},
        "resume": {"filename": uploaded_pdf.name, "text": resume_text},
        "output_path": None,
    }
    if payload_key:
        result[payload_key] = payload
    return result
