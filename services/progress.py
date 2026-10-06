"""Deterministic progress summaries from saved interview-session evaluations."""

import json
import re
from collections import Counter, defaultdict
from datetime import datetime, timedelta, timezone

import config
from services.sessions import read_progress_data

# Phrase-based categories are intentionally small and inspectable. Original
# feedback is retained so users can assess the grouping rather than trust a label.
WEAKNESS_PATTERNS = {
    "Answer structure and clarity": r"\b(star|structur\w*|concis\w*|clarity|clearer|rambl\w*|organiz\w*)\b",
    "Examples and measurable outcomes": r"\b(example\w*|specific\w*|detail\w*|metric\w*|quantif\w*|measur\w*|impact|outcome\w*|result\w*|evidence)\b",
    "Technical depth and trade-offs": r"\b(technical|trade[ -]?offs?|complexity|edge cases?|depth|alternatives?)\b",
    "Relevance to the role": r"\b(relevan\w*|align\w*|job requirements?|role requirements?)\b",
}
TOPIC_PATTERNS = {
    "Python": r"\bpython\b",
    "SQL and databases": r"\b(sql|databases?|postgres\w*|mysql|joins?|indexes|indexing)\b",
    "Machine learning": r"\b(machine learning|ml|models?|training|prediction\w*|accuracy|neural|classification)\b",
    "APIs and web development": r"\b(apis?|rest|http|fastapi|web|frontend|backend)\b",
    "Testing and reliability": r"\b(test\w*|validat\w*|debug\w*|reliab\w*|failures?|monitor\w*)\b",
    "System design": r"\b(system design|architect\w*|scal\w*|distributed|caching|cache|latency)\b",
    "Projects and experience": r"\b(project\w*|experience|built|implemented)\b",
    "Teamwork and leadership": r"\b(team\w*|leader\w*|conflict\w*|collaborat\w*|stakeholder\w*)\b",
}


def _timestamp(value):
    parsed = datetime.fromisoformat(value)
    return (
        parsed.replace(tzinfo=timezone.utc)
        if parsed.tzinfo is None
        else parsed.astimezone(timezone.utc)
    )


def _weakness_keys(text):
    categories = [
        name
        for name, pattern in WEAKNESS_PATTERNS.items()
        if re.search(pattern, text, re.IGNORECASE)
    ]
    # Unknown feedback is grouped only on identical normalized text.
    return categories or [" ".join(text.casefold().split())]


