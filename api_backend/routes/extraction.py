"""Job description and resume extraction endpoint."""

from fastapi import APIRouter, File, Form, UploadFile
from pydantic import HttpUrl
from starlette.concurrency import run_in_threadpool

from api_backend.exceptions import to_http_exception
from api_backend.helpers import extract_jd_resume_inputs, write_json_file
from config import JSON_PATH
from utils.history import save_history

router = APIRouter()


@router.post("/extract/jd-resume")
async def extract_jd_and_resume(
    jd_url: HttpUrl = Form(...),
    resume: UploadFile = File(...),
    save_output: bool = Form(True),
):
    """
    Extract text from a job-description URL and a resume PDF, then save both
    extracted texts in one JSON file.
    """
    try:
        jd_text, resume_text, resume_name, jd_name = await extract_jd_resume_inputs(
            jd_url, resume
        )
    except Exception as exc:
        raise to_http_exception(exc) from exc
    result = {
        "jd": {"url": str(jd_url), "text": jd_text},
        "resume": {"filename": resume.filename, "text": resume_text},
        "output_path": None,
    }
    if save_output:
        output_filename = f"extracted_{resume_name}_{jd_name}.json"
        result["output_path"] = await run_in_threadpool(
            write_json_file, JSON_PATH, output_filename, result
        )
    await run_in_threadpool(
        save_history, "extract_jd_resume", f"{resume.filename} + {jd_name}", result
    )
    return result
