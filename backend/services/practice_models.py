"""Validated daily practice responses."""

from typing import Literal
from pydantic import BaseModel, Field

Difficulty = Literal["foundational", "applied", "advanced"]


class PracticeQuestion(BaseModel):
    question: str = Field(min_length=1, max_length=2000)
    skill: str
    difficulty: Literal["original", "foundational", "applied", "advanced"]
    reason: str
    source_session_id: str | None = None
    previous_score: int | None = Field(default=None, ge=0, le=100)
    completed: bool = False
    score: int | None = Field(default=None, ge=0, le=100)


class SkillProgress(BaseModel):
    skill: str
    attempts: int
    difficulty: Difficulty
    recent_average: float
    baseline_average: float | None
    comparison_average: float | None
    score_change: float | None
    comparison_samples: int
    daily_practice_attempts: int
    trend: list[dict]


class DailyPractice(BaseModel):
    date: str
    timezone: Literal["UTC"] = "UTC"
    session_id: str | None
    status: Literal["not_started", "active", "completed"]
    answered_questions: int
    items: list[PracticeQuestion] = Field(min_length=3, max_length=5)
    skills: list[SkillProgress]