def get_progress(days=None, include_followups=True):
    """Summarize saved answers without extra model calls or changing saved data."""
    now = datetime.now(timezone.utc)
    since = now - timedelta(days=days) if days is not None else None
    session_rows, answer_rows = read_progress_data()
    session_map = {
        row["id"]: {**row, "questions": json.loads(row["questions"])}
        for row in session_rows
    }
    selected = [
        row
        for row in answer_rows
        if (include_followups or not row["is_followup"])
        and (since is None or _timestamp(row["created_at"]) >= since)
        and _timestamp(row["created_at"]) <= now
    ]
    selected.sort(
        key=lambda row: (
            _timestamp(row["created_at"]),
            row["session_id"],
            row["question_index"],
        )
    )
    relevant_ids = {row["session_id"] for row in selected}
    relevant_sessions = [
        row
        for row in session_map.values()
        if since is None
        or row["id"] in relevant_ids
        or since <= _timestamp(row["created_at"]) <= now
    ]
    scores = [row["score"] for row in selected]
    window = config.PROGRESS_TREND_WINDOW
    change = None
    if len(scores) >= 2 * window:
        change = round(
            sum(scores[-window:]) / window
            - sum(scores[-2 * window : -window]) / window,
            1,
        )
    daily = defaultdict(list)
    by_session = defaultdict(list)
    weaknesses = {}
    topics = {}
    for row in selected:
        session = session_map[row["session_id"]]
        question = session["questions"][row["question_index"]]
        evaluation = json.loads(row["evaluation"])
        improvements = evaluation["improvements"]
        daily[_timestamp(row["created_at"]).date().isoformat()].append(row["score"])
        by_session[row["session_id"]].append(row["score"])
        answer_keys = set()
        for suggestion in improvements:
            for key in _weakness_keys(suggestion):
                item = weaknesses.setdefault(
                    key,
                    {
                        "theme": key if key in WEAKNESS_PATTERNS else suggestion,
                        "answer_count": 0,
                        "session_ids": set(),
                        "examples": [],
                    },
                )
                if key not in answer_keys:
                    item["answer_count"] += 1
                    item["session_ids"].add(row["session_id"])
                if suggestion not in item["examples"] and len(item["examples"]) < 3:
                    item["examples"].append(suggestion)
                answer_keys.add(key)
        labels = [
            name
            for name, pattern in TOPIC_PATTERNS.items()
            if re.search(pattern, question, re.IGNORECASE)
        ] or ["General interview answers"]
        for label in labels:
            item = topics.setdefault(
                label,
                {"scores": [], "feedback": Counter(), "questions": [], "examples": []},
            )
            item["scores"].append(row["score"])
            item["feedback"].update(answer_keys)
            item["questions"].append(
                {
                    "question": question,
                    "score": row["score"],
                    "session_id": row["session_id"],
                }
            )
            for suggestion in improvements:
                if suggestion not in item["examples"] and len(item["examples"]) < 3:
                    item["examples"].append(suggestion)
    recurring = [
        {
            "theme": item["theme"],
            "answer_count": item["answer_count"],
            "session_count": len(item["session_ids"]),
            "examples": item["examples"],
        }
        for item in weaknesses.values()
        if item["answer_count"] >= config.PROGRESS_RECURRING_MIN_ANSWERS
    ]
    recurring.sort(key=lambda item: (-item["answer_count"], item["theme"]))
    topic_results = []
    for label, item in topics.items():
        average = sum(item["scores"]) / len(item["scores"])
        reasons = []
        if average < config.PROGRESS_PRACTICE_SCORE:
            reasons.append(f"Average score below {config.PROGRESS_PRACTICE_SCORE}/100")
        if any(
            count >= config.PROGRESS_RECURRING_MIN_ANSWERS
            for count in item["feedback"].values()
        ):
            reasons.append("Repeated improvement feedback")
        topic_results.append(
            {
                "topic": label,
                "answer_count": len(item["scores"]),
                "average_score": round(average, 1),
                "needs_practice": bool(reasons),
                "reasons": reasons,
                "suggestions": item["examples"],
                "practice_questions": sorted(
                    item["questions"], key=lambda question: question["score"]
                )[:3],
            }
        )
    topic_results.sort(
        key=lambda item: (
            not item["needs_practice"],
            item["average_score"],
            item["topic"],
        )
    )
    return {
        "days": days,
        "include_followups": include_followups,
        "summary": {
            "sessions": len(relevant_sessions),
            "completed_sessions": sum(
                row["current_index"] >= len(row["questions"])
                for row in relevant_sessions
            ),
            "answers": len(scores),
            "average_score": round(sum(scores) / len(scores), 1) if scores else None,
            "score_change": change,
            "trend_window": window,
            "practice_score_target": config.PROGRESS_PRACTICE_SCORE,
        },
        "score_trend": [
            {
                "date": day,
                "average_score": round(sum(values) / len(values), 1),
                "answer_count": len(values),
            }
            for day, values in sorted(daily.items())
        ],
        "session_scores": [
            {
                "session_id": row["id"],
                "title": row["title"],
                "created_at": row["created_at"],
                "answer_count": len(by_session[row["id"]]),
                "average_score": round(
                    sum(by_session[row["id"]]) / len(by_session[row["id"]]), 1
                ),
            }
            for row in sorted(
                relevant_sessions, key=lambda row: _timestamp(row["created_at"])
            )
            if by_session[row["id"]]
        ],
        "recurring_weaknesses": recurring,
        "topics": topic_results,
    }
