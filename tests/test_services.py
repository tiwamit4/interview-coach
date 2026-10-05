"""Shared service behavior and API/UI adapter compatibility."""

import json
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch

from api_backend import helpers as api_helpers
from errors import GroqServiceError
from services import extraction, files, generation
from streamlit_ui import helpers as ui_helpers
from prompts.prompt import VOICE_ANSWER_EVALUATION_PROMPT
from result_fixtures import response_for_prompt, result_for_prompt


class SharedServiceTests(unittest.TestCase):
    def test_resume_extraction_cleans_up_on_success_and_failure(self):
        for failure in (False, True):
            with self.subTest(failure=failure):

                def read(path):
                    self.assertEqual(path.read_bytes(), b"PDF content")
                    if failure:
                        raise ValueError("Broken PDF")
                    return "Resume text"

                with patch.object(extraction, "read_pdf", side_effect=read) as reader:
                    if failure:
                        with self.assertRaisesRegex(ValueError, "Broken PDF"):
                            extraction.extract_resume_bytes(
                                b"PDF content", "resume.PDF"
                            )
                    else:
                        self.assertEqual(
                            extraction.extract_resume_bytes(
                                b"PDF content", "resume.PDF"
                            ),
                            "Resume text",
                        )
                    self.assertFalse(reader.call_args.args[0].exists())

    def test_invalid_resume_is_rejected_before_extraction(self):
        with patch.object(extraction, "read_pdf") as reader:
            for filename in (None, "", "resume.txt"):
                with self.subTest(filename=filename), self.assertRaises(ValueError):
                    extraction.extract_resume_bytes(b"content", filename)
            reader.assert_not_called()

    def test_audio_translation_options_and_cleanup(self):
        with patch.object(
            extraction, "translate_audio", return_value="English answer"
        ) as translate:
            result = extraction.extract_audio_bytes(
                b"audio", "answer.m4a", translate=True, prompt="Interview"
            )
            self.assertEqual(result, "English answer")
            self.assertEqual(translate.call_args.kwargs, {"prompt": "Interview"})
            self.assertEqual(translate.call_args.args[0].suffix, ".m4a")
            self.assertFalse(translate.call_args.args[0].exists())

    def test_json_parsing_and_adapter_errors(self):
        for text in ('{"score": 90}', '```json\n{"score": 90}\n```'):
            self.assertEqual(generation.parse_json_response(text), {"score": 90})
            self.assertEqual(
                api_helpers.parse_json_response(text),
                ui_helpers.parse_json_response(text),
            )
        for text in ("not JSON", "prefix {broken} suffix"):
            with self.assertRaises(json.JSONDecodeError):
                api_helpers.parse_json_response(text)
            with self.assertRaisesRegex(GroqServiceError, "invalid JSON"):
                ui_helpers.parse_json_response(text)

    def test_api_and_ui_use_shared_generation(self):
        with patch.object(
            generation, "groq_prompt_call", side_effect=response_for_prompt
        ) as call:
            self.assertEqual(
                api_helpers.run_json_prompt(
                    VOICE_ANSWER_EVALUATION_PROMPT, answer_text="resume"
                ),
                result_for_prompt(VOICE_ANSWER_EVALUATION_PROMPT),
            )
            self.assertEqual(
                ui_helpers.run_json_prompt(
                    VOICE_ANSWER_EVALUATION_PROMPT, answer_text="resume"
                ),
                result_for_prompt(VOICE_ANSWER_EVALUATION_PROMPT),
            )
            self.assertEqual(call.call_count, 2)
        with patch.object(
            generation, "groq_model_call", return_value="Questions"
        ) as call:
            self.assertEqual(
                ui_helpers.generate_questions("resume", "prompt"), "Questions"
            )
            call.assert_called_once_with("resume", "prompt")

    def test_shared_file_writers_preserve_adapter_types_and_unicode(self):
        with TemporaryDirectory() as directory:
            content = "हिंदी résumé"
            api_path = api_helpers.write_text_file(directory, "api.txt", content)
            ui_path = ui_helpers.write_text_file(directory, "ui.txt", content)
            self.assertIsInstance(api_path, str)
            self.assertIsInstance(ui_path, Path)
            self.assertEqual(Path(api_path).read_text(encoding="utf-8"), content)
            self.assertEqual(ui_path.read_text(encoding="utf-8"), content)
            result = files.save_result(
                directory, "result.json", {"text": content, "output_path": None}
            )
            self.assertEqual(
                json.loads(Path(result["output_path"]).read_text(encoding="utf-8")),
                result,
            )


if __name__ == "__main__":
    unittest.main()
