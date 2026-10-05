"""Resume pdf tab rendering."""

from pathlib import Path

import streamlit as st

import config
from config import QUESTION, TEXT_PATH
from prompts.prompt import QUESTION_PROMPT
from services.extraction import extract_resume_bytes
from streamlit_ui.components import render_output
from streamlit_ui.helpers import (
    generate_questions,
    safe_filename,
    show_error,
    write_text_file,
)


def render_resume_pdf_tab():
    st.header("Generate from Resume PDF")
    uploaded_pdf = st.file_uploader(
        "Upload resume PDF", type=["pdf"], max_upload_size=config.MAX_RESUME_UPLOAD_MB
    )
    save_resume = st.checkbox(
        "Save extracted text and questions", value=True, key="save_resume_pdf"
    )
    generate_resume_pdf = st.button("Generate Resume Questions", type="primary")
    if generate_resume_pdf and uploaded_pdf:
        try:
            with st.spinner("Extracting resume text..."):
                resume_text = extract_resume_bytes(
                    uploaded_pdf.getbuffer(), uploaded_pdf.name
                )
            with st.spinner("Generating questions with Groq..."):
                questions = generate_questions(resume_text, QUESTION_PROMPT)
            output_path = None
            if save_resume:
                stem = safe_filename(Path(uploaded_pdf.name).stem)
                write_text_file(TEXT_PATH, f"{stem}.txt", resume_text)
                output_path = write_text_file(
                    QUESTION, f"{stem}_questions.txt", questions
                )
            render_output("Resume Questions", questions, output_path, resume_text)
        except Exception as exc:
            show_error(exc, operation="resume_pdf")
    elif generate_resume_pdf and (not uploaded_pdf):
        st.warning("Upload a PDF first.")
