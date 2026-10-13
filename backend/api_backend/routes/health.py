"""Service health endpoint."""

from fastapi import APIRouter

from backend import config

router = APIRouter()


@router.get("/health")
async def health():
    return {"status": "ok"}


@router.get("/ui-config")
async def ui_config():
    """Public input and recording limits for the browser frontend; no credentials."""
    return {
        "max_resume_upload_bytes": config.MAX_RESUME_UPLOAD_BYTES,
        "max_audio_upload_bytes": config.MAX_AUDIO_UPLOAD_BYTES,
        "recording_silence_seconds": config.RECORDING_SILENCE_SECONDS,
        "recording_max_seconds": config.RECORDING_MAX_SECONDS,
        "recording_start_timeout_seconds": config.RECORDING_START_TIMEOUT_SECONDS,
        "recording_energy_threshold": config.RECORDING_ENERGY_THRESHOLD,
        "live_transcription_language": config.LIVE_TRANSCRIPTION_LANGUAGE,
        "max_session_questions": config.MAX_SESSION_QUESTIONS,
        "max_session_answer_characters": config.MAX_SESSION_ANSWER_CHARACTERS,
    }
