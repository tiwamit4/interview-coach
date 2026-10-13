"use strict";
(() => {
  const button = document.getElementById("record");
  const status = document.getElementById("status");
  const transcript = document.getElementById("transcript");
  const Speech = window.SpeechRecognition || window.webkitSpeechRecognition;
  let args = {}, active = false, starting = false, finishing = false, stream, recorder, context, recognition;
  let chunks = [], byteCount = 0, timer, restartTimer, lastSpeech = 0, began = 0, heardSpeech = false;
  let committed = "", interim = "", prior = "", recordingId = "", previewFailed = false;
  let supported = true, autoStarted = false, captureFailed = false;
  const send = (type, data = {}) => window.parent.postMessage({isStreamlitMessage: true, type, ...data}, "*");
  const value = data => send("streamlit:setComponentValue", {value: data, dataType: "json"});
  const setHeight = () => send("streamlit:setFrameHeight", {height: document.body.scrollHeight + 8});
  function show(text) { status.textContent = text; setHeight(); }
  function displayTranscript() {
    transcript.textContent = [prior, committed, interim].filter(Boolean).join(" ").trim() ||
      (previewFailed ? "Live preview is unavailable. Your recording can still be transcribed after stopping." : "Listening...");
  }
  function release() {
    clearInterval(timer); clearTimeout(restartTimer);
    if (recognition) { try { recognition.abort(); } catch (_) {} }
    if (stream) stream.getTracks().forEach(track => track.stop());
    stream = null;
    if (context) context.close().catch(() => {});
    context = null;
  }
  function startRecognition() {
    if (!Speech || !active || previewFailed) return;
    recognition = new Speech();
    const instance = recognition, id = recordingId;
    recognition.continuous = true; recognition.interimResults = true;
    recognition.lang = args.language || "en-US";
    recognition.onresult = event => {
      if (id !== recordingId || instance !== recognition) return;
      committed = ""; interim = "";
      for (const result of Array.from(event.results)) {
        if (result.isFinal) committed += result[0].transcript + " ";
        else interim += result[0].transcript + " ";
      }
      displayTranscript();
    };
    recognition.onerror = event => {
      if (id !== recordingId || instance !== recognition) return;
      if (event.error === "no-speech" || event.error === "aborted") return;
      previewFailed = true;
      show("Live preview is unavailable. Recording continues; Groq will transcribe after stopping.");
      displayTranscript();
    };
    recognition.onend = () => {
      if (!active || previewFailed || id !== recordingId || instance !== recognition) return;
      prior = [prior, committed, interim].filter(Boolean).join(" ").trim();
      committed = ""; interim = "";
      restartTimer = setTimeout(startRecognition, 200);
    };
    try { recognition.start(); }
    catch (_) { previewFailed = true; displayTranscript(); }
  }
  function stop(message = "Recording stopped. Preparing transcript...") {
    if (!active) return;
    active = false; finishing = true; clearInterval(timer); clearTimeout(restartTimer);
    button.disabled = true; button.classList.remove("recording");
    if (recognition) { try { recognition.stop(); } catch (_) {} }
    show(message);
    if (recorder && recorder.state !== "inactive") recorder.stop();
    else { release(); finishing = false; button.disabled = false; }
  }
  async function start() {
    if (!supported || active || starting || finishing) return;
    starting = true; button.disabled = true;
    show("Requesting microphone access...");
    try {
      stream = await navigator.mediaDevices.getUserMedia({audio: {channelCount: 1, sampleRate: args.sample_rate, echoCancellation: true}});
      const mime = ["audio/webm;codecs=opus", "audio/webm", "audio/mp4"].find(type => MediaRecorder.isTypeSupported(type));
      if (!mime) throw new Error("unsupported-format");
      recorder = new MediaRecorder(stream, {mimeType: mime});
      captureFailed = false;
      chunks = []; byteCount = 0; committed = ""; interim = ""; prior = "";
      previewFailed = !Speech; heardSpeech = false;
      recordingId = crypto.randomUUID();
      recorder.ondataavailable = event => {
        if (!event.data.size) return;
        chunks.push(event.data); byteCount += event.data.size;
        if (byteCount > args.max_bytes) stop("Recording reached the size limit.");
      };
      recorder.onerror = () => {
        captureFailed = true;
        active = false; finishing = false; release();
        button.disabled = false; button.classList.remove("recording");
        value({status: "error", error: "Audio recording failed. Please try again."});
        show("Audio recording failed. Please try again.");
      };
      recorder.onstop = async () => {
        release();
        try {
          if (captureFailed) throw new Error("capture-failed");
          const blob = new Blob(chunks, {type: mime});
          if (blob.size > args.max_bytes) throw new Error("size-limit");
          if (!blob.size) throw new Error("empty-recording");
          const encoded = await new Promise((resolve, reject) => {
            const reader = new FileReader(); reader.onerror = reject;
            reader.onload = () => resolve(reader.result.split(",")[1]); reader.readAsDataURL(blob);
          });
          value({status: "complete", recording_id: recordingId, audio: encoded,
                 filename: mime.includes("mp4") ? "live_recording.m4a" : "live_recording.webm",
                 preview: [prior, committed, interim].filter(Boolean).join(" ").trim()});
          show("Recording saved. Review the final transcript below before submitting.");
        } catch (_) {
          value({status: "error", error: "Recording was empty or exceeded the size limit. Record a shorter answer."});
          show("Recording was empty or exceeded the size limit. Record a shorter answer.");
        } finally { finishing = false; button.disabled = false; button.textContent = "Record again"; setHeight(); }
      };
      context = new AudioContext({sampleRate: args.sample_rate});
      await context.resume();
      const analyser = context.createAnalyser(); analyser.fftSize = 2048;
      context.createMediaStreamSource(stream).connect(analyser);
      const samples = new Float32Array(analyser.fftSize);
      began = performance.now(); lastSpeech = began; active = true;
      recorder.start(250);
      value({status: "recording", recording_id: recordingId});
      button.disabled = false; button.textContent = "Stop recording"; button.classList.add("recording");
      show(Speech ? "Recording - live transcript preview" : "Recording. This browser has no live preview; Groq transcribes after stopping.");
      displayTranscript(); startRecognition();
      timer = setInterval(() => {
        if (!active) return;
        const now = performance.now(); analyser.getFloatTimeDomainData(samples);
        const rms = Math.sqrt(samples.reduce((sum, sample) => sum + sample * sample, 0) / samples.length);
        if (rms >= args.energy_threshold) { heardSpeech = true; lastSpeech = now; }
        if (now - began >= args.max_seconds * 1000) stop("Maximum recording time reached.");
        else if (!heardSpeech && now - began >= args.start_timeout * 1000) stop("No speech detected. Recording stopped.");
        else if (heardSpeech && now - lastSpeech >= args.silence_seconds * 1000) stop();
      }, 100);
    } catch (_) {
      active = false; release();
      value({status: "error", error: "Microphone could not start. Allow microphone access and use HTTPS or localhost."});
      show("Microphone could not start. Allow microphone access and use HTTPS or localhost.");
      button.disabled = false;
    } finally { starting = false; }
  }
  button.onclick = () => active ? stop() : start();
  window.addEventListener("message", event => {
    if (event.source !== window.parent || event.data?.type !== "streamlit:render") return;
    args = event.data.args;
    const theme = event.data.theme;
    if (theme) {
      document.body.style.setProperty("--text", theme.textColor);
      document.body.style.setProperty("--background", theme.backgroundColor);
    }
    supported = Boolean(window.isSecureContext && navigator.mediaDevices?.getUserMedia && window.MediaRecorder && window.AudioContext);
    if (!supported) { button.disabled = true; show("Recording needs a supported browser, microphone permission, and HTTPS or localhost."); }
    else if (!active && !starting && !finishing) button.textContent = args.label || "Start recording";
    if (supported && args.auto_start && !autoStarted) { autoStarted = true; start(); }
    setHeight();
  });
  window.addEventListener("pagehide", () => {
    active = false;
    if (recognition) { try { recognition.abort(); } catch (_) {} }
    if (recorder && recorder.state !== "inactive") recorder.stop();
    release();
  });
  send("streamlit:componentReady", {apiVersion: 1}); setHeight();
})();
