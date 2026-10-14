"""Daily queue stability, review selection, adaptive difficulty, and skill trends."""

import unittest
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timedelta, timezone
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch

from fastapi.testclient import TestClient
from backend import config
from backend.api import app
from backend.services import practice, sessions
from backend.prompts.prompt import VOICE_ANSWER_EVALUATION_PROMPT
from result_fixtures import result_for_prompt


class DailyPracticeTests(unittest.TestCase):
    def setUp(self):
        temporary = TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        location = patch.object(config, "DB_PATH", Path(temporary.name) / "practice.db")
        location.start()
        self.addCleanup(location.stop)
        self.client = TestClient(app)
        self.stamp = datetime.now(timezone.utc) - timedelta(days=2)

    def evaluation(self, score):
        result = result_for_prompt(VOICE_ANSWER_EVALUATION_PROMPT)
        result["score"] = score
        for index, criterion in enumerate(result["rubric"].values()):
            criterion["points"] = score // 4 + (index < score % 4)
        return result

    def seed(self, question, score):
        self.stamp += timedelta(minutes=1)
        with patch.object(sessions, "_now", return_value=self.stamp.isoformat()):
            session = sessions.create_session("Earlier practice", [question])
            with patch.object(
                sessions, "run_json_prompt", return_value=self.evaluation(score)
            ):
                sessions.submit_answer(session["id"], "Answer", 0)
        return session

    def test_new_user_has_stable_unique_five_question_baseline(self):
        response = self.client.get("/practice/daily")
        self.assertEqual(response.status_code, 200, response.text)
        plan = response.json()
        self.assertEqual(len(plan["items"]), 5)
        self.assertEqual(len({item["question"] for item in plan["items"]}), 5)
        self.assertEqual(plan["skills"], [])
        self.assertEqual(plan["status"], "not_started")
        self.assertTrue(
            all(item["difficulty"] == "foundational" for item in plan["items"])
        )
        self.assertEqual(self.client.get("/practice/daily").json(), plan)

    def test_weak_skills_and_low_score_retries_take_priority(self):
        low = self.seed("Explain SQL joins.", 40)
        self.seed("Describe Python testing.", 90)
        plan = practice.get_daily_practice()
        self.assertEqual(plan["items"][0]["question"], "Explain SQL joins.")
        self.assertEqual(plan["items"][0]["source_session_id"], low["id"])
        self.assertEqual(plan["items"][0]["previous_score"], 40)
        self.assertEqual(plan["items"][0]["difficulty"], "original")
        self.assertEqual(plan["items"][1]["skill"], "SQL and databases")

    def test_mastered_question_is_not_retried_for_its_old_low_score(self):
        self.seed("Explain SQL joins.", 40)
        self.seed("Explain SQL joins.", 90)
        plan = practice.get_daily_practice()
        self.assertFalse(any(item["source_session_id"] for item in plan["items"]))

    def test_queue_stays_fixed_today_but_next_day_increases_difficulty(self):
        self.seed("Explain SQL joins.", 40)
        first = practice.get_daily_practice()
        for index in range(3):
            self.seed(f"Explain SQL indexes example {index}.", 95)
        today = practice.get_daily_practice()
        self.assertEqual(first["items"], today["items"])
        self.assertEqual(today["skills"][0]["difficulty"], "advanced")
        with patch.object(practice, "_today", return_value="2099-01-02"):
            tomorrow = practice.get_daily_practice()
        new_items = [
            item for item in tomorrow["items"] if item["difficulty"] != "original"
        ]
        self.assertTrue(all(item["difficulty"] == "advanced" for item in new_items))
        skill = tomorrow["skills"][0]
        self.assertEqual(skill["baseline_average"], 67.5)
        self.assertEqual(skill["comparison_average"], 95)
        self.assertEqual(skill["score_change"], 27.5)
        self.assertEqual(skill["comparison_samples"], 2)

    def test_applied_difficulty_and_regression(self):
        for index in range(2):
            self.seed(f"Explain Python example {index}.", 75)
        self.assertEqual(
            practice.get_daily_practice()["skills"][0]["difficulty"], "applied"
        )
        for index in range(3):
            self.seed(f"Explain Python failure {index}.", 40)
        skill = practice.get_daily_practice()["skills"][0]
        self.assertEqual(skill["difficulty"], "foundational")
        self.assertLess(skill["score_change"], 0)

    def test_start_is_atomic_and_resumes_saved_answers(self):
        with ThreadPoolExecutor(max_workers=3) as pool:
            opened = list(pool.map(lambda _: practice.start_daily_practice(), range(3)))
        self.assertEqual(len({session["id"] for session in opened}), 1)
        session = opened[0]
        self.assertFalse(session["followups_enabled"])
        with patch.object(
            sessions, "run_json_prompt", return_value=self.evaluation(90)
        ):
            sessions.submit_answer(session["id"], "Answer", 0)
        resumed = self.client.post("/practice/daily/start")
        self.assertEqual(resumed.status_code, 200, resumed.text)
        self.assertEqual(resumed.json()["id"], session["id"])
        self.assertEqual(resumed.json()["answered_questions"], 1)
        plan = practice.get_daily_practice()
        self.assertTrue(plan["items"][0]["completed"])
        self.assertEqual(plan["items"][0]["score"], 90)
        self.assertEqual(plan["skills"][0]["daily_practice_attempts"], 1)
        self.assertIsNone(plan["skills"][0]["score_change"])

    def test_explicit_skill_tracks_same_skill_across_wording_and_levels(self):
        self.seed("Explain SQL joins.", 40)
        session = practice.start_daily_practice()
        with patch.object(
            sessions, "run_json_prompt", return_value=self.evaluation(90)
        ):
            for index in range(len(session["questions"])):
                sessions.submit_answer(session["id"], "Answer", index)
        plan = practice.get_daily_practice()
        self.assertEqual(plan["status"], "completed")
        self.assertEqual(plan["answered_questions"], 5)
        self.assertEqual(plan["skills"][0]["skill"], "SQL and databases")
        self.assertEqual(plan["skills"][0]["daily_practice_attempts"], 5)
        self.assertGreater(plan["skills"][0]["score_change"], 0)
        self.assertEqual(
            self.client.post("/practice/daily/start").json()["id"], session["id"]
        )

    def test_queue_size_configuration_and_next_day_session(self):
        with patch.object(config, "DAILY_PRACTICE_QUESTION_COUNT", 3):
            first = practice.start_daily_practice()
        self.assertEqual(first["total_questions"], 3)
        with patch.object(practice, "_today", return_value="2099-01-02"):
            second = practice.start_daily_practice()
        self.assertNotEqual(first["id"], second["id"])
        self.assertEqual(second["total_questions"], 5)
