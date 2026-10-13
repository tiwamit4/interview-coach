import { useEffect, useRef, useState } from "react";
import type { UIConfig } from "../lib/types";
interface SpeechResult {
  isFinal: boolean;
  0: { transcript: string };
}
interface SpeechRecognizer {
  continuous: boolean;
  interimResults: boolean;
  lang: string;
  onresult: ((event: { results: ArrayLike<SpeechResult> }) => void) | null;
  onerror: ((event: { error: string }) => void) | null;
  onend: (() => void) | null;
  start: () => void;
  stop: () => void;
  abort: () => void;
}
declare global {
  interface Window {
    SpeechRecognition?: new () => SpeechRecognizer;
    webkitSpeechRecognition?: new () => SpeechRecognizer;
  }
}
export function useRecorder(
  config: UIConfig,
  onRecorded: (file: File) => void,
  onReset: () => void,
) {
  const [status, setStatus] = useState<
      "idle" | "requesting" | "recording" | "finishing"
    >("idle"),
    [preview, setPreview] = useState(""),
    [notice, setNotice] = useState(""),
    [error, setError] = useState<unknown>(null);
  const callbacks = useRef({ onRecorded, onReset });
  callbacks.current = { onRecorded, onReset };
  const resources = useRef<{
    stream?: MediaStream;
    media?: MediaRecorder;
    context?: AudioContext;
    speech?: SpeechRecognizer;
    timer?: ReturnType<typeof setInterval>;
    restart?: ReturnType<typeof setTimeout>;
    active: boolean;
    generation: number;
  }>({ active: false, generation: 0 });
  const mounted = useRef(true);
  const release = () => {
    const r = resources.current;
    clearInterval(r.timer);
    clearTimeout(r.restart);
    try {
      r.speech?.abort();
    } catch {}
    r.stream?.getTracks().forEach((track) => track.stop());
    void r.context?.close().catch(() => {});
  };
  useEffect(() => {
    mounted.current = true;
    return () => {
      mounted.current = false;
      resources.current.active = false;
      resources.current.generation++;
      release();
      if (resources.current.media?.state === "recording")
        resources.current.media.stop();
    };
  }, []);
  function stop() {
    const r = resources.current;
    if (!r.active) return;
    r.active = false;
    clearInterval(r.timer);
    clearTimeout(r.restart);
    setStatus("finishing");
    try {
      r.speech?.stop();
    } catch {}
    if (r.media && r.media.state !== "inactive") r.media.stop();
  }
  async function start() {
    if (resources.current.active || status !== "idle") return;
    setError(null);
    setPreview("");
    setNotice("");
    callbacks.current.onReset();
    setStatus("requesting");
    const generation = ++resources.current.generation;
    try {
      if (
        !window.isSecureContext ||
        !navigator.mediaDevices?.getUserMedia ||
        !window.MediaRecorder
      )
        throw new Error(
          "Recording needs a supported browser, microphone permission, and HTTPS or localhost.",
        );
      const stream = await navigator.mediaDevices.getUserMedia({
        audio: { channelCount: 1, echoCancellation: true },
      });
      if (!mounted.current || generation !== resources.current.generation) {
        stream.getTracks().forEach((track) => track.stop());
        return;
      }
      resources.current.stream = stream;
      const mime = ["audio/webm;codecs=opus", "audio/webm", "audio/mp4"].find(
        (type) => MediaRecorder.isTypeSupported(type),
      );
      if (!mime)
        throw new Error(
          "This browser cannot record a supported audio format. Upload an audio file or paste your answer.",
        );
      const media = new MediaRecorder(stream, { mimeType: mime });
      resources.current.media = media;
      const chunks: BlobPart[] = [];
      let bytes = 0,
        failed = false;
      media.ondataavailable = (event) => {
        if (event.data.size) {
          chunks.push(event.data);
          bytes += event.data.size;
          if (bytes > config.max_audio_upload_bytes) stop();
        }
      };
      media.onerror = () => {
        failed = true;
        stop();
        setError(new Error("Audio capture failed. Please try again."));
      };
      media.onstop = () => {
        release();
        if (!mounted.current || generation !== resources.current.generation)
          return;
        setStatus("idle");
        if (failed) return;
        if (!bytes || bytes > config.max_audio_upload_bytes) {
          setError(
            new Error(
              "Recording was empty or exceeded the audio limit. Try a shorter answer.",
            ),
          );
          return;
        }
        callbacks.current.onRecorded(
          new File(
            chunks,
            mime.includes("mp4") ? "answer.m4a" : "answer.webm",
            { type: mime },
          ),
        );
      };
      const context = new AudioContext();
      resources.current.context = context;
      await context.resume();
      const analyser = context.createAnalyser();
      analyser.fftSize = 2048;
      context.createMediaStreamSource(stream).connect(analyser);
      const samples = new Float32Array(analyser.fftSize);
      const began = performance.now();
      let lastSpeech = began,
        heard = false;
      resources.current.active = true;
      media.start(250);
      setStatus("recording");
      const Speech = window.SpeechRecognition || window.webkitSpeechRecognition;
      let prior = "",
        final = "",
        interim = "",
        recognitionFailed = false;
      function recognize() {
        if (!Speech || !resources.current.active || recognitionFailed) return;
        const speech = new Speech();
        resources.current.speech = speech;
        speech.continuous = true;
        speech.interimResults = true;
        speech.lang = config.live_transcription_language;
        speech.onresult = (event) => {
          if (
            generation !== resources.current.generation ||
            resources.current.speech !== speech
          )
            return;
          final = "";
          interim = "";
          for (const item of Array.from(event.results)) {
            if (item.isFinal) final += item[0].transcript + " ";
            else interim += item[0].transcript + " ";
          }
          setPreview([prior, final, interim].filter(Boolean).join(" ").trim());
        };
        speech.onerror = (event) => {
          if (["no-speech", "aborted"].includes(event.error)) return;
          recognitionFailed = true;
          setNotice(
            "Live preview is unavailable. Recording continues; your final transcript will appear after stopping.",
          );
        };
        speech.onend = () => {
          if (
            !resources.current.active ||
            recognitionFailed ||
            generation !== resources.current.generation
          )
            return;
          prior = [prior, final, interim].filter(Boolean).join(" ").trim();
          final = "";
          interim = "";
          resources.current.restart = setTimeout(recognize, 200);
        };
        try {
          speech.start();
        } catch {
          recognitionFailed = true;
          setNotice(
            "Live preview is unavailable. You can still record and transcribe your answer.",
          );
        }
      }
      if (Speech) recognize();
      else
        setNotice(
          "This browser has no live preview. Your final transcript will appear after recording.",
        );
      resources.current.timer = setInterval(() => {
        if (!resources.current.active) return;
        const now = performance.now();
        analyser.getFloatTimeDomainData(samples);
        const energy = Math.sqrt(
          samples.reduce((sum, value) => sum + value * value, 0) /
            samples.length,
        );
        if (energy >= config.recording_energy_threshold) {
          heard = true;
          lastSpeech = now;
        }
        if (
          now - began >= config.recording_max_seconds * 1000 ||
          (!heard &&
            now - began >= config.recording_start_timeout_seconds * 1000) ||
          (heard && now - lastSpeech >= config.recording_silence_seconds * 1000)
        )
          stop();
      }, 100);
    } catch (error) {
      resources.current.active = false;
      release();
      if (mounted.current) {
        setStatus("idle");
        setError(error);
      }
    }
  }
  return { status, preview, notice, error, start, stop };
}
