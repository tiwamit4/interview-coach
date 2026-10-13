import { Download, FileText, Printer } from "lucide-react";
import type { Evaluation, Result } from "../lib/types";
import { Bullets, Card, Score } from "./ui";
const labels: Record<string, string> = {
  relevance: "Relevance",
  depth: "Depth",
  supporting_details: "Supporting details",
  clarity: "Clarity",
};
function save(content: string, mime: string, name: string) {
  const url = URL.createObjectURL(new Blob([content], { type: mime }));
  const a = document.createElement("a");
  a.href = url;
  a.download = name;
  a.click();
  setTimeout(() => URL.revokeObjectURL(url), 1000);
}
export function toMarkdown(value: unknown, level = 1): string {
  if (value === null || value === undefined) return "";
  if (typeof value !== "object") return String(value);
  if (Array.isArray(value))
    return value
      .map((item) =>
        typeof item === "object"
          ? toMarkdown(item, Math.min(level + 1, 6))
          : `- ${String(item)}`,
      )
      .join("\n\n");
  return Object.entries(value as Result)
    .filter(
      ([key]) =>
        !["output_path", "jd", "resume", "task", "source_type"].includes(key),
    )
    .map(
      ([key, entry]) =>
        `${"#".repeat(Math.min(level, 6))} ${key.replaceAll("_", " ")}\n\n${toMarkdown(entry, level + 1)}`,
    )
    .join("\n\n");
}
export function Downloads({
  result,
  title = "interview-coach",
}: {
  result: unknown;
  title?: string;
}) {
  const name = title.toLowerCase().replace(/[^a-z0-9-]+/g, "-");
  return (
    <div className="download-row">
      <button
        className="button ghost"
        onClick={() =>
          save(
            JSON.stringify(result, null, 2),
            "application/json",
            `${name}.json`,
          )
        }
      >
        <Download size={15} />
        JSON
      </button>
      <button
        className="button ghost"
        onClick={() =>
          save(toMarkdown(result), "text/markdown;charset=utf-8", `${name}.md`)
        }
      >
        <FileText size={15} />
        Markdown
      </button>
      <button
        className="button ghost"
        onClick={() => {
          const popup = window.open("", "_blank");
          if (!popup) return;
          popup.document.title = title;
          const pre = popup.document.createElement("pre");
          pre.style.cssText =
            "white-space:pre-wrap;font:14px/1.7 system-ui;max-width:800px;margin:40px auto";
          pre.textContent = toMarkdown(result);
          popup.document.body.append(pre);
          popup.focus();
          popup.print();
        }}
      >
        <Printer size={15} />
        Print / PDF
      </button>
    </div>
  );
}
export function EvaluationView({ evaluation }: { evaluation: Evaluation }) {
  return (
    <div className="result-document">
      <div className="evaluation-top">
        <Score value={evaluation.score} label="Answer score" />
        <div>
          <p className="eyebrow">YOUR FEEDBACK</p>
          <p>{evaluation.feedback}</p>
        </div>
      </div>
      {evaluation.rubric ? (
        <>
          <h3>Why this score?</h3>
          <p className="muted">
            Rubric {evaluation.rubric_version}: four criteria, 25 points each.
            Quotes are checked against your answer.
          </p>
          <div className="rubric-grid">
            {Object.entries(evaluation.rubric).map(([key, item]) => (
              <details key={key} className="rubric">
                <summary>
                  {labels[key] || key}
                  <b>{item.points}/25</b>
                </summary>
                <p>{item.reasoning}</p>
                {item.quotes.map((quote, i) => (
                  <blockquote key={i}>{quote}</blockquote>
                ))}
                {!item.quotes.length && (
                  <p className="muted">Not demonstrated in this answer.</p>
                )}
              </details>
            ))}
          </div>
        </>
      ) : (
        <p className="muted">
          This saved evaluation predates the scoring rubric.
        </p>
      )}
      <div className="two-columns">
        <div>
          <h3>What worked</h3>
          <Bullets items={evaluation.strengths} />
        </div>
        <div>
          <h3>What to improve</h3>
          <Bullets items={evaluation.improvements} />
        </div>
      </div>
      <div className="soft-panel">
        <h3>A stronger answer</h3>
        <p className="pre-wrap">{evaluation.better_answer}</p>
      </div>
      <p className="fine-print">
        Quotes verify source text, not the truth of a claim or the evaluator’s
        judgment.
      </p>
    </div>
  );
}
type Match = {
  role_fit_score: number;
  summary: string;
  matched_skills: {
    skill: string;
    resume_evidence: string;
    jd_evidence: string;
  }[];
  missing_skills: {
    skill: string;
    why_it_matters: string;
    suggested_action: string;
  }[];
  improvement_suggestions: string[];
};
type Prep = {
  likely_interview_questions: {
    question: string;
    why_it_may_be_asked: string;
    answer_based_on_resume: string;
  }[];
  weak_areas_to_revise: {
    area: string;
    reason: string;
    revision_plan: string;
  }[];
  project_explanations_to_prepare: {
    project: string;
    how_to_explain: string;
    jd_connection: string;
  }[];
};
type Improvement = {
  rewritten_bullets: { original: string; improved: string; reason: string }[];
  suggested_keywords: string[];
  ats_optimization: string[];
  missing_project_or_skill_suggestions: {
    gap: string;
    suggested_resume_addition: string;
  }[];
};
export function ResultView({ result }: { result: Result }) {
  const match = result.match_analysis as Match | undefined,
    prep = result.interview_prep as Prep | undefined,
    improvement = result.resume_improvements as Improvement | undefined,
    messages = result.application_messages as
      | Record<string, string>
      | undefined;
  return (
    <Card className="result-card">
      <div className="section-heading">
        <div>
          <p className="eyebrow">READY TO REVIEW</p>
          <h2>Your results</h2>
        </div>
        <Downloads result={result} />
      </div>
      {typeof result.questions === "string" && (
        <div className="prose pre-wrap">{result.questions}</div>
      )}
      {match && (
        <>
          <div className="evaluation-top">
            <Score value={match.role_fit_score} label="Role fit" />
            <p>{match.summary}</p>
          </div>
          <div className="two-columns">
            <div>
              <h3>Matched skills</h3>
              {match.matched_skills.map((item, i) => (
                <details className="rubric" key={i}>
                  <summary>{item.skill}</summary>
                  <p>
                    <b>Your experience:</b> {item.resume_evidence}
                  </p>
                  <p>
                    <b>The role:</b> {item.jd_evidence}
                  </p>
                </details>
              ))}
            </div>
            <div>
              <h3>Skills to develop</h3>
              {match.missing_skills.map((item, i) => (
                <div className="soft-panel" key={i}>
                  <b>{item.skill}</b>
                  <p>{item.why_it_matters}</p>
                  <p>{item.suggested_action}</p>
                </div>
              ))}
            </div>
          </div>
          <h3>Your next steps</h3>
          <Bullets items={match.improvement_suggestions} />
        </>
      )}
      {prep && (
        <>
          <h3>Likely interview questions</h3>
          {prep.likely_interview_questions.map((item, i) => (
            <details className="rubric" key={i}>
              <summary>
                {i + 1}. {item.question}
              </summary>
              <p>{item.why_it_may_be_asked}</p>
              <h4>How to answer</h4>
              <p>{item.answer_based_on_resume}</p>
            </details>
          ))}
          <h3>Revision plan</h3>
          {prep.weak_areas_to_revise.map((item, i) => (
            <div className="soft-panel" key={i}>
              <b>{item.area}</b>
              <p>{item.reason}</p>
              <p>{item.revision_plan}</p>
            </div>
          ))}
          <h3>Explain your projects</h3>
          {prep.project_explanations_to_prepare.map((item, i) => (
            <details className="rubric" key={i}>
              <summary>{item.project}</summary>
              <p>{item.how_to_explain}</p>
              <p>{item.jd_connection}</p>
            </details>
          ))}
        </>
      )}
      {improvement && (
        <>
          <h3>Stronger resume bullets</h3>
          {improvement.rewritten_bullets.map((item, i) => (
            <div className="soft-panel" key={i}>
              <small>BEFORE</small>
              <p>{item.original}</p>
              <small>AFTER</small>
              <p>
                <b>{item.improved}</b>
              </p>
              <p className="muted">{item.reason}</p>
            </div>
          ))}
          <h3>Keywords for this role</h3>
          <div className="tag-row">
            {improvement.suggested_keywords.map((word, i) => (
              <span className="tag" key={i}>
                {word}
              </span>
            ))}
          </div>
          <h3>ATS suggestions</h3>
          <Bullets items={improvement.ats_optimization} />
          {improvement.missing_project_or_skill_suggestions.map((item, i) => (
            <div className="soft-panel" key={i}>
              <b>{item.gap}</b>
              <p>{item.suggested_resume_addition}</p>
            </div>
          ))}
        </>
      )}
      {messages &&
        Object.entries(messages).map(([key, text]) => (
          <div key={key}>
            <h3>{key.replaceAll("_", " ")}</h3>
            <p className="prose pre-wrap">{text}</p>
          </div>
        ))}
      {Boolean(result.evaluation) && (
        <EvaluationView evaluation={result.evaluation as Evaluation} />
      )}
      <details className="raw-result">
        <summary>View complete response</summary>
        <pre>{JSON.stringify(result, null, 2)}</pre>
      </details>
    </Card>
  );
}
