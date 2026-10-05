"""Validated interview-session inputs."""

from typing import Annotated

from pydantic import BaseModel, ConfigDict, Field, StringConstraints

import config

SessionText = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1)]
QuestionText = Annotated[
    str, StringConstraints(strip_whitespace=True, min_length=1, max_length=2000)
]


class SessionCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")
    title: SessionText = Field(default="Interview practice", max_length=120)
    questions: list[QuestionText] = Field(
        min_length=1, max_length=config.MAX_SESSION_QUESTIONS
    )
    role_context: str = Field(default="", max_length=10000)


class SessionAnswer(BaseModel):
    model_config = ConfigDict(extra="forbid")
    answer_text: SessionText = Field(max_length=config.MAX_SESSION_ANSWER_CHARACTERS)
    expected_question_index: int = Field(ge=0, strict=True)
