"""Main text workflow endpoint."""

import json
from pathlib import Path

from fastapi import APIRouter, File, Form, HTTPException, UploadFile
from starlette.concurrency import run_in_threadpool

from api_backend.exceptions import to_http_exception
from api_backend.helpers import (
    extract_jd_resume_inputs,
    extract_resume_upload,
    run_json_prompt,
    safe_filename,
    safe_filename_from_url,
    write_json_file,
    write_text_file,
)
from config import (
    ANALYSIS_PATH,
    APPLICATIONS_PATH,
    MATCH_PATH,
    PREP_PATH,
    QUESTION,
    RESUME_IMPROVEMENTS_PATH,
)
from prompts.prompt import (
    COVER_LETTER_PROMPT,
    INTERVIEW_PREP_PROMPT,
    JD_PROMPT,
    MATCH_SCORE_PROMPT,
    QUESTION_PROMPT,
    RESUME_IMPROVEMENT_PROMPT,
    RESUME_JD_PROMPT,
)
from services.extraction import extract_job_description as scrape_job_description
from services.generation import generate_prompt_response as groq_prompt_call
from utils.history import save_history

router = APIRouter()


@router.post("/run")
async def run_task(
    task: str = Form(...),
    jd_url: str | None = Form(None),
    resume: UploadFile | None = File(None),
    text: str | None = Form(None),
    save_output: bool = Form(True),
):
    """
    Main text workflow endpoint.

    Supported tasks:
    jd_questions, resume_questions, jd_resume_questions, match_score,
    interview_prep, cover_letter, resume_improvement, full_analysis.
    """
    task = task.strip().lower()
    try:
        if task == "jd_questions":
            if not jd_url:
                raise HTTPException(status_code=400, detail="jd_url is required.")
            jd_text = await run_in_threadpool(scrape_job_description, jd_url)
            questions = await run_in_threadpool(
                groq_prompt_call, JD_PROMPT, jd_text=jd_text
            )
            result = {
                "task": task,
                "jd": {"url": jd_url, "text": jd_text},
                "questions": questions,
                "output_path": None,
            }
            if save_output:
                result["output_path"] = await run_in_threadpool(
                    write_text_file,
                    QUESTION,
                    f"jd_questions_{safe_filename_from_url(jd_url)}.txt",
                    questions,
                )
            await run_in_threadpool(
                save_history, task, safe_filename_from_url(jd_url), result
            )
            return result
        if task == "resume_questions":
            if resume:
                resume_text = await extract_resume_upload(resume)
                resume_name = safe_filename(Path(resume.filename).stem)
                filename = resume.filename
            elif text:
                resume_text = text
                resume_name = "resume_text"
                filename = None
            else:
                raise HTTPException(
                    status_code=400, detail="resume file or text is required."
                )
            questions = await run_in_threadpool(
                groq_prompt_call, QUESTION_PROMPT, resume_text=resume_text
            )
            result = {
                "task": task,
                "resume": {"filename": filename, "text": resume_text},
                "questions": questions,
                "output_path": None,
            }
            if save_output:
                result["output_path"] = await run_in_threadpool(
                    write_text_file, QUESTION, f"{resume_name}_questions.txt", questions
                )
            await run_in_threadpool(save_history, task, resume_name, result)
            return result
        if task not in {
            "jd_resume_questions",
            "match_score",
            "interview_prep",
            "cover_letter",
            "resume_improvement",
            "full_analysis",
        }:
            raise HTTPException(status_code=400, detail=f"Unsupported task: {task}")
        if not jd_url or not resume:
            raise HTTPException(
                status_code=400, detail="jd_url and resume are required for this task."
            )
        jd_text, resume_text, resume_name, jd_name = await extract_jd_resume_inputs(
            jd_url, resume
        )
        result = {
            "task": task,
            "jd": {"url": jd_url, "text": jd_text},
            "resume": {"filename": resume.filename, "text": resume_text},
            "output_path": None,
        }
        if task == "jd_resume_questions":
            questions = await run_in_threadpool(
                groq_prompt_call,
                RESUME_JD_PROMPT,
                resume_text=resume_text,
                jd_text=jd_text,
            )
            result["questions"] = questions
            if save_output:
                result["output_path"] = await run_in_threadpool(
                    write_text_file,
                    QUESTION,
                    f"jd_resume_questions_{resume_name}_{jd_name}.txt",
                    questions,
                )
        elif task == "match_score":
            result["match_analysis"] = await run_in_threadpool(
                run_json_prompt,
                MATCH_SCORE_PROMPT,
                resume_text=resume_text,
                jd_text=jd_text,
            )
            if save_output:
                result["output_path"] = await run_in_threadpool(
                    write_json_file,
                    MATCH_PATH,
                    f"match_{resume_name}_{jd_name}.json",
                    result,
                )
        elif task == "interview_prep":
            result["interview_prep"] = await run_in_threadpool(
                run_json_prompt,
                INTERVIEW_PREP_PROMPT,
                resume_text=resume_text,
                jd_text=jd_text,
            )
            if save_output:
                result["output_path"] = await run_in_threadpool(
                    write_json_file,
                    PREP_PATH,
                    f"prep_{resume_name}_{jd_name}.json",
                    result,
                )
        elif task == "cover_letter":
            result["application_messages"] = await run_in_threadpool(
                run_json_prompt,
                COVER_LETTER_PROMPT,
                resume_text=resume_text,
                jd_text=jd_text,
            )
            if save_output:
                result["output_path"] = await run_in_threadpool(
                    write_json_file,
                    APPLICATIONS_PATH,
                    f"application_{resume_name}_{jd_name}.json",
                    result,
                )
        elif task == "resume_improvement":
            result["resume_improvements"] = await run_in_threadpool(
                run_json_prompt,
                RESUME_IMPROVEMENT_PROMPT,
                resume_text=resume_text,
                jd_text=jd_text,
            )
            if save_output:
                result["output_path"] = await run_in_threadpool(
                    write_json_file,
                    RESUME_IMPROVEMENTS_PATH,
                    f"resume_improvements_{resume_name}_{jd_name}.json",
                    result,
                )
        elif task == "full_analysis":
            result["match_analysis"] = await run_in_threadpool(
                run_json_prompt,
                MATCH_SCORE_PROMPT,
                resume_text=resume_text,
                jd_text=jd_text,
            )
            result["interview_prep"] = await run_in_threadpool(
                run_json_prompt,
                INTERVIEW_PREP_PROMPT,
                resume_text=resume_text,
                jd_text=jd_text,
            )
            result["resume_improvements"] = await run_in_threadpool(
                run_json_prompt,
                RESUME_IMPROVEMENT_PROMPT,
                resume_text=resume_text,
                jd_text=jd_text,
            )
            if save_output:
                result["output_path"] = await run_in_threadpool(
                    write_json_file,
                    ANALYSIS_PATH,
                    f"analysis_{resume_name}_{jd_name}.json",
                    result,
                )
        await run_in_threadpool(
            save_history, task, f"{resume.filename} + {jd_name}", result
        )
        return result
    except json.JSONDecodeError as exc:
        raise HTTPException(
            status_code=502, detail="Groq returned invalid JSON."
        ) from exc
    except HTTPException:
        raise
    except Exception as exc:
        raise to_http_exception(exc) from exc
