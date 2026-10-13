"""Live recorder payload limits, final transcript caching, edits, and failures."""

import base64
import unittest
from unittest.mock import patch
from pathlib import Path
from tempfile import TemporaryDirectory

from backend.prompts.prompt import VOICE_ANSWER_EVALUATION_PROMPT
from result_fixtures import response_for_prompt, result_for_prompt
from backend.services import generation, sessions
from frontend.streamlit_ui.tabs import voice_practice

from streamlit.testing.v1 import AppTest

from backend import config
from backend.errors import GroqServiceError, UploadTooLargeError
from frontend.streamlit_ui import recorder


class LiveRecorderTests(unittest.TestCase):
    def recording(self, content=b"recorded audio", filename="live_recording.webm"):
        return {
            "status": "complete",
            "audio": base64.b64encode(content).decode(),
            "filename": filename,
        }

    def app(self):
        return AppTest.from_string(
            "from frontend.streamlit_ui.recorder import record_live_audio, review_recorded_answer, recording_active\n"
            "import streamlit as st\n"
            "audio = record_live_audio('Record', key='test')\n"
            "text = review_recorded_answer(audio, key='test')\n"
            "st.write(text)\n"
            "st.button('Submit', disabled=recording_active('test'))",
            default_timeout=10,
        )

    def test_recording_payload_decodes_and_retains_supported_format(self):
        for filename in ("live_recording.webm", "live_recording.m4a"):
            audio = recorder.decode_recording(self.recording(filename=filename))
            self.assertEqual(audio.getvalue(), b"recorded audio")
            self.assertEqual(audio.name, filename)
        for result in (None, {"status": "recording"}, {"status": "error"}):
            self.assertIsNone(recorder.decode_recording(result))

    def test_invalid_base64_empty_audio_and_invalid_filenames_are_rejected(self):
        for payload in (
            {"status": "complete", "audio": "%%", "filename": "live_recording.webm"},
            self.recording(b""),
            self.recording(filename="../secret.wav"),
        ):
            with self.assertRaises(ValueError):
                recorder.decode_recording(payload)

    def test_audio_limit_is_checked_before_and_after_base64_decode(self):
        with patch.object(config, "MAX_AUDIO_UPLOAD_BYTES", 3), self.assertRaises(
            UploadTooLargeError
        ):
            recorder.decode_recording(self.recording(b"1234"))
        with patch.object(config, "MAX_AUDIO_UPLOAD_BYTES", 4):
            self.assertEqual(
                recorder.decode_recording(self.recording(b"1234")).getvalue(), b"1234"
            )
            with self.assertRaises(UploadTooLargeError):
                recorder.decode_recording(self.recording(b"123456"))

    def test_final_transcript_is_cached_and_user_edits_survive_reruns(self):
        with patch.object(
            recorder, "_live_recorder", return_value=self.recording()
        ), patch.object(
            recorder, "extract_audio_bytes", return_value="Original transcript"
        ) as transcribe:
            ui = self.app().run()
            self.assertFalse(ui.exception)
            self.assertFalse(ui.error)
            self.assertEqual(ui.text_area[0].value, "Original transcript")
            ui.text_area[0].set_value("My corrected answer").run()
            self.assertFalse(ui.exception)
            self.assertEqual(ui.text_area[0].value, "My corrected answer")
            self.assertTrue(
                any(item.value == "My corrected answer" for item in ui.markdown)
            )
            transcribe.assert_called_once()

    def test_new_recording_replaces_previous_transcript(self):
        with patch.object(
            recorder, "_live_recorder", return_value=self.recording()
        ) as widget, patch.object(
            recorder,
            "extract_audio_bytes",
            side_effect=["First answer", "Second answer"],
        ) as transcribe:
            ui = self.app().run()
            widget.return_value = self.recording(b"a different recording")
            ui.run()
            self.assertFalse(ui.exception)
            self.assertEqual(ui.text_area[0].value, "Second answer")
            self.assertEqual(transcribe.call_count, 2)

    def test_recording_start_clears_old_answer_and_disables_submission(self):
        with patch.object(
            recorder, "_live_recorder", return_value=self.recording()
        ) as widget, patch.object(
            recorder, "extract_audio_bytes", return_value="Old answer"
        ):
            ui = self.app().run()
            widget.return_value = {"status": "recording", "recording_id": "new"}
            ui.run()
            self.assertFalse(ui.exception)
            self.assertFalse(ui.text_area)
            self.assertTrue(ui.button[0].disabled)

    def test_transcription_failure_requires_retry_and_does_not_reuse_old_answer(self):
        with patch.object(
            recorder, "_live_recorder", return_value=self.recording()
        ) as widget, patch.object(
            recorder,
            "extract_audio_bytes",
            side_effect=[
                "Old answer",
                GroqServiceError("Unavailable"),
                "Recovered answer",
            ],
        ) as transcribe:
            ui = self.app().run()
            widget.return_value = self.recording(b"new recording")
            ui.run()
            self.assertFalse(ui.exception)
            self.assertTrue(ui.error)
            self.assertFalse(ui.text_area)
            ui.run()
            self.assertFalse(ui.exception)
            self.assertEqual(transcribe.call_count, 2)
            ui.button[0].click().run()
            self.assertFalse(ui.exception)
            self.assertEqual(ui.text_area[0].value, "Recovered answer")
            self.assertEqual(transcribe.call_count, 3)

    def test_voice_evaluation_uses_corrected_transcript(self):
        with patch.object(
            recorder, "_live_recorder", return_value=self.recording()
        ), patch.object(
            recorder, "extract_audio_bytes", return_value="Original transcript"
        ), patch.object(
            voice_practice,
            "run_json_prompt",
            return_value=result_for_prompt(VOICE_ANSWER_EVALUATION_PROMPT),
        ) as evaluate, patch.object(
            voice_practice, "save_history"
        ):
            ui = AppTest.from_string(
                "from frontend.streamlit_ui.tabs.voice_practice import render_voice_practice_tab\nrender_voice_practice_tab()",
                default_timeout=10,
            ).run()
            ui.text_area[0].set_value("Describe your project")
            ui.text_area[1].set_value("Corrected project answer")
            ui.checkbox[0].uncheck()
            ui.button[0].click().run()
            self.assertFalse(ui.exception)
            self.assertFalse(ui.error)
            self.assertEqual(
                evaluate.call_args.kwargs["answer_text"], "Corrected project answer"
            )

    def test_session_saves_corrected_transcript(self):
        with TemporaryDirectory() as directory, patch.object(
            config, "DB_PATH", Path(directory) / "sessions.db"
        ), patch.object(
            recorder, "_live_recorder", return_value=self.recording()
        ), patch.object(
            recorder, "extract_audio_bytes", return_value="Original transcript"
        ), patch.object(
            generation, "groq_prompt_call", side_effect=response_for_prompt
        ):
            session = sessions.create_session(
                "Voice practice", ["Describe your project"]
            )
            ui = AppTest.from_string(
                "from frontend.streamlit_ui.tabs.sessions import render_sessions_tab\nrender_sessions_tab()",
                default_timeout=10,
            ).run()
            ui.radio[0].set_value("Record speech").run()
            self.assertFalse(ui.exception)
            self.assertFalse(ui.error)
            next(
                area for area in ui.text_area if area.label == "Review your transcript"
            ).set_value("Corrected project answer")
            ui.button(key=f"submit_session_{session['id']}_0").click().run()
            self.assertFalse(ui.exception)
            self.assertFalse(ui.error)
            self.assertEqual(
                sessions.get_session(session["id"])["answers"][0]["answer_text"],
                "Corrected project answer",
            )


if __name__ == "__main__":
    unittest.main()
