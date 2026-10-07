"""Score trends, repeated feedback, and practice priorities from saved sessions."""

import streamlit as st

from services.progress import get_progress
from streamlit_ui.helpers import show_error


def render_progress_tab():
    st.header("Progress Dashboard")
    st.caption("Review saved interview-session scores and find what to practise next.")
    period = st.selectbox(
        "Time range",
        ["All time", "Last 7 days", "Last 30 days", "Last 90 days"],
        key="progress_period",
    )
    days = {"All time": None, "Last 7 days": 7, "Last 30 days": 30, "Last 90 days": 90}[
        period
    ]
    include_followups = st.checkbox(
        "Include follow-up answers", value=True, key="progress_followups"
    )
    try:
        data = get_progress(days, include_followups)
        summary = data["summary"]
        columns = st.columns(4)
        columns[0].metric("Sessions", summary["sessions"])
        columns[1].metric("Completed sessions", summary["completed_sessions"])
        columns[2].metric("Evaluated answers", summary["answers"])
        delta = (
            f"{summary['score_change']:+.1f} points"
            if summary["score_change"] is not None
            else None
        )
        columns[3].metric(
            "Average score",
            (
                f"{summary['average_score']}/100"
                if summary["average_score"] is not None
                else "No scores yet"
            ),
            delta=delta,
        )
        if not summary["answers"]:
            st.info(
                "Answer questions in Interview Sessions to build your dashboard. Try a wider time range if you already have saved answers."
            )
            return
        st.subheader("Score trend")
        st.line_chart(
            [
                {"Day (UTC)": row["date"], "Average score": row["average_score"]}
                for row in data["score_trend"]
            ],
            x="Day (UTC)",
            y="Average score",
        )
        window = summary["trend_window"]
        st.caption(
            f"Daily averages use UTC. The score change compares the latest {window} answers with the preceding {window}; it needs {2 * window} answers. AI scores may vary with question difficulty and role. Older saved scores may use an earlier evaluation method."
        )
        st.dataframe(
            [
                {
                    "Session": row["title"],
                    "Answers in range": row["answer_count"],
                    "Average score": row["average_score"],
                }
                for row in data["session_scores"]
            ],
            hide_index=True,
        )
        st.subheader("Recurring weaknesses")
        st.caption(
            "Feedback is grouped by matching phrases; counts represent distinct answers. Original suggestions are shown below."
        )
        if data["recurring_weaknesses"]:
            st.bar_chart(
                [
                    {"Theme": row["theme"], "Answers": row["answer_count"]}
                    for row in data["recurring_weaknesses"]
                ],
                x="Theme",
                y="Answers",
            )
            for row in data["recurring_weaknesses"]:
                with st.expander(
                    f"{row['theme']} ({row['answer_count']} answers across {row['session_count']} sessions)"
                ):
                    for example in row["examples"]:
                        st.write(example)
        else:
            st.info("No repeated feedback themes in the selected answers yet.")
        st.subheader("Topics needing practice")
        st.caption(
            f"Topics are matched from question wording. Priorities have an average below {summary['practice_score_target']}/100 or repeated improvement feedback. An answer can belong to several topics."
        )
        st.dataframe(
            [
                {
                    "Topic": row["topic"],
                    "Answers": row["answer_count"],
                    "Average score": row["average_score"],
                    "Needs practice": row["needs_practice"],
                }
                for row in data["topics"]
            ],
            hide_index=True,
        )
        priorities = [row for row in data["topics"] if row["needs_practice"]]
        if not priorities:
            st.success(
                "No practice priorities found in the selected answers. Keep practising to build more evidence."
            )
        for row in priorities:
            with st.expander(f"Practise {row['topic']}"):
                st.write("; ".join(row["reasons"]))
                for suggestion in row["suggestions"]:
                    st.write(suggestion)
                st.write("Revisit these questions in a new interview session:")
                for question in row["practice_questions"]:
                    st.write(
                        f"{question['question']} (previous score: {question['score']}/100)"
                    )
    except Exception as exc:
        show_error(exc, operation="progress_dashboard")
