"""Persistent interview sessions with atomic question progression."""

import json
from contextlib import contextmanager
from datetime import datetime, timezone
from uuid import uuid4

import config

from errors import GeneratedResultError, SessionConflictError, SessionNotFoundError
from prompts.prompt import SESSION_FOLLOWUP_PROMPT, VOICE_ANSWER_EVALUATION_PROMPT
from services.generation import run_json_prompt
from services.session_models import SessionAnswer, SessionCreate
from utils.database import connection
from utils.logging_utils import log_info


@contextmanager
def _connection():
    with connection() as db:
        db.execute("""CREATE TABLE IF NOT EXISTS interview_sessions (
            id TEXT PRIMARY KEY, title TEXT NOT NULL, questions TEXT NOT NULL,
            role_context TEXT NOT NULL, current_index INTEGER NOT NULL DEFAULT 0,
            created_at TEXT NOT NULL, updated_at TEXT NOT NULL
        )""")
        db.execute("""CREATE TABLE IF NOT EXISTS interview_answers (
            session_id TEXT NOT NULL REFERENCES interview_sessions(id),
            question_index INTEGER NOT NULL, answer_text TEXT NOT NULL,
            evaluation TEXT NOT NULL, score INTEGER NOT NULL,
            created_at TEXT NOT NULL,
            PRIMARY KEY(session_id, question_index)
        )""")
        db.execute("""CREATE TABLE IF NOT EXISTS interview_session_options (
            session_id TEXT PRIMARY KEY REFERENCES interview_sessions(id),
            followups_enabled INTEGER NOT NULL
        )""")
        db.execute("""CREATE TABLE IF NOT EXISTS interview_followups (
            session_id TEXT NOT NULL REFERENCES interview_sessions(id),
            question_index INTEGER NOT NULL, parent_question_index INTEGER NOT NULL,
            reason TEXT NOT NULL, PRIMARY KEY(session_id, question_index)
        )""")
        yield db


def _now():
    return datetime.now(timezone.utc).isoformat()


def create_session(title, questions, role_context="", followups_enabled=False):
    request = SessionCreate(
        title=title,
        questions=questions,
        role_context=role_context,
        followups_enabled=followups_enabled,
    )
    session_id = uuid4().hex
    now = _now()
    with _connection() as db:
        db.execute(
            "INSERT INTO interview_sessions (id, title, questions, role_context, created_at, updated_at) VALUES (?, ?, ?, ?, ?, ?)",
            (
                session_id,
                request.title,
                json.dumps(request.questions, ensure_ascii=False),
                request.role_context,
                now,
                now,
            ),
        )
        db.execute(
            "INSERT INTO interview_session_options VALUES (?, ?)",
            (session_id, int(request.followups_enabled)),
        )
    log_info(
        "session_created", session_id=session_id, question_count=len(request.questions)
    )
    return get_session(session_id)


def _load(db, session_id):
    row = db.execute(
        "SELECT * FROM interview_sessions WHERE id = ?", (session_id,)
    ).fetchone()
    if row is None:
        raise SessionNotFoundError("Interview session not found.")
    answers = db.execute(
        "SELECT * FROM interview_answers WHERE session_id = ? ORDER BY question_index",
        (session_id,),
    ).fetchall()
    questions = json.loads(row["questions"])
    options = db.execute(
        "SELECT followups_enabled FROM interview_session_options WHERE session_id = ?",
        (session_id,),
    ).fetchone()
    followups = [
        dict(item)
        for item in db.execute(
            "SELECT question_index, parent_question_index, reason FROM interview_followups WHERE session_id = ? ORDER BY question_index",
            (session_id,),
        ).fetchall()
    ]
    completed = row["current_index"] >= len(questions)
    return {
        "id": row["id"],
        "title": row["title"],
        "questions": questions,
        "role_context": row["role_context"],
        "followups_enabled": bool(options["followups_enabled"]) if options else False,
        "followups": followups,
        "current_question_is_followup": any(
            item["question_index"] == row["current_index"] for item in followups
        ),
        "current_question_index": row["current_index"],
        "current_question": None if completed else questions[row["current_index"]],
        "status": "completed" if completed else "active",
        "total_questions": len(questions),
        "answered_questions": len(answers),
        "average_score": (
            round(sum(answer["score"] for answer in answers) / len(answers), 1)
            if answers
            else None
        ),
        "created_at": row["created_at"],
        "updated_at": row["updated_at"],
        "answers": [
            {
                "question_index": answer["question_index"],
                "question": questions[answer["question_index"]],
                "answer_text": answer["answer_text"],
                "evaluation": json.loads(answer["evaluation"]),
                "created_at": answer["created_at"],
            }
            for answer in answers
        ],
    }


