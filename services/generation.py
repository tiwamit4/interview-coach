"""Shared question generation, prompt execution, and JSON parsing."""

import json

from pydantic import TypeAdapter, ValidationError

from errors import ConfigurationError, GeneratedResultError
from prompts.prompt import (
    COVER_LETTER_PROMPT,
    INTERVIEW_PREP_PROMPT,
    MATCH_SCORE_PROMPT,
    RESUME_IMPROVEMENT_PROMPT,
    VOICE_ANSWER_EVALUATION_PROMPT,
    SESSION_FOLLOWUP_PROMPT,
)
from services.result_models import (
    ApplicationMessages,
    GeneratedResult,
    InterviewPrep,
    MatchAnalysis,
    NonEmptyText,
    ResumeImprovements,
    VoiceEvaluation,
    FollowUpQuestion,
)
from utils.groq_service import groq_model_call, groq_prompt_call
from utils.logging_utils import log_info, log_operation

RESPONSE_MODELS = {
    MATCH_SCORE_PROMPT: MatchAnalysis,
    INTERVIEW_PREP_PROMPT: InterviewPrep,
    COVER_LETTER_PROMPT: ApplicationMessages,
    RESUME_IMPROVEMENT_PROMPT: ResumeImprovements,
    VOICE_ANSWER_EVALUATION_PROMPT: VoiceEvaluation,
    SESSION_FOLLOWUP_PROMPT: FollowUpQuestion,
}
RESULT_NAMES = {
    MatchAnalysis: "match analysis",
    InterviewPrep: "interview preparation",
    ApplicationMessages: "application messages",
    ResumeImprovements: "resume improvements",
    VoiceEvaluation: "answer evaluation",
    FollowUpQuestion: "follow-up question",
}
TEXT_RESULT = TypeAdapter(NonEmptyText)


def validate_text_response(response):
    try:
        return TEXT_RESULT.validate_python(response, strict=True)
    except ValidationError as exc:
        raise GeneratedResultError(
            "Groq returned an empty or invalid text response. Try generating again."
        ) from exc


def generate_questions(source_text, prompt):
    with log_operation("generate_questions"):
        return validate_text_response(groq_model_call(source_text, prompt))


def generate_prompt_response(prompt, **prompt_values):
    model = RESPONSE_MODELS.get(prompt)
    operation = RESULT_NAMES.get(model, "generate_questions")
    with log_operation(operation):
        return validate_text_response(groq_prompt_call(prompt, **prompt_values))


def parse_json_response(response_text):
    try:
        return json.loads(response_text)
    except json.JSONDecodeError:
        start = response_text.find("{")
        end = response_text.rfind("}")
        if start != -1 and end > start:
            return json.loads(response_text[start : end + 1])
        raise


def run_json_prompt(
    prompt, *, response_model: type[GeneratedResult] | None = None, **values
):
    """Validate structured output before rendering, saving, or returning it."""
    model = response_model or RESPONSE_MODELS.get(prompt)
    if model is None:
        raise ConfigurationError(
            "No response model is configured for this JSON prompt."
        )
    name = RESULT_NAMES.get(model, "generated result")
    response_text = generate_prompt_response(prompt, **values)
    try:
        payload = parse_json_response(response_text)
    except json.JSONDecodeError as exc:
        raise GeneratedResultError(
            f"Groq returned invalid JSON for {name}. Try generating again."
        ) from exc
    try:
        result = model.model_validate(
            payload, strict=True, context={"answer_text": values.get("answer_text")}
        ).model_dump(mode="json")
    except ValidationError as exc:
        issues = []
        for error in exc.errors(include_input=False, include_url=False)[:3]:
            location = ".".join(str(part) for part in error["loc"]) or "response"
            issues.append(f"{location}: {error['msg']}")
        raise GeneratedResultError(
            f"Groq returned invalid {name}. {'; '.join(issues)}. Try generating again."
        ) from exc
    log_info("result_validated", response_model=model.__name__)
    return result
