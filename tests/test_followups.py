"""Answer-based follow-ups, persistence, bounds, failures, and concurrent saves."""

import json
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
from errors import SessionConflictError
from prompts.prompt import SESSION_FOLLOWUP_PROMPT, VOICE_ANSWER_EVALUATION_PROMPT
from result_fixtures import result_for_prompt
from services import generation, sessions
from utils.database import connection


class FollowUpTests(unittest.TestCase):
    def setUp(self):
        directory = TemporaryDirectory()
        self.addCleanup(directory.cleanup)
        location = patch.object(config, "DB_PATH", Path(directory.name) / "practice.db")
        location.start()
        self.addCleanup(location.stop)
        provider = patch.object(
            generation, "groq_prompt_call", side_effect=self.provider
        )
        self.provider_mock = provider.start()
        self.addCleanup(provider.stop)
        self.client = TestClient(app)

    @staticmethod
    def provider(prompt, **values):
        if prompt == SESSION_FOLLOWUP_PROMPT:
            return json.dumps(
                {
                    "question": "How did you validate "
                    + values["question"].rstrip("?")
                    + "?",
                    "reason": "Explore the validation of the project described in the answer.",
                }
            )
        return json.dumps(
            result_for_prompt(prompt, values.get("answer_text", "Answer"))
        )

    def create(self, questions=None):
        response = self.client.post(
            "/sessions",
            json={
                "questions": questions or ["First project", "Second project"],
                "role_context": "Python developer",
                "followups_enabled": True,
            },
        )
        self.assertEqual(response.status_code, 201, response.text)
        return response.json()

    def submit(self, session_id, index):
        return self.client.post(
            f"/sessions/{session_id}/answers",
            json={
                "answer_text": "I built a Python project and measured its accuracy.",
                "expected_question_index": index,
            },
        )

    def test_followup_uses_answer_and_context_and_resumes_original_plan(self):
        created = self.create()
        for index in range(4):
            response = self.submit(created["id"], index)
            self.assertEqual(response.status_code, 200, response.text)
            saved = self.client.get(f"/sessions/{created['id']}").json()
            if index == 0:
                self.assertEqual(
                    saved["current_question"], "How did you validate First project?"
                )
                self.assertTrue(saved["current_question_is_followup"])
                self.assertEqual(saved["followups"][0]["parent_question_index"], 0)
            if index == 1:
                self.assertEqual(saved["current_question"], "Second project")
                self.assertFalse(saved["current_question_is_followup"])
        self.assertEqual(saved["status"], "completed")
        self.assertEqual(saved["total_questions"], 4)
        self.assertEqual(len(saved["followups"]), 2)
        self.assertEqual(
            saved["answers"][1]["question"], "How did you validate First project?"
        )
        calls = [
            call
            for call in self.provider_mock.call_args_list
            if call.args[0] == SESSION_FOLLOWUP_PROMPT
        ]
        self.assertEqual(len(calls), 2)
        self.assertEqual(
            calls[0].kwargs["answer_text"],
            "I built a Python project and measured its accuracy.",
        )
        self.assertEqual(calls[0].kwargs["role_context"], "Python developer")
        self.assertEqual(
            json.loads(calls[0].kwargs["existing_questions"]), created["questions"]
        )
        summary = self.client.get("/sessions").json()["items"][0]
        self.assertEqual(summary["answered_questions"], 4)
        self.assertEqual(summary["total_questions"], 4)
        self.assertEqual(self.submit(created["id"], 3).status_code, 409)

    def test_followup_limit_and_no_recursive_followups(self):
        created = self.create()
        with patch.object(config, "MAX_SESSION_FOLLOWUPS", 1):
            for index in range(3):
                response = self.submit(created["id"], index)
                self.assertEqual(response.status_code, 200, response.text)
        saved = sessions.get_session(created["id"])
        self.assertEqual(saved["status"], "completed")
        self.assertEqual(len(saved["followups"]), 1)
        self.assertEqual(saved["questions"][-1], "Second project")

    def test_malformed_or_duplicate_followup_leaves_answer_and_plan_unsaved(self):
        payloads = (
            {},
            {"question": " ", "reason": "Reason"},
            {"question": "x" * 2001, "reason": "Reason"},
            {"question": "Valid?", "reason": "x" * 501},
            {"question": " FIRST PROJECT? ", "reason": "Reason"},
        )
        created = self.create()
        for payload in payloads:

            def provider(prompt, **values):
                return (
                    json.dumps(payload)
                    if prompt == SESSION_FOLLOWUP_PROMPT
                    else self.provider(prompt, **values)
                )

            with self.subTest(payload=payload), patch.object(
                generation, "groq_prompt_call", side_effect=provider
            ):
                response = self.submit(created["id"], 0)
                self.assertEqual(response.status_code, 502, response.text)
            saved = sessions.get_session(created["id"])
            self.assertEqual(saved["answers"], [])
            self.assertEqual(saved["questions"], created["questions"])
            self.assertEqual(saved["followups"], [])

    def test_disabled_and_legacy_sessions_do_not_call_followup_provider(self):
        created = sessions.create_session("Legacy practice", ["First project"])
        # Existing databases have sessions without a row in the new options table.
        with connection() as db:
            db.execute(
                "DELETE FROM interview_session_options WHERE session_id = ?",
                (created["id"],),
            )
        saved = sessions.get_session(created["id"])
        self.assertFalse(saved["followups_enabled"])
        response = self.submit(created["id"], 0)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["session"]["status"], "completed")
        self.assertEqual(self.provider_mock.call_count, 1)
        self.assertEqual(
            self.provider_mock.call_args.args[0], VOICE_ANSWER_EVALUATION_PROMPT
        )

    def test_concurrent_answers_insert_only_one_followup(self):
        created = self.create(["First project"])
        barrier = Barrier(2)

        def provider(prompt, **values):
            if prompt == SESSION_FOLLOWUP_PROMPT:
                barrier.wait(timeout=5)
            return self.provider(prompt, **values)

        def submit(text):
            try:
                sessions.submit_answer(created["id"], text, 0)
                return "saved"
            except SessionConflictError:
                return "stale"

        with patch.object(
            generation, "groq_prompt_call", side_effect=provider
        ), ThreadPoolExecutor(max_workers=2) as pool:
            outcomes = list(pool.map(submit, ["Answer A", "Answer B"]))
        self.assertCountEqual(outcomes, ["saved", "stale"])
        saved = sessions.get_session(created["id"])
        self.assertEqual(saved["answered_questions"], 1)
        self.assertEqual(len(saved["followups"]), 1)
        self.assertEqual(saved["total_questions"], 2)

    def test_api_requires_boolean_followup_option(self):
        response = self.client.post(
            "/sessions", json={"questions": ["Question"], "followups_enabled": "yes"}
        )
        self.assertEqual(response.status_code, 422)

    def test_streamlit_followup_label_and_completion(self):
        ui = AppTest.from_string(
            "from streamlit_ui.tabs.sessions import render_sessions_tab\nrender_sessions_tab()",
            default_timeout=10,
        ).run()
        ui.text_area[0].set_value("First project")
        ui.button[0].click().run()
        session_id = sessions.list_sessions()[0]["id"]
        for index in range(2):
            ui.text_area(key=f"session_answer_{session_id}_{index}").set_value(
                "I built a Python project."
            )
            ui.button(key=f"submit_session_{session_id}_{index}").click().run()
            self.assertFalse(ui.exception)
            self.assertFalse(ui.error)
            if index == 0:
                self.assertTrue(
                    any("Follow-up to question 1" in item.value for item in ui.caption)
                )
        self.assertEqual(sessions.get_session(session_id)["status"], "completed")
        self.assertTrue(any(item.value == "Session completed." for item in ui.success))


if __name__ == "__main__":
    unittest.main()
