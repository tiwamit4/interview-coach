"""API integration checks with external services replaced by mocks."""

import unittest
from contextlib import ExitStack
from pathlib import Path
from unittest.mock import patch

from fastapi.testclient import TestClient

from api import app
from api_backend.routes import (
    analysis,
    extraction,
    history,
    questions,
    voice,
    workflows,
)
from errors import GroqServiceError
from services import extraction as extraction_service, generation
from prompts.prompt import VOICE_ANSWER_EVALUATION_PROMPT
from result_fixtures import response_for_prompt, result_for_prompt


class ApiTests(unittest.TestCase):
    def setUp(self):
        self.client = TestClient(app)
        self.stack = ExitStack()
        self.addCleanup(self.stack.close)
        for module in (analysis, extraction, questions, voice, workflows):
            self.stack.enter_context(patch.object(module, "save_history"))
        self.stack.enter_context(
            patch.object(extraction_service, "read_pdf", return_value="Resume text")
        )
        self.stack.enter_context(
            patch.object(
                extraction_service, "scrape_job_description", return_value="JD text"
            )
        )
        self.stack.enter_context(
            patch.object(
                generation, "groq_prompt_call", side_effect=response_for_prompt
            )
        )
        for module in (questions, voice, workflows):
            self.stack.enter_context(
                patch.object(module, "scrape_job_description", return_value="JD text")
            )
        for module in (questions, workflows):
            self.stack.enter_context(
                patch.object(module, "groq_prompt_call", return_value="Questions")
            )
        self.stack.enter_context(
            patch.object(questions, "groq_model_call", return_value="Questions")
        )
        self.transcribe = self.stack.enter_context(
            patch.object(
                extraction_service, "transcribe_audio", return_value="Answer text"
            )
        )

    def post_resume(self, path, **data):
        return self.client.post(
            path,
            data={
                "jd_url": "https://example.com/jobs/engineer",
                "save_output": "false",
                **data,
            },
            files={"resume": ("resume.pdf", b"mock PDF", "application/pdf")},
        )

    def test_health_and_history(self):
        self.assertEqual(self.client.get("/health").json(), {"status": "ok"})
        with patch.object(history, "list_history", return_value=[{"id": 1}]) as listing:
            self.assertEqual(
                self.client.get("/history?limit=3").json(), {"items": [{"id": 1}]}
            )
            listing.assert_called_once_with(3)
        with patch.object(history, "get_history", return_value={"id": 1}):
            self.assertEqual(self.client.get("/history/1").json(), {"id": 1})
        with patch.object(history, "get_history", return_value=None):
            self.assertEqual(self.client.get("/history/2").status_code, 404)

    def test_questions_input_combinations(self):
        for source, data, files in (
            ("text", {"text": "Resume text"}, {}),
            ("jd", {"jd_url": "https://example.com/job"}, {}),
            ("resume", {}, {"resume": ("resume.pdf", b"mock PDF", "application/pdf")}),
            (
                "jd_resume",
                {"jd_url": "https://example.com/job"},
                {"resume": ("resume.pdf", b"mock PDF", "application/pdf")},
            ),
        ):
            with self.subTest(source=source):
                response = self.client.post(
                    "/questions", data={"save_output": "false", **data}, files=files
                )
                self.assertEqual(response.status_code, 200, response.text)
                self.assertEqual(response.json()["source_type"], source)
                self.assertEqual(response.json()["questions"], "Questions")

    def test_all_text_workflows(self):
        for task, result_key in (
            ("jd_questions", "questions"),
            ("resume_questions", "questions"),
            ("jd_resume_questions", "questions"),
            ("match_score", "match_analysis"),
            ("interview_prep", "interview_prep"),
            ("cover_letter", "application_messages"),
            ("resume_improvement", "resume_improvements"),
            ("full_analysis", "match_analysis"),
        ):
            with self.subTest(task=task):
                response = self.post_resume("/run", task=task)
                self.assertEqual(response.status_code, 200, response.text)
                self.assertEqual(response.json()["task"], task)
                self.assertIn(result_key, response.json())
        response = self.client.post(
            "/run",
            data={
                "task": "resume_questions",
                "text": "Resume text",
                "save_output": "false",
            },
        )
        self.assertEqual(response.status_code, 200, response.text)

    def test_extraction_and_compatibility_routes(self):
        for path, result_key in (
            ("/extract/jd-resume", "resume"),
            ("/jd-resume/questions", "questions"),
            ("/analyze/jd-resume-match", "match_analysis"),
            ("/prep/interview", "interview_prep"),
            ("/generate/cover-letter", "application_messages"),
            ("/improve/resume", "resume_improvements"),
            ("/analyze/jd-resume", "match_analysis"),
        ):
            with self.subTest(path=path):
                response = self.post_resume(path)
                self.assertEqual(response.status_code, 200, response.text)
                self.assertIn(result_key, response.json())
        response = self.client.post(
            "/jd/questions",
            json={"url": "https://example.com/job", "save_output": False},
        )
        self.assertEqual(response.status_code, 200, response.text)
        response = self.client.post(
            "/text/resume/questions", json={"text": "Resume text", "save_output": False}
        )
        self.assertEqual(response.status_code, 200, response.text)
        response = self.client.post(
            "/resume/questions?save_output=false",
            files={"file": ("resume.pdf", b"mock PDF", "application/pdf")},
        )
        self.assertEqual(response.status_code, 200, response.text)

    def test_voice_tasks_and_temporary_file_cleanup(self):
        response = self.client.post(
            "/voice/run",
            data={"task": "transcribe", "save_output": "false"},
            files={"audio": ("answer.wav", b"mock audio", "audio/wav")},
        )
        self.assertEqual(response.status_code, 200, response.text)
        self.assertEqual(response.json()["transcript"], "Answer text")
        self.assertFalse(Path(self.transcribe.call_args.args[0]).exists())
        for path in ("/voice/run", "/voice/evaluate-answer"):
            with self.subTest(path=path):
                response = self.client.post(
                    path,
                    data={
                        "task": "evaluate_answer",
                        "question": "Tell me about yourself",
                        "answer_text": "Answer",
                        "save_output": "false",
                    },
                )
                self.assertEqual(response.status_code, 200, response.text)
                self.assertEqual(
                    response.json()["evaluation"],
                    result_for_prompt(VOICE_ANSWER_EVALUATION_PROMPT),
                )
        self.transcribe.side_effect = GroqServiceError("Service unavailable")
        response = self.client.post(
            "/voice/run",
            data={"task": "transcribe"},
            files={"audio": ("answer.wav", b"mock audio", "audio/wav")},
        )
        self.assertEqual(response.status_code, 502)
        self.assertFalse(Path(self.transcribe.call_args.args[0]).exists())

    def test_validation_and_service_errors(self):
        for path, data in (
            ("/questions", {}),
            ("/run", {"task": "unknown"}),
            ("/voice/run", {"task": "transcribe"}),
        ):
            with self.subTest(path=path):
                self.assertEqual(self.client.post(path, data=data).status_code, 400)
        response = self.client.post(
            "/questions", files={"resume": ("resume.txt", b"text", "text/plain")}
        )
        self.assertEqual(response.status_code, 400)
        with patch.object(
            workflows,
            "groq_prompt_call",
            side_effect=GroqServiceError("Service unavailable"),
        ):
            response = self.client.post(
                "/run",
                data={
                    "task": "resume_questions",
                    "text": "Resume text",
                    "save_output": "false",
                },
            )
            self.assertEqual(response.status_code, 502)

    def test_malformed_ai_results_are_rejected_before_saving(self):
        cases = (
            ("/run", {"task": "match_score"}, workflows),
            ("/run", {"task": "interview_prep"}, workflows),
            ("/run", {"task": "cover_letter"}, workflows),
            ("/run", {"task": "resume_improvement"}, workflows),
            ("/run", {"task": "full_analysis"}, workflows),
            ("/analyze/jd-resume-match", {}, analysis),
            ("/prep/interview", {}, analysis),
            ("/generate/cover-letter", {}, analysis),
            ("/improve/resume", {}, analysis),
            ("/analyze/jd-resume", {}, analysis),
        )
        for path, data, module in cases:
            with self.subTest(path=path, data=data), patch.object(
                generation, "groq_prompt_call", return_value="{}"
            ), patch.object(module, "write_json_file") as writer, patch.object(
                module, "save_history"
            ) as history_writer:
                response = self.post_resume(path, save_output="true", **data)
                self.assertEqual(response.status_code, 502, response.text)
                self.assertIn("Field required", response.json()["detail"])
                writer.assert_not_called()
                history_writer.assert_not_called()
        for path in ("/voice/run", "/voice/evaluate-answer"):
            with self.subTest(path=path), patch.object(
                generation, "groq_prompt_call", return_value="{}"
            ), patch.object(voice, "write_json_file") as writer, patch.object(
                voice, "save_history"
            ) as history_writer:
                response = self.client.post(
                    path,
                    data={
                        "task": "evaluate_answer",
                        "question": "Question",
                        "answer_text": "Answer",
                    },
                )
                self.assertEqual(response.status_code, 502, response.text)
                self.assertIn("score", response.json()["detail"])
                writer.assert_not_called()
                history_writer.assert_not_called()
        with patch.object(generation, "groq_prompt_call", return_value="invalid JSON"):
            response = self.post_resume("/run", task="match_score")
            self.assertEqual(response.status_code, 502)


if __name__ == "__main__":
    unittest.main()
