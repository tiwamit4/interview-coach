import { useEffect, useState } from "react";
import { RefreshCw } from "lucide-react";
import { api } from "../lib/api";
import type { Progress } from "../lib/types";
import {
  Bullets,
  Card,
  EmptyState,
  ErrorNotice,
  PageHeader,
  Stat,
} from "../components/ui";
function Trend({ rows }: { rows: Progress["score_trend"] }) {
  const width = 760,
    height = 220,
    left = 36,
    top = 16,
    bottom = 28;
  const x = (i: number) =>
    left +
    (width - left - 20) * (rows.length === 1 ? 0.5 : i / (rows.length - 1));
  const y = (value: number) =>
    top + ((100 - value) / 100) * (height - top - bottom);
  return (
    <div className="trend-chart">
      <svg
        viewBox={`0 0 ${width} ${height}`}
        role="img"
        aria-label="Daily average interview scores from zero to one hundred"
      >
        {[0, 25, 50, 75, 100].map((score) => (
          <g key={score}>
            <line
              x1={left}
              x2={width}
              y1={y(score)}
              y2={y(score)}
              stroke="var(--line)"
            />
            <text x={0} y={y(score) + 4}>
              {score}
            </text>
          </g>
        ))}
        <polyline
          fill="none"
          stroke="var(--green)"
          strokeWidth="3"
          points={rows
            .map((row, i) => `${x(i)},${y(row.average_score)}`)
            .join(" ")}
        />
        {rows.map((row, i) => (
          <circle
            key={row.date}
            cx={x(i)}
            cy={y(row.average_score)}
            r={4}
            fill="var(--green)"
          >
            <title>
              {row.date}: {row.average_score}/100 ({row.answer_count} answers)
            </title>
          </circle>
        ))}
      </svg>
      <div className="chart-labels">
        <span>{rows[0]?.date}</span>
        <span>{rows.at(-1)?.date}</span>
      </div>
    </div>
  );
}
export default function ProgressPage({
  onPractice,
}: {
  onPractice: (questions: string) => void;
}) {
  const [days, setDays] = useState(""),
    [include, setInclude] = useState(true),
    [data, setData] = useState<Progress | null>(null),
    [error, setError] = useState<unknown>(null),
    [loading, setLoading] = useState(false),
    [version, setVersion] = useState(0);
  useEffect(() => {
    const controller = new AbortController();
    setLoading(true);
    setError(null);
    api<Progress>(
      `/progress?include_followups=${include}${days ? `&days=${days}` : ""}`,
      { signal: controller.signal },
    )
      .then(setData)
      .catch((e) => {
        if (!controller.signal.aborted) setError(e);
      })
      .finally(() => {
        if (!controller.signal.aborted) setLoading(false);
      });
    return () => controller.abort();
  }, [days, include, version]);
  return (
    <>
      <PageHeader
        eyebrow="SMALL STEPS. REAL PROGRESS."
        title="See how far you’ve come."
        description="Spot patterns in your practice and find the next thing worth working on."
      >
        <button
          className="button secondary"
          onClick={() => setVersion((v) => v + 1)}
          disabled={loading}
        >
          <RefreshCw size={16} />
          Refresh
        </button>
      </PageHeader>
      <div className="filter-row">
        <label>
          Time range
          <select value={days} onChange={(e) => setDays(e.target.value)}>
            <option value="">All time</option>
            <option value="7">Last 7 days</option>
            <option value="30">Last 30 days</option>
            <option value="90">Last 90 days</option>
          </select>
        </label>
        <label className="check">
          <input
            type="checkbox"
            checked={include}
            onChange={(e) => setInclude(e.target.checked)}
          />
          Include follow-up answers
        </label>
      </div>
      <ErrorNotice error={error} />
      {loading && (
        <p role="status" className="muted">
          Updating your progress…
        </p>
      )}
      {data && (
        <>
          <div className="stats-grid">
            <Stat label="Practice sessions" value={data.summary.sessions} />
            <Stat label="Completed" value={data.summary.completed_sessions} />
            <Stat label="Answers evaluated" value={data.summary.answers} />
            <Stat
              label="Average score"
              value={
                data.summary.average_score === null
                  ? "—"
                  : `${data.summary.average_score}/100`
              }
              detail={
                data.summary.score_change === null
                  ? undefined
                  : `${data.summary.score_change > 0 ? "+" : ""}${data.summary.score_change} points across recent answers`
              }
            />
          </div>
          {data.summary.answers ? (
            <>
              <Card>
                <div className="section-heading">
                  <div>
                    <p className="eyebrow">KEEP SHOWING UP</p>
                    <h2>Your score trend</h2>
                  </div>
                  <span className="tag">DAILY AVERAGE</span>
                </div>
                <Trend rows={data.score_trend} />
                <p className="fine-print">
                  Dates use UTC. Score change compares your latest{" "}
                  {data.summary.trend_window} answers with the previous{" "}
                  {data.summary.trend_window}. Question difficulty and earlier
                  scoring methods can affect comparisons.
                </p>
                <details className="rubric">
                  <summary>View session averages</summary>
                  <div className="table-wrap">
                    <table>
                      <thead>
                        <tr>
                          <th>Session</th>
                          <th>Answers</th>
                          <th>Average</th>
                        </tr>
                      </thead>
                      <tbody>
                        {data.session_scores.map((row) => (
                          <tr key={row.session_id}>
                            <td>{row.title}</td>
                            <td>{row.answer_count}</td>
                            <td>{row.average_score}/100</td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>
                </details>
              </Card>
              <div className="two-columns">
                <Card>
                  <p className="eyebrow">NOTICE THE PATTERNS</p>
                  <h2>Recurring feedback</h2>
                  {data.recurring_weaknesses.length ? (
                    data.recurring_weaknesses.map((row, i) => (
                      <details className="rubric" key={i}>
                        <summary>
                          {row.theme}
                          <b>{row.answer_count} answers</b>
                        </summary>
                        <small>{row.session_count} sessions</small>
                        <Bullets items={row.examples} />
                      </details>
                    ))
                  ) : (
                    <p className="muted">
                      No recurring themes yet. Keep practising to build more
                      evidence.
                    </p>
                  )}
                  <p className="fine-print">
                    Related English phrases are grouped together. Review the
                    original suggestions inside each theme.
                  </p>
                </Card>
                <Card>
                  <p className="eyebrow">YOUR NEXT FOCUS</p>
                  <h2>Topics to practise</h2>
                  {data.topics
                    .filter((row) => row.needs_practice)
                    .map((row) => (
                      <details className="rubric" key={row.topic}>
                        <summary>
                          {row.topic}
                          <b>{row.average_score}/100</b>
                        </summary>
                        <p>{row.reasons.join(" · ")}</p>
                        <Bullets items={row.suggestions} />
                        <button
                          className="button secondary"
                          onClick={() =>
                            onPractice(
                              row.practice_questions
                                .map((item) => item.question)
                                .join("\n"),
                            )
                          }
                        >
                          Practise this topic
                        </button>
                      </details>
                    ))}
                  {!data.topics.some((row) => row.needs_practice) && (
                    <p className="muted">
                      No practice priorities found in this selection.
                    </p>
                  )}
                  <p className="fine-print">
                    Topics are matched from question wording. Scores below{" "}
                    {data.summary.practice_score_target}/100 or repeated
                    feedback suggest a priority.
                  </p>
                </Card>
              </div>
              <Card>
                <h2>All topic scores</h2>
                <div className="table-wrap">
                  <table>
                    <thead>
                      <tr>
                        <th>Topic</th>
                        <th>Answers</th>
                        <th>Average</th>
                        <th>Focus</th>
                      </tr>
                    </thead>
                    <tbody>
                      {data.topics.map((row) => (
                        <tr key={row.topic}>
                          <td>{row.topic}</td>
                          <td>{row.answer_count}</td>
                          <td>{row.average_score}/100</td>
                          <td>
                            <span
                              className={`tag ${row.needs_practice ? "warm" : ""}`}
                            >
                              {row.needs_practice
                                ? "Practise next"
                                : "Keep going"}
                            </span>
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              </Card>
            </>
          ) : (
            <Card>
              <EmptyState
                title="Every answer adds up"
                description="Complete an answer in Interview Sessions to start tracking your scores, feedback themes, and practice priorities."
              />
              <button
                className="button secondary"
                onClick={() => onPractice("")}
              >
                Start a practice session
              </button>
            </Card>
          )}
        </>
      )}
    </>
  );
}
