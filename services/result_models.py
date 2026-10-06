"""Validated AI output contracts shared by the API and UI."""

from typing import Annotated

from pydantic import BaseModel, ConfigDict, Field, StringConstraints

NonEmptyText = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1)]
Score = Annotated[int, Field(ge=0, le=100)]


class GeneratedResult(BaseModel):
    model_config = ConfigDict(strict=True, extra="forbid")


class MatchedSkill(GeneratedResult):
    skill: NonEmptyText
    resume_evidence: NonEmptyText
    jd_evidence: NonEmptyText


class MissingSkill(GeneratedResult):
    skill: NonEmptyText
    why_it_matters: NonEmptyText
    suggested_action: NonEmptyText


class MatchAnalysis(GeneratedResult):
    role_fit_score: Score
    summary: NonEmptyText
    matched_skills: list[MatchedSkill]
    missing_skills: list[MissingSkill]
    improvement_suggestions: list[NonEmptyText]


class InterviewQuestion(GeneratedResult):
    question: NonEmptyText
    why_it_may_be_asked: NonEmptyText
    answer_based_on_resume: NonEmptyText


class WeakArea(GeneratedResult):
    area: NonEmptyText
    reason: NonEmptyText
    revision_plan: NonEmptyText


class ProjectExplanation(GeneratedResult):
    project: NonEmptyText
    how_to_explain: NonEmptyText
    jd_connection: NonEmptyText


class InterviewPrep(GeneratedResult):
    likely_interview_questions: list[InterviewQuestion]
    weak_areas_to_revise: list[WeakArea]
    project_explanations_to_prepare: list[ProjectExplanation]


class ApplicationMessages(GeneratedResult):
    customized_cover_letter: NonEmptyText
    short_recruiter_message: NonEmptyText
    linkedin_dm_message: NonEmptyText


class RewrittenBullet(GeneratedResult):
    original: NonEmptyText
    improved: NonEmptyText
    reason: NonEmptyText


class ResumeGap(GeneratedResult):
    gap: NonEmptyText
    suggested_resume_addition: NonEmptyText


class ResumeImprovements(GeneratedResult):
    rewritten_bullets: list[RewrittenBullet]
    suggested_keywords: list[NonEmptyText]
    ats_optimization: list[NonEmptyText]
    missing_project_or_skill_suggestions: list[ResumeGap]


class VoiceEvaluation(GeneratedResult):
    score: Score
    feedback: NonEmptyText
    strengths: list[NonEmptyText]
    improvements: list[NonEmptyText]
    better_answer: NonEmptyText


class FollowUpQuestion(GeneratedResult):
    question: Annotated[
        str, StringConstraints(strip_whitespace=True, min_length=1, max_length=2000)
    ]
    reason: Annotated[
        str, StringConstraints(strip_whitespace=True, min_length=1, max_length=500)
    ]
