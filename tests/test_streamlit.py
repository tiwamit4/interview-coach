"""Streamlit rendering and feature flows using the shared services."""

import unittest
from contextlib import ExitStack
from io import BytesIO
from unittest.mock import patch

from streamlit.testing.v1 import AppTest

import config
from result_fixtures import response_for_prompt
from services import extraction, generation, sessions
from services import progress
from streamlit_ui.tabs import (
    analysis,
    applications,
    history,
    interview_prep,
    match,
    questions,
    resume_optimizer,
    voice_practice,
)


class StreamlitTests(unittest.TestCase):
    def setUp(self):
        self.stack = ExitStack()
        self.addCleanup(self.stack.close)
        for module in (
            analysis,
            applications,
            interview_prep,
            questions,
            resume_optimizer,
            voice_practice,
        ):
            self.stack.enter_context(patch.object(module, "save_history"))
        self.stack.enter_context(patch.object(history, "list_history", return_value=[]))
        self.stack.enter_context(
            patch.object(sessions, "list_sessions", return_value=[])
        )
        self.stack.enter_context(
            patch.object(progress, "read_progress_data", return_value=([], []))
        )
        self.stack.enter_context(
            patch.object(extraction, "scrape_job_description", return_value="JD text")
        )
        self.reader = self.stack.enter_context(
            patch.object(extraction, "read_pdf", return_value="Resume text")
        )
        self.prompt = self.stack.enter_context(
            patch.object(
                generation, "groq_prompt_call", side_effect=response_for_prompt
            )
        )
        self.stack.enter_context(
            patch.object(
                generation, "groq_model_call", return_value="Interview questions"
            )
        )
        self.transcribe = self.stack.enter_context(
            patch.object(extraction, "transcribe_audio", return_value="Spoken answer")
        )

    def test_main_app_renders_existing_tabs(self):
        app = AppTest.from_file("streamlit_app.py").run()
        self.assertFalse(app.exception)
        self.assertEqual(
            [tab.label for tab in app.tabs],
            [
                "Analyze Fit",
                "Questions",
                "Interview Prep",
                "Resume Optimizer",
                "Application Writer",
                "Voice Practice",
                "Interview Sessions",
                "Progress Dashboard",
                "History",
            ],
        )

    def test_oversized_ui_resume_shows_error_before_extraction(self):
        upload = BytesIO(b"12345")
        upload.name = "resume.pdf"
        with patch.object(config, "MAX_RESUME_UPLOAD_BYTES", 4), patch(
            "streamlit.file_uploader", return_value=upload
        ):
            app = AppTest.from_string(
                "from streamlit_ui.tabs.questions import render_jd_resume_questions_tab\nrender_jd_resume_questions_tab()"
            ).run()
            app.button[0].click().run()
            self.assertFalse(app.exception)
            self.assertEqual(len(app.error), 1)
            self.assertIn("too large", app.error[0].value)
            self.reader.assert_not_called()
            self.prompt.assert_not_called()

    def test_invalid_ai_output_shows_error_before_rendering_or_saving(self):
        upload = BytesIO(b"mock PDF")
        upload.name = "resume.pdf"
        with patch("streamlit.file_uploader", return_value=upload), patch.object(
            generation, "groq_prompt_call", return_value='{"role_fit_score": 200}'
        ), patch.object(match, "render_match_analysis") as render, patch.object(
            match, "write_json_file"
        ) as write:
            app = AppTest.from_string(
                "from streamlit_ui.tabs.match import render_match_score_tab\nrender_match_score_tab()"
            ).run()
            app.button[0].click().run()
            self.assertFalse(app.exception)
            self.assertEqual(len(app.error), 1)
            self.assertIn("role_fit_score", app.error[0].value)
            self.assertIn("invalid match analysis", app.error[0].value)
            self.assertFalse(app.metric)
            render.assert_not_called()
            write.assert_not_called()

    def test_document_feature_flows(self):
        upload = BytesIO(b"mock PDF")
        upload.name = "resume.pdf"
        features = (
            ("job_description", "render_jd_tab"),
            ("resume_pdf", "render_resume_pdf_tab"),
            ("resume_text", "render_resume_text_tab"),
            ("extraction", "render_jd_resume_json_tab"),
            ("questions", "render_jd_resume_questions_tab"),
            ("match", "render_match_score_tab"),
            ("interview_prep", "render_interview_prep_tab"),
            ("applications", "render_cover_letter_tab"),
            ("resume_optimizer", "render_resume_improvement_tab"),
            ("analysis", "render_combined_analysis_tab"),
        )
        with patch("streamlit.file_uploader", return_value=upload):
            for module, function in features:
                with self.subTest(feature=module):
                    app = AppTest.from_string(
                        f"from streamlit_ui.tabs.{module} import {function}\n{function}()"
                    ).run()
                    self.assertFalse(app.exception)
                    if module == "resume_text":
                        app.text_area[0].set_value("Resume text")
                    for checkbox in app.checkbox:
                        checkbox.uncheck()
                    app.button[0].click().run()
                    self.assertFalse(app.exception)
                    self.assertFalse(app.error)
                    self.assertFalse(app.warning)
                    self.assertTrue(app.subheader)
        self.assertTrue(self.reader.called)
        self.assertTrue(self.prompt.called)

    def test_voice_feature_flows(self):
        audio = BytesIO(b"mock audio")
        audio.name = "answer.wav"
        with patch.object(voice_practice, "record_live_audio", return_value=audio):
            app = AppTest.from_string(
                "from streamlit_ui.tabs.voice_practice import render_voice_practice_tab\nrender_voice_practice_tab()"
            ).run()
            app.text_area[0].set_value("Tell me about yourself")
            app.checkbox[0].uncheck()
            app.button[0].click().run()
            self.assertFalse(app.exception)
            self.assertFalse(app.error)
            self.assertTrue(app.metric)
        with patch("streamlit.file_uploader", return_value=audio):
            app = AppTest.from_string(
                "from streamlit_ui.tabs.speech_to_text import render_voice_tab\nrender_voice_tab()"
            ).run()
            app.checkbox(key="save_voice_transcript").uncheck()
            app.button[0].click().run()
            self.assertFalse(app.exception)
            self.assertFalse(app.error)
            self.assertEqual(app.text_area[0].value, "Spoken answer")
        self.assertFalse(self.transcribe.call_args.args[0].exists())


if __name__ == "__main__":
    unittest.main()
