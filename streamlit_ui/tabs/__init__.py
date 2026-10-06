"""Feature tabs with stable imports for the Streamlit application."""

from streamlit_ui.tabs.analysis import render_combined_analysis_tab
from streamlit_ui.tabs.applications import render_cover_letter_tab
from streamlit_ui.tabs.extraction import render_jd_resume_json_tab
from streamlit_ui.tabs.history import render_history_tab
from streamlit_ui.tabs.interview_prep import render_interview_prep_tab
from streamlit_ui.tabs.job_description import render_jd_tab
from streamlit_ui.tabs.match import render_match_score_tab
from streamlit_ui.tabs.questions import render_jd_resume_questions_tab
from streamlit_ui.tabs.resume_optimizer import render_resume_improvement_tab
from streamlit_ui.tabs.resume_pdf import render_resume_pdf_tab
from streamlit_ui.tabs.resume_text import render_resume_text_tab
from streamlit_ui.tabs.sessions import render_sessions_tab
from streamlit_ui.tabs.progress import render_progress_tab
from streamlit_ui.tabs.speech_to_text import convert_speech_to_text, render_voice_tab
from streamlit_ui.tabs.voice_practice import render_voice_practice_tab

__all__ = [
    "render_jd_tab",
    "render_resume_pdf_tab",
    "render_resume_text_tab",
    "render_jd_resume_json_tab",
    "render_jd_resume_questions_tab",
    "render_match_score_tab",
    "render_interview_prep_tab",
    "render_cover_letter_tab",
    "render_resume_improvement_tab",
    "render_combined_analysis_tab",
    "render_voice_practice_tab",
    "render_history_tab",
    "convert_speech_to_text",
    "render_voice_tab",
    "render_sessions_tab",
    "render_progress_tab",
]
