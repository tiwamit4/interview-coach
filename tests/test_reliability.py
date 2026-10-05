"""Upload bounds, output integrity, and structured error diagnostics."""

import json
import logging
import unittest
from concurrent.futures import ThreadPoolExecutor
from io import BytesIO, StringIO
from pathlib import Path
from tempfile import TemporaryDirectory
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

from fastapi.testclient import TestClient

import config
from api import app
from api_backend.routes import history, workflows
from errors import UploadTooLargeError
from result_fixtures import response_for_prompt
from services import extraction, files, generation
from services.uploads import read_upload
from utils import logging_utils


class UploadReadTests(unittest.IsolatedAsyncioTestCase):
    async def test_reported_size_rejects_without_reading(self):
        upload = SimpleNamespace(size=6, read=AsyncMock())
        with self.assertRaises(UploadTooLargeError):
            await read_upload(upload, 5, "resume")
        upload.read.assert_not_called()

    async def test_unknown_size_is_bounded_and_boundary_is_allowed(self):
        for content in (b"12345", b"1234567890"):
            with self.subTest(content=content):
                source = BytesIO(content)
                upload = SimpleNamespace(
                    size=None, read=AsyncMock(side_effect=source.read)
                )
                with patch.object(config, "UPLOAD_READ_CHUNK_BYTES", 4):
                    if len(content) == 5:
                        self.assertEqual(
                            await read_upload(upload, 5, "resume"), content
                        )
                    else:
                        with self.assertRaises(UploadTooLargeError):
                            await read_upload(upload, 5, "resume")
                        self.assertEqual(source.tell(), 6)
                self.assertTrue(
                    all(call.args[0] <= 4 for call in upload.read.call_args_list)
                )


class FileReliabilityTests(unittest.TestCase):
    def test_concurrent_writes_are_unique_and_preserve_existing_files(self):
        with TemporaryDirectory() as directory:
            original = Path(directory) / "answer.txt"
            original.write_text("original", encoding="utf-8")
            contents = [f"résumé हिंदी {index}" for index in range(20)]
            with ThreadPoolExecutor(max_workers=4) as pool:
                paths = list(
                    pool.map(
                        lambda text: files.write_text_file(
                            directory, "answer.txt", text
                        ),
                        contents,
                    )
                )
            self.assertEqual(len(set(paths)), 20)
            self.assertEqual(
                [path.read_text(encoding="utf-8") for path in paths], contents
            )
            self.assertEqual(original.read_text(encoding="utf-8"), "original")

    def test_exclusive_creation_retries_a_collision(self):
        with TemporaryDirectory() as directory:
            existing = Path(directory) / "answer_collision.txt"
            existing.write_text("original", encoding="utf-8")
            with patch.object(
                files,
                "uuid4",
                side_effect=[
                    SimpleNamespace(hex="collision"),
                    SimpleNamespace(hex="unique"),
                ],
            ):
                path = files.write_text_file(directory, "answer.txt", "new")
            self.assertEqual(path.name, "answer_unique.txt")
            self.assertEqual(existing.read_text(encoding="utf-8"), "original")

    def test_failed_serialization_removes_partial_output(self):
        with TemporaryDirectory() as directory:
            with self.assertRaises(TypeError):
                files.write_json_file(directory, "result.json", {"invalid": object()})
            self.assertEqual(list(Path(directory).iterdir()), [])

    def test_json_path_matches_response_and_history(self):
        with TemporaryDirectory() as directory, patch.object(
            workflows, "MATCH_PATH", directory
        ), patch.object(workflows, "save_history") as save_history, patch.object(
            extraction, "read_pdf", return_value="Résumé"
        ), patch.object(
            extraction, "scrape_job_description", return_value="Job"
        ), patch.object(
            generation, "groq_prompt_call", side_effect=response_for_prompt
        ):
            responses = []
            for _ in range(2):
                response = TestClient(app).post(
                    "/run",
                    data={"task": "match_score", "jd_url": "https://example.com/job"},
                    files={"resume": ("resume.pdf", b"PDF", "application/pdf")},
                )
                self.assertEqual(response.status_code, 200, response.text)
                result = response.json()
                path = Path(result["output_path"])
                self.assertEqual(json.loads(path.read_text(encoding="utf-8")), result)
                self.assertEqual(save_history.call_args.args[2], result)
                responses.append(result)
            self.assertNotEqual(
                responses[0]["output_path"], responses[1]["output_path"]
            )


