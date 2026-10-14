"""Stable daily queues, exact question retries, and evidence-based skill progression."""

import json
from collections import defaultdict
from contextlib import contextmanager
from datetime import datetime, timezone

from backend import config
from backend.errors import ConfigurationError
from backend.services import sessions
from backend.services.session_models import SessionCreate
from backend.services.practice_models import (
    DailyPractice,
    PracticeQuestion,
    SkillProgress,
)
from backend.services.topics import question_skills
from backend.utils.logging_utils import logged_step, log_info

# Increasing demands rather than model-invented difficulty labels.
QUESTION_TEMPLATES = {
    "foundational": (
        "Explain a core concept in {skill} in plain language and give one concrete example.",
        "Describe a small task involving {skill}. What steps would you take and why?",
        "What common mistake occurs in {skill}, and how would you avoid it?",
        "How would you check that a simple solution involving {skill} works correctly?",
        "Describe what you learned from using {skill}, with a specific example.",
    ),
    "applied": (
        "Describe how you would use {skill} to solve a real problem. Explain the steps, constraints, and measurable result.",
        "Walk through diagnosing a failure involving {skill}. What evidence would you collect and how would you validate the fix?",
        "Compare two ways to approach a task involving {skill}. Which would you choose under a tight deadline and why?",
        "Describe a challenging decision involving {skill}. Explain your reasoning and how you assessed the outcome.",
        "How would you improve an existing approach to {skill}? Give a concrete example and a way to measure success.",
    ),
    "advanced": (
        "Compare two approaches to {skill} under competing constraints. Discuss trade-offs, failure modes, and how you would test your choice.",
        "Design an approach to {skill} for a team whose requirements change rapidly. Explain alternatives, risks, and how you would measure long-term results.",
        "A previously successful approach to {skill} is failing at scale. Explain your investigation, mitigation, and evidence for a durable solution.",
        "Defend a difficult decision involving {skill} to a skeptical stakeholder. Address alternatives, uncertainty, and measurable impact.",
        "How would you evaluate and improve a team's approach to {skill}? Discuss conflicting goals, edge cases, and a staged rollout.",
    ),
}


@contextmanager
def _connection():
    with sessions._connection() as db:
        db.execute("""CREATE TABLE IF NOT EXISTS daily_practice (
            day TEXT PRIMARY KEY, items TEXT NOT NULL,
            session_id TEXT UNIQUE REFERENCES interview_sessions(id)
        )""")
        yield db


def _today():
    return datetime.now(timezone.utc).date().isoformat()


def _normalize(question):
    return " ".join(question.casefold().split()).rstrip("?.!")


def _evidence():
    session_rows, answers = sessions.read_progress_data()
    session_map = {row["id"]: json.loads(row["questions"]) for row in session_rows}
    with _connection() as db:
        plans = db.execute(
            "SELECT session_id, items FROM daily_practice WHERE session_id IS NOT NULL"
        ).fetchall()
    tagged = {
        (row["session_id"], index): item
        for row in plans
        for index, item in enumerate(json.loads(row["items"]))
    }
    now = datetime.now(timezone.utc)
    records = []
    for answer in answers:
        stamp = datetime.fromisoformat(answer["created_at"])
        if stamp.tzinfo is None:
            stamp = stamp.replace(tzinfo=timezone.utc)
        if stamp > now:
            continue
        question = session_map[answer["session_id"]][answer["question_index"]]
        tag = tagged.get((answer["session_id"], answer["question_index"]))
        skills = [tag["skill"]] if tag else question_skills(question)
        for skill in skills:
            records.append(
                {
                    "skill": skill,
                    "question": question,
                    "score": answer["score"],
                    "session_id": answer["session_id"],
                    "stamp": stamp.isoformat(),
                    "difficulty": tag["difficulty"] if tag else "unclassified",
                    "daily_practice": tag is not None,
                }
            )
    return sorted(
        records, key=lambda row: (row["stamp"], row["session_id"], row["question"])
    )


