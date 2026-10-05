"""Reject malformed AI results before application code consumes them."""

import json
import unittest
from unittest.mock import patch

from errors import ConfigurationError, GeneratedResultError
from prompts.prompt import MATCH_SCORE_PROMPT, VOICE_ANSWER_EVALUATION_PROMPT
from result_fixtures import RESULTS, result_for_prompt
from services import generation
from services.result_models import VoiceEvaluation


class GeneratedResultTests(unittest.TestCase):
    def generate(self, prompt, payload):
        with patch.object(
            generation, "groq_prompt_call", return_value=json.dumps(payload)
        ):
            return generation.run_json_prompt(prompt)

    def test_all_complete_response_shapes_are_preserved(self):
        for prompt, result in RESULTS.items():
            with self.subTest(model=generation.RESPONSE_MODELS[prompt].__name__):
                self.assertEqual(self.generate(prompt, result), result)
                with patch.object(
                    generation,
                    "groq_prompt_call",
                    return_value="```json\n" + json.dumps(result) + "\n```",
                ):
                    self.assertEqual(generation.run_json_prompt(prompt), result)

    def test_missing_required_fields_and_wrong_root_types(self):
        for prompt in RESULTS:
            for payload in ({}, [], None, "text"):
                with self.subTest(prompt=prompt, payload=payload), self.assertRaises(
                    GeneratedResultError
                ):
                    self.generate(prompt, payload)

    def test_scores_are_strict_integers_in_range(self):
        for prompt, field in (
            (MATCH_SCORE_PROMPT, "role_fit_score"),
            (VOICE_ANSWER_EVALUATION_PROMPT, "score"),
        ):
            for score in (-1, 101, "90", True, 90.5, None):
                payload = result_for_prompt(prompt)
                payload[field] = score
                with self.subTest(field=field, score=score), self.assertRaisesRegex(
                    GeneratedResultError, field
                ):
                    self.generate(prompt, payload)
            for score in (0, 100):
                payload = result_for_prompt(prompt)
                payload[field] = score
                self.assertEqual(self.generate(prompt, payload)[field], score)

    def test_nested_items_blank_strings_and_unexpected_fields(self):
        for value, field in (
            (["Python"], "matched_skills"),
            ([{"skill": "Python"}], "matched_skills"),
            (
                [
                    {
                        "skill": " ",
                        "resume_evidence": "Evidence",
                        "jd_evidence": "Evidence",
                    }
                ],
                "matched_skills",
            ),
            ("Python", "matched_skills"),
            ([123], "improvement_suggestions"),
            ([" "], "improvement_suggestions"),
            (" ", "summary"),
        ):
            payload = result_for_prompt(MATCH_SCORE_PROMPT)
            payload[field] = value
            with self.subTest(value=value, field=field), self.assertRaisesRegex(
                GeneratedResultError, field
            ):
                self.generate(MATCH_SCORE_PROMPT, payload)
        payload = result_for_prompt(MATCH_SCORE_PROMPT)
        payload["unexpected"] = "Confidential model output"
        with self.assertRaises(GeneratedResultError) as raised:
            self.generate(MATCH_SCORE_PROMPT, payload)
        self.assertIn("unexpected", str(raised.exception))
        self.assertNotIn("Confidential model output", str(raised.exception))

    def test_empty_lists_are_valid_but_required(self):
        for prompt, original in RESULTS.items():
            payload = {
                key: [] if isinstance(value, list) else value
                for key, value in original.items()
            }
            self.assertEqual(self.generate(prompt, payload), payload)

    def test_invalid_json_and_empty_text_produce_clear_errors(self):
        for text in ("invalid JSON", "{broken}"):
            with patch.object(
                generation, "groq_prompt_call", return_value=text
            ), self.assertRaisesRegex(
                GeneratedResultError, "invalid JSON for match analysis"
            ):
                generation.run_json_prompt(MATCH_SCORE_PROMPT)
        for text in ("", " ", None, 123):
            with patch.object(
                generation, "groq_prompt_call", return_value=text
            ), self.assertRaisesRegex(GeneratedResultError, "invalid text response"):
                generation.generate_prompt_response("prompt")
            with patch.object(
                generation, "groq_model_call", return_value=text
            ), self.assertRaises(GeneratedResultError):
                generation.generate_questions("resume", "prompt")

    def test_unknown_prompts_require_explicit_model(self):
        with patch.object(generation, "groq_prompt_call") as call, self.assertRaises(
            ConfigurationError
        ):
            generation.run_json_prompt("new prompt")
        call.assert_not_called()
        payload = result_for_prompt(VOICE_ANSWER_EVALUATION_PROMPT)
        with patch.object(
            generation, "groq_prompt_call", return_value=json.dumps(payload)
        ):
            self.assertEqual(
                generation.run_json_prompt(
                    "new prompt", response_model=VoiceEvaluation
                ),
                payload,
            )


if __name__ == "__main__":
    unittest.main()
