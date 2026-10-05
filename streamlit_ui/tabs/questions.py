"""Questions tab rendering."""

from pathlib import Path

import streamlit as st

import config
from config import QUESTION
from prompts.prompt import JD_PROMPT, QUESTION_PROMPT, RESUME_JD_PROMPT
from services.extraction import (
    extract_job_description as scrape_job_description,
    extract_resume_bytes,
)
from streamlit_ui.components import render_output
from streamlit_ui.helpers import (
    generate_prompt_response,
    safe_filename,
    safe_filename_from_url,
    show_error,
    write_text_file,
)
from streamlit_ui.tabs._shared import (
    build_jd_resume_result,
    extract_jd_resume_from_upload,
)
from utils.history import save_history


def render_jd_resume_questions_tab():
    st.header("Generate Questions")
    st.caption(
        "Generate interview questions from a resume, JD link, pasted text, or JD + resume together."
    )
    input_type = st.radio(
        "Question source",
        ["JD + Resume", "Resume only", "JD only", "Text only"],
        horizontal=True,
        key="questions_input_type",
    )
    jd_url = None
    uploaded_pdf = None
    text_input = None
    if input_type in {"JD + Resume", "JD only"}:
        jd_url = st.text_input(
            "Job description URL",
            value="https://careers.qualcomm.com/careers/job/446718764455",
            key="questions_jd_url",
        )
    if input_type in {"JD + Resume", "Resume only"}:
        uploaded_pdf = st.file_uploader(
            "Upload resume PDF",
            type=["pdf"],
            key="questions_resume_pdf",
            max_upload_size=config.MAX_RESUME_UPLOAD_MB,
        )
    if input_type == "Text only":
        text_input = st.text_area(
            "Paste resume or job description text",
            height=280,
            key="questions_text_input",
        )
    save_questions = st.checkbox(
        f"Save questions to {QUESTION}", value=True, key="save_questions_flexible"
    )
    generate_combined_questions = st.button("Generate Questions", type="primary")
    if generate_combined_questions:
        try:
            output_path = None
            source_text = None
            if input_type == "JD + Resume":
                if not jd_url or not uploaded_pdf:
                    st.warning("Enter a JD URL and upload a resume PDF.")
                    return
                jd_text, resume_text = extract_jd_resume_from_upload(
                    jd_url, uploaded_pdf
                )
                with st.spinner("Generating JD + resume interview questions..."):
                    questions = generate_prompt_response(
                        RESUME_JD_PROMPT, resume_text=resume_text, jd_text=jd_text
                    )
                if save_questions:
                    output_path = write_text_file(
                        QUESTION,
                        f"jd_resume_questions_{safe_filename(Path(uploaded_pdf.name).stem)}_{safe_filename_from_url(jd_url)}.txt",
                        questions,
                    )
                result = build_jd_resume_result(
                    jd_url, uploaded_pdf, jd_text, resume_text
                )
                result["questions"] = questions
                result["output_path"] = str(output_path) if output_path else None
                save_history("questions", "jd_resume", result)
                source_text = f"{resume_text}\n\n{jd_text}"
            elif input_type == "Resume only":
                if not uploaded_pdf:
                    st.warning("Upload a resume PDF.")
                    return
                with st.spinner("Extracting resume text..."):
                    resume_text = extract_resume_bytes(
                        uploaded_pdf.getbuffer(), uploaded_pdf.name
                    )
                with st.spinner("Generating resume questions..."):
                    questions = generate_prompt_response(
                        QUESTION_PROMPT, resume_text=resume_text
                    )
                if save_questions:
                    output_path = write_text_file(
                        QUESTION,
                        f"{safe_filename(Path(uploaded_pdf.name).stem)}_questions.txt",
                        questions,
                    )
                save_history(
                    "questions",
                    "resume",
                    {
                        "source_type": "resume",
                        "resume": {"filename": uploaded_pdf.name, "text": resume_text},
                        "questions": questions,
                        "output_path": str(output_path) if output_path else None,
                    },
                )
                source_text = resume_text
            elif input_type == "JD only":
                if not jd_url:
                    st.warning("Enter a JD URL.")
                    return
                with st.spinner("Scraping job description..."):
                    jd_text = scrape_job_description(jd_url)
                with st.spinner("Generating JD questions..."):
                    questions = generate_prompt_response(JD_PROMPT, jd_text=jd_text)
                if save_questions:
                    output_path = write_text_file(
                        QUESTION,
                        f"jd_questions_{safe_filename_from_url(jd_url)}.txt",
                        questions,
                    )
                save_history(
                    "questions",
                    "jd",
                    {
                        "source_type": "jd",
                        "jd": {"url": jd_url, "text": jd_text},
                        "questions": questions,
                        "output_path": str(output_path) if output_path else None,
                    },
                )
                source_text = jd_text
            else:
                if not text_input or not text_input.strip():
                    st.warning("Paste some text first.")
                    return
                with st.spinner("Generating text questions..."):
                    questions = generate_prompt_response(
                        QUESTION_PROMPT, resume_text=text_input
                    )
                if save_questions:
                    output_path = write_text_file(
                        QUESTION, "text_questions.txt", questions
                    )
                save_history(
                    "questions",
                    "text",
                    {
                        "source_type": "text",
                        "text": text_input,
                        "questions": questions,
                        "output_path": str(output_path) if output_path else None,
                    },
                )
                source_text = text_input
            render_output(
                f"{input_type} Questions", questions, output_path, source_text
            )
        except Exception as exc:
            show_error(exc, operation="questions")
