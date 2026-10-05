"""Resume text tab rendering."""

import streamlit as st

from config import QUESTION
from prompts.prompt import QUESTION_PROMPT
from streamlit_ui.components import render_output
from streamlit_ui.helpers import (
    generate_questions,
    safe_filename,
    show_error,
    write_text_file,
)


def render_resume_text_tab():
    st.header("Generate from Resume Text")
    resume_text_input = st.text_area("Paste resume text", height=320)
    output_name = st.text_input("Output name", value="resume_text")
    save_text_questions = st.checkbox(
        f"Save questions to {QUESTION}", value=False, key="save_resume_text"
    )
    if st.button("Generate Text Questions", type="primary"):
        try:
            with st.spinner("Generating questions with Groq..."):
                questions = generate_questions(resume_text_input, QUESTION_PROMPT)
            output_path = None
            if save_text_questions:
                output_path = write_text_file(
                    QUESTION, f"{safe_filename(output_name)}_questions.txt", questions
                )
            render_output(
                "Resume Text Questions", questions, output_path, resume_text_input
            )
        except Exception as exc:
            show_error(exc, operation="resume_text")