def _skill_progress(records):
    groups = defaultdict(list)
    for row in records:
        groups[row["skill"]].append(row)
    results = []
    for skill, rows in groups.items():
        scores = [row["score"] for row in rows]
        window = max(1, config.DAILY_PRACTICE_WINDOW)
        recent = round(sum(scores[-window:]) / len(scores[-window:]), 1)
        level = "foundational"
        if (
            len(scores) >= config.DAILY_PRACTICE_ADVANCED_MIN_ANSWERS
            and recent >= config.DAILY_PRACTICE_ADVANCED_SCORE
        ):
            level = "advanced"
        elif (
            len(scores) >= config.DAILY_PRACTICE_APPLIED_MIN_ANSWERS
            and recent >= config.PROGRESS_PRACTICE_SCORE
        ):
            level = "applied"
        samples = min(window, len(scores) // 2)
        baseline = round(sum(scores[:samples]) / samples, 1) if samples else None
        comparison = round(sum(scores[-samples:]) / samples, 1) if samples else None
        results.append(
            SkillProgress(
                skill=skill,
                attempts=len(rows),
                difficulty=level,
                recent_average=recent,
                baseline_average=baseline,
                comparison_average=comparison,
                score_change=round(comparison - baseline, 1) if samples else None,
                comparison_samples=samples,
                daily_practice_attempts=sum(row["daily_practice"] for row in rows),
                trend=[
                    {
                        "date": row["stamp"],
                        "score": row["score"],
                        "difficulty": row["difficulty"],
                    }
                    for row in rows
                ],
            ).model_dump()
        )
    return sorted(results, key=lambda item: (item["recent_average"], item["skill"]))


def _build_items(records, skills, day):
    count = config.DAILY_PRACTICE_QUESTION_COUNT
    if not 3 <= count <= 5:
        raise ConfigurationError(
            "DAILY_PRACTICE_QUESTION_COUNT must be between 3 and 5."
        )
    items, seen = [], set()
    # Revisit only the latest attempt at each question: an old low score does not
    # keep a question in the retry queue after it has been answered successfully.
    latest = {}
    for row in records:
        latest[_normalize(row["question"])] = row
    poor = sorted(
        (
            row
            for row in latest.values()
            if row["score"] < config.PROGRESS_PRACTICE_SCORE
        ),
        key=lambda row: (row["score"], row["stamp"], row["question"]),
    )
    for row in poor[: max(0, min(config.DAILY_PRACTICE_REVIEW_COUNT, count - 1))]:
        seen.add(_normalize(row["question"]))
        items.append(
            PracticeQuestion(
                question=row["question"],
                skill=row["skill"],
                difficulty="original",
                reason=f"Retry your earlier answer scored {row['score']}/100.",
                source_session_id=row["session_id"],
                previous_score=row["score"],
            ).model_dump()
        )
    focus = skills or [
        {"skill": name, "difficulty": "foundational", "attempts": 0}
        for name in (
            "Projects and experience",
            "Teamwork and leadership",
            "General interview answers",
        )
    ]
    offset = datetime.fromisoformat(day).toordinal()
    index = 0
    while len(items) < count:
        skill = focus[index % len(focus)]
        level = skill["difficulty"]
        template = QUESTION_TEMPLATES[level][
            (offset + index // len(focus)) % len(QUESTION_TEMPLATES[level])
        ]
        question = template.format(skill=skill["skill"])
        index += 1
        if _normalize(question) in seen:
            continue
        seen.add(_normalize(question))
        reason = (
            f"Focus on {skill['skill']} at {level} difficulty based on recent answers."
            if skill["attempts"]
            else "Build a baseline before personalized difficulty increases."
        )
        items.append(
            PracticeQuestion(
                question=question, skill=skill["skill"], difficulty=level, reason=reason
            ).model_dump()
        )
    return items


@logged_step("daily_practice")
def get_daily_practice():
    day = _today()
    records = _evidence()
    skills = _skill_progress(records)
    with _connection() as db:
        row = db.execute(
            "SELECT * FROM daily_practice WHERE day = ?", (day,)
        ).fetchone()
    if row is None:
        items = _build_items(records, skills, day)
        with _connection() as db:
            db.execute(
                "INSERT OR IGNORE INTO daily_practice (day, items) VALUES (?, ?)",
                (day, json.dumps(items, ensure_ascii=False)),
            )
            row = db.execute(
                "SELECT * FROM daily_practice WHERE day = ?", (day,)
            ).fetchone()
        log_info("daily_queue_ready", day=day, question_count=len(items))
    items = json.loads(row["items"])
    session = sessions.get_session(row["session_id"]) if row["session_id"] else None
    if session:
        for answer in session["answers"]:
            item = items[answer["question_index"]]
            item["completed"] = True
            item["score"] = answer["evaluation"]["score"]
    return DailyPractice(
        date=day,
        session_id=row["session_id"],
        status=session["status"] if session else "not_started",
        answered_questions=session["answered_questions"] if session else 0,
        items=items,
        skills=skills,
    ).model_dump(mode="json")


@logged_step("start_daily_practice")
def start_daily_practice():
    plan = get_daily_practice()
    with _connection() as db:
        db.execute("BEGIN IMMEDIATE")
        row = db.execute(
            "SELECT * FROM daily_practice WHERE day = ?", (plan["date"],)
        ).fetchone()
        session_id = row["session_id"]
        if session_id is None:
            items = json.loads(row["items"])
            request = SessionCreate(
                title=f"Daily practice - {plan['date']}",
                questions=[item["question"] for item in items],
                role_context="Daily skill practice. Evaluate the answer against the question and consistent rubric.",
                followups_enabled=False,
            )
            session_id = sessions.insert_session(db, request)
            db.execute(
                "UPDATE daily_practice SET session_id = ? WHERE day = ?",
                (session_id, plan["date"]),
            )
    log_info("daily_practice_opened", day=plan["date"], session_id=session_id)
    return sessions.get_session(session_id)
