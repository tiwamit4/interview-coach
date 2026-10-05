"""Match tab rendering."""

from pathlib import Path

import streamlit as st

import config
from config import MATCH_PATH
from prompts.prompt import MATCH_SCORE_PROMPT
from services.extraction import (
    extract_job_description as scrape_job_description,
    extract_resume_bytes,
)
from streamlit_ui.components import render_match_analysis
from streamlit_ui.helpers import (
    run_json_prompt,
    safe_filename,
    safe_filename_from_url,
    show_error,
    write_json_file,
)


def render_match_score_tab():
    st.header("JD + Resume Match Score")
    st.caption(
        "Compare a resume with a job description and get matched skills, missing skills, fit score, and suggestions."
    )
    jd_url = st.text_input(
        "Job description URL",
        value="https://careers.qualcomm.com/careers/job/446718764455",
        key="match_jd_url",
    )
    uploaded_pdf = st.file_uploader(
        "Upload resume PDF",
        type=["pdf"],
        key="match_resume_pdf",
        max_upload_size=config.MAX_RESUME_UPLOAD_MB,
    )
    save_match = st.checkbox(
        f"Save match analysis to {MATCH_PATH}", value=True, key="save_match_analysis"
    )
    analyze_match = st.button("Analyze Match", type="primary")
    if analyze_match and jd_url and uploaded_pdf:
        try:
            with st.spinner("Scraping job description..."):
                jd_text = scrape_job_description(jd_url)
            with st.spinner("Extracting resume text..."):
                resume_text = extract_resume_bytes(
                    uploaded_pdf.getbuffer(), uploaded_pdf.name
                )
            with st.spinner("Analyzing resume match with Groq..."):
                match_analysis = run_json_prompt(
                    MATCH_SCORE_PROMPT, resume_text=resume_text, jd_text=jd_text
                )
            resume_name = safe_filename(Path(uploaded_pdf.name).stem)
            jd_name = safe_filename_from_url(jd_url)
            result = {
                "jd": {"url": jd_url, "text": jd_text},
                "resume": {"filename": uploaded_pdf.name, "text": resume_text},
                "match_analysis": match_analysis,
                "output_path": None,
            }
            if save_match:
                output_filename = f"match_{resume_name}_{jd_name}.json"
                output_path = write_json_file(MATCH_PATH, output_filename, result)
                result["output_path"] = str(output_path)
            render_match_analysis(result)
        except Exception as exc:
            show_error(exc, operation="match")
    elif analyze_match:
        if not jd_url:
            st.warning("Enter a job description URL.")
        elif not uploaded_pdf:
            st.warning("Upload a resume PDF.")
