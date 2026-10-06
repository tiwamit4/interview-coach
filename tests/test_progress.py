"""Progress summaries from persisted sessions, topic evidence, and dashboard filters."""

import json
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch

from fastapi.testclient import TestClient
from streamlit.testing.v1 import AppTest

import config
from api import app
from prompts.prompt import VOICE_ANSWER_EVALUATION_PROMPT
from result_fixtures import result_for_prompt
from services import sessions
from services.progress import get_progress
from utils.database import connection


class ProgressTests(unittest.TestCase):
    def setUp(self):
        directory = TemporaryDirectory()
        self.addCleanup(directory.cleanup)
        location = patch.object(config, "DB_PATH", Path(directory.name) / "progress.db")
        location.start()
        self.addCleanup(location.stop)
        self.client = TestClient(app)

    def seed(
        self, title, questions, scores, improvements=None, age_days=0, followups=()
    ):
        created_at = datetime.now(timezone.utc) - timedelta(days=age_days, hours=2)
        with patch.object(sessions, "_now", return_value=created_at.isoformat()):
            session = sessions.create_session(title, questions)
        with connection() as db:
            for index, score in enumerate(scores):
                evaluation = result_for_prompt(VOICE_ANSWER_EVALUATION_PROMPT)
                evaluation["score"] = score
                evaluation["improvements"] = improvements[index] if improvements else []
                stamp = (created_at + timedelta(minutes=index)).isoformat()
                db.execute(
                    "INSERT INTO interview_answers VALUES (?, ?, ?, ?, ?, ?)",
                    (
                        session["id"],
                        index,
                        "Saved answer",
                        json.dumps(evaluation),
                        score,
                        stamp,
                    ),
                )
                if index in followups:
                    db.execute(
                        "INSERT INTO interview_followups VALUES (?, ?, ?, ?)",
                        (session["id"], index, index - 1, "A relevant follow-up"),
                    )
            db.execute(
                "UPDATE interview_sessions SET current_index = ? WHERE id = ?",
                (len(scores), session["id"]),
            )
        return session["id"]

    def test_empty_and_unanswered_sessions_have_no_invented_scores(self):
        data = get_progress()
        self.assertEqual(data["summary"]["sessions"], 0)
        self.assertIsNone(data["summary"]["average_score"])
        self.assertIsNone(data["summary"]["score_change"])
        self.assertEqual(data["score_trend"], [])
        sessions.create_session("Unanswered", ["Python"])
        data = get_progress()
        self.assertEqual(data["summary"]["sessions"], 1)
        self.assertEqual(data["summary"]["answers"], 0)
        self.assertEqual(data["topics"], [])

    def test_average_is_weighted_by_answers_and_zero_scores_are_included(self):
        self.seed(
            "Long session", ["Python one", "Python two", "Python three"], [0, 40, 60]
        )
        self.seed("Short session", ["SQL joins"], [100])
        data = get_progress()
        self.assertEqual(data["summary"]["average_score"], 50)
        self.assertEqual(data["summary"]["answers"], 4)
        self.assertEqual(data["summary"]["completed_sessions"], 2)
        self.assertEqual(sum(row["answer_count"] for row in data["score_trend"]), 4)
        self.assertEqual(len(data["session_scores"]), 2)
        self.assertEqual(
            {row["topic"] for row in data["topics"]}, {"Python", "SQL and databases"}
        )

    def test_trend_compares_consecutive_windows_in_answer_time_order(self):
        self.seed("Practice", ["Question"] * 4, [20, 30, 70, 90])
        with patch.object(config, "PROGRESS_TREND_WINDOW", 2):
            data = get_progress()
        self.assertEqual(data["summary"]["score_change"], 55)
        self.assertEqual(data["summary"]["trend_window"], 2)
        self.assertIsNone(get_progress()["summary"]["score_change"])

    def test_weakness_counts_distinct_answers_with_original_evidence(self):
        self.seed(
            "First",
            ["Explain Python"],
            [80],
            [
                [
                    "Include measurable metrics",
                    "Quantify the impact",
                    "Revise an unfamiliar tool",
                ]
            ],
        )
        self.seed(
            "Second", ["Explain Python"], [85], [["Describe measurable outcomes"]]
        )
        data = get_progress()
        weaknesses = data["recurring_weaknesses"]
        self.assertEqual(len(weaknesses), 1)
        self.assertEqual(weaknesses[0]["answer_count"], 2)
        self.assertEqual(weaknesses[0]["session_count"], 2)
        self.assertIn("Include measurable metrics", weaknesses[0]["examples"])
        python = next(row for row in data["topics"] if row["topic"] == "Python")
        self.assertTrue(python["needs_practice"])
        self.assertIn("Repeated improvement feedback", python["reasons"])
        self.assertEqual(len(python["practice_questions"]), 2)

    def test_low_scores_are_priorities_and_unrelated_topics_stay_separate(self):
        self.seed(
            "Practice",
            ["How do you test an API?", "Explain SQL joins", "Tell me about yourself"],
            [45, 95, 80],
        )
        data = get_progress()
        topics = {row["topic"]: row for row in data["topics"]}
        self.assertTrue(topics["Testing and reliability"]["needs_practice"])
        self.assertTrue(topics["APIs and web development"]["needs_practice"])
        self.assertFalse(topics["SQL and databases"]["needs_practice"])
        self.assertFalse(topics["General interview answers"]["needs_practice"])
        self.assertEqual(topics["SQL and databases"]["average_score"], 95)
        self.assertIn(
            "Average score below 70/100", topics["Testing and reliability"]["reasons"]
        )

    def test_date_and_followup_filters_change_all_answer_statistics(self):
        self.seed("Old", ["Python"], [20], [["Use examples"]], age_days=40)
        self.seed(
            "Recent",
            ["Python", "Python follow-up"],
            [80, 40],
            [["Use examples"], ["Use examples"]],
            followups=(1,),
        )
        self.assertEqual(get_progress()["summary"]["answers"], 3)
        data = get_progress(days=7, include_followups=False)
        self.assertEqual(data["summary"]["sessions"], 1)
        self.assertEqual(data["summary"]["answers"], 1)
        self.assertEqual(data["summary"]["average_score"], 80)
        self.assertEqual(data["recurring_weaknesses"], [])
        self.assertFalse(data["topics"][0]["needs_practice"])
        self.assertEqual(len(data["session_scores"]), 1)

    def test_dashboard_covers_more_than_the_session_picker_limit(self):
        for index in range(51):
            sessions.create_session(f"Practice {index}", ["Question"])
        self.assertEqual(get_progress()["summary"]["sessions"], 51)

    def test_api_returns_saved_data_and_validates_filters(self):
        self.seed("Practice", ["Python"], [60])
        response = self.client.get("/progress?days=7&include_followups=false")
        self.assertEqual(response.status_code, 200, response.text)
        self.assertEqual(response.json()["summary"]["average_score"], 60)
        for query in (
            "days=0",
            "days=-1",
            "days=3651",
            "days=bad",
            "include_followups=bad",
        ):
            self.assertEqual(self.client.get("/progress?" + query).status_code, 422)

    def test_ui_empty_state_and_saved_progress_filters(self):
        ui = AppTest.from_string(
            "from streamlit_ui.tabs.progress import render_progress_tab\nrender_progress_tab()",
            default_timeout=10,
        ).run()
        self.assertFalse(ui.exception)
        self.assertFalse(ui.error)
        self.assertTrue(any("Answer questions" in item.value for item in ui.info))
        self.seed(
            "Old practice",
            ["Explain Python"],
            [50],
            [["Add measurable metrics"]],
            age_days=30,
        )
        self.seed(
            "Recent practice",
            ["Explain Python", "Explain Python follow-up"],
            [90, 50],
            [["Quantify outcomes"], []],
            followups=(1,),
        )
        ui.run()
        self.assertFalse(ui.exception)
        self.assertFalse(ui.error)
        self.assertTrue(ui.dataframe)
        self.assertTrue(
            any(
                "Examples and measurable outcomes" in item.label for item in ui.expander
            )
        )
        ui.selectbox(key="progress_period").set_value("Last 7 days")
        ui.checkbox(key="progress_followups").uncheck().run()
        self.assertFalse(ui.exception)
        self.assertFalse(ui.error)
        metrics = {item.label: item.value for item in ui.metric}
        self.assertEqual(metrics["Evaluated answers"], "1")
        self.assertEqual(metrics["Average score"], "90.0/100")
        self.assertFalse(
            any(
                "Examples and measurable outcomes" in item.label for item in ui.expander
            )
        )


if __name__ == "__main__":
    unittest.main()
