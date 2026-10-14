import type { SimulationReport as Report } from "../lib/types";
import { Bullets } from "./ui";

export function SimulationReport({ report }: { report: Report }) {
  const reason =
    {
      all_questions_answered: "All questions answered",
      time_expired: "Time is up",
      finished_early: "Finished early",
    }[report.completion_reason] || "Interview complete";
  return (
    <section
      className="result-document"
      aria-label="Interview performance report"
    >
      <h2>Interview performance report</h2>
      <p>
        {reason}. {report.answered_questions} answered;{" "}
        {report.unanswered_questions} unanswered.
      </p>
      <p>
        Average answer score:{" "}
        <b>
          {report.average_score === null
            ? "No scored answers"
            : `${report.average_score}/100`}
        </b>
      </p>
      <p className="muted">
        Scores summarize submitted answers only. Unanswered questions receive no
        score.
      </p>
      {Object.keys(report.rubric_averages).length > 0 && (
        <>
          <h3>Average rubric scores</h3>
          {Object.entries(report.rubric_averages).map(([criterion, points]) => (
            <p key={criterion}>
              {criterion.replaceAll("_", " ")}: <b>{points}/25</b>
            </p>
          ))}
        </>
      )}
      {report.strengths.length > 0 && (
        <>
          <h3>Strengths</h3>
          <Bullets items={report.strengths} />
        </>
      )}
      {report.practice_priorities.length > 0 && (
        <>
          <h3>Practice priorities</h3>
          <Bullets items={report.practice_priorities} />
        </>
      )}
      {report.question_scores.length > 0 && (
        <>
          <h3>Question scores</h3>
          <ol>
            {report.question_scores.map((item, index) => (
              <li key={index}>
                {item.question}: <b>{item.score}/100</b>
              </li>
            ))}
          </ol>
        </>
      )}
      <p className="muted">
        This report combines your saved answer evaluations. Review the
        supporting quotes below.
      </p>
    </section>
  );
}
