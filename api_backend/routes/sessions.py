"""Persistent interview-session API routes."""

from fastapi import APIRouter, Query

from api_backend.exceptions import to_http_exception
from services import sessions
from services.progress import get_progress
from services.session_models import SessionAnswer, SessionCreate

router = APIRouter()


@router.post("/sessions", status_code=201)
def create_interview_session(request: SessionCreate):
    try:
        return sessions.create_session(
            request.title,
            request.questions,
            request.role_context,
            request.followups_enabled,
        )
    except Exception as exc:
        raise to_http_exception(exc) from exc


@router.get("/sessions")
def list_interview_sessions(limit: int = Query(50, ge=1, le=100)):
    return {"items": sessions.list_sessions(limit)}


@router.get("/sessions/{session_id}")
def get_interview_session(session_id: str):
    try:
        return sessions.get_session(session_id)
    except Exception as exc:
        raise to_http_exception(exc) from exc


@router.post("/sessions/{session_id}/answers")
def answer_interview_question(session_id: str, request: SessionAnswer):
    try:
        return sessions.submit_answer(
            session_id, request.answer_text, request.expected_question_index
        )
    except Exception as exc:
        raise to_http_exception(exc) from exc


@router.get("/progress")
def interview_progress(
    days: int | None = Query(None, ge=1, le=3650), include_followups: bool = True
):
    try:
        return get_progress(days, include_followups)
    except Exception as exc:
        raise to_http_exception(exc) from exc
