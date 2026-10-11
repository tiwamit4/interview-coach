"""Browser live transcript preview with final Groq transcription for review."""

import base64
import binascii
from hashlib import sha256
from io import BytesIO
from pathlib import Path

import streamlit as st
import streamlit.components.v1 as components

import config
from services.extraction import extract_audio_bytes
from services.uploads import validate_upload_size
from streamlit_ui.helpers import show_error

_live_recorder = components.declare_component(
    "interview_live_recorder", path=str(Path(__file__).parent / "live_recorder")
)


def decode_recording(result):
    """Validate component data before allocating or transcribing recorded audio."""
    if not isinstance(result, dict) or result.get("status") != "complete":
        return None
    encoded = result.get("audio")
    filename = result.get("filename")
    if not isinstance(encoded, str) or filename not in (
        "live_recording.webm",
        "live_recording.m4a",
    ):
        raise ValueError("The recorder returned invalid audio. Try recording again.")
    # Bound base64 input before decoding (four encoded bytes per three raw bytes).
    validate_upload_size(
        len(encoded), 4 * ((config.MAX_AUDIO_UPLOAD_BYTES + 2) // 3), "audio"
    )
    try:
        content = base64.b64decode(encoded, validate=True)
    except (ValueError, binascii.Error) as exc:
        raise ValueError(
            "The recorder returned invalid audio. Try recording again."
        ) from exc
    validate_upload_size(len(content), config.MAX_AUDIO_UPLOAD_BYTES, "audio")
    if not content:
        raise ValueError("The recording is empty. Try recording again.")
    audio = BytesIO(content)
    audio.name = filename
    return audio


def record_live_audio(label, *, key):
    result = _live_recorder(
        label=label,
        language=config.LIVE_TRANSCRIPTION_LANGUAGE,
        sample_rate=config.RECORDING_SAMPLE_RATE,
        silence_seconds=config.RECORDING_SILENCE_SECONDS,
        max_seconds=config.RECORDING_MAX_SECONDS,
        start_timeout=config.RECORDING_START_TIMEOUT_SECONDS,
        energy_threshold=config.RECORDING_ENERGY_THRESHOLD,
        max_bytes=config.MAX_AUDIO_UPLOAD_BYTES,
        auto_start=config.RECORDING_AUTO_START,
        key=key,
        default=None,
    )
    st.session_state[f"{key}_recording"] = (
        isinstance(result, dict) and result.get("status") == "recording"
    )
    st.caption(
        f"Click to start or stop. Recording stops after {config.RECORDING_SILENCE_SECONDS * 1000:g} ms of silence once speech starts. Maximum: {config.RECORDING_MAX_SECONDS:g} seconds."
    )
    if isinstance(result, dict) and result.get("status") == "error":
        # Do not echo untrusted browser messages or upload data into logs.
        st.error(
            "Recording failed. Check microphone permission and try a shorter recording on HTTPS or localhost."
        )
        return None
    try:
        return decode_recording(result)
    except Exception as exc:
        show_error(exc, operation="live_recording")
        return None


def recording_active(key):
    return bool(st.session_state.get(f"{key}_recording", False))


def review_recorded_answer(audio, *, key):
    """Transcribe each recording once and let the user correct it before evaluation."""
    if audio is None:
        return ""
    digest = sha256(audio.getbuffer()).hexdigest()
    cache_key = f"{key}_transcript"
    cached = st.session_state.get(cache_key)
    failure_key = f"{key}_failed_transcription"
    if st.session_state.get(failure_key) == digest:
        st.warning(
            "The final transcript could not be prepared. Retry transcription or paste your answer instead."
        )
        if not st.button("Retry transcription", key=f"{key}_retry_{digest}"):
            return ""
        st.session_state.pop(failure_key, None)
    if not cached or cached["digest"] != digest:
        # Clear any older transcript before a failed new transcription.
        st.session_state.pop(cache_key, None)
        try:
            with st.spinner("Preparing the final transcript..."):
                text = extract_audio_bytes(audio.getbuffer(), audio.name)
            st.session_state[cache_key] = {"digest": digest, "text": text}
            st.session_state.pop(failure_key, None)
        except Exception as exc:
            st.session_state[failure_key] = digest
            show_error(exc, operation="recording_transcription")
            return ""
    st.audio(audio)
    return st.text_area(
        "Review your transcript",
        value=st.session_state[cache_key]["text"],
        key=f"{key}_review_{digest}",
        height=160,
        help="The live browser preview is approximate. Review this Groq transcript; corrections are used for evaluation.",
    )
