"""Compatibility endpoints for analysis and application preparation."""

import json

from fastapi import APIRouter, File, Form, HTTPException, UploadFile
from pydantic import HttpUrl
from starlette.concurrency import run_in_threadpool

from api_backend.exceptions import to_http_exception
from api_backend.helpers import (
    extract_jd_resume_inputs,
    run_json_prompt,
    write_json_file,
)
from config import (
    ANALYSIS_PATH,
    APPLICATIONS_PATH,
    MATCH_PATH,
    PREP_PATH,
    RESUME_IMPROVEMENTS_PATH,
)
from prompts.prompt import (
    COVER_LETTER_PROMPT,
    INTERVIEW_PREP_PROMPT,
    MATCH_SCORE_PROMPT,
    RESUME_IMPROVEMENT_PROMPT,
)
from utils.history import save_history

router = APIRouter()


@router.post("/analyze/jd-resume-match", deprecated=True)
async def analyze_jd_resume_match(
    jd_url: HttpUrl = Form(...),
    resume: UploadFile = File(...),
    save_output: bool = Form(True),
):
    """
    Compare a resume PDF with a job-description URL and return a structured
    match score with matched skills, missing skills, and improvement ideas.
    """
    try:
        jd_text, resume_text, resume_name, jd_name = await extract_jd_resume_inputs(
            jd_url, resume
        )
        match_analysis = await run_in_threadpool(
            run_json_prompt,
            MATCH_SCORE_PROMPT,
            resume_text=resume_text,
            jd_text=jd_text,
        )
    except json.JSONDecodeError as exc:
        raise HTTPException(
            status_code=500, detail="Groq returned invalid JSON for match analysis."
        ) from exc
    except Exception as exc:
        raise to_http_exception(exc) from exc
    result = {
        "jd": {"url": str(jd_url), "text": jd_text},
        "resume": {"filename": resume.filename, "text": resume_text},
        "match_analysis": match_analysis,
        "output_path": None,
    }
    if save_output:
        output_filename = f"match_{resume_name}_{jd_name}.json"
        result["output_path"] = await run_in_threadpool(
            write_json_file, MATCH_PATH, output_filename, result
        )
    await run_in_threadpool(
        save_history, "match_analysis", f"{resume.filename} + {jd_name}", result
    )
    return result


@router.post("/prep/interview", deprecated=True)
async def generate_interview_prep(
    jd_url: HttpUrl = Form(...),
    resume: UploadFile = File(...),
    save_output: bool = Form(True),
):
    try:
        jd_text, resume_text, resume_name, jd_name = await extract_jd_resume_inputs(
            jd_url, resume
        )
        prep = await run_in_threadpool(
            run_json_prompt,
            INTERVIEW_PREP_PROMPT,
            resume_text=resume_text,
            jd_text=jd_text,
        )
    except json.JSONDecodeError as exc:
        raise HTTPException(
            status_code=502, detail="Groq returned invalid JSON for interview prep."
        ) from exc
    except Exception as exc:
        raise to_http_exception(exc) from exc
    result = {
        "jd": {"url": str(jd_url), "text": jd_text},
        "resume": {"filename": resume.filename, "text": resume_text},
        "interview_prep": prep,
        "output_path": None,
    }
    if save_output:
        output_filename = f"prep_{resume_name}_{jd_name}.json"
        result["output_path"] = await run_in_threadpool(
            write_json_file, PREP_PATH, output_filename, result
        )
    await run_in_threadpool(
        save_history, "interview_prep", f"{resume.filename} + {jd_name}", result
    )
    return result


