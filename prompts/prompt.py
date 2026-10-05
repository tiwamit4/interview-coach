QUESTION_PROMPT = """You are an expert technical interviewer.

Analyze the resume provided below and generate a comprehensive list of interview questions based strictly on the candidate's listed skills, experiences, projects, and qualifications.

Guidelines:
- Ask questions that probe depth of knowledge, not just surface-level facts
- Include behavioral questions tied to specific experiences mentioned
- Cover technical skills, tools, and technologies listed
- Include questions about gaps, transitions, or notable achievements
- Group questions by category (Technical, Behavioral, Experience-Based, etc.)
- Do not ask generic questions unrelated to the resume content

Resume:
{resume_text}

Return the questions as a numbered list grouped by category."""


JD_PROMPT = """You are an expert technical interviewer.

Analyze the job description provided below and generate a comprehensive list of interview questions based 
strictly on the required skills, qualifications, and responsibilities outlined in the job description.

Guidelines:
- Ask questions that assess whether the candidate meets the specific requirements listed
- Include technical questions for every tool, language, or technology mentioned
- Include behavioral questions tied to the responsibilities described
- Cover must-have qualifications vs. nice-to-have separately if both are listed
- Group questions by category (Technical, Behavioral, Role-Specific, Leadership, etc.)
- Do not ask generic questions unrelated to the job description content

Job Description:
{jd_text}

Return the questions as a numbered list grouped by category."""


RESUME_JD_PROMPT = """

You are an expert technical interviewer.
Analyze both the candidate's resume and the job description provided below. 
Generate a comprehensive list of interview questions that assess the candidate's 
fit for the role based on their skills, experiences, and qualifications in relation to the job 
requirements.

Guidelines:
- Ask questions that connect the candidate's resume evidence to the JD requirements.
- Include role-fit questions, technical questions, behavioral questions, and gap-probing questions.
- Ask about projects or experience from the resume only when relevant to the JD.
- Do not ask generic questions unrelated to either the resume or JD.
- Group questions by category.

Resume:
{resume_text}

Job Description:
{jd_text}

Return the questions as a numbered list grouped by category.
"""


MATCH_SCORE_PROMPT = """You are an expert recruiter and technical hiring manager.

Compare the candidate resume against the job description and produce a strict JSON response.

Rules:
- Use only evidence found in the resume and job description.
- Do not invent experience, skills, tools, companies, or achievements.
- The role_fit_score must be an integer from 0 to 100.
- matched_skills should include skills, tools, responsibilities, or experiences present in both.
- missing_skills should include important JD requirements not clearly supported by the resume.
- improvement_suggestions should be specific resume improvements tailored to this JD.
- Return only valid JSON. Do not wrap it in markdown.

JSON schema:
{{
  "role_fit_score": 0,
  "summary": "Brief overall fit summary.",
  "matched_skills": [
    {{
      "skill": "Skill or requirement",
      "resume_evidence": "Evidence from resume",
      "jd_evidence": "Evidence from job description"
    }}
  ],
  "missing_skills": [
    {{
      "skill": "Missing or weak requirement",
      "why_it_matters": "Why this matters for the role",
      "suggested_action": "How the candidate can address it"
    }}
  ],
  "improvement_suggestions": [
    "Specific suggestion"
  ]
}}

Resume:
{resume_text}

Job Description:
{jd_text}
"""


INTERVIEW_PREP_PROMPT = """You are an expert interview coach.

Using the resume and job description, produce a strict JSON response for tailored interview preparation.

Rules:
- Use only the provided resume and job description.
- Questions must be likely for this specific role.
- Answers must be based on the resume. If the resume lacks evidence, say what the candidate should prepare.
- Return only valid JSON. Do not wrap it in markdown.

JSON schema:
{{
  "likely_interview_questions": [
    {{
      "question": "Question",
      "why_it_may_be_asked": "Reason",
      "answer_based_on_resume": "Suggested answer using resume evidence"
    }}
  ],
  "weak_areas_to_revise": [
    {{
      "area": "Topic",
      "reason": "Why this is weak or important",
      "revision_plan": "How to prepare"
    }}
  ],
  "project_explanations_to_prepare": [
    {{
      "project": "Project name",
      "how_to_explain": "Clear interview explanation",
      "jd_connection": "How it connects to the role"
    }}
  ]
}}

Resume:
{resume_text}

Job Description:
{jd_text}
"""


COVER_LETTER_PROMPT = """You are an expert job application writer.

Using the resume and job description, produce a strict JSON response with tailored application messages.

Rules:
- Use only evidence from the resume and JD.
- Keep the tone professional, clear, and specific.
- Return only valid JSON. Do not wrap it in markdown.

JSON schema:
{{
  "customized_cover_letter": "Cover letter text",
  "short_recruiter_message": "Short email/message to recruiter",
  "linkedin_dm_message": "Brief LinkedIn DM"
}}

Resume:
{resume_text}

Job Description:
{jd_text}
"""


RESUME_IMPROVEMENT_PROMPT = """You are an expert resume coach and ATS optimization specialist.

Using the resume and job description, produce a strict JSON response with resume improvements tailored to the JD.

Rules:
- Use only the provided resume and JD.
- Do not invent experience.
- Rewrite bullets only by improving wording around existing evidence.
- Return only valid JSON. Do not wrap it in markdown.

JSON schema:
{{
  "rewritten_bullets": [
    {{
      "original": "Original resume bullet or section",
      "improved": "Improved version",
      "reason": "Why this helps"
    }}
  ],
  "suggested_keywords": [
    "Keyword"
  ],
  "ats_optimization": [
    "ATS suggestion"
  ],
  "missing_project_or_skill_suggestions": [
    {{
      "gap": "Missing skill/project area",
      "suggested_resume_addition": "What to add if the candidate truly has this experience"
    }}
  ]
}}

Resume:
{resume_text}

Job Description:
{jd_text}
"""


VOICE_ANSWER_EVALUATION_PROMPT = """You are an expert interview evaluator.

Evaluate the candidate answer against the interview question and optional job description context.
Return a strict JSON response.

Rules:
- Be constructive and specific.
- Do not invent details.
- The score must be an integer from 0 to 100.
- Return only valid JSON. Do not wrap it in markdown.

JSON schema:
{{
  "score": 0,
  "feedback": "Detailed feedback",
  "strengths": ["Strength"],
  "improvements": ["Improvement"],
  "better_answer": "A stronger answer the candidate could give"
}}

Question:
{question}

Candidate Answer:
{answer_text}

Job Description Context:
{jd_text}
"""