def get_session(session_id):
    with _connection() as db:
        db.execute("BEGIN")
        return _load(db, session_id)


def list_sessions(limit=50):
    with _connection() as db:
        rows = db.execute(
            """SELECT s.id, s.title, s.questions, s.current_index,
            s.created_at, s.updated_at, AVG(a.score) AS average_score
            FROM interview_sessions s LEFT JOIN interview_answers a ON a.session_id = s.id
            GROUP BY s.id ORDER BY s.created_at DESC LIMIT ?""",
            (limit,),
        ).fetchall()
    return [
        {
            "id": row["id"],
            "title": row["title"],
            "status": (
                "completed"
                if row["current_index"] >= len(json.loads(row["questions"]))
                else "active"
            ),
            "total_questions": len(json.loads(row["questions"])),
            "answered_questions": row["current_index"],
            "average_score": (
                round(row["average_score"], 1)
                if row["average_score"] is not None
                else None
            ),
            "created_at": row["created_at"],
            "updated_at": row["updated_at"],
        }
        for row in rows
    ]


def submit_answer(session_id, answer_text, expected_question_index):
    request = SessionAnswer(
        answer_text=answer_text, expected_question_index=expected_question_index
    )
    session = get_session(session_id)
    if (
        session["status"] == "completed"
        or session["current_question_index"] != request.expected_question_index
    ):
        raise SessionConflictError(
            "This question has already been answered. Reload the session to continue."
        )
    # Network calls stay outside the database transaction.
    evaluation = run_json_prompt(
        VOICE_ANSWER_EVALUATION_PROMPT,
        question=session["current_question"],
        answer_text=request.answer_text,
        jd_text=session["role_context"],
    )
    followup = None
    if (
        session["followups_enabled"]
        and not session["current_question_is_followup"]
        and len(session["followups"]) < config.MAX_SESSION_FOLLOWUPS
    ):
        followup = run_json_prompt(
            SESSION_FOLLOWUP_PROMPT,
            question=session["current_question"],
            answer_text=request.answer_text,
            role_context=session["role_context"],
            existing_questions=json.dumps(session["questions"], ensure_ascii=False),
        )

        def normalized(text):
            return " ".join(text.casefold().split()).rstrip("?.!")

        if normalized(followup["question"]) in {
            normalized(question) for question in session["questions"]
        }:
            raise GeneratedResultError(
                "The generated follow-up repeats an existing question. Try submitting again."
            )
    now = _now()
    with _connection() as db:
        db.execute("BEGIN IMMEDIATE")
        current = _load(db, session_id)
        if (
            current["current_question_index"] != request.expected_question_index
            or current["status"] == "completed"
        ):
            raise SessionConflictError(
                "This question has already been answered. Reload the session to continue."
            )
        db.execute(
            "INSERT INTO interview_answers VALUES (?, ?, ?, ?, ?, ?)",
            (
                session_id,
                request.expected_question_index,
                request.answer_text,
                json.dumps(evaluation, ensure_ascii=False),
                evaluation["score"],
                now,
            ),
        )
        if followup is not None:
            questions = current["questions"]
            next_index = request.expected_question_index + 1
            questions.insert(next_index, followup["question"])
            db.execute(
                "UPDATE interview_sessions SET questions = ? WHERE id = ?",
                (json.dumps(questions, ensure_ascii=False), session_id),
            )
            db.execute(
                "INSERT INTO interview_followups VALUES (?, ?, ?, ?)",
                (
                    session_id,
                    next_index,
                    request.expected_question_index,
                    followup["reason"],
                ),
            )
        db.execute(
            "UPDATE interview_sessions SET current_index = current_index + 1, updated_at = ? WHERE id = ?",
            (now, session_id),
        )
        updated = _load(db, session_id)
    log_info(
        "session_answer_saved",
        session_id=session_id,
        question_index=request.expected_question_index,
        followup_generated=followup is not None,
    )
    return {"session": updated, "answer": updated["answers"][-1]}