@router.post("/generate/cover-letter", deprecated=True)
async def generate_cover_letter(
    jd_url: HttpUrl = Form(...),
    resume: UploadFile = File(...),
    save_output: bool = Form(True),
):
    try:
        jd_text, resume_text, resume_name, jd_name = await extract_jd_resume_inputs(
            jd_url, resume
        )
        application_messages = await run_in_threadpool(
            run_json_prompt,
            COVER_LETTER_PROMPT,
            resume_text=resume_text,
            jd_text=jd_text,
        )
    except json.JSONDecodeError as exc:
        raise HTTPException(
            status_code=502, detail="Groq returned invalid JSON for cover letter."
        ) from exc
    except Exception as exc:
        raise to_http_exception(exc) from exc
    result = {
        "jd": {"url": str(jd_url), "text": jd_text},
        "resume": {"filename": resume.filename, "text": resume_text},
        "application_messages": application_messages,
        "output_path": None,
    }
    if save_output:
        output_filename = f"application_{resume_name}_{jd_name}.json"
        result["output_path"] = await run_in_threadpool(
            write_json_file, APPLICATIONS_PATH, output_filename, result
        )
    await run_in_threadpool(
        save_history, "cover_letter", f"{resume.filename} + {jd_name}", result
    )
    return result


@router.post("/improve/resume", deprecated=True)
async def improve_resume_for_jd(
    jd_url: HttpUrl = Form(...),
    resume: UploadFile = File(...),
    save_output: bool = Form(True),
):
    try:
        jd_text, resume_text, resume_name, jd_name = await extract_jd_resume_inputs(
            jd_url, resume
        )
        improvements = await run_in_threadpool(
            run_json_prompt,
            RESUME_IMPROVEMENT_PROMPT,
            resume_text=resume_text,
            jd_text=jd_text,
        )
    except json.JSONDecodeError as exc:
        raise HTTPException(
            status_code=502,
            detail="Groq returned invalid JSON for resume improvements.",
        ) from exc
    except Exception as exc:
        raise to_http_exception(exc) from exc
    result = {
        "jd": {"url": str(jd_url), "text": jd_text},
        "resume": {"filename": resume.filename, "text": resume_text},
        "resume_improvements": improvements,
        "output_path": None,
    }
    if save_output:
        output_filename = f"resume_improvements_{resume_name}_{jd_name}.json"
        result["output_path"] = await run_in_threadpool(
            write_json_file, RESUME_IMPROVEMENTS_PATH, output_filename, result
        )
    await run_in_threadpool(
        save_history, "resume_improvement", f"{resume.filename} + {jd_name}", result
    )
    return result


@router.post("/analyze/jd-resume", deprecated=True)
async def analyze_jd_resume(
    jd_url: HttpUrl = Form(...),
    resume: UploadFile = File(...),
    save_output: bool = Form(True),
):
    try:
        jd_text, resume_text, resume_name, jd_name = await extract_jd_resume_inputs(
            jd_url, resume
        )
        match_analysis = await run_in_threadpool(
            run_json_prompt,
            MATCH_SCORE_PROMPT,
            resume_text=resume_text,
            jd_text=jd_text,
        )
        interview_prep = await run_in_threadpool(
            run_json_prompt,
            INTERVIEW_PREP_PROMPT,
            resume_text=resume_text,
            jd_text=jd_text,
        )
        resume_improvements = await run_in_threadpool(
            run_json_prompt,
            RESUME_IMPROVEMENT_PROMPT,
            resume_text=resume_text,
            jd_text=jd_text,
        )
    except json.JSONDecodeError as exc:
        raise HTTPException(
            status_code=502, detail="Groq returned invalid JSON for combined analysis."
        ) from exc
    except Exception as exc:
        raise to_http_exception(exc) from exc
    result = {
        "jd": {"url": str(jd_url), "text": jd_text},
        "resume": {"filename": resume.filename, "text": resume_text},
        "match_analysis": match_analysis,
        "interview_prep": interview_prep,
        "resume_improvements": resume_improvements,
        "output_path": None,
    }
    if save_output:
        output_filename = f"analysis_{resume_name}_{jd_name}.json"
        result["output_path"] = await run_in_threadpool(
            write_json_file, ANALYSIS_PATH, output_filename, result
        )
    await run_in_threadpool(
        save_history, "jd_resume_analysis", f"{resume.filename} + {jd_name}", result
    )
    return result
