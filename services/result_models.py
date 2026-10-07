"""Validated AI output contracts shared by the API and UI."""

from typing import Annotated, Literal

from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    StringConstraints,
    ValidationInfo,
    model_validator,
)

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


class RubricCriterion(GeneratedResult):
    points: Annotated[int, Field(ge=0, le=25)]
    reasoning: NonEmptyText
    evidence_status: Literal["demonstrated", "not_demonstrated"]
    quotes: list[Annotated[str, Field(min_length=1, max_length=2000)]] = Field(
        max_length=3
    )

    @model_validator(mode="after")
    def check_evidence(self):
        if self.evidence_status == "not_demonstrated":
            if self.points != 0 or self.quotes:
                raise ValueError(
                    "A criterion not demonstrated must have zero points and no quotes"
                )
        elif not self.quotes or any(not quote.strip() for quote in self.quotes):
            raise ValueError("A demonstrated criterion needs nonblank answer quotes")
        return self


class AnswerRubric(GeneratedResult):
    relevance: RubricCriterion
    depth: RubricCriterion
    supporting_details: RubricCriterion
    clarity: RubricCriterion


class VoiceEvaluation(GeneratedResult):
    score: Score
    feedback: NonEmptyText
    strengths: list[NonEmptyText]
    improvements: list[NonEmptyText]
    better_answer: NonEmptyText
    rubric_version: Literal["1"]
    rubric: AnswerRubric

    @model_validator(mode="after")
    def check_grounding(self, info: ValidationInfo):
        criteria = [getattr(self.rubric, name) for name in AnswerRubric.model_fields]
        if self.score != sum(criterion.points for criterion in criteria):
            raise ValueError("score must equal the sum of the four rubric criteria")
        answer = (info.context or {}).get("answer_text")
        if not isinstance(answer, str) or not answer.strip():
            raise ValueError(
                "The original answer is required to verify rubric evidence"
            )
        for criterion in criteria:
            if any(quote not in answer for quote in criterion.quotes):
                raise ValueError(
                    "Rubric evidence contains a quote not found in the submitted answer"
                )
        return self


class FollowUpQuestion(GeneratedResult):
    question: Annotated[
        str, StringConstraints(strip_whitespace=True, min_length=1, max_length=2000)
    ]
    reason: Annotated[
        str, StringConstraints(strip_whitespace=True, min_length=1, max_length=500)
    ]
