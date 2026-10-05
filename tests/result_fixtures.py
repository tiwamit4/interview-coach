"""Representative complete AI results for service and integration checks."""

from copy import deepcopy
import json

from prompts.prompt import (
    COVER_LETTER_PROMPT,
    INTERVIEW_PREP_PROMPT,
    MATCH_SCORE_PROMPT,
    RESUME_IMPROVEMENT_PROMPT,
    VOICE_ANSWER_EVALUATION_PROMPT,
)

RESULTS = {
    MATCH_SCORE_PROMPT: {
        "role_fit_score": 90,
        "summary": "The resume aligns with the role.",
        "matched_skills": [
            {
                "skill": "Python",
                "resume_evidence": "Python project",
                "jd_evidence": "Python required",
            }
        ],
        "missing_skills": [
            {
                "skill": "SQL",
                "why_it_matters": "Data analysis",
                "suggested_action": "Prepare a SQL example",
            }
        ],
        "improvement_suggestions": ["Explain the Python project outcomes"],
    },
    INTERVIEW_PREP_PROMPT: {
        "likely_interview_questions": [
            {
                "question": "Explain your Python project",
                "why_it_may_be_asked": "The role requires Python",
                "answer_based_on_resume": "Discuss the listed project",
            }
        ],
        "weak_areas_to_revise": [
            {
                "area": "SQL",
                "reason": "Required by the role",
                "revision_plan": "Practice joins",
            }
        ],
        "project_explanations_to_prepare": [
            {
                "project": "Python project",
                "how_to_explain": "Explain the implementation",
                "jd_connection": "Python is required",
            }
        ],
    },
    COVER_LETTER_PROMPT: {
        "customized_cover_letter": "I am interested in the Python role.",
        "short_recruiter_message": "I would like to discuss this role.",
        "linkedin_dm_message": "May we discuss this opportunity?",
    },
    RESUME_IMPROVEMENT_PROMPT: {
        "rewritten_bullets": [
            {
                "original": "Built a Python project",
                "improved": "Implemented the project in Python",
                "reason": "Clearer wording",
            }
        ],
        "suggested_keywords": ["Python"],
        "ats_optimization": ["Use clear section titles"],
        "missing_project_or_skill_suggestions": [
            {"gap": "SQL", "suggested_resume_addition": "Mention SQL work if supported"}
        ],
    },
    VOICE_ANSWER_EVALUATION_PROMPT: {
        "score": 90,
        "feedback": "The answer is relevant.",
        "strengths": ["Clear explanation"],
        "improvements": ["Add a concrete outcome"],
        "better_answer": "Explain the project and its outcome.",
    },
}


def result_for_prompt(prompt):
    return deepcopy(RESULTS[prompt])


def response_for_prompt(prompt, **values):
    if prompt in RESULTS:
        return json.dumps(RESULTS[prompt])
    return "Interview questions"
