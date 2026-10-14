import { useEffect, useState } from "react";
import { RefreshCw } from "lucide-react";
import { api } from "../lib/api";
import type { DailyPractice as Plan, Session } from "../lib/types";
import { BusyButton, Card, ErrorNotice, PageHeader } from "../components/ui";

export default function DailyPractice({
  onOpenSession,
}: {
  onOpenSession: (id: string) => void;
}) {
  const [plan, setPlan] = useState<Plan | null>(null);
  const [error, setError] = useState<unknown>(null);
  const [loading, setLoading] = useState(false);
  const [starting, setStarting] = useState(false);
  const [version, setVersion] = useState(0);
  useEffect(() => {
    const controller = new AbortController();
    setLoading(true);
    setError(null);
    api<Plan>("/practice/daily", { signal: controller.signal })
      .then(setPlan)
      .catch((e) => {
        if (!controller.signal.aborted) setError(e);
      })
      .finally(() => {
        if (!controller.signal.aborted) setLoading(false);
      });
    return () => controller.abort();
  }, [version]);
  async function start() {
    setStarting(true);
    setError(null);
    try {
      const session = await api<Session>("/practice/daily/start", {
        method: "POST",
      });
      onOpenSession(session.id);
    } catch (e) {
      setError(e);
    } finally {
      setStarting(false);
    }
  }
  return (
    <>
      <PageHeader
        eyebrow="A LITTLE PRACTICE, EVERY DAY"
        title="Your daily practice"
        description="Revisit difficult answers, strengthen weak skills, and build toward harder questions."
      >
        <button
          className="button secondary"
          disabled={loading || starting}
          onClick={() => setVersion((v) => v + 1)}
        >
          <RefreshCw size={16} />
          Refresh practice
        </button>
      </PageHeader>
      <ErrorNotice error={error} />
      {loading && <p role="status">Loading your practice plan...</p>}
      {plan && (
        <>
          <Card>
            <div className="section-heading">
              <div>
                <p className="eyebrow">
                  {plan.date} ({plan.timezone})
                </p>
                <h2>Today's queue</h2>
              </div>
              <span className="tag">
                {plan.answered_questions}/{plan.items.length} answered
              </span>
            </div>
            <p>
              Questions stay the same for this UTC day. Your weakest recent
              skill scores come first; earlier low-scoring answers return for
              another attempt.
            </p>
            <progress value={plan.answered_questions} max={plan.items.length} />
            <ol>
              {plan.items.map((item, index) => (
                <li key={index} className="rubric">
                  <h3>{item.question}</h3>
                  <p>
                    <span className="tag">{item.skill}</span>{" "}
                    <span className="tag">
                      {item.difficulty === "original"
                        ? "Retry original question"
                        : item.difficulty}
                    </span>
                  </p>
                  <p className="muted">{item.reason}</p>
                  {item.completed && (
                    <p>
                      Completed: <b>{item.score}/100</b>
                      {item.previous_score !== null && (
                        <> (previously {item.previous_score}/100)</>
                      )}
                    </p>
                  )}
                </li>
              ))}
            </ol>
            <BusyButton
              busy={starting}
              disabled={loading}
              onClick={() => void start()}
            >
              {plan.status === "completed"
                ? "Review today's answers"
                : plan.session_id
                  ? "Continue daily practice"
                  : "Start daily practice"}
            </BusyButton>
            {plan.status === "completed" && (
              <p className="notice">
                Today's practice is complete. Your next queue is available
                tomorrow (UTC).
              </p>
            )}
          </Card>
          <Card>
            <h2>Skill improvement</h2>
            <p>
              Difficulty uses the latest scores for each skill: foundational,
              applied, then advanced. Lower scores can move the next queue back
              to foundational practice.
            </p>
            {!plan.skills.length ? (
              <p className="muted">
                Answer your first questions to establish a baseline.
              </p>
            ) : (
              <>
                <div className="table-wrap">
                  <table>
                    <thead>
                      <tr>
                        <th>Skill</th>
                        <th>Attempts</th>
                        <th>Recent average</th>
                        <th>Change</th>
                        <th>Next difficulty</th>
                      </tr>
                    </thead>
                    <tbody>
                      {plan.skills.map((skill) => (
                        <tr key={skill.skill}>
                          <td>{skill.skill}</td>
                          <td>
                            {skill.attempts} ({skill.daily_practice_attempts}{" "}
                            daily)
                          </td>
                          <td>{skill.recent_average}/100</td>
                          <td>
                            {skill.score_change === null
                              ? "Need more attempts"
                              : `${skill.score_change > 0 ? "+" : ""}${skill.score_change} points`}
                          </td>
                          <td>{skill.difficulty}</td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
                {plan.skills.map((skill) => (
                  <details className="rubric" key={skill.skill}>
                    <summary>{skill.skill} score history</summary>
                    {skill.comparison_samples > 0 && (
                      <p>
                        First {skill.comparison_samples} attempts:{" "}
                        {skill.baseline_average}/100. Latest{" "}
                        {skill.comparison_samples}: {skill.comparison_average}
                        /100. These groups do not overlap.
                      </p>
                    )}
                    <div className="table-wrap">
                      <table>
                        <thead>
                          <tr>
                            <th>Date (UTC)</th>
                            <th>Score</th>
                            <th>Question difficulty</th>
                          </tr>
                        </thead>
                        <tbody>
                          {skill.trend.map((row, i) => (
                            <tr key={i}>
                              <td>{row.date.slice(0, 10)}</td>
                              <td>{row.score}/100</td>
                              <td>{row.difficulty}</td>
                            </tr>
                          ))}
                        </tbody>
                      </table>
                    </div>
                  </details>
                ))}
                <p className="fine-print">
                  Topic matching groups earlier answers by question wording.
                  Daily questions keep their assigned skill. Score changes
                  describe saved evaluations; question difficulty and scoring
                  variation affect comparisons.
                </p>
              </>
            )}
          </Card>
        </>
      )}
    </>
  );
}
