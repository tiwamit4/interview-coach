import json

import streamlit as st

from streamlit_ui.exports import (
    application_messages_to_markdown,
    interview_prep_to_markdown,
    markdown_to_pdf,
    match_analysis_to_markdown,
    questions_to_markdown,
    resume_improvements_to_markdown,
    voice_evaluation_to_markdown,
)
from streamlit_ui.helpers import safe_filename


def render_output(title, questions, output_path=None, source_text=None):
    st.subheader(title)
    st.markdown(questions)
    markdown_text = questions_to_markdown(title, questions, source_text)
    render_markdown_pdf_downloads(markdown_text, safe_filename(title.lower()))

    if output_path:
        st.caption(f"Saved to {output_path}")

    if source_text:
        with st.expander("View extracted source text"):
            st.text_area(
                "Extracted text", source_text, height=320, label_visibility="collapsed"
            )


def render_transcript(transcript, output_path=None):
    st.subheader("Audio Transcript")
    st.text_area("Transcript", transcript, height=300, label_visibility="collapsed")
    st.download_button(
        "Download transcript",
        transcript,
        file_name="audio_transcript.txt",
        mime="text/plain",
    )

    if output_path:
        st.caption(f"Saved to {output_path}")


def render_json_extraction(result):
    st.subheader("Extracted JSON")
    st.json(result)
    json_text = json.dumps(result, indent=2, ensure_ascii=False)
    st.download_button(
        "Download JSON",
        json_text,
        file_name="jd_resume_extracted.json",
        mime="application/json",
    )

    output_path = result.get("output_path")
    if output_path:
        st.caption(f"Saved to {output_path}")


def render_match_analysis(result):
    analysis = result["match_analysis"]
    st.subheader("Resume Match Analysis")
    st.metric("Role Fit Score", f"{analysis.get('role_fit_score', 0)}/100")

    summary = analysis.get("summary")
    if summary:
        st.markdown(f"**Summary:** {summary}")

    matched_skills = analysis.get("matched_skills", [])
    missing_skills = analysis.get("missing_skills", [])
    suggestions = analysis.get("improvement_suggestions", [])

    col_match, col_missing = st.columns(2)
    with col_match:
        st.markdown("### Matched Skills")
        if matched_skills:
            for item in matched_skills:
                skill = item.get("skill", "Matched skill")
                with st.expander(skill):
                    st.markdown(
                        f"**Resume evidence:** {item.get('resume_evidence', 'Not provided')}"
                    )
                    st.markdown(
                        f"**JD evidence:** {item.get('jd_evidence', 'Not provided')}"
                    )
        else:
            st.caption("No matched skills returned.")

    with col_missing:
        st.markdown("### Missing Skills")
        if missing_skills:
            for item in missing_skills:
                skill = item.get("skill", "Missing skill")
                with st.expander(skill):
                    st.markdown(
                        f"**Why it matters:** {item.get('why_it_matters', 'Not provided')}"
                    )
                    st.markdown(
                        f"**Suggested action:** {item.get('suggested_action', 'Not provided')}"
                    )
        else:
            st.caption("No missing skills returned.")

    st.markdown("### Improvement Suggestions")
    if suggestions:
        for suggestion in suggestions:
            st.markdown(f"- {suggestion}")
    else:
        st.caption("No suggestions returned.")

    render_markdown_pdf_downloads(
        match_analysis_to_markdown(result),
        "jd_resume_match_analysis",
    )
    render_json_download(result, "jd_resume_match_analysis.json")


def render_interview_prep(result):
    prep = result["interview_prep"]
    st.subheader("Tailored Interview Prep")

    st.markdown("### Likely Interview Questions")
    for item in prep.get("likely_interview_questions", []):
        with st.expander(item.get("question", "Question")):
            st.markdown(
                f"**Why it may be asked:** {item.get('why_it_may_be_asked', 'Not provided')}"
            )
            st.markdown(
                f"**Answer based on resume:** {item.get('answer_based_on_resume', 'Not provided')}"
            )

    st.markdown("### Weak Areas to Revise")
    for item in prep.get("weak_areas_to_revise", []):
        with st.expander(item.get("area", "Area")):
            st.markdown(f"**Reason:** {item.get('reason', 'Not provided')}")
            st.markdown(
                f"**Revision plan:** {item.get('revision_plan', 'Not provided')}"
            )

    st.markdown("### Project Explanations to Prepare")
    for item in prep.get("project_explanations_to_prepare", []):
        with st.expander(item.get("project", "Project")):
            st.markdown(
                f"**How to explain:** {item.get('how_to_explain', 'Not provided')}"
            )
            st.markdown(
                f"**JD connection:** {item.get('jd_connection', 'Not provided')}"
            )

    render_markdown_pdf_downloads(interview_prep_to_markdown(result), "interview_prep")
    render_json_download(result, "interview_prep.json")


