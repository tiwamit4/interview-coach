"""Voice practice tab rendering."""

import streamlit as st

from backend.config import VOICE_PRACTICE_PATH
from backend.prompts.prompt import VOICE_ANSWER_EVALUATION_PROMPT
from backend.services.extraction import (
    extract_job_description as scrape_job_description,
)
from frontend.streamlit_ui.components import render_voice_evaluation
from frontend.streamlit_ui.helpers import run_json_prompt, safe_filename, save_result, show_error
from frontend.streamlit_ui.recorder import (
    record_live_audio,
    recording_active,
    review_recorded_answer,
)
from backend.utils.history import save_history


def render_voice_practice_tab():
    st.header("Voice Interview Practice")
    question = st.text_area(
        "Interview question",
        height=100,
        placeholder="Tell me about a project where you used machine learning.",
    )
    jd_url = st.text_input("Optional JD URL for context", key="voice_practice_jd_url")
    input_mode = st.radio(
        "Answer input", ["Record speech", "Paste text"], horizontal=True
    )
    answer_text = ""
    answer_audio = None
    if input_mode == "Record speech":
        answer_audio = record_live_audio(
            "Record your answer", key="voice_practice_recorder"
        )
        answer_text = review_recorded_answer(
            answer_audio, key="voice_practice_recorder"
        )
    else:
        answer_text = st.text_area("Paste your answer", height=180)
    save_output = st.checkbox(
        f"Save evaluation to {VOICE_PRACTICE_PATH}",
        value=True,
        key="save_voice_practice",
    )
    if st.button(
        "Evaluate Answer",
        type="primary",
        disabled=input_mode == "Record speech"
        and recording_active("voice_practice_recorder"),
    ):
        if not question.strip():
            st.warning("Enter an interview question.")
            return
        try:
            if not answer_text.strip():
                st.warning("Record or paste an answer first.")
                return
            jd_text = ""
            if jd_url:
                with st.spinner("Scraping JD context..."):
                    jd_text = scrape_job_description(jd_url)
            with st.spinner("Evaluating answer..."):
                evaluation = run_json_prompt(
                    VOICE_ANSWER_EVALUATION_PROMPT,
                    question=question,
                    answer_text=answer_text,
                    jd_text=jd_text,
                )
            result = {
                "question": question,
                "answer_text": answer_text,
                "jd": {"url": jd_url or None, "text": jd_text},
                "evaluation": evaluation,
                "output_path": None,
            }
            if save_output:
                result = save_result(
                    VOICE_PRACTICE_PATH,
                    f"voice_practice_{safe_filename(question[:48])}.json",
                    result,
                )
            save_history("voice_answer_evaluation", question[:80], result)
            render_voice_evaluation(result)
        except Exception as exc:
            show_error(exc, operation="voice_practice")
