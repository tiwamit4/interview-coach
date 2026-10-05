"""
Speech-to-text helpers.

This module converts audio input to text output using Groq Whisper. It does not
generate audio output.
"""

from pathlib import Path

from dotenv import load_dotenv

from config import (
    VOICE_AUDIO_PATH,
    VOICE_LANGUAGE,
    VOICE_MODEL,
    VOICE_PROMPT,
    VOICE_RESPONSE_FORMAT,
    VOICE_TEMPERATURE,
    VOICE_TRANSLATE,
)
from errors import GroqServiceError
from utils.groq_service import get_groq_client
from utils.logging_utils import log_error

load_dotenv()

DEFAULT_MODEL = VOICE_MODEL
DEFAULT_TEMPERATURE = VOICE_TEMPERATURE


def transcribe_audio(
    audio_path,
    model=DEFAULT_MODEL,
    language=VOICE_LANGUAGE,
    prompt=VOICE_PROMPT,
    response_format=VOICE_RESPONSE_FORMAT,
    temperature=DEFAULT_TEMPERATURE,
):
    """
    Convert an audio file to text using Groq's whisper-large-v3 model.
    Supported response formats include json, text, srt, verbose_json, and vtt.
    """
    path = Path(audio_path)
    if not path.exists():
        raise FileNotFoundError(f"Audio file not found: {path}")

    request = {
        "file": (path.name, path.read_bytes()),
        "model": model,
        "response_format": response_format,
        "temperature": temperature,
    }

    if language:
        request["language"] = language
    if prompt:
        request["prompt"] = prompt

    client = get_groq_client()
    try:
        transcription = client.audio.transcriptions.create(**request)
    except Exception as exc:
        raise GroqServiceError(
            "Groq could not transcribe the audio right now. Check your API key, quota, and network."
        ) from exc
    finally:
        client.close()

    if response_format == "text":
        return transcription
    text = getattr(transcription, "text", transcription)
    if not text:
        raise GroqServiceError(
            "Groq returned an empty transcript. Try a clearer or longer recording."
        )
    return text


def translate_audio(
    audio_path,
    model=DEFAULT_MODEL,
    prompt=VOICE_PROMPT,
    response_format=VOICE_RESPONSE_FORMAT,
    temperature=DEFAULT_TEMPERATURE,
):
    """
    Convert non-English audio to English text using Groq's whisper-large-v3 model.
    """
    path = Path(audio_path)
    if not path.exists():
        raise FileNotFoundError(f"Audio file not found: {path}")

    request = {
        "file": (path.name, path.read_bytes()),
        "model": model,
        "response_format": response_format,
        "temperature": temperature,
    }

    if prompt:
        request["prompt"] = prompt

    client = get_groq_client()
    try:
        translation = client.audio.translations.create(**request)
    except Exception as exc:
        raise GroqServiceError(
            "Groq could not translate the audio right now. Check your API key, quota, and network."
        ) from exc
    finally:
        client.close()

    if response_format == "text":
        return translation
    text = getattr(translation, "text", translation)
    if not text:
        raise GroqServiceError(
            "Groq returned an empty translation. Try a clearer or longer recording."
        )
    return text


def main():
    """Convert the audio file selected in config.py without command-line options."""
    if VOICE_TRANSLATE:
        text = translate_audio(VOICE_AUDIO_PATH)
    else:
        text = transcribe_audio(VOICE_AUDIO_PATH)

    print(text)


if __name__ == "__main__":
    try:
        main()
    except Exception as exc:
        log_error(exc, event="cli_operation_failed", operation="speech_to_text")
        raise
