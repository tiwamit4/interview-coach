"""Voice transcription and answer evaluation endpoints."""

import json
from pathlib import Path

from fastapi import APIRouter, File, Form, HTTPException, UploadFile
from pydantic import HttpUrl
from starlette.concurrency import run_in_threadpool

from api_backend.exceptions import to_http_exception
from api_backend.helpers import (
    extract_audio_upload,
    run_json_prompt,
    safe_filename,
    write_json_file,
    write_text_file,
)
from config import TRANSCRIPT_PATH, VOICE_MODEL, VOICE_PRACTICE_PATH
from prompts.prompt import VOICE_ANSWER_EVALUATION_PROMPT
from services.extraction import extract_job_description as scrape_job_description
from utils.history import save_history

router = APIRouter()


@router.post("/voice/run")
async def run_voice_task(
    task: str = Form(...),
    audio: UploadFile | None = File(None),
    answer_audio: UploadFile | None = File(None),
    answer_text: str | None = Form(None),
    question: str | None = Form(None),
    jd_url: str | None = Form(None),
    save_output: bool = Form(True),
):
    """
    Main voice workflow endpoint.

    Supported tasks: transcribe, evaluate_answer.
    """
    task = task.strip().lower()
    try:
        if task == "transcribe":
            if not audio:
                raise HTTPException(status_code=400, detail="audio is required.")
            transcript = await extract_audio_upload(audio, model=VOICE_MODEL)
            result = {
                "task": task,
                "filename": audio.filename,
                "transcript": transcript,
                "output_path": None,
            }
            if save_output:
                stem = safe_filename(Path(audio.filename or "audio").stem)
                result["output_path"] = await run_in_threadpool(
                    write_text_file,
                    TRANSCRIPT_PATH,
                    f"{stem}_transcript.txt",
                    transcript,
                )
            await run_in_threadpool(
                save_history, "voice_transcription", audio.filename or "audio", result
            )
            return result
        if task == "evaluate_answer":
            if not question:
                raise HTTPException(status_code=400, detail="question is required.")
            if not answer_text and (not answer_audio):
                raise HTTPException(
                    status_code=400, detail="answer_text or answer_audio is required."
                )
            if answer_audio:
                answer_text = await extract_audio_upload(
                    answer_audio, model=VOICE_MODEL
                )
            jd_text = (
                await run_in_threadpool(scrape_job_description, jd_url)
                if jd_url
                else ""
            )
            evaluation = await run_in_threadpool(
                run_json_prompt,
                VOICE_ANSWER_EVALUATION_PROMPT,
                question=question,
                answer_text=answer_text or "",
                jd_text=jd_text,
            )
            result = {
                "task": task,
                "question": question,
                "answer_text": answer_text,
                "jd": {"url": jd_url, "text": jd_text},
                "evaluation": evaluation,
                "output_path": None,
            }
            if save_output:
                result["output_path"] = await run_in_threadpool(
                    write_json_file,
                    VOICE_PRACTICE_PATH,
                    f"voice_practice_{safe_filename(question[:48])}.json",
                    result,
                )
            await run_in_threadpool(
                save_history, "voice_answer_evaluation", question[:80], result
            )
            return result
        raise HTTPException(status_code=400, detail=f"Unsupported voice task: {task}")
    except json.JSONDecodeError as exc:
        raise HTTPException(
            status_code=502, detail="Groq returned invalid JSON."
        ) from exc
    except HTTPException:
        raise
    except Exception as exc:
        raise to_http_exception(exc) from exc


@router.post("/voice/evaluate-answer", deprecated=True)
async def evaluate_voice_answer(
    question: str = Form(...),
    answer_text: str | None = Form(None),
    jd_url: HttpUrl | None = Form(None),
    answer_audio: UploadFile | None = File(None),
    save_output: bool = Form(True),
):
    if not answer_text and (not answer_audio):
        raise HTTPException(
            status_code=400, detail="Provide answer_text or answer_audio."
        )
    try:
        if answer_audio:
            answer_text = await extract_audio_upload(answer_audio, model=VOICE_MODEL)
        jd_text = (
            await run_in_threadpool(scrape_job_description, str(jd_url))
            if jd_url
            else ""
        )
        evaluation = await run_in_threadpool(
            run_json_prompt,
            VOICE_ANSWER_EVALUATION_PROMPT,
            question=question,
            answer_text=answer_text or "",
            jd_text=jd_text,
        )
    except json.JSONDecodeError as exc:
        raise HTTPException(
            status_code=502, detail="Groq returned invalid JSON for answer evaluation."
        ) from exc
    except Exception as exc:
        raise to_http_exception(exc) from exc
    result = {
        "question": question,
        "answer_text": answer_text,
        "jd": {"url": str(jd_url) if jd_url else None, "text": jd_text},
        "evaluation": evaluation,
        "output_path": None,
    }
    if save_output:
        output_filename = f"voice_practice_{safe_filename(question[:48])}.json"
        result["output_path"] = await run_in_threadpool(
            write_json_file, VOICE_PRACTICE_PATH, output_filename, result
        )
    await run_in_threadpool(
        save_history, "voice_answer_evaluation", question[:80], result
    )
    return result
