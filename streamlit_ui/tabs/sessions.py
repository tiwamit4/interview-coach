"""Interview sessions with one question at a time and saved progress."""

import re

import streamlit as st

from services import sessions
from services.extraction import extract_audio_bytes
from streamlit_ui.components import render_voice_evaluation, render_evaluation_rubric
from streamlit_ui.helpers import show_error
from streamlit_ui.recorder import record_live_audio


def render_sessions_tab():
    st.header("Interview Sessions")
    st.caption(
        "Practice one question at a time. Answers, feedback, and progress are saved automatically."
    )
    try:
        with st.expander("Start a new session"):
            with st.form("new_interview_session"):
                title = st.text_input("Session title", value="Interview practice")
                question_text = st.text_area(
                    "Questions, one per line",
                    placeholder="Paste questions from the Questions tab or enter your own.",
                    height=180,
                )
                context = st.text_area("Optional role context", height=100)
                followups_enabled = st.checkbox(
                    "Generate follow-up questions",
                    value=True,
                    help="Ask one answer-based follow-up per planned question, up to the configured session limit.",
                )
                start = st.form_submit_button("Start Session")
            if start:
                questions = [
                    re.sub(r"^\s*(?:\d+[.)]|[-*])\s*", "", line).strip()
                    for line in question_text.splitlines()
                    if line.strip()
                ]
                if not questions:
                    st.warning("Enter at least one question.")
                    return
                created = sessions.create_session(
                    title, questions, context, followups_enabled
                )
                st.session_state["interview_session_id"] = created["id"]
        items = sessions.list_sessions()
        if not items:
            st.info("Start a session to begin practicing.")
            return
        st.subheader("Progress across sessions")
        st.dataframe(
            [
                {
                    "Session": item["title"],
                    "Answered": item["answered_questions"],
                    "Questions": item["total_questions"],
                    "Average score": item["average_score"],
                    "Status": item["status"],
                }
                for item in items
            ],
            hide_index=True,
        )
        ids = [item["id"] for item in items]
        labels = {
            item[
                "id"
            ]: f"{item['title']} ({item['answered_questions']}/{item['total_questions']}) - {item['id'][:8]}"
            for item in items
        }
        preferred = st.session_state.get("interview_session_id")
        selected = st.selectbox(
            "Practice session",
            ids,
            index=ids.index(preferred) if preferred in ids else 0,
            format_func=labels.get,
        )
        session = sessions.get_session(selected)
        st.progress(session["answered_questions"] / session["total_questions"])
        if session["answers"]:
            previous = session["answers"][-1]
            with st.expander("Latest answer and feedback", expanded=True):
                st.write(previous["question"])
                st.write(previous["answer_text"])
                render_voice_evaluation(
                    {
                        "evaluation": previous["evaluation"],
                        "question": previous["question"],
                        "answer_text": previous["answer_text"],
                    }
                )
        if session["status"] == "completed":
            st.success("Session completed.")
            st.metric("Average answer score", f"{session['average_score']}/100")
        else:
            index = session["current_question_index"]
            st.subheader(f"Question {index + 1} of {session['total_questions']}")
            if session["current_question_is_followup"]:
                metadata = next(
                    item
                    for item in session["followups"]
                    if item["question_index"] == index
                )
                st.caption(
                    f"Follow-up to question {metadata['parent_question_index'] + 1}: {metadata['reason']}"
                )
            st.write(session["current_question"])
            mode = st.radio(
                "Session answer input",
                ["Paste text", "Record speech"],
                horizontal=True,
                key=f"session_mode_{selected}_{index}",
            )
            answer = ""
            audio = None
            if mode == "Paste text":
                answer = st.text_area(
                    "Your answer", key=f"session_answer_{selected}_{index}", height=180
                )
            else:
                audio = record_live_audio(
                    "Record your answer", key=f"session_audio_{selected}_{index}"
                )
            if st.button(
                "Submit Answer",
                type="primary",
                key=f"submit_session_{selected}_{index}",
            ):
                if audio:
                    with st.spinner("Transcribing your answer..."):
                        answer = extract_audio_bytes(audio.getbuffer(), audio.name)
                if not answer.strip():
                    st.warning("Record or paste an answer first.")
                    return
                with st.spinner(
                    "Evaluating your answer and preparing the next question..."
                ):
                    sessions.submit_answer(selected, answer, index)
                st.session_state["interview_session_id"] = selected
                st.rerun()
        with st.expander("Review all saved answers"):
            for answer in session["answers"]:
                st.markdown(
                    f"**Question {answer['question_index'] + 1}: {answer['question']}**"
                )
                st.write(answer["answer_text"])
                st.write(f"Score: {answer['evaluation']['score']}/100")
                st.write(answer["evaluation"]["feedback"])
                render_evaluation_rubric(answer["evaluation"])
    except Exception as exc:
        show_error(exc, operation="interview_session")
