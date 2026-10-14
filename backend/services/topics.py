"""Shared question-to-skill matching for progress and daily practice."""

import re

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


def question_skills(question):
    return [
        name
        for name, pattern in TOPIC_PATTERNS.items()
        if re.search(pattern, question, re.IGNORECASE)
    ] or ["General interview answers"]
