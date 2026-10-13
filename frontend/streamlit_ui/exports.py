import json

import textwrap


def _line(value=""):
    return str(value or "").strip()


def _bullet_list(items):
    return "\n".join(f"- {item}" for item in items) if items else "- Not provided"


def _markdown_header(title):
    return f"# {title}\n"


def questions_to_markdown(title, questions, source_text=None):
    parts = [_markdown_header(title), _line(questions)]
    if source_text:
        parts.extend(["\n## Extracted Source Text", _line(source_text)])
    return "\n\n".join(part for part in parts if part)


def match_analysis_to_markdown(result):
    analysis = result.get("match_analysis", {})
    parts = [
        _markdown_header("Resume Match Analysis"),
        f"**Role Fit Score:** {analysis.get('role_fit_score', 0)}/100",
        f"**Summary:** {_line(analysis.get('summary')) or 'Not provided'}",
        "\n## Matched Skills",
    ]

    for item in analysis.get("matched_skills", []):
        parts.append(
            "\n".join(
                [
                    f"### {_line(item.get('skill')) or 'Matched skill'}",
                    f"**Resume evidence:** {_line(item.get('resume_evidence')) or 'Not provided'}",
                    f"**JD evidence:** {_line(item.get('jd_evidence')) or 'Not provided'}",
                ]
            )
        )

    parts.append("\n## Missing Skills")
    for item in analysis.get("missing_skills", []):
        parts.append(
            "\n".join(
                [
                    f"### {_line(item.get('skill')) or 'Missing skill'}",
                    f"**Why it matters:** {_line(item.get('why_it_matters')) or 'Not provided'}",
                    f"**Suggested action:** {_line(item.get('suggested_action')) or 'Not provided'}",
                ]
            )
        )

    parts.extend(
        [
            "\n## Improvement Suggestions",
            _bullet_list(analysis.get("improvement_suggestions", [])),
        ]
    )
    return "\n\n".join(part for part in parts if part)


def interview_prep_to_markdown(result):
    prep = result.get("interview_prep", {})
    parts = [
        _markdown_header("Tailored Interview Prep"),
        "## Likely Interview Questions",
    ]

    for item in prep.get("likely_interview_questions", []):
        parts.append(
            "\n".join(
                [
                    f"### {_line(item.get('question')) or 'Question'}",
                    f"**Why it may be asked:** {_line(item.get('why_it_may_be_asked')) or 'Not provided'}",
                    f"**Answer based on resume:** {_line(item.get('answer_based_on_resume')) or 'Not provided'}",
                ]
            )
        )

    parts.append("\n## Weak Areas to Revise")
    for item in prep.get("weak_areas_to_revise", []):
        parts.append(
            "\n".join(
                [
                    f"### {_line(item.get('area')) or 'Area'}",
                    f"**Reason:** {_line(item.get('reason')) or 'Not provided'}",
                    f"**Revision plan:** {_line(item.get('revision_plan')) or 'Not provided'}",
                ]
            )
        )

    parts.append("\n## Project Explanations to Prepare")
    for item in prep.get("project_explanations_to_prepare", []):
        parts.append(
            "\n".join(
                [
                    f"### {_line(item.get('project')) or 'Project'}",
                    f"**How to explain:** {_line(item.get('how_to_explain')) or 'Not provided'}",
                    f"**JD connection:** {_line(item.get('jd_connection')) or 'Not provided'}",
                ]
            )
        )

    return "\n\n".join(part for part in parts if part)


def application_messages_to_markdown(result):
    messages = result.get("application_messages", {})
    return "\n\n".join(
        [
            _markdown_header("Application Messages"),
            "## Customized Cover Letter",
            _line(messages.get("customized_cover_letter")) or "Not provided",
            "## Short Recruiter Message",
            _line(messages.get("short_recruiter_message")) or "Not provided",
            "## LinkedIn DM Message",
            _line(messages.get("linkedin_dm_message")) or "Not provided",
        ]
    )


def resume_improvements_to_markdown(result):
    improvements = result.get("resume_improvements", {})
    parts = [_markdown_header("Resume Improvements"), "## Rewritten Bullets"]

    for item in improvements.get("rewritten_bullets", []):
        parts.append(
            "\n".join(
                [
                    f"### {_line(item.get('original'))[:90] or 'Resume bullet'}",
                    f"**Original:** {_line(item.get('original')) or 'Not provided'}",
                    f"**Improved:** {_line(item.get('improved')) or 'Not provided'}",
                    f"**Reason:** {_line(item.get('reason')) or 'Not provided'}",
                ]
            )
        )

    parts.extend(
        [
            "\n## Suggested Keywords",
            ", ".join(improvements.get("suggested_keywords", [])) or "Not provided",
            "\n## ATS Optimization",
            _bullet_list(improvements.get("ats_optimization", [])),
            "\n## Missing Project or Skill Suggestions",
        ]
    )
    for item in improvements.get("missing_project_or_skill_suggestions", []):
        parts.append(
            "\n".join(
                [
                    f"### {_line(item.get('gap')) or 'Gap'}",
                    _line(item.get("suggested_resume_addition")) or "Not provided",
                ]
            )
        )

    return "\n\n".join(part for part in parts if part)


