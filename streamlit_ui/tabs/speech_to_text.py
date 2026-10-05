"""Speech to text tab rendering."""

from pathlib import Path

import streamlit as st

import config
from config import TRANSCRIPT_PATH, VOICE_MODEL as DEFAULT_MODEL
from services.extraction import extract_audio_bytes
from streamlit_ui.components import render_transcript
from streamlit_ui.helpers import safe_filename, show_error, write_text_file
from streamlit_ui.recorder import record_live_audio


def convert_speech_to_text(
    audio_file,
    selected_language,
    language_options,
    translate_to_english,
    voice_prompt,
    save_transcript,
):
    try:
        suffix = Path(audio_file.name).suffix or ".wav"
        st.audio(audio_file)
        with st.spinner("Converting speech to text with Groq Whisper..."):
            if translate_to_english:
                transcript = extract_audio_bytes(
                    audio_file.getbuffer(),
                    audio_file.name,
                    translate=True,
                    model=DEFAULT_MODEL,
                    prompt=voice_prompt or None,
                )
            else:
                transcript = extract_audio_bytes(
                    audio_file.getbuffer(),
                    audio_file.name,
                    model=DEFAULT_MODEL,
                    language=language_options[selected_language],
                    prompt=voice_prompt or None,
                )
        output_path = None
        if save_transcript:
            stem = safe_filename(Path(audio_file.name).stem or "live_recording")
            output_path = write_text_file(
                TRANSCRIPT_PATH, f"{stem}_transcript.txt", transcript
            )
        render_transcript(transcript, output_path)
    except Exception as exc:
        show_error(exc, operation="speech_to_text")


def render_voice_tab():
    st.header("Speech to Text")
    st.caption("Upload or record audio, then convert it into a text transcript.")
    st.caption(f"Model: **{DEFAULT_MODEL}**")
    voice_mode = st.radio(
        "Input type", ["Upload audio file", "Record live speech"], horizontal=True
    )
    uploaded_audio = None
    live_audio = None
    if voice_mode == "Upload audio file":
        uploaded_audio = st.file_uploader(
            "Upload audio",
            type=["mp3", "mp4", "mpeg", "mpga", "m4a", "wav", "webm", "mpg", "mpeg4"],
            max_upload_size=config.MAX_AUDIO_UPLOAD_MB,
        )
    else:
        live_audio = record_live_audio(
            "Record live speech", key="speech_to_text_recorder"
        )
    language_options = {"Auto detect": None, "English": "en", "Hindi": "hi"}
    selected_language = st.selectbox("Language hint", list(language_options.keys()))
    translate_to_english = st.checkbox("Translate transcript to English", value=False)
    voice_prompt = st.text_input(
        "Optional context prompt",
        placeholder="Example: Technical interview conversation about data science",
    )
    save_transcript = st.checkbox(
        f"Save transcript to {TRANSCRIPT_PATH}", value=True, key="save_voice_transcript"
    )
    generate_transcript = st.button("Convert Speech to Text", type="primary")
    audio_file = uploaded_audio if voice_mode == "Upload audio file" else live_audio
    if generate_transcript and audio_file:
        convert_speech_to_text(
            audio_file,
            selected_language,
            language_options,
            translate_to_english,
            voice_prompt,
            save_transcript,
        )
    elif generate_transcript and (not audio_file):
        if voice_mode == "Upload audio file":
            st.warning("Upload an audio file first.")
        else:
            st.warning("Record your speech first.")
