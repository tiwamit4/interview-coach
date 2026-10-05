"""Question generation endpoints and compatibility routes."""

from pathlib import Path

from fastapi import APIRouter, File, Form, HTTPException, UploadFile
from pydantic import HttpUrl
from starlette.concurrency import run_in_threadpool

from api_backend.exceptions import to_http_exception
from api_backend.helpers import (
    extract_jd_resume_inputs,
    extract_resume_upload,
    safe_filename,
    safe_filename_from_url,
    write_text_file,
)
from api_backend.schemas import JobDescriptionRequest, TextRequest
from config import QUESTION, TEXT_PATH
from prompts.prompt import JD_PROMPT, QUESTION_PROMPT, RESUME_JD_PROMPT
from services.extraction import extract_job_description as scrape_job_description
from services.generation import (
    generate_prompt_response as groq_prompt_call,
    generate_questions as groq_model_call,
)
from utils.history import save_history

router = APIRouter()


@router.post("/questions")
async def generate_questions_endpoint(
    jd_url: str | None = Form(None),
    resume: UploadFile | None = File(None),
    text: str | None = Form(None),
    save_output: bool = Form(True),
):
    """
    Generate questions from one flexible endpoint.

    Accepted input combinations:
    - resume only -> resume questions
    - jd_url only -> JD questions
    - text only -> text/resume-style questions
    - resume + jd_url -> targeted JD + resume questions
    """
    if not jd_url and (not resume) and (not text):
        raise HTTPException(
            status_code=400,
            detail="Provide at least one input: jd_url, resume, or text.",
        )
    try:
        result = {"questions": None, "output_path": None}
        if jd_url and resume:
            jd_text, resume_text, resume_name, jd_name = await extract_jd_resume_inputs(
                jd_url, resume
            )
            questions = await run_in_threadpool(
                groq_prompt_call,
                RESUME_JD_PROMPT,
                resume_text=resume_text,
                jd_text=jd_text,
            )
            result.update(
                {
                    "source_type": "jd_resume",
                    "jd": {"url": jd_url, "text": jd_text},
                    "resume": {"filename": resume.filename, "text": resume_text},
                    "questions": questions,
                }
            )
            if save_output:
                result["output_path"] = await run_in_threadpool(
                    write_text_file,
                    QUESTION,
                    f"jd_resume_questions_{resume_name}_{jd_name}.txt",
                    questions,
                )
        elif jd_url:
            jd_text = await run_in_threadpool(scrape_job_description, jd_url)
            questions = await run_in_threadpool(
                groq_prompt_call, JD_PROMPT, jd_text=jd_text
            )
            result.update(
                {
                    "source_type": "jd",
                    "jd": {"url": jd_url, "text": jd_text},
                    "questions": questions,
                }
            )
            if save_output:
                result["output_path"] = await run_in_threadpool(
                    write_text_file,
                    QUESTION,
                    f"jd_questions_{safe_filename_from_url(jd_url)}.txt",
                    questions,
                )
        elif resume:
            resume_text = await extract_resume_upload(resume)
            resume_name = safe_filename(Path(resume.filename).stem)
            questions = await run_in_threadpool(
                groq_prompt_call, QUESTION_PROMPT, resume_text=resume_text
            )
            result.update(
                {
                    "source_type": "resume",
                    "resume": {"filename": resume.filename, "text": resume_text},
                    "questions": questions,
                }
            )
            if save_output:
                result["output_path"] = await run_in_threadpool(
                    write_text_file, QUESTION, f"{resume_name}_questions.txt", questions
                )
        else:
            questions = await run_in_threadpool(
                groq_prompt_call, QUESTION_PROMPT, resume_text=text
            )
            result.update({"source_type": "text", "text": text, "questions": questions})
            if save_output:
                result["output_path"] = await run_in_threadpool(
                    write_text_file, QUESTION, "text_questions.txt", questions
                )
        await run_in_threadpool(
            save_history, "questions", result["source_type"], result
        )
        return result
    except HTTPException:
        raise
    except Exception as exc:
        raise to_http_exception(exc) from exc


@router.post("/jd/questions", deprecated=True)
def generate_jd_questions(request: JobDescriptionRequest):
    try:
        jd_text = scrape_job_description(str(request.url))
        questions = groq_model_call(jd_text, JD_PROMPT)
    except Exception as exc:
        raise to_http_exception(exc) from exc
    output_path = None
    if request.save_output:
        output_path = write_text_file(
            QUESTION,
            f"jd_questions_{safe_filename_from_url(request.url)}.txt",
            questions,
        )
    return {
        "source_url": str(request.url),
        "job_description": jd_text,
        "questions": questions,
        "output_path": output_path,
    }


@router.post("/resume/questions", deprecated=True)
async def generate_resume_questions(
    file: UploadFile = File(...), save_output: bool = True
):
    if not file.filename or not file.filename.lower().endswith(".pdf"):
        raise HTTPException(status_code=400, detail="Please upload a PDF file.")
    try:
        resume_text = await extract_resume_upload(file)
        questions = await run_in_threadpool(
            groq_model_call, resume_text, QUESTION_PROMPT
        )
    except Exception as exc:
        raise to_http_exception(exc) from exc
    stem = safe_filename(Path(file.filename).stem)
    text_output_path = None
    question_output_path = None
    if save_output:
        text_output_path = await run_in_threadpool(
            write_text_file, TEXT_PATH, f"{stem}.txt", resume_text
        )
        question_output_path = await run_in_threadpool(
            write_text_file, QUESTION, f"{stem}_questions.txt", questions
        )
    return {
        "filename": file.filename,
        "resume_text": resume_text,
        "questions": questions,
        "text_output_path": text_output_path,
        "question_output_path": question_output_path,
    }


@router.post("/text/resume/questions", deprecated=True)
def generate_resume_questions_from_text(request: TextRequest):
    if not request.text.strip():
        raise HTTPException(status_code=400, detail="Text cannot be empty.")
    try:
        questions = groq_model_call(request.text, QUESTION_PROMPT)
    except Exception as exc:
        raise to_http_exception(exc) from exc
    output_path = None
    if request.save_output:
        output_name = safe_filename(request.output_name or "resume_text")
        output_path = write_text_file(
            QUESTION, f"{output_name}_questions.txt", questions
        )
    return {"questions": questions, "output_path": output_path}


@router.post("/jd-resume/questions", deprecated=True)
async def generate_jd_resume_questions(
    jd_url: HttpUrl = Form(...),
    resume: UploadFile = File(...),
    save_output: bool = Form(True),
):
    """
    Generate interview questions using both a job-description URL and a resume PDF.
    """
    try:
        jd_text, resume_text, resume_name, jd_name = await extract_jd_resume_inputs(
            jd_url, resume
        )
        questions = await run_in_threadpool(
            groq_prompt_call, RESUME_JD_PROMPT, resume_text=resume_text, jd_text=jd_text
        )
    except Exception as exc:
        raise to_http_exception(exc) from exc
    result = {
        "jd": {"url": str(jd_url), "text": jd_text},
        "resume": {"filename": resume.filename, "text": resume_text},
        "questions": questions,
        "output_path": None,
    }
    if save_output:
        output_filename = f"jd_resume_questions_{resume_name}_{jd_name}.txt"
        result["output_path"] = await run_in_threadpool(
            write_text_file, QUESTION, output_filename, questions
        )
    await run_in_threadpool(
        save_history, "jd_resume_questions", f"{resume.filename} + {jd_name}", result
    )
    return result
