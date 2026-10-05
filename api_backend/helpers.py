"""FastAPI upload and output adapters for shared services."""

from pathlib import Path

from fastapi import HTTPException
from starlette.concurrency import run_in_threadpool

import config
from services import files
from services.extraction import (
    extract_audio_bytes,
    extract_job_description,
    extract_resume_bytes,
)
from services.files import safe_filename, safe_filename_from_url
from services.generation import parse_json_response, run_json_prompt
from services.uploads import read_upload


def write_text_file(directory, filename, content):
    return str(files.write_text_file(directory, filename, content))


def write_json_file(directory, filename, content):
    return str(files.write_json_file(directory, filename, content))


async def extract_resume_upload(resume):
    if not resume.filename or not resume.filename.lower().endswith(".pdf"):
        raise HTTPException(status_code=400, detail="Please upload a PDF resume.")
    content = await read_upload(resume, config.MAX_RESUME_UPLOAD_BYTES, "resume")
    return await run_in_threadpool(extract_resume_bytes, content, resume.filename)


async def extract_audio_upload(audio, **options):
    content = await read_upload(audio, config.MAX_AUDIO_UPLOAD_BYTES, "audio")
    return await run_in_threadpool(
        extract_audio_bytes, content, audio.filename, **options
    )


async def extract_jd_resume_inputs(jd_url, resume):
    resume_text = await extract_resume_upload(resume)
    jd_text = await run_in_threadpool(extract_job_description, jd_url)
    resume_name = safe_filename(Path(resume.filename).stem)
    jd_name = safe_filename_from_url(jd_url)
    return (jd_text, resume_text, resume_name, jd_name)
