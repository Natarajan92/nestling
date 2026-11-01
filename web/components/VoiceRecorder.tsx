"use client";
import { useEffect, useRef, useState } from "react";

/** Records in memory only; always closes the microphone. */
export default function VoiceRecorder(
  {
    onRecorded,
    disabled = false,
    label = "Record a minute"
  }: {
    onRecorded: (audio: Blob) => void;
    disabled?: boolean;
    label?: string;
  }
) {
  const recorder = useRef<MediaRecorder | null>(null);
  const stream = useRef<MediaStream | null>(null);
  const timer = useRef<ReturnType<typeof setInterval> | null>(null);
  const mounted = useRef(true);
  const [recording, setRecording] = useState(false);
  const [starting, setStarting] = useState(false);
  const [seconds, setSeconds] = useState(0);
  const [error, setError] = useState("");

  const cleanup = () => {
    if (timer.current)
      clearInterval(timer.current);

    timer.current = null;
    stream.current?.getTracks().forEach(t => t.stop());
    stream.current = null;
  };

  useEffect(() => {
    mounted.current = true;

    return () => {
      mounted.current = false;

      if (recorder.current?.state === "recording")
        recorder.current.stop();

      cleanup();
    };
  }, []);

  async function start() {
    if (!navigator.mediaDevices?.getUserMedia || typeof MediaRecorder === "undefined") {
      setError("Recording is unavailable in this browser. You can type your entry instead.");
      return;
    }

    setError("");
    setStarting(true);

    try {
      const audio = await navigator.mediaDevices.getUserMedia({
        audio: true
      });

      if (!mounted.current) {
        audio.getTracks().forEach(t => t.stop());
        return;
      }

      stream.current = audio;
      const mimeType = ["audio/webm;codecs=opus", "audio/mp4", "audio/ogg;codecs=opus"].find(m => MediaRecorder.isTypeSupported(m));

      const current = new MediaRecorder(audio, mimeType ? {
        mimeType
      } : undefined);

      recorder.current = current;
      const chunks: BlobPart[] = [];

      current.ondataavailable = e => {
        if (e.data.size)
          chunks.push(e.data);
      };

      current.onerror = () => {
        cleanup();

        if (mounted.current) {
          setRecording(false);
          setError("Recording failed. Please try again or type your entry.");
        }
      };

      current.onstop = () => {
        cleanup();

        if (mounted.current) {
          setRecording(false);

          const blob = new Blob(chunks, {
            type: current.mimeType
          });

          if (blob.size)
            onRecorded(blob);
          else
            setError("No audio was recorded. Please try again.");
        }
      };

      current.start();
      setRecording(true);
      setSeconds(0);
      const started = Date.now();

      timer.current = setInterval(() => {
        const elapsed = Math.floor((Date.now() - started) / 1000);

        if (mounted.current)
          setSeconds(Math.min(elapsed, 60));

        if (elapsed >= 60 && current.state === "recording")
          current.stop();
      }, 200);
    } catch {
      cleanup();

      if (mounted.current)
        setError("Microphone access was not available. Allow it in your browser or type your entry.");
    } finally {
      if (mounted.current)
        setStarting(false);
    }
  }

  return (
    <div><button
        type="button"
        className="quiet-button"
        disabled={(disabled && !recording) || starting}
        onClick={() => recording ? recorder.current?.stop() : start()}>{starting ? "Opening microphone…" : recording ? `Stop recording · ${seconds}s / 60s` : label}</button><p className="mt-2 text-xs text-ink-soft">{recording ? "Microphone is on. Recording stops at one minute." : "Audio stays in memory until you choose to send it. The microphone closes when you stop."}</p>{error && <p className="mt-2 text-sm" role="alert">{error}</p>}</div>
  );
}
