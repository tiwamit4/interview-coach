import { useState } from "react";
import { ArrowRight, FileUp, ShieldCheck } from "lucide-react";
import { api, multipart, validateFile } from "../lib/api";
import type { Result, UIConfig } from "../lib/types";
import {
  BusyButton,
  Card,
  EmptyState,
  ErrorNotice,
  PageHeader,
} from "../components/ui";
import { ResultView } from "../components/Results";
export const workflows = {
  analyze: {
    eyebrow: "FIND YOUR FIT",
    title: "A clearer picture of your next role.",
    description:
      "See where your experience matches the job, and where to focus your preparation.",
    task: "match_score",
    action: "Analyze my fit",
  },
  questions: {
    eyebrow: "PREPARE WITH PURPOSE",
    title: "The right questions. Better answers.",
    description:
      "Build a focused set of interview questions from your resume, a job description, or your own notes.",
    task: "",
    action: "Generate questions",
  },
  prep: {
    eyebrow: "YOUR PREPARATION PLAN",
    title: "Walk in with a plan.",
    description:
      "Prepare likely questions, project stories, and the areas that need a little more work.",
    task: "interview_prep",
    action: "Create my prep plan",
  },
  resume: {
    eyebrow: "TELL YOUR STORY",
    title: "Make your experience stand out.",
    description:
      "Improve resume bullets and discover the keywords that matter for your target role.",
    task: "resume_improvement",
    action: "Improve my resume",
  },
  applications: {
    eyebrow: "MAKE THE FIRST MOVE",
    title: "An application that sounds like you.",
    description:
      "Draft a tailored cover letter, recruiter message, and LinkedIn introduction using your experience.",
    task: "cover_letter",
    action: "Draft my application",
  },
  full: {
    eyebrow: "THE COMPLETE PICTURE",
    title: "Your interview toolkit, all together.",
    description:
      "Get a fit analysis, preparation plan, and resume improvements in one workflow.",
    task: "full_analysis",
    action: "Generate full analysis",
  },
};
export type WorkflowKey = keyof typeof workflows;
export function Workflows({
  page,
  config,
  onPractice,
}: {
  page: WorkflowKey;
  config: UIConfig;
  onPractice: (questions: string) => void;
}) {
  const info = workflows[page];
  const [url, setUrl] = useState(""),
    [file, setFile] = useState<File | null>(null),
    [text, setText] = useState(""),
    [source, setSource] = useState("JD + resume"),
    [save, setSave] = useState(true),
    [busy, setBusy] = useState(false),
    [error, setError] = useState<unknown>(null),
    [result, setResult] = useState<Result | null>(null);
  const isQuestions = page === "questions",
    needsFile = !isQuestions || source.toLowerCase().includes("resume"),
    needsUrl = !isQuestions || source.includes("JD"),
    needsText = isQuestions && source === "Pasted text";
  async function submit(event: React.FormEvent) {
    event.preventDefault();
    setError(null);
    setBusy(true);
    try {
      if (needsFile && !file)
        throw new Error("Upload a PDF resume to continue.");
      if (needsUrl && !url.trim())
        throw new Error("Enter a job description URL.");
      if (needsText && !text.trim())
        throw new Error("Paste some text to generate questions.");
      if (file && needsFile)
        validateFile(file, config.max_resume_upload_bytes, "resume");
      const data = await api<Result>(isQuestions ? "/questions" : "/run", {
        method: "POST",
        body: multipart({
          task: info.task || null,
          jd_url: needsUrl ? url : null,
          resume: needsFile ? file : null,
          text: needsText ? text : null,
          save_output: save,
        }),
      });
      setResult(data);
    } catch (e) {
      setError(e);
    } finally {
      setBusy(false);
    }
  }
  return (
    <>
      <PageHeader {...info} />
      <div className="workflow-layout">
        <Card>
          <form onSubmit={submit}>
            <div className="section-heading">
              <h2>Your starting point</h2>
              <span className="step">01 / INPUT</span>
            </div>
            {isQuestions && (
              <label>
                Question source
                <select
                  value={source}
                  onChange={(e) => setSource(e.target.value)}
                >
                  {["JD + resume", "Resume only", "JD only", "Pasted text"].map(
                    (value) => (
                      <option key={value}>{value}</option>
                    ),
                  )}
                </select>
              </label>
            )}
            {needsUrl && (
              <label>
                Job description URL
                <input
                  type="url"
                  value={url}
                  onChange={(e) => setUrl(e.target.value)}
                  placeholder="https://careers.company.com/your-next-role"
                  required
                />
                <small>Use a public page containing the job description.</small>
              </label>
            )}
            {needsFile && (
              <label>
                Resume PDF
                <div className="file-drop">
                  <FileUp size={28} />
                  <span>{file ? file.name : "Choose your resume"}</span>
                  <small>
                    PDF · up to {config.max_resume_upload_bytes / 1024 / 1024}{" "}
                    MiB
                  </small>
                  <input
                    type="file"
                    accept=".pdf,application/pdf"
                    onChange={(e) => {
                      const next = e.target.files?.[0] || null;
                      try {
                        if (next)
                          validateFile(
                            next,
                            config.max_resume_upload_bytes,
                            "resume",
                          );
                        setFile(next);
                        setError(null);
                      } catch (error) {
                        setError(error);
                        e.target.value = "";
                        setFile(null);
                      }
                    }}
                  />
                </div>
              </label>
            )}
            {needsText && (
              <label>
                Your notes or resume text
                <textarea
                  rows={8}
                  value={text}
                  onChange={(e) => setText(e.target.value)}
                  placeholder="Paste the experience or job description you want to practise."
                  required
                />
              </label>
            )}
            <label className="check">
              <input
                type="checkbox"
                checked={save}
                onChange={(e) => setSave(e.target.checked)}
              />
              Save generated files
            </label>
            <p className="fine-print">
              Results are added to your history even when file saving is off.
            </p>
            <ErrorNotice error={error} />
            <BusyButton busy={busy} type="submit">
              {busy ? "Preparing your results…" : info.action}
            </BusyButton>
          </form>
        </Card>
        <aside className="preparation-note">
          <span className="note-label">
            A LITTLE PREPARATION GOES A LONG WAY
          </span>
          <h2>
            Your experience.
            <br />
            Your next chapter.
          </h2>
          <p>
            Good interview preparation starts with the details that make your
            experience yours.
          </p>
          <div className="note-rule" />
          <p className="note-tip">
            <ShieldCheck size={20} />
            Feedback uses the documents you provide. Review every suggestion
            before using it.
          </p>
          <span className="note-footer">
            ONE STEP CLOSER <ArrowRight size={17} />
          </span>
        </aside>
      </div>
      {result ? (
        <>
          <ResultView result={result} />
          {typeof result.questions === "string" && (
            <button
              className="button secondary"
              onClick={() => onPractice(result.questions as string)}
            >
              Practise these questions <ArrowRight size={17} />
            </button>
          )}
        </>
      ) : (
        <Card className="result-placeholder">
          <EmptyState
            title="Your preparation starts here"
            description="Add your details above. Your personalized results will appear here, ready to review and download."
          />
        </Card>
      )}
    </>
  );
}
