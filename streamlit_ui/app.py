import streamlit as st
from dotenv import load_dotenv

from streamlit_ui.tabs import (
    render_cover_letter_tab,
    render_history_tab,
    render_interview_prep_tab,
    render_jd_resume_questions_tab,
    render_match_score_tab,
    render_resume_improvement_tab,
    render_sessions_tab,
    render_voice_practice_tab,
)
from streamlit_ui.theme import apply_theme


def render_sidebar():
    with st.sidebar:
        theme = st.radio("Theme", ["Dark", "Light"], horizontal=True)
        st.markdown("**Welcome My Friend Welcome**")
    return theme


def render_hero():
    st.markdown(
        """
        <div class="app-hero">
            <h1>Interview Coach</h1>
            <p>Generate focused interview questions from a resume PDF, pasted resume text, or a live job description URL.</p>
        </div>
        <div class="metric-row">
            <div class="metric-pill"><strong>JD</strong><span>Scrape and question</span></div>
            <div class="metric-pill"><strong>Match</strong><span>Score role fit</span></div>
            <div class="metric-pill"><strong>Prep</strong><span>Practice smarter</span></div>
            <div class="metric-pill"><strong>Voice</strong><span>Evaluate answers</span></div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def render_tabs():
    (
        tab_analyze,
        tab_questions,
        tab_prep,
        tab_improve,
        tab_cover,
        tab_voice_practice,
        tab_sessions,
        tab_history,
    ) = st.tabs(
        [
            "Analyze Fit",
            "Questions",
            "Interview Prep",
            "Resume Optimizer",
            "Application Writer",
            "Voice Practice",
            "Interview Sessions",
            "History",
        ]
    )

    with tab_analyze:
        render_match_score_tab()
    with tab_questions:
        render_jd_resume_questions_tab()
    with tab_prep:
        render_interview_prep_tab()
    with tab_improve:
        render_resume_improvement_tab()
    with tab_cover:
        render_cover_letter_tab()
    with tab_voice_practice:
        render_voice_practice_tab()
    with tab_sessions:
        render_sessions_tab()
    with tab_history:
        render_history_tab()


def run_app():
    load_dotenv()
    st.set_page_config(page_title="Interview Coach", page_icon="🎯", layout="wide")

    theme = render_sidebar()
    apply_theme(theme)
    render_hero()
    render_tabs()
