"""Streamlit validation and error presentation adapters for shared services."""

import json

import streamlit as st

from errors import GroqServiceError
from services import generation
from services.files import (
    safe_filename,
    safe_filename_from_url,
    save_result,
    write_json_file,
    write_text_file,
)
from services.generation import generate_prompt_response
from utils.logging_utils import log_error


def generate_questions(source_text, prompt):
    if not source_text.strip():
        raise ValueError("No text was extracted.")
    return generation.generate_questions(source_text, prompt)


def parse_json_response(response_text):
    try:
        return generation.parse_json_response(response_text)
    except json.JSONDecodeError as exc:
        raise GroqServiceError("Groq returned invalid JSON. Try again.") from exc


def run_json_prompt(prompt, **values):
    try:
        return generation.run_json_prompt(prompt, **values)
    except json.JSONDecodeError as exc:
        raise GroqServiceError("Groq returned invalid JSON. Try again.") from exc


def show_error(exc, *, operation):
    log_error(exc, event="ui_operation_failed", operation=operation)
    st.error(str(exc))
