"""Persistent practice sessions, stale submissions, and Streamlit progression."""

import unittest
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from tempfile import TemporaryDirectory
from threading import Barrier
from unittest.mock import patch

from fastapi.testclient import TestClient
from streamlit.testing.v1 import AppTest

import config
from api import app
from errors import GeneratedResultError, SessionConflictError
from prompts.prompt import VOICE_ANSWER_EVALUATION_PROMPT
from result_fixtures import result_for_prompt
from services import sessions


class SessionTests(unittest.TestCase):
    def setUp(self):
        directory = TemporaryDirectory()
        self.addCleanup(directory.cleanup)
        location = patch.object(config, "DB_PATH", Path(directory.name) / "session.db")
        location.start()
        self.addCleanup(location.stop)
        evaluation = patch.object(
            sessions,
            "run_json_prompt",
            return_value=result_for_prompt(VOICE_ANSWER_EVALUATION_PROMPT),
        )
        evaluation.start()
        self.addCleanup(evaluation.stop)
        self.client = TestClient(app)

    def create(self, questions=None):
        response = self.client.post(
            "/sessions",
            json={
                "title": "Practice",
                "questions": questions or ["First question", "Second question"],
            },
        )
        self.assertEqual(response.status_code, 201, response.text)
        return response.json()

    def test_session_progress_answers_and_summary_survive_reload(self):
        created = self.create()
        self.assertEqual(created["current_question"], "First question")
        for index, answer in enumerate(("First answer", "Second answer")):
            response = self.client.post(
                f"/sessions/{created['id']}/answers",
                json={"answer_text": answer, "expected_question_index": index},
            )
            self.assertEqual(response.status_code, 200, response.text)
        saved = self.client.get(f"/sessions/{created['id']}").json()
        self.assertEqual(saved["status"], "completed")
        self.assertIsNone(saved["current_question"])
        self.assertEqual(
            [answer["answer_text"] for answer in saved["answers"]],
            ["First answer", "Second answer"],
        )
        summary = self.client.get("/sessions").json()["items"][0]
        self.assertEqual(summary["answered_questions"], 2)
        self.assertEqual(summary["average_score"], 90)
        self.assertEqual(
            self.client.post(
                f"/sessions/{created['id']}/answers",
                json={"answer_text": "Duplicate", "expected_question_index": 1},
            ).status_code,
            409,
        )

    def test_invalid_or_missing_sessions_and_answers(self):
        self.assertEqual(self.client.get("/sessions/missing").status_code, 404)
        self.assertEqual(
            self.client.post("/sessions", json={"questions": []}).status_code, 422
        )
        self.assertEqual(
            self.client.post("/sessions", json={"questions": [" "]}).status_code, 422
        )
        created = self.create()
        self.assertEqual(
            self.client.post(
                f"/sessions/{created['id']}/answers",
                json={"answer_text": " ", "expected_question_index": 0},
            ).status_code,
            422,
        )
        self.assertEqual(
            self.client.post(
                f"/sessions/{created['id']}/answers",
                json={"answer_text": "answer", "expected_question_index": True},
            ).status_code,
            422,
        )

    def test_failed_evaluation_does_not_advance_session(self):
        created = self.create()
        with patch.object(
            sessions,
            "run_json_prompt",
            side_effect=GeneratedResultError("Invalid answer evaluation"),
        ):
            response = self.client.post(
                f"/sessions/{created['id']}/answers",
                json={"answer_text": "Answer", "expected_question_index": 0},
            )
        self.assertEqual(response.status_code, 502)
        saved = sessions.get_session(created["id"])
        self.assertEqual(saved["answered_questions"], 0)
        self.assertEqual(saved["answers"], [])

    def test_concurrent_answers_only_advance_once(self):
        created = self.create()
        barrier = Barrier(2)

        def evaluate(*args, **kwargs):
            barrier.wait(timeout=3)
            return result_for_prompt(VOICE_ANSWER_EVALUATION_PROMPT)

        def answer(text):
            try:
                sessions.submit_answer(created["id"], text, 0)
                return "saved"
            except SessionConflictError:
                return "stale"

        with patch.object(
            sessions, "run_json_prompt", side_effect=evaluate
        ), ThreadPoolExecutor(max_workers=2) as workers:
            outcomes = list(workers.map(answer, ("Answer A", "Answer B")))
        self.assertCountEqual(outcomes, ["saved", "stale"])
        self.assertEqual(sessions.get_session(created["id"])["answered_questions"], 1)

    def test_streamlit_creates_session_and_advances_questions(self):
        app_test = AppTest.from_string(
            "from streamlit_ui.tabs.sessions import render_sessions_tab\nrender_sessions_tab()"
        ).run()
        app_test.text_area[0].set_value("First question\nSecond question")
        app_test.button[0].click().run()
        self.assertFalse(app_test.exception)
        self.assertFalse(app_test.error)
        session_id = sessions.list_sessions()[0]["id"]
        for index in range(2):
            app_test.text_area(key=f"session_answer_{session_id}_{index}").set_value(
                f"Answer {index + 1}"
            )
            app_test.button(key=f"submit_session_{session_id}_{index}").click().run()
            self.assertFalse(app_test.exception)
            self.assertFalse(app_test.error)
        self.assertTrue(
            any(item.value == "Session completed." for item in app_test.success)
        )
        self.assertEqual(sessions.get_session(session_id)["status"], "completed")


if __name__ == "__main__":
    unittest.main()
