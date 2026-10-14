"""Personalized daily practice API."""

from fastapi import APIRouter
from backend.api_backend.exceptions import to_http_exception
from backend.services.practice import get_daily_practice, start_daily_practice
from backend.services.practice_models import DailyPractice

router = APIRouter()


@router.get("/practice/daily", response_model=DailyPractice)
def daily_practice():
    try:
        return get_daily_practice()
    except Exception as exc:
        raise to_http_exception(exc) from exc


@router.post("/practice/daily/start")
def start_practice():
    try:
        return start_daily_practice()
    except Exception as exc:
        raise to_http_exception(exc) from exc
