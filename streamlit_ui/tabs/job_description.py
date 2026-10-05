"""Job description tab rendering."""

import streamlit as st

from config import QUESTION
from prompts.prompt import JD_PROMPT
from services.extraction import extract_job_description as scrape_job_description
from streamlit_ui.components import render_output
from streamlit_ui.helpers import (
    generate_questions,
    safe_filename_from_url,
    show_error,
    write_text_file,
)


def render_jd_tab():
    st.header("Generate from Job Description")
    jd_url = st.text_input(
        "Job description URL",
        value="https://careers.qualcomm.com/careers/job/446718764455",
    )
    save_jd = st.checkbox(f"Save questions to {QUESTION}", value=True, key="save_jd")
    if st.button("Generate JD Questions", type="primary"):
        try:
            with st.spinner("Scraping job description..."):
                jd_text = scrape_job_description(jd_url)
            with st.spinner("Generating questions with Groq..."):
                questions = generate_questions(jd_text, JD_PROMPT)
            output_path = None
            if save_jd:
                output_path = write_text_file(
                    QUESTION,
                    f"jd_questions_{safe_filename_from_url(jd_url)}.txt",
                    questions,
                )
            render_output("Job Description Questions", questions, output_path, jd_text)
        except Exception as exc:
            show_error(exc, operation="job_description")
