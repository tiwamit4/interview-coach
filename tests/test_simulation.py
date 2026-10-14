"""Timed interview API, deadline races, report aggregation, and legacy compatibility."""

import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch
from fastapi.testclient import TestClient
from backend import config
from backend.api import app
from backend.services import sessions
from backend.services.progress import get_progress
from backend.prompts.prompt import VOICE_ANSWER_EVALUATION_PROMPT
from result_fixtures import result_for_prompt


class SimulationTests(unittest.TestCase):
    def setUp(self):
        directory = TemporaryDirectory()
        self.addCleanup(directory.cleanup)
        location = patch.object(config, "DB_PATH", Path(directory.name) / "test.db")
        location.start()
        self.addCleanup(location.stop)
        self.evaluation = result_for_prompt(VOICE_ANSWER_EVALUATION_PROMPT)
        self.generator = patch.object(
            sessions, "run_json_prompt", return_value=self.evaluation
        )
        self.mock = self.generator.start()
        self.addCleanup(self.generator.stop)
        self.client = TestClient(app)

    def create(self, **options):
        response = self.client.post(
            "/sessions",
            json={
                "questions": ["First?", "Second?"],
                "simulation_duration_minutes": 20,
                **options,
            },
        )
        self.assertEqual(response.status_code, 201, response.text)
        return response.json()

    def answer(self, session, index=0):
        return self.client.post(
            f"/sessions/{session['id']}/answers",
            json={"answer_text": "Answer", "expected_question_index": index},
        )

    def expire(self, session):
        with sessions._connection() as db:
            db.execute(
                "UPDATE interview_simulations SET deadline_at = ? WHERE session_id = ?",
                (
                    (datetime.now(timezone.utc) - timedelta(seconds=1)).isoformat(),
                    session["id"],
                ),
            )

    def test_deadline_persists_and_completed_report_matches_evaluations(self):
        session = self.create()
        reloaded = self.client.get(f"/sessions/{session['id']}").json()
        self.assertEqual(
            reloaded["simulation"]["deadline_at"], session["simulation"]["deadline_at"]
        )
        self.assertIsNone(reloaded["report"])
        self.assertEqual(self.answer(session).status_code, 200)
        response = self.answer(session, 1)
        self.assertEqual(response.status_code, 200)
        report = response.json()["session"]["report"]
        self.assertEqual(report["completion_reason"], "all_questions_answered")
        self.assertEqual(report["average_score"], 90)
        self.assertEqual(report["rubric_averages"]["depth"], 22)
        self.assertEqual(report["unanswered_questions"], 0)
        self.assertEqual(report["strengths"], ["Clear explanation"])
        self.assertEqual(len(report["question_scores"]), 2)
        self.assertEqual(self.answer(session, 2).status_code, 409)

    def test_expired_interview_rejects_new_answers_without_model_call(self):
        session = self.create()
        self.expire(session)
        self.assertEqual(self.answer(session).status_code, 409)
        self.mock.assert_not_called()
        saved = sessions.get_session(session["id"])
        self.assertEqual(saved["status"], "completed")
        self.assertIsNone(saved["current_question"])
        self.assertEqual(saved["report"]["completion_reason"], "time_expired")
        self.assertIsNone(saved["report"]["average_score"])
        self.assertEqual(saved["report"]["unanswered_questions"], 2)
        self.assertEqual(sessions.list_sessions()[0]["status"], "completed")
        self.assertEqual(get_progress()["summary"]["completed_sessions"], 1)

    def test_early_finish_is_idempotent_and_preserves_scored_answers(self):
        session = self.create()
        self.answer(session)
        path = f"/sessions/{session['id']}/finish"
        response = self.client.post(path)
        self.assertEqual(response.status_code, 200)
        saved = response.json()
        self.assertEqual(saved["report"]["completion_reason"], "finished_early")
        self.assertEqual(saved["report"]["unanswered_questions"], 1)
        self.assertEqual(saved["report"]["average_score"], 90)
        repeated = self.client.post(path).json()
        self.assertEqual(repeated["report"], saved["report"])
        self.assertEqual(
            repeated["simulation"]["finished_at"], saved["simulation"]["finished_at"]
        )
        self.assertEqual(self.answer(session, 1).status_code, 409)

    def test_answer_submitted_before_deadline_is_saved_if_evaluation_runs_late(self):
        session = self.create()

        def slow_evaluation(*args, **kwargs):
            self.expire(session)
            return self.evaluation

        self.mock.side_effect = slow_evaluation
        response = self.answer(session)
        self.assertEqual(response.status_code, 200, response.text)
        saved = response.json()["session"]
        self.assertEqual(saved["answered_questions"], 1)
        self.assertEqual(saved["report"]["completion_reason"], "time_expired")

    def test_manual_finish_wins_over_inflight_evaluation(self):
        session = self.create()

        def finish_while_evaluating(*args, **kwargs):
            sessions.finish_simulation(session["id"])
            return self.evaluation

        self.mock.side_effect = finish_while_evaluating
        self.assertEqual(self.answer(session).status_code, 409)
        self.assertEqual(sessions.get_session(session["id"])["answered_questions"], 0)

    def test_duration_validation_and_untimed_sessions(self):
        for duration in (0, config.SIMULATION_MAX_MINUTES + 1, True, "20"):
            response = self.client.post(
                "/sessions",
                json={
                    "questions": ["Question?"],
                    "simulation_duration_minutes": duration,
                },
            )
            self.assertEqual(response.status_code, 422)
        session = self.create(simulation_duration_minutes=None)
        self.assertIsNone(session["simulation"])
        self.assertEqual(
            self.client.post(f"/sessions/{session['id']}/finish").status_code, 409
        )
        self.assertEqual(self.client.post("/sessions/missing/finish").status_code, 404)

    def test_simulation_followups_remain_in_the_same_time_budget(self):
        session = self.create(followups_enabled=True, questions=["First?"])

        def generate(prompt, **values):
            return result_for_prompt(prompt)

        self.mock.side_effect = generate
        response = self.answer(session)
        self.assertEqual(response.status_code, 200, response.text)
        updated = response.json()["session"]
        self.assertTrue(updated["current_question_is_followup"])
        self.assertEqual(
            updated["simulation"]["deadline_at"], session["simulation"]["deadline_at"]
        )
        completed = self.answer(session, 1).json()["session"]
        self.assertEqual(completed["status"], "completed")
        self.assertEqual(completed["report"]["answered_questions"], 2)
