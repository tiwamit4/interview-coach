"""Voice practice tab rendering."""

import streamlit as st

from config import VOICE_MODEL as DEFAULT_MODEL, VOICE_PRACTICE_PATH
from prompts.prompt import VOICE_ANSWER_EVALUATION_PROMPT
from services.extraction import (
    extract_audio_bytes,
    extract_job_description as scrape_job_description,
)
from streamlit_ui.components import render_voice_evaluation
from streamlit_ui.helpers import run_json_prompt, safe_filename, save_result, show_error
from streamlit_ui.recorder import record_live_audio
from utils.history import save_history


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
    else:
        answer_text = st.text_area("Paste your answer", height=180)
    save_output = st.checkbox(
        f"Save evaluation to {VOICE_PRACTICE_PATH}",
        value=True,
        key="save_voice_practice",
    )
    if st.button("Evaluate Answer", type="primary"):
        if not question.strip():
            st.warning("Enter an interview question.")
            return
        try:
            if answer_audio:
                st.audio(answer_audio)
                with st.spinner("Transcribing your answer..."):
                    answer_text = extract_audio_bytes(
                        answer_audio.getbuffer(), answer_audio.name, model=DEFAULT_MODEL
                    )
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
