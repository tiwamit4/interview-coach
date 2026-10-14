"""Persistent interview deadlines and reports derived from saved evaluations."""

from collections import Counter
from datetime import datetime, timezone

from pydantic import BaseModel

CRITERIA = ("relevance", "depth", "supporting_details", "clarity")


class SimulationReport(BaseModel):
    completion_reason: str
    answered_questions: int
    unanswered_questions: int
    average_score: float | None
    rubric_averages: dict[str, float]
    strengths: list[str]
    practice_priorities: list[str]
    question_scores: list[dict]


def timing(row, now=None):
    if row is None:
        return None
    now = now or datetime.now(timezone.utc)
    deadline = datetime.fromisoformat(row["deadline_at"])
    return {
        "duration_minutes": row["duration_minutes"],
        "deadline_at": row["deadline_at"],
        "finished_at": row["finished_at"],
        "server_time": now.isoformat(),
        "remaining_seconds": max(0, (deadline - now).total_seconds()),
    }


def report(session, reason):
    answers = session["answers"]
    evaluations = [answer["evaluation"] for answer in answers]
    rubric = {}
    for criterion in CRITERIA:
        points = [
            evaluation["rubric"][criterion]["points"]
            for evaluation in evaluations
            if criterion in evaluation.get("rubric", {})
        ]
        if points:
            rubric[criterion] = round(sum(points) / len(points), 1)

    def common(field):
        counts = Counter(
            text for evaluation in evaluations for text in evaluation.get(field, [])
        )
        return [text for text, _ in counts.most_common(5)]

    return SimulationReport(
        completion_reason=reason,
        answered_questions=len(answers),
        unanswered_questions=session["total_questions"] - len(answers),
        average_score=session["average_score"],
        rubric_averages=rubric,
        strengths=common("strengths"),
        practice_priorities=common("improvements"),
        question_scores=[
            {"question": answer["question"], "score": answer["evaluation"]["score"]}
            for answer in answers
        ],
    ).model_dump(mode="json")
