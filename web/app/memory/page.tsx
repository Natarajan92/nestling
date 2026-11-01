"use client";
import Link from "next/link";
import { useEffect, useRef, useState, type FormEvent } from "react";
import Card from "@/components/Card";
import VoiceRecorder from "@/components/VoiceRecorder";
import WeeklyCard from "@/components/WeeklyCard";
import { cloneVoice, deleteVoice, speakLetter, transcribe } from "@/lib/api";

import {
  addJournalEntry,
  addLetter,
  removeJournalEntry,
  removeLetter,
  saveProfile,
  setVoiceId,
  useJournal,
  useLetters,
  useProfile,
  useVoiceId,
} from "@/lib/store";

import { dateLabel } from "@/lib/format";

function AudioPreview(
  {
    blob
  }: {
    blob: Blob;
  }
) {
  const audio = useRef<HTMLAudioElement>(null);

  useEffect(() => {
    const value = URL.createObjectURL(blob);
    const element = audio.current;

    if (element)
      element.src = value;

    return () => {
      element?.pause();
      element?.removeAttribute("src");
      URL.revokeObjectURL(value);
    };
  }, [blob]);

  return <audio ref={audio} className="mt-3 w-full" controls>Audio preview is unavailable.</audio>;
}

export default function MemoryPage() {
  const {
    profile
  } = useProfile();

  const entries = useJournal();
  const letters = useLetters();
  const voiceId = useVoiceId();
  const [text, setText] = useState("");
  const [title, setTitle] = useState("");
  const [letter, setLetter] = useState("");
  const [localConsent, setLocalConsent] = useState(false);
  const saveConsent = profile?.consent.save_journal ?? localConsent;
  const [recorded, setRecorded] = useState<Blob | null>(null);
  const [transcribeConsent, setTranscribeConsent] = useState(false);
  const [sample, setSample] = useState<Blob | null>(null);
  const [voiceConsent, setVoiceConsent] = useState(false);
  const [speakConsent, setSpeakConsent] = useState(false);
  const [busy, setBusy] = useState("");
  const [error, setError] = useState("");
  const [status, setStatus] = useState("");
  const [readAudio, setReadAudio] = useState<Blob | null>(null);
  const active = useRef(true);

  useEffect(() => {
    active.current = true;

    return () => {
      active.current = false;
    };
  }, []);

  const [deletingVoice, setDeletingVoice] = useState(false);

  function consent(value: boolean) {
    setLocalConsent(value);

    if (profile) saveProfile({
      ...profile,

      consent: {
        ...profile.consent,
        save_journal: value
      }
    });
  }

  function saveEntry(e: FormEvent) {
    e.preventDefault();

    if (!saveConsent || !text.trim())
      return;

    addJournalEntry(text.trim());
    setText("");
    setRecorded(null);
    setStatus("Journal entry saved in this browser.");
  }

  function saveLetter(e: FormEvent) {
    e.preventDefault();

    if (!saveConsent || !letter.trim())
      return;

    addLetter(title.trim() || "Dear baby", letter.trim());
    setTitle("");
    setLetter("");
    setStatus("Letter saved in this browser.");
  }

  async function toText() {
    if (!recorded || !transcribeConsent)
      return;

    setBusy("transcribe");
    setError("");

    try {
      const result = await transcribe(recorded);

      if (active.current) {
        setText(previous => previous ? `${previous}\n${result.text}` : result.text);
        setStatus("Transcript ready. Review it before saving.");
        setRecorded(null);
      }
    } catch {
      if (active.current)
        setError("Transcription is unavailable just now. Retry, or type your entry below.");
    } finally {
      if (active.current)
        setBusy("");
    }
  }

  async function clone() {
    if (!sample || !voiceConsent)
      return;

    setBusy("clone");
    setError("");

    try {
      const result = await cloneVoice(sample);
      setVoiceId(result.voice_id);

      if (active.current) {
        if (profile) saveProfile({
          ...profile,

          consent: {
            ...profile.consent,
            voice: true
          }
        });

        setSample(null);
        setVoiceConsent(false);
        setStatus("Your own voice is ready. You can delete it below.");
      }
    } catch {
      if (active.current)
        setError("Your voice could not be created. Please try again.");
    } finally {
      if (active.current)
        setBusy("");
    }
  }

  async function removeVoice() {
    if (!voiceId)
      return;

    setBusy("delete");
    setError("");

    try {
      await deleteVoice(voiceId);
      setVoiceId(null);
      setReadAudio(null);

      if (profile) saveProfile({
        ...profile,

        consent: {
          ...profile.consent,
          voice: false
        }
      });

      setStatus("Your cloned voice has been deleted.");
      setDeletingVoice(false);
    } catch {
      setError("Your voice could not be deleted. Its ID is kept so you can retry.");
    } finally {
      setBusy("");
    }
  }

  async function read(text: string, id: string) {
    if (!speakConsent)
      return;

    setBusy(id);
    setError("");
    setReadAudio(null);

    try {
      const audio = await speakLetter(text, voiceId);

      if (active.current)
        setReadAudio(audio);
    } catch {
      if (active.current)
        setError("Read aloud is unavailable just now. Please try again.");
    } finally {
      if (active.current)
        setBusy("");
    }
  }

  return (
    <div className="space-y-5"><div><h1 className="text-3xl font-semibold">Memory book</h1><p className="mt-2 text-ink-soft">The little things you&apos;ll want to remember.</p></div><Card tone="sage"><h2 className="text-xl">Yours to keep</h2><p className="mt-2 text-sm">Journal entries and letters stay in this browser. They are not synced or saved on our server. Clearing browser data removes them. You can delete individual memories below, or everything in Settings.</p><label className="mt-4 flex gap-2 text-sm"><input type="checkbox" checked={saveConsent} onChange={e => consent(e.target.checked)} />I agree to keep journal entries and letters in this browser.</label></Card>
      {error && <p role="alert" className="rounded-card bg-blush/25 p-4 text-sm">{error}</p>}{status && <p role="status" className="rounded-card bg-sage/25 p-4 text-sm">{status}</p>}
      <Card><h2 className="text-2xl">A moment from today</h2><div className="mt-4"><VoiceRecorder disabled={!!busy} onRecorded={audio => { setRecorded(audio); setTranscribeConsent(false); }} />{recorded && <><AudioPreview blob={recorded} /><label className="mt-3 flex gap-2 text-sm"><input type="checkbox" checked={transcribeConsent} onChange={e => setTranscribeConsent(e.target.checked)} />Send this recording to ElevenLabs for transcription. Audio is processed in memory and not stored by Nestling.</label><div className="mt-3 flex gap-2"><button className="button text-sm" disabled={!!busy || !transcribeConsent} onClick={toText}>{busy === "transcribe" ? "Transcribing…" : "Transcribe recording"}</button><button className="quiet-button text-sm" disabled={!!busy} onClick={() => setRecorded(null)}>Discard audio</button></div></>}</div><form onSubmit={saveEntry} className="mt-5"><label className="block text-sm">Write, or review your transcript<textarea
              className="field min-h-32"
              maxLength={10000}
              required
              value={text}
              onChange={e => setText(e.target.value)}
              placeholder="Today, I want to remember…" /></label><button className="button mt-3" disabled={!saveConsent || !text.trim() || !!busy}>Save journal entry</button></form></Card>
      {entries.length > 0 && <section><h2 className="mb-3 text-2xl">Your journal</h2><div className="space-y-3">{[...entries].reverse().map(
            e => <Card key={e.id}><p className="text-xs text-ink-soft">{dateLabel(e.saved_at)}</p><p className="mt-3 whitespace-pre-line leading-relaxed">{e.text}</p><button className="mt-4 text-xs underline" onClick={() => removeJournalEntry(e.id)}>Delete entry</button></Card>
          )}</div></section>}
      <Card tone="blush"><h2 className="text-2xl">Letters to baby</h2><form onSubmit={saveLetter} className="mt-4 space-y-3"><label className="block text-sm">Title<input
              className="field"
              maxLength={100}
              value={title}
              onChange={e => setTitle(e.target.value)}
              placeholder="Dear baby" /></label><label className="block text-sm">Your letter<textarea
              className="field min-h-40"
              required
              maxLength={2500}
              value={letter}
              onChange={e => setLetter(e.target.value)}
              placeholder="There is something I want to tell you…" /></label><button className="button" disabled={!saveConsent || !letter.trim()}>Save letter</button></form></Card>
      <Card><h2 className="text-xl">Read letters aloud</h2><p className="mt-2 text-sm">{voiceId ? "Your cloned voice will read your letter." : "A gentle default voice will read your letter. You can set up your own below."}</p><label className="mt-3 flex gap-2 text-sm"><input
            type="checkbox"
            checked={speakConsent}
            onChange={e => {
              setSpeakConsent(e.target.checked);

              if (!e.target.checked)
                setReadAudio(null);
            }} />I agree to send the selected letter to ElevenLabs to make audio. Nestling does not store the letter or audio on the server.</label>{readAudio && <AudioPreview blob={readAudio} />}{letters.length === 0 && <p className="mt-3 text-sm text-ink-soft">Save a letter above to read it aloud.</p>}</Card>
      {letters.length > 0 && <div className="space-y-3">{[...letters].reverse().map(
          l => <Card key={l.id}><h3 className="text-xl">{l.title}</h3><p className="mt-1 text-xs text-ink-soft">{dateLabel(l.saved_at)}</p><p className="mt-3 whitespace-pre-line leading-relaxed">{l.text}</p><div className="mt-4 flex gap-3"><button className="quiet-button text-sm" disabled={!!busy || !speakConsent} onClick={() => read(l.text, l.id)}>{busy === l.id ? "Making audio…" : "Read aloud"}</button><button className="text-xs underline" disabled={!!busy} onClick={() => removeLetter(l.id)}>Delete letter</button></div></Card>
        )}</div>}
      <Card tone="peach"><h2 className="text-2xl">A letter in your own voice</h2>{voiceId ? <><p className="mt-3 text-sm">Your voice is ready. The voice ID lives in this browser; the cloned voice is held by ElevenLabs until you delete it.</p>{deletingVoice ? <div className="mt-4 flex gap-3"><button className="button text-sm" disabled={!!busy} onClick={removeVoice}>{busy === "delete" ? "Deleting…" : "Yes, delete my voice"}</button><button className="quiet-button text-sm" disabled={!!busy} onClick={() => setDeletingVoice(false)}>Keep voice</button></div> : <button className="quiet-button mt-4 text-sm" onClick={() => setDeletingVoice(true)}>Delete my voice</button>}</> : <><p className="mt-3 text-sm">Record a clear sample of your own voice, up to a minute. Cloning sends it to ElevenLabs. Nestling keeps only the voice ID in your browser; ElevenLabs holds the cloned voice until you delete it. Never use another person&apos;s voice.</p><div className="mt-4"><VoiceRecorder label="Record my voice sample" disabled={!!busy} onRecorded={audio => { setSample(audio); setVoiceConsent(false); }} /></div>{sample && <><AudioPreview blob={sample} /><label className="mt-4 flex gap-2 text-sm"><input type="checkbox" checked={voiceConsent} onChange={e => setVoiceConsent(e.target.checked)} />This is my own voice. I explicitly consent to send this sample to ElevenLabs and create a clone for reading my letters.</label><div className="mt-3 flex gap-2"><button className="button text-sm" disabled={!voiceConsent || !!busy} onClick={clone}>{busy === "clone" ? "Creating your voice…" : "Create my own voice"}</button><button
                className="quiet-button text-sm"
                disabled={!!busy}
                onClick={() => {
                  setSample(null);
                  setVoiceConsent(false);
                }}>Discard sample</button></div></>}</>}</Card>
      <WeeklyCard /><Link className="quiet-button w-full text-center" href="/journeys/partner">Open partner view</Link>
    </div>
  );
}
