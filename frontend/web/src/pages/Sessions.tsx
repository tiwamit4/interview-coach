import { useEffect, useRef, useState } from "react";
import { CheckCircle2, Plus, RefreshCw } from "lucide-react";
import { api, jsonBody, parseQuestions } from "../lib/api";
import type { Session, SessionSummary, UIConfig } from "../lib/types";
import { SimulationReport } from "../components/SimulationReport";
import { AnswerInput } from "../components/AnswerInput";
import { Downloads, EvaluationView } from "../components/Results";
import {
  BusyButton,
  Card,
  EmptyState,
  ErrorNotice,
  PageHeader,
} from "../components/ui";
export default function Sessions({
  config,
  draft,
  onDraftUsed,
}: {
  config: UIConfig;
  draft: string;
  onDraftUsed: () => void;
}) {
  const [items, setItems] = useState<SessionSummary[]>([]),
    [session, setSession] = useState<Session | null>(null),
    [title, setTitle] = useState("Interview practice"),
    [questions, setQuestions] = useState(draft),
    [context, setContext] = useState(""),
    [followups, setFollowups] = useState(true),
    [timed, setTimed] = useState(false),
    [duration, setDuration] = useState(config.simulation_default_minutes),
    [remaining, setRemaining] = useState<number | null>(null),
    [answer, setAnswer] = useState(""),
    [busy, setBusy] = useState(false),
    [loading, setLoading] = useState(false),
    [recording, setRecording] = useState(false),
    [error, setError] = useState<unknown>(null),
    [showCreate, setShowCreate] = useState(true);
  const expirationRequested = useRef<string | null>(null);
  useEffect(() => {
    if (!session?.simulation || session.status === "completed") {
      setRemaining(null);
      return;
    }
    // Anchor to the server's remaining time so a different browser clock is safe.
    const end = performance.now() + session.simulation.remaining_seconds * 1000;
    const tick = () =>
      setRemaining(Math.max(0, Math.ceil((end - performance.now()) / 1000)));
    tick();
    const interval = window.setInterval(tick, 250);
    return () => window.clearInterval(interval);
  }, [session]);
  useEffect(() => {
    if (
      remaining !== 0 ||
      busy ||
      !session?.simulation ||
      session.status === "completed" ||
      expirationRequested.current === session.id
    )
      return;
    expirationRequested.current = session.id;
    void load(session.id).then(() => refresh());
  }, [remaining, busy, session?.id, session?.status]);
  useEffect(() => {
    if (draft) {
      setQuestions(draft);
      setShowCreate(true);
      onDraftUsed();
    }
  }, [draft, onDraftUsed]);
  async function refresh() {
    setLoading(true);
    try {
      const result = await api<{ items: SessionSummary[] }>(
        "/sessions?limit=100",
      );
      setItems(result.items);
    } catch (e) {
      setError(e);
    } finally {
      setLoading(false);
    }
  }
  useEffect(() => {
    void refresh();
  }, []);
  async function load(id: string) {
    setBusy(true);
    setError(null);
    try {
      setSession(await api<Session>(`/sessions/${id}`));
      setAnswer("");
    } catch (e) {
      setError(e);
    } finally {
      setBusy(false);
    }
  }
  async function create(event: React.FormEvent) {
    event.preventDefault();
    setBusy(true);
    setError(null);
    try {
      const parsed = parseQuestions(questions);
      if (!parsed.length || parsed.length > config.max_session_questions)
        throw new Error(
          `Enter between 1 and ${config.max_session_questions} questions, one per line.`,
        );
      const created = await api<Session>(
        "/sessions",
        jsonBody({
          title,
          questions: parsed,
          role_context: context,
          followups_enabled: followups,
          simulation_duration_minutes: timed ? duration : null,
        }),
      );
      setSession(created);
      setAnswer("");
      setShowCreate(false);
      await refresh();
    } catch (e) {
      setError(e);
    } finally {
      setBusy(false);
    }
  }
  async function submit(event: React.FormEvent) {
    event.preventDefault();
    if (!session) return;
    setBusy(true);
    setError(null);
    try {
      if (!answer.trim()) throw new Error("Record or type an answer first.");
      const result = await api<{ session: Session }>(
        `/sessions/${session.id}/answers`,
        jsonBody({
          answer_text: answer,
          expected_question_index: session.current_question_index,
        }),
      );
      setSession(result.session);
      setAnswer("");
      await refresh();
    } catch (e) {
      setError(e);
    } finally {
      setBusy(false);
    }
  }
  async function finish() {
    if (!session) return;
    setBusy(true);
    setError(null);
    try {
      setSession(
        await api<Session>(`/sessions/${session.id}/finish`, {
          method: "POST",
        }),
      );
      setAnswer("");
      await refresh();
    } catch (e) {
      setError(e);
    } finally {
      setBusy(false);
    }
  }
  const previous = session?.answers.at(-1),
    followup = session?.followups.find(
      (item) => item.question_index === session.current_question_index,
    );
  return (
    <>
      <PageHeader
        eyebrow="BUILD YOUR CONFIDENCE"
        title="One question. One step forward."
        description="Practise a complete interview, with saved answers and follow-ups that respond to your story."
      >
        <button
          className="button secondary"
          onClick={() => setShowCreate(!showCreate)}
        >
          <Plus size={17} />
          New session
        </button>
      </PageHeader>
      <ErrorNotice error={error} />
      {showCreate && (
        <Card>
          <h2>Start a practice session</h2>
          <form onSubmit={create}>
            <div className="two-columns">
              <label>
                Session title
                <input
                  value={title}
                  onChange={(e) => setTitle(e.target.value)}
                  maxLength={120}
                  required
                />
              </label>
              <label>
                Role context <span className="muted">(optional)</span>
                <input
                  value={context}
                  onChange={(e) => setContext(e.target.value)}
                  maxLength={10000}
                  placeholder="e.g. Python developer at a small product team"
                />
              </label>
            </div>
            <label>
              Questions, one per line
              <textarea
                rows={5}
                value={questions}
                onChange={(e) => setQuestions(e.target.value)}
                placeholder="Tell me about your latest project.
How did you test it?"
                required
              />
            </label>
            <label className="check">
              <input
                type="checkbox"
                checked={followups}
                onChange={(e) => setFollowups(e.target.checked)}
              />
              Generate answer-based follow-up questions
            </label>
            <label className="check">
              <input
                type="checkbox"
                checked={timed}
                onChange={(e) => setTimed(e.target.checked)}
              />
              Timed interview simulation
            </label>
            {timed && (
              <label>
                Interview duration (minutes)
                <input
                  type="number"
                  min={1}
                  max={config.simulation_max_minutes}
                  required
                  value={duration}
                  onChange={(e) => setDuration(Number(e.target.value))}
                />
                <span className="muted">
                  The timer starts immediately and continues during recording
                  and AI processing. Feedback appears at the end. Follow-ups
                  share the same time budget.
                </span>
              </label>
            )}
            <BusyButton busy={busy} type="submit">
              Start session
            </BusyButton>
          </form>
        </Card>
      )}
      <div className="sessions-layout">
        <Card>
          <div className="section-heading">
            <h2>Saved sessions</h2>
            <button
              aria-label="Refresh sessions"
              className="icon-button"
              disabled={busy || loading}
              onClick={() => void refresh()}
            >
              <RefreshCw size={16} />
            </button>
          </div>
          {loading && <p className="muted">Loading sessionsâ€¦</p>}
          {!items.length && !loading && (
            <p className="muted">Your sessions will appear here.</p>
          )}
          <div className="session-list">
            {items.map((item) => (
              <button
                key={item.id}
                className={`session-item ${session?.id === item.id ? "selected" : ""}`}
                disabled={busy || recording}
                onClick={() => void load(item.id)}
              >
                <strong>{item.title}</strong>
                <span>
                  {item.answered_questions}/{item.total_questions} answered Â·{" "}
                  {item.average_score === null
                    ? "No score yet"
                    : `${item.average_score}/100`}
                </span>
                <small>
                  {item.status === "completed" ? "Completed" : "In progress"}
                </small>
              </button>
            ))}
          </div>
        </Card>
        <div>
          {session ? (
            <>
              <Card>
                <div className="section-heading">
                  <div>
                    <p className="eyebrow">{session.title}</p>
                    <h2>
                      {session.status === "completed"
                        ? "Practice complete"
                        : `Question ${session.current_question_index + 1} of ${session.total_questions}`}
                    </h2>
                  </div>
                  <span className="tag">
                    {session.answered_questions} answered
                  </span>
                </div>
                {session.simulation && session.status !== "completed" && (
                  <div className="notice">
                    <strong role="timer" aria-label="Interview time remaining">
                      Time remaining: {Math.floor((remaining ?? 0) / 60)}:
                      {String((remaining ?? 0) % 60).padStart(2, "0")}
                    </strong>
                    <p>
                      Your submitted answers are saved. You can finish early to
                      view your report. Any unsubmitted answer will be discarded
                      when you finish or time expires.
                    </p>
                    <button
                      className="button secondary"
                      disabled={busy || recording}
                      onClick={() => void finish()}
                    >
                      Finish interview
                    </button>
                    <button
                      className="button ghost"
                      disabled={busy || recording}
                      onClick={() => void load(session.id)}
                    >
                      Refresh interview
                    </button>
                  </div>
                )}
                <progress
                  value={session.answered_questions}
                  max={session.total_questions}
                />
                {session.status === "completed" ? (
                  <div className="completed">
                    <CheckCircle2 size={36} />
                    <h2>You showed up. Thatâ€™s progress.</h2>
                    {session.report ? (
                      <SimulationReport report={session.report} />
                    ) : (
                      <p>
                        Average answer score:{" "}
                        <b>
                          {session.average_score === null
                            ? "No score yet"
                            : `${session.average_score}/100`}
                        </b>
                      </p>
                    )}
                    <Downloads result={session} title={session.title} />
                  </div>
                ) : (
                  <>
                    <h3 className="question-text">
                      {session.current_question}
                    </h3>
                    {followup && (
                      <p className="notice">
                        Follow-up to question{" "}
                        {followup.parent_question_index + 1}: {followup.reason}
                      </p>
                    )}
                    <form onSubmit={submit}>
                      <AnswerInput
                        key={`${session.id}_${session.current_question_index}`}
                        config={config}
                        value={answer}
                        onChange={setAnswer}
                        onBusy={setRecording}
                        disabled={busy || remaining === 0}
                      />
                      <BusyButton
                        busy={busy}
                        disabled={recording || remaining === 0}
                        type="submit"
                      >
                        Submit answer
                      </BusyButton>
                    </form>
                  </>
                )}
              </Card>
              {previous &&
                (!session.simulation || session.status === "completed") && (
                  <Card>
                    <h2>Feedback on your latest answer</h2>
                    <p className="muted">{previous.question}</p>
                    <EvaluationView evaluation={previous.evaluation} />
                  </Card>
                )}
              {session.answers.length > 0 &&
                (!session.simulation || session.status === "completed") && (
                  <Card>
                    <h2>Your saved answers</h2>
                    {session.answers.map((item) => (
                      <details className="rubric" key={item.question_index}>
                        <summary>
                          {item.question_index + 1}. {item.question}
                          <b>{item.evaluation.score}/100</b>
                        </summary>
                        <p className="pre-wrap">{item.answer_text}</p>
                        <EvaluationView evaluation={item.evaluation} />
                      </details>
                    ))}
                  </Card>
                )}
            </>
          ) : (
            <Card>
              <EmptyState
                title="Make room for practice"
                description="Start a new session or select a saved one. Your progress is saved after every answer."
              />
            </Card>
          )}
        </div>
      </div>
    </>
  );
}
