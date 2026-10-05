"""Microphone recording with automatic stop after a pause in speech."""

from io import BytesIO

import streamlit as st
from audio_recorder_streamlit import audio_recorder

import config


def record_live_audio(label, *, key):
    audio_bytes = audio_recorder(
        text=label,
        pause_threshold=config.RECORDING_SILENCE_SECONDS,
        sample_rate=config.RECORDING_SAMPLE_RATE,
        auto_start=config.RECORDING_AUTO_START,
        key=key,
    )
    start_message = (
        "Recording starts automatically."
        if config.RECORDING_AUTO_START
        else "Click the microphone to start."
    )
    silence_ms = config.RECORDING_SILENCE_SECONDS * 1000
    st.caption(f"{start_message} Recording stops after {silence_ms:g} ms of silence.")
    if not audio_bytes:
        return None

    audio_file = BytesIO(audio_bytes)
    audio_file.name = "live_recording.wav"
    return audio_file
