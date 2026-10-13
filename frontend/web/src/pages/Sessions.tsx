import { useEffect, useState } from "react";
import { CheckCircle2, Plus, RefreshCw } from "lucide-react";
import { api, jsonBody, parseQuestions } from "../lib/api";
import type { Session, SessionSummary, UIConfig } from "../lib/types";
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
    [answer, setAnswer] = useState(""),
    [busy, setBusy] = useState(false),
    [loading, setLoading] = useState(false),
    [recording, setRecording] = useState(false),
    [error, setError] = useState<unknown>(null),
    [showCreate, setShowCreate] = useState(true);
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
          {loading && <p className="muted">Loading sessions…</p>}
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
                  {item.answered_questions}/{item.total_questions} answered ·{" "}
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
                <progress
                  value={session.answered_questions}
                  max={session.total_questions}
                />
                {session.status === "completed" ? (
                  <div className="completed">
                    <CheckCircle2 size={36} />
                    <h2>You showed up. That’s progress.</h2>
                    <p>
                      Average answer score: <b>{session.average_score}/100</b>
                    </p>
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
                        disabled={busy}
                      />
                      <BusyButton
                        busy={busy}
                        disabled={recording}
                        type="submit"
                      >
                        Submit answer
                      </BusyButton>
                    </form>
                  </>
                )}
              </Card>
              {previous && (
                <Card>
                  <h2>Feedback on your latest answer</h2>
                  <p className="muted">{previous.question}</p>
                  <EvaluationView evaluation={previous.evaluation} />
                </Card>
              )}
              {session.answers.length > 0 && (
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
