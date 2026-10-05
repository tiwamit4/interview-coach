"""Document and audio extraction independent of web frameworks."""

from contextlib import contextmanager
from pathlib import Path
from tempfile import NamedTemporaryFile

import config
from jd.extract_text import scrape_job_description
from resume.extract_text import read_pdf
from services.uploads import validate_upload_size
from utils.logging_utils import log_operation
from voice.groq_voice_text import transcribe_audio, translate_audio


@contextmanager
def temporary_upload(content, suffix):
    """Close uploads before reading them and remove them even when extraction fails."""
    temp_path = None
    try:
        with NamedTemporaryFile(delete=False, suffix=suffix) as temp_file:
            temp_path = Path(temp_file.name)
            temp_file.write(content)
        yield temp_path
    finally:
        if temp_path:
            temp_path.unlink(missing_ok=True)


def extract_job_description(url):
    with log_operation("extract_job_description"):
        return scrape_job_description(str(url))


def extract_resume_bytes(content, filename):
    if not filename or not filename.lower().endswith(".pdf"):
        raise ValueError("Please upload a PDF resume.")
    validate_upload_size(len(content), config.MAX_RESUME_UPLOAD_BYTES, "resume")
    with (
        log_operation("extract_resume", size_bytes=len(content)),
        temporary_upload(content, ".pdf") as temp_path,
    ):
        return read_pdf(temp_path)


def extract_audio_bytes(content, filename, *, translate=False, **options):
    validate_upload_size(len(content), config.MAX_AUDIO_UPLOAD_BYTES, "audio")
    suffix = Path(filename or "audio.wav").suffix or ".wav"
    operation = "translate_audio" if translate else "transcribe_audio"
    with (
        log_operation(operation, size_bytes=len(content)),
        temporary_upload(content, suffix) as temp_path,
    ):
        convert = translate_audio if translate else transcribe_audio
        return convert(temp_path, **options)