def render_cover_letter(result):
    messages = result["application_messages"]
    st.subheader("Application Messages")
    st.markdown("### Customized Cover Letter")
    st.write(messages.get("customized_cover_letter", ""))
    st.markdown("### Short Recruiter Message")
    st.write(messages.get("short_recruiter_message", ""))
    st.markdown("### LinkedIn DM Message")
    st.write(messages.get("linkedin_dm_message", ""))
    render_markdown_pdf_downloads(
        application_messages_to_markdown(result), "application_messages"
    )
    render_json_download(result, "application_messages.json")


def render_resume_improvements(result):
    improvements = result["resume_improvements"]
    st.subheader("Resume Improvements")

    st.markdown("### Rewritten Bullets")
    for item in improvements.get("rewritten_bullets", []):
        with st.expander(item.get("original", "Resume bullet")[:90]):
            st.markdown(f"**Original:** {item.get('original', 'Not provided')}")
            st.markdown(f"**Improved:** {item.get('improved', 'Not provided')}")
            st.markdown(f"**Reason:** {item.get('reason', 'Not provided')}")

    st.markdown("### Suggested Keywords")
    st.write(
        ", ".join(improvements.get("suggested_keywords", [])) or "No keywords returned."
    )

    st.markdown("### ATS Optimization")
    for suggestion in improvements.get("ats_optimization", []):
        st.markdown(f"- {suggestion}")

    st.markdown("### Missing Project or Skill Suggestions")
    for item in improvements.get("missing_project_or_skill_suggestions", []):
        with st.expander(item.get("gap", "Gap")):
            st.markdown(item.get("suggested_resume_addition", "Not provided"))

    render_markdown_pdf_downloads(
        resume_improvements_to_markdown(result), "resume_improvements"
    )
    render_json_download(result, "resume_improvements.json")


def render_evaluation_rubric(evaluation):
    rubric = evaluation.get("rubric")
    if not rubric:
        st.caption(
            "This saved evaluation predates the scoring rubric; quoted evidence is unavailable."
        )
        return
    st.markdown("### Score breakdown")
    st.caption(
        f"Rubric version {evaluation.get('rubric_version', '1')}: four equally weighted criteria, 25 points each."
    )
    labels = {
        "relevance": "Relevance",
        "depth": "Depth",
        "supporting_details": "Supporting details",
        "clarity": "Clarity",
    }
    for name, label in labels.items():
        criterion = rubric[name]
        with st.expander(f"{label}: {criterion['points']}/25"):
            st.write(criterion["reasoning"])
            if criterion["quotes"]:
                st.write("Passages from your answer:")
                for quote in criterion["quotes"]:
                    st.text(quote)
            else:
                st.write(
                    "Not demonstrated in this answer; no supporting passage cited."
                )
    st.caption(
        "Quotes are checked against your submitted answer. They do not independently verify its claims or the evaluator's reasoning."
    )


def render_voice_evaluation(result):
    evaluation = result["evaluation"]
    st.subheader("Voice Interview Evaluation")
    st.metric("Answer Score", f"{evaluation.get('score', 0)}/100")
    st.markdown(f"**Feedback:** {evaluation.get('feedback', 'Not provided')}")
    render_evaluation_rubric(evaluation)

    st.markdown("### Strengths")
    for item in evaluation.get("strengths", []):
        st.markdown(f"- {item}")

    st.markdown("### Improvements")
    for item in evaluation.get("improvements", []):
        st.markdown(f"- {item}")

    st.markdown("### Better Answer")
    st.write(evaluation.get("better_answer", "Not provided"))
    render_markdown_pdf_downloads(
        voice_evaluation_to_markdown(result), "voice_answer_evaluation"
    )
    render_json_download(result, "voice_answer_evaluation.json")


def render_markdown_pdf_downloads(markdown_text, filename_stem):
    col_md, col_pdf = st.columns(2)
    with col_md:
        st.download_button(
            "Download Markdown",
            markdown_text,
            file_name=f"{filename_stem}.md",
            mime="text/markdown",
        )
    with col_pdf:
        st.download_button(
            "Download PDF",
            markdown_to_pdf(markdown_text),
            file_name=f"{filename_stem}.pdf",
            mime="application/pdf",
        )


def render_json_download(result, filename):
    json_text = json.dumps(result, indent=2, ensure_ascii=False)
    st.download_button(
        "Download JSON", json_text, file_name=filename, mime="application/json"
    )
    output_path = result.get("output_path")
    if output_path:
        st.caption(f"Saved to {output_path}")
    with st.expander("View full JSON"):
        st.json(result)