def _rubric_to_markdown(evaluation):
    rubric = evaluation.get("rubric")
    if not rubric:
        return "This saved evaluation predates the scoring rubric; quoted evidence is unavailable."
    labels = {
        "relevance": "Relevance",
        "depth": "Depth",
        "supporting_details": "Supporting details",
        "clarity": "Clarity",
    }
    parts = [f"## Score Breakdown (Rubric {evaluation.get('rubric_version', '1')})"]
    for name, label in labels.items():
        criterion = rubric[name]
        parts.extend([f"### {label}: {criterion['points']}/25", criterion["reasoning"]])
        if criterion["quotes"]:
            parts.extend(
                "> " + quote.replace("\n", "\n> ") for quote in criterion["quotes"]
            )
        else:
            parts.append(
                "Not demonstrated in this answer; no supporting passage cited."
            )
    return "\n\n".join(parts)


def voice_evaluation_to_markdown(result):
    evaluation = result.get("evaluation", {})
    return "\n\n".join(
        [
            _markdown_header("Voice Interview Evaluation"),
            f"**Answer Score:** {evaluation.get('score', 0)}/100",
            f"**Feedback:** {_line(evaluation.get('feedback')) or 'Not provided'}",
            _rubric_to_markdown(evaluation),
            "## Strengths",
            _bullet_list(evaluation.get("strengths", [])),
            "## Improvements",
            _bullet_list(evaluation.get("improvements", [])),
            "## Better Answer",
            _line(evaluation.get("better_answer")) or "Not provided",
        ]
    )


def result_to_markdown(result, title="Interview Coach Output"):
    if "match_analysis" in result:
        return match_analysis_to_markdown(result)
    if "interview_prep" in result:
        return interview_prep_to_markdown(result)
    if "application_messages" in result:
        return application_messages_to_markdown(result)
    if "resume_improvements" in result:
        return resume_improvements_to_markdown(result)
    if "evaluation" in result:
        return voice_evaluation_to_markdown(result)
    if "questions" in result:
        return questions_to_markdown(title, result["questions"])
    return (
        _markdown_header(title)
        + "\n```json\n"
        + json.dumps(result, indent=2, ensure_ascii=False)
        + "\n```"
    )


def _escape_pdf_text(text):
    return str(text).replace("\\", "\\\\").replace("(", "\\(").replace(")", "\\)")


def _text_to_pdf_lines(markdown_text):
    text = markdown_text.replace("**", "")
    lines = []
    for raw_line in text.splitlines():
        line = raw_line.strip()
        if not line:
            lines.append("")
            continue
        for wrapped in textwrap.wrap(line, width=92, replace_whitespace=False):
            lines.append(wrapped)
    return lines


def markdown_to_pdf(markdown_text):
    lines = _text_to_pdf_lines(markdown_text)
    pages = []
    page_lines = []
    for line in lines:
        page_lines.append(line)
        if len(page_lines) == 46:
            pages.append(page_lines)
            page_lines = []
    if page_lines or not pages:
        pages.append(page_lines)

    objects = []

    def add_object(body):
        objects.append(body)
        return len(objects)

    catalog_id = add_object("<< /Type /Catalog /Pages 2 0 R >>")
    pages_id = add_object("")
    font_id = add_object("<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>")
    page_ids = []

    for page in pages:
        content_lines = ["BT", "/F1 10 Tf", "50 780 Td", "14 TL"]
        for line in page:
            content_lines.append(f"({_escape_pdf_text(line)}) Tj")
            content_lines.append("T*")
        content_lines.append("ET")
        content = "\n".join(content_lines)
        content_id = add_object(
            f"<< /Length {len(content.encode('latin-1', 'replace'))} >>\nstream\n{content}\nendstream"
        )
        page_id = add_object(
            f"<< /Type /Page /Parent {pages_id} 0 R /MediaBox [0 0 612 792] "
            f"/Resources << /Font << /F1 {font_id} 0 R >> >> /Contents {content_id} 0 R >>"
        )
        page_ids.append(page_id)

    objects[pages_id - 1] = (
        f"<< /Type /Pages /Kids [{' '.join(f'{page_id} 0 R' for page_id in page_ids)}] /Count {len(page_ids)} >>"
    )

    pdf = ["%PDF-1.4\n"]
    offsets = [0]
    for index, body in enumerate(objects, start=1):
        offsets.append(sum(len(part.encode("latin-1", "replace")) for part in pdf))
        pdf.append(f"{index} 0 obj\n{body}\nendobj\n")

    xref_offset = sum(len(part.encode("latin-1", "replace")) for part in pdf)
    pdf.append(f"xref\n0 {len(objects) + 1}\n")
    pdf.append("0000000000 65535 f \n")
    for offset in offsets[1:]:
        pdf.append(f"{offset:010d} 00000 n \n")
    pdf.append(
        f"trailer\n<< /Size {len(objects) + 1} /Root {catalog_id} 0 R >>\n"
        f"startxref\n{xref_offset}\n%%EOF\n"
    )
    return "".join(pdf).encode("latin-1", "replace")
