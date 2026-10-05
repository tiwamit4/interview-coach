"""Groq calls with explicit network policy and bounded input/output budgets."""

import os

from dotenv import load_dotenv
from groq import Groq

import config
from errors import ConfigurationError, GroqServiceError, InputTooLongError
from utils.logging_utils import log_info

load_dotenv()


def get_groq_client():
    api_key = os.getenv("GROQ_API_KEY")
    if not api_key:
        raise ConfigurationError(
            "GROQ_API_KEY is missing. Add it to your .env file before using Groq features."
        )
    return Groq(
        api_key=api_key,
        timeout=config.GROQ_TIMEOUT_SECONDS,
        max_retries=config.GROQ_MAX_RETRIES,
    )


def _complete(content, *, temperature, max_tokens):
    if len(content.encode("utf-8")) > config.MAX_CHAT_PROMPT_BYTES:
        limit_kib = config.MAX_CHAT_PROMPT_BYTES / 1024
        raise InputTooLongError(
            f"The combined resume, job description, and prompt are too long (maximum {limit_kib:g} KiB of UTF-8 text). Shorten the documents or select the relevant sections and try again."
        )
    client = get_groq_client()
    budget = min(max_tokens, config.CHAT_MAX_COMPLETION_TOKENS)
    try:
        for attempt in range(config.CHAT_COMPLETION_EXPANSIONS + 1):
            response = client.chat.completions.create(
                model=config.CHAT_MODEL,
                messages=[{"role": "user", "content": content}],
                temperature=temperature,
                max_completion_tokens=budget,
                top_p=config.CHAT_TOP_P,
                stream=False,
                stop=config.CHAT_STOP,
            )
            choice = response.choices[0]
            if getattr(choice, "finish_reason", None) == "length":
                if (
                    attempt < config.CHAT_COMPLETION_EXPANSIONS
                    and budget < config.CHAT_MAX_COMPLETION_TOKENS
                ):
                    budget = min(budget * 2, config.CHAT_MAX_COMPLETION_TOKENS)
                    log_info(
                        "generation_retry",
                        reason="output_truncated",
                        completion_budget=budget,
                    )
                    continue
                raise GroqServiceError(
                    "Groq's response was cut off at the output limit. Shorten the input or increase the configured completion budget and try again."
                )
            if not choice.message.content or not choice.message.content.strip():
                raise GroqServiceError("Groq returned an empty response. Try again.")
            return choice.message.content
    except GroqServiceError:
        raise
    except Exception as exc:
        raise GroqServiceError(
            "Groq could not generate a response right now. Check your API key, quota, and network."
        ) from exc
    finally:
        client.close()


def groq_model_call(text, prompt):
    return _complete(
        prompt.format(resume_text=text, jd_text=text),
        temperature=config.QUESTION_TEMPERATURE,
        max_tokens=config.QUESTION_MAX_COMPLETION_TOKENS,
    )


def groq_prompt_call(prompt, **prompt_values):
    try:
        content = prompt.format(**prompt_values)
    except KeyError as exc:
        raise GroqServiceError(
            f"The prompt is missing a required value: {exc}."
        ) from exc
    return _complete(
        content,
        temperature=config.PROMPT_TEMPERATURE,
        max_tokens=config.PROMPT_MAX_COMPLETION_TOKENS,
    )