class ReliabilityIntegrationTests(unittest.TestCase):
    def test_oversized_resumes_return_413_before_extraction(self):
        endpoints = (
            ("/questions", {}),
            ("/run", {"task": "match_score"}),
            ("/jd-resume/questions", {}),
            ("/extract/jd-resume", {}),
            ("/analyze/jd-resume-match", {}),
            ("/prep/interview", {}),
            ("/generate/cover-letter", {}),
            ("/improve/resume", {}),
            ("/analyze/jd-resume", {}),
            ("/resume/questions", {}),
        )
        with patch.object(config, "MAX_RESUME_UPLOAD_BYTES", 4), patch.object(
            extraction, "read_pdf"
        ) as read_pdf, patch.object(extraction, "scrape_job_description") as scrape:
            for path, data in endpoints:
                field = "file" if path == "/resume/questions" else "resume"
                with self.subTest(path=path):
                    response = TestClient(app).post(
                        path,
                        data={"jd_url": "https://example.com/job", **data},
                        files={field: ("resume.pdf", b"12345", "application/pdf")},
                    )
                    self.assertEqual(response.status_code, 413, response.text)
                    self.assertIn("too large", response.json()["detail"])
            read_pdf.assert_not_called()
            scrape.assert_not_called()

    def test_oversized_audio_is_rejected_for_api_and_shared_ui_service(self):
        with patch.object(config, "MAX_AUDIO_UPLOAD_BYTES", 4), patch.object(
            extraction, "transcribe_audio"
        ) as transcribe:
            for path, task, field in (
                ("/voice/run", "transcribe", "audio"),
                ("/voice/run", "evaluate_answer", "answer_audio"),
                ("/voice/evaluate-answer", "evaluate_answer", "answer_audio"),
            ):
                response = TestClient(app).post(
                    path,
                    data={"task": task, "question": "Question"},
                    files={field: ("answer.wav", b"12345", "audio/wav")},
                )
                self.assertEqual(response.status_code, 413, response.text)
            with self.assertRaises(UploadTooLargeError):
                extraction.extract_audio_bytes(b"12345", "answer.wav")
            transcribe.assert_not_called()

    def test_error_logs_are_json_and_do_not_include_exception_inputs(self):
        stream = StringIO()
        handler = logging.StreamHandler(stream)
        handler.setFormatter(logging_utils.JsonFormatter())
        logger = logging.Logger("test")
        logger.addHandler(handler)
        token = logging_utils.REQUEST_ID.set("request123")
        try:
            with patch.object(logging_utils, "get_logger", return_value=logger):
                try:
                    raise RuntimeError("secret request body and API key")
                except RuntimeError as exc:
                    logging_utils.log_error(
                        exc, event="test_failure", operation="generation"
                    )
        finally:
            logging_utils.REQUEST_ID.reset(token)
        result = json.loads(stream.getvalue())
        self.assertEqual(result["event"], "test_failure")
        self.assertEqual(result["error_type"], "RuntimeError")
        self.assertEqual(result["request_id"], "request123")
        self.assertTrue(result["traceback"])
        self.assertNotIn("secret", stream.getvalue())

    def test_api_failure_logs_include_response_request_id(self):
        with self.assertLogs("interview_coach", level="WARNING") as logs:
            response = TestClient(app).post("/questions")
        self.assertEqual(response.status_code, 400)
        event = next(
            record
            for record in logs.records
            if record.getMessage() == "api_request_failed"
        )
        self.assertEqual(event.context["request_id"], response.headers["x-request-id"])
        self.assertEqual(event.context["route"], "/questions")
        self.assertEqual(event.context["status_code"], 400)

    def test_unhandled_failure_is_logged_and_returns_clear_500(self):
        with patch.object(
            history, "list_history", side_effect=RuntimeError("private failure")
        ), self.assertLogs("interview_coach", level="ERROR") as logs:
            response = TestClient(app, raise_server_exceptions=False).get("/history")
        self.assertEqual(response.status_code, 500)
        self.assertEqual(
            response.json(), {"detail": "Something went wrong. Please try again."}
        )
        event = next(
            record
            for record in logs.records
            if record.getMessage() == "api_unhandled_error"
        )
        self.assertEqual(event.context["request_id"], response.headers["x-request-id"])


if __name__ == "__main__":
    unittest.main()
