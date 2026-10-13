import { useState } from "react";
import { api, multipart } from "../lib/api";
import type { Result, UIConfig } from "../lib/types";
import { AnswerInput } from "../components/AnswerInput";
import { BusyButton, Card, ErrorNotice, PageHeader } from "../components/ui";
import { ResultView } from "../components/Results";
export default function Voice({ config }: { config: UIConfig }) {
  const [question, setQuestion] = useState(""),
    [context, setContext] = useState(""),
    [answer, setAnswer] = useState(""),
    [save, setSave] = useState(true),
    [busy, setBusy] = useState(false),
    [recording, setRecording] = useState(false),
    [error, setError] = useState<unknown>(null),
    [result, setResult] = useState<Result | null>(null);
  async function evaluate(event: React.FormEvent) {
    event.preventDefault();
    setBusy(true);
    setError(null);
    try {
      if (!answer.trim()) throw new Error("Record or type an answer first.");
      setResult(
        await api<Result>("/voice/run", {
          method: "POST",
          body: multipart({
            task: "evaluate_answer",
            question,
            answer_text: answer,
            jd_url: context,
            save_output: save,
          }),
        }),
      );
    } catch (error) {
      setError(error);
    } finally {
      setBusy(false);
    }
  }
  return (
    <>
      <PageHeader
        eyebrow="SAY IT WITH CONFIDENCE"
        title="Practice out loud. Find your voice."
        description="Record or write an answer, then get specific feedback grounded in what you actually said."
      />
      <Card>
        <form onSubmit={evaluate}>
          <label>
            Interview question
            <textarea
              rows={2}
              value={question}
              onChange={(e) => setQuestion(e.target.value)}
              placeholder="Tell me about a project you’re proud of."
              required
            />
          </label>
          <label>
            Job description URL <span className="muted">(optional)</span>
            <input
              type="url"
              value={context}
              onChange={(e) => setContext(e.target.value)}
              placeholder="Add role context for more focused feedback"
            />
          </label>
          <AnswerInput
            config={config}
            value={answer}
            onChange={setAnswer}
            onBusy={setRecording}
            disabled={busy}
          />
          <label className="check">
            <input
              type="checkbox"
              checked={save}
              onChange={(e) => setSave(e.target.checked)}
            />
            Save evaluation files
          </label>
          <ErrorNotice error={error} />
          <BusyButton busy={busy} disabled={recording} type="submit">
            Evaluate my answer
          </BusyButton>
        </form>
      </Card>
      {result && <ResultView result={result} />}
    </>
  );
}
