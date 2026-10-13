import { useEffect, useId, useRef, useState } from "react";
import { Mic, Square, Upload, LoaderCircle } from "lucide-react";
import { api, multipart, validateFile } from "../lib/api";
import type { UIConfig } from "../lib/types";
import { useRecorder } from "../hooks/useRecorder";
import { ErrorNotice } from "./ui";
export function AnswerInput({
  config,
  value,
  onChange,
  onBusy,
  disabled = false,
}: {
  config: UIConfig;
  value: string;
  onChange: (text: string) => void;
  onBusy?: (busy: boolean) => void;
  disabled?: boolean;
}) {
  const answerId = useId();
  const [transcribing, setTranscribing] = useState(false),
    [error, setError] = useState<unknown>(null),
    [audio, setAudio] = useState<File | null>(null),
    [audioUrl, setAudioUrl] = useState("");
  const request = useRef<AbortController | null>(null);
  const mounted = useRef(true);
  const currentOnChange = useRef(onChange);
  currentOnChange.current = onChange;
  useEffect(() => {
    mounted.current = true;
    return () => {
      mounted.current = false;
      request.current?.abort();
    };
  }, []);
  useEffect(() => {
    if (!audio) {
      setAudioUrl("");
      return;
    }
    const url = URL.createObjectURL(audio);
    setAudioUrl(url);
    return () => URL.revokeObjectURL(url);
  }, [audio]);
  async function transcribe(file: File) {
    request.current?.abort();
    const controller = new AbortController();
    request.current = controller;
    setError(null);
    try {
      validateFile(file, config.max_audio_upload_bytes, "audio");
      setAudio(file);
      currentOnChange.current("");
      setTranscribing(true);
      const response = await api<{ transcript: string }>("/voice/run", {
        method: "POST",
        body: multipart({
          task: "transcribe",
          audio: file,
          save_output: false,
        }),
        signal: controller.signal,
      });
      if (mounted.current && request.current === controller)
        currentOnChange.current(response.transcript);
    } catch (error) {
      if (
        !(error instanceof DOMException && error.name === "AbortError") &&
        mounted.current
      )
        setError(error);
    } finally {
      if (mounted.current && request.current === controller)
        setTranscribing(false);
    }
  }
  const recorder = useRecorder(
    config,
    (file) => void transcribe(file),
    () => {
      request.current?.abort();
      setTranscribing(false);
      setAudio(null);
      setError(null);
      currentOnChange.current("");
    },
  );
  const busy = recorder.status !== "idle" || transcribing;
  useEffect(() => {
    onBusy?.(busy);
    return () => onBusy?.(false);
  }, [busy, onBusy]);
  return (
    <div className="answer-input">
      <div className="recorder-actions">
        <button
          type="button"
          className={`button ${recorder.status === "recording" ? "recording" : "secondary"}`}
          disabled={
            disabled ||
            transcribing ||
            ["requesting", "finishing"].includes(recorder.status)
          }
          onClick={() =>
            recorder.status === "recording"
              ? recorder.stop()
              : void recorder.start()
          }
        >
          {recorder.status === "recording" ? (
            <Square size={17} />
          ) : (
            <Mic size={17} />
          )}{" "}
          {recorder.status === "recording"
            ? "Stop recording"
            : recorder.status === "requesting"
              ? "Opening microphone…"
              : "Record your answer"}
        </button>
        <label className="button ghost file-button">
          <Upload size={16} />
          Upload audio
          <input
            aria-label="Upload audio"
            type="file"
            accept="audio/*"
            disabled={disabled || busy}
            onChange={(e) => {
              const file = e.target.files?.[0];
              if (file) void transcribe(file);
              e.target.value = "";
            }}
          />
        </label>
      </div>
      <p className="fine-print">
        Live preview uses browser recognition and may send audio to its
        provider. Groq transcribes the final recording. Use HTTPS or localhost.
      </p>
      {recorder.status === "recording" && (
        <div className="live-preview" role="status">
          <span className="live-dot" /> LIVE TRANSCRIPT
          <p>{recorder.preview || "Listening. Start speaking…"}</p>
        </div>
      )}
      {recorder.notice && <p className="notice">{recorder.notice}</p>}
      {transcribing && (
        <p className="notice">
          <LoaderCircle size={16} className="spin" />
          Preparing your final transcript…
        </p>
      )}
      <ErrorNotice error={error || recorder.error} />
      {Boolean(error) && audio && (
        <button
          className="button ghost"
          type="button"
          disabled={busy}
          onClick={() => void transcribe(audio)}
        >
          Retry transcription
        </button>
      )}
      {audioUrl && <audio controls src={audioUrl} />}
      <label htmlFor={answerId}>Your answer</label>
      <textarea
        id={answerId}
        aria-label="Your answer"
        value={value}
        onChange={(e) => onChange(e.target.value)}
        disabled={disabled || busy}
        rows={7}
        maxLength={config.max_session_answer_characters}
        placeholder="Record an answer above, or type it here. Review and correct the final transcript before submitting."
      />
      <small className="muted">
        {value.length.toLocaleString()} /{" "}
        {config.max_session_answer_characters.toLocaleString()} characters
      </small>
    </div>
  );
}
