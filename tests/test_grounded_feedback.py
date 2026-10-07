"""Fixed scoring, exact evidence, API persistence, exports, and legacy rendering."""

import json
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch

from fastapi.testclient import TestClient
from streamlit.testing.v1 import AppTest

import config
from api import app
from errors import GeneratedResultError
from prompts.prompt import VOICE_ANSWER_EVALUATION_PROMPT
from result_fixtures import result_for_prompt
from services import generation, sessions
from utils import history
from streamlit_ui.exports import voice_evaluation_to_markdown


class GroundedFeedbackTests(unittest.TestCase):
    answer = "I built a Python API.\nI tested it with 30 cases."

    def setUp(self):
        directory = TemporaryDirectory()
        self.addCleanup(directory.cleanup)
        location = patch.object(config, "DB_PATH", Path(directory.name) / "grounded.db")
        location.start()
        self.addCleanup(location.stop)
        history_location = patch.object(
            history, "DB_PATH", Path(directory.name) / "grounded.db"
        )
        history_location.start()
        self.addCleanup(history_location.stop)
        self.client = TestClient(app)

    def payload(self):
        result = result_for_prompt(VOICE_ANSWER_EVALUATION_PROMPT, self.answer)
        for criterion in result["rubric"].values():
            criterion["quotes"] = [
                "I built a Python API.",
                "I tested it with 30 cases.",
            ]
        return result

    def generate(self, payload, answer=None):
        with patch.object(
            generation, "groq_prompt_call", return_value=json.dumps(payload)
        ):
            return generation.run_json_prompt(
                VOICE_ANSWER_EVALUATION_PROMPT,
                question="Describe your project",
                answer_text=self.answer if answer is None else answer,
                jd_text="Python role",
            )

    def test_valid_quotes_and_score_sum_are_preserved(self):
        result = self.generate(self.payload())
        self.assertEqual(result["score"], 90)
        self.assertEqual(sum(item["points"] for item in result["rubric"].values()), 90)
        self.assertEqual(
            result["rubric"]["depth"]["quotes"][1], "I tested it with 30 cases."
        )
        self.assertEqual(result["rubric_version"], "1")

    def test_invented_paraphrased_and_context_only_quotes_are_rejected_without_echoing_them(
        self,
    ):
        for quote in (
            "I built a Java API.",
            "i built a Python API.",
            "I tested 30 cases.",
            "Python role",
            "SECRET INVENTED TEXT",
        ):
            result = self.payload()
            result["rubric"]["depth"]["quotes"] = [quote]
            with self.subTest(quote=quote), self.assertRaisesRegex(
                GeneratedResultError, "quote not found"
            ) as raised:
                self.generate(result)
            self.assertNotIn(quote, str(raised.exception))

    def test_quotes_preserve_multiline_and_non_ascii_text(self):
        answer = "  Built an API.\nMeasured latency: 12 ms. "
        result = result_for_prompt(VOICE_ANSWER_EVALUATION_PROMPT, answer)
        self.assertEqual(
            self.generate(result, answer)["rubric"]["clarity"]["quotes"], [answer]
        )
        answer = "\u0939\u093f\u0902\u0926\u0940: Python API"
        result = result_for_prompt(VOICE_ANSWER_EVALUATION_PROMPT, answer)
        self.assertEqual(
            self.generate(result, answer)["rubric"]["clarity"]["quotes"], [answer]
        )

    def test_scores_and_fixed_criteria_are_validated(self):
        for points in (-1, 26, True, "20", 20.5):
            result = self.payload()
            result["rubric"]["relevance"]["points"] = points
            with self.subTest(points=points), self.assertRaises(GeneratedResultError):
                self.generate(result)
        result = self.payload()
        result["score"] = 91
        with self.assertRaisesRegex(GeneratedResultError, "score must equal"):
            self.generate(result)
        result = self.payload()
        del result["rubric"]["depth"]
        with self.assertRaises(GeneratedResultError):
            self.generate(result)
        result = self.payload()
        result["rubric_version"] = "2"
        with self.assertRaises(GeneratedResultError):
            self.generate(result)

    def test_missing_criteria_use_zero_and_no_fabricated_evidence(self):
        result = self.payload()
        result["rubric"]["supporting_details"] = {
            "points": 0,
            "reasoning": "The answer lacks concrete details.",
            "evidence_status": "not_demonstrated",
            "quotes": [],
        }
        result["score"] = 68
        self.assertEqual(self.generate(result)["score"], 68)
        for points, quotes in ((1, []), (0, ["I built a Python API."])):
            result["rubric"]["supporting_details"]["points"] = points
            result["rubric"]["supporting_details"]["quotes"] = quotes
            with self.assertRaises(GeneratedResultError):
                self.generate(result)

    def test_demonstrated_criteria_require_real_nonblank_evidence(self):
        for quotes in ([], [" "], ["x" * 2001], ["I built a Python API."] * 4):
            result = self.payload()
            result["rubric"]["relevance"]["quotes"] = quotes
            with self.subTest(quotes=quotes), self.assertRaises(GeneratedResultError):
                self.generate(result)
        with patch.object(
            generation, "groq_prompt_call", return_value=json.dumps(self.payload())
        ), self.assertRaisesRegex(GeneratedResultError, "original answer"):
            generation.run_json_prompt(VOICE_ANSWER_EVALUATION_PROMPT)

    def test_both_voice_api_endpoints_return_grounded_evaluations(self):
        with patch.object(
            generation, "groq_prompt_call", return_value=json.dumps(self.payload())
        ):
            for path in ("/voice/run", "/voice/evaluate-answer"):
                response = self.client.post(
                    path,
                    data={
                        "task": "evaluate_answer",
                        "question": "Describe your project",
                        "answer_text": self.answer,
                        "save_output": "false",
                    },
                )
                self.assertEqual(response.status_code, 200, response.text)
                self.assertEqual(response.json()["evaluation"], self.payload())

    def test_session_persists_evidence_and_invalid_evidence_cannot_advance_it(self):
        created = sessions.create_session(
            "Grounded practice", ["Describe your project"]
        )
        invalid = self.payload()
        invalid["rubric"]["depth"]["quotes"] = ["An invented project"]
        with patch.object(
            generation, "groq_prompt_call", return_value=json.dumps(invalid)
        ):
            response = self.client.post(
                f"/sessions/{created['id']}/answers",
                json={"answer_text": self.answer, "expected_question_index": 0},
            )
        self.assertEqual(response.status_code, 502)
        saved = sessions.get_session(created["id"])
        self.assertEqual(saved["answers"], [])
        self.assertEqual(saved["current_question_index"], 0)
        with patch.object(
            generation, "groq_prompt_call", return_value=json.dumps(self.payload())
        ):
            sessions.submit_answer(created["id"], self.answer, 0)
        self.assertEqual(
            sessions.get_session(created["id"])["answers"][0]["evaluation"],
            self.payload(),
        )

    def test_ui_and_exports_show_evidence_and_support_legacy_saved_results(self):
        result = {
            "evaluation": self.payload(),
            "question": "Describe your project",
            "answer_text": self.answer,
        }
        markdown = voice_evaluation_to_markdown(result)
        self.assertIn("Relevance: 23/25", markdown)
        self.assertIn("> I tested it with 30 cases.", markdown)
        with patch("streamlit_ui.components.render_markdown_pdf_downloads"), patch(
            "streamlit_ui.components.render_json_download"
        ):
            # Pass an ordinary dictionary through session state rather than a module fixture.
            ui = AppTest.from_string(
                "import streamlit as st\nfrom streamlit_ui.components import render_voice_evaluation\nrender_voice_evaluation(st.session_state['result'])",
                default_timeout=10,
            )
            ui.session_state["result"] = result
            ui.run()
            self.assertFalse(ui.exception)
            self.assertFalse(ui.error)
            self.assertEqual(len(ui.expander), 4)
            self.assertTrue(
                any(item.value == "I tested it with 30 cases." for item in ui.text)
            )
            legacy = {
                key: value
                for key, value in self.payload().items()
                if key not in ("rubric", "rubric_version")
            }
            ui.session_state["result"] = {"evaluation": legacy}
            ui.run()
            self.assertFalse(ui.exception)
            self.assertTrue(any("predates" in item.value for item in ui.caption))
            self.assertIn(
                "predates", voice_evaluation_to_markdown({"evaluation": legacy})
            )


if __name__ == "__main__":
    unittest.main()
