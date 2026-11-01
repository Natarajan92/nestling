"use client";
import { useEffect, useRef, useState, type Dispatch, type FormEvent, type SetStateAction } from "react";
import { askNestling, type AskResponse } from "@/lib/api";
import { addJournalEntry, profileBody, useProfile } from "@/lib/store";
import LessonCard from "./LessonCard";
import SourceChip from "./SourceChip";

export type Msg = { role: "me"; text: string } | { role: "nestling"; res: AskResponse; question: string } | { role: "error" };

const PULSE = {
  calm: { dot: "bg-sage", label: "Guardian: all calm" },
  amber: { dot: "bg-gold", label: "Guardian: taking extra care with this one" },
  red: { dot: "bg-red-600", label: "Guardian: please act on this now" },
} as const;

function Pulse({ level }: { level: keyof typeof PULSE }) {
  return (
    <p className="flex items-center gap-2 text-xs text-ink-soft">
      <span aria-hidden className={`inline-block size-2.5 rounded-full ${PULSE[level].dot}`} />
      <span aria-hidden>🛡️</span> {PULSE[level].label}
    </p>
  );
}

function HowIAnswered({ res }: { res: AskResponse }) {
  return (
    <details className="mt-3 text-sm">
      <summary className="cursor-pointer text-ink-soft">How I answered</summary>
      <ul className="mt-2 list-disc space-y-1 pl-5 text-ink-soft">
        {res.how_i_answered.map((s, i) => (
          <li key={i}>{s}</li>
        ))}
        {res.verification && (
          <li>
            Checked against the sources: {res.verification.verdict}
            {res.verification.unsupported.length > 0 && ` (not supported: ${res.verification.unsupported.join("; ")})`}
          </li>
        )}
      </ul>
    </details>
  );
}

function Answer({ res, question }: { res: AskResponse; question: string }) {
  const [saved, setSaved] = useState(false);
  const red = res.guardian.level === "red" || res.escalate;
  const lesson = res.lesson ?? null;
  return (
    <div
      role={red ? "alert" : undefined}
      className={`rounded-card p-4 shadow-soft ${red ? "border-2 border-red-600 bg-red-50" : "bg-white"}`}
    >
      <Pulse level={red ? "red" : res.guardian.level} />
      {red && <p className="mt-2 font-display text-lg font-semibold text-red-800">Please speak to your doctor now.</p>}
      <p className={`mt-2 whitespace-pre-line leading-relaxed ${red ? "font-medium" : ""}`}>{res.answer}</p>
      {lesson && (
        <div className="mt-4">
          <h3 className="font-display text-lg font-semibold">{lesson.title}</h3>
          <LessonCard lesson={lesson} pageUrl={`${window.location.origin}/lessons/${lesson.lesson_id}`} />
        </div>
      )}
      {(!lesson || lesson.sources.length === 0) && res.sources.length > 0 && (
        <div className="mt-3 flex flex-wrap gap-2">
          {res.sources.map((s) => (
            <SourceChip key={s.id} source={s} />
          ))}
        </div>
      )}
      {res.save && (
        <button
          type="button"
          disabled={saved}
          onClick={() => {
            addJournalEntry(question);
            setSaved(true);
          }}
          className="mt-3 rounded-full border border-sage bg-sage/20 px-4 py-1.5 text-sm"
        >
          {saved ? "Saved to your journal" : "Save to my journal (stays on this phone)"}
        </button>
      )}
      <HowIAnswered res={res} />
    </div>
  );
}

/** The conversation, used in the bottom sheet and on /ask. Messages live only in memory. */
export default function AskPanel({ msgs, setMsgs, initialText = "" }: { msgs: Msg[]; setMsgs: Dispatch<SetStateAction<Msg[]>>; initialText?: string }) {
  const { profile } = useProfile();
  const [text, setText] = useState(initialText);
  const [busy, setBusy] = useState(false);
  const end = useRef<HTMLDivElement>(null);

  useEffect(() => end.current?.scrollIntoView({ block: "end" }), [msgs, busy]);

  async function send(e: FormEvent) {
    e.preventDefault();
    const q = text.trim();
    if (!q || busy) return;
    setText("");
    setMsgs((m) => [...m, { role: "me", text: q }]);
    setBusy(true);
    try {
      const res = await askNestling(q, profile ? profileBody(profile) : null, !!profile?.consent.save_journal);
      setMsgs((m) => [...m, res.error && !res.escalate ? { role: "error" } : { role: "nestling", res, question: q }]);
    } catch {
      setMsgs((m) => [...m, { role: "error" }]);
    }
    setBusy(false);
  }

  return (
    <div className="flex min-h-0 flex-1 flex-col">
      <div className="flex-1 space-y-3 overflow-y-auto px-1 py-2" aria-live="polite">
        {msgs.length === 0 && (
          <p className="text-ink-soft">
            Ask anything about pregnancy, the first weeks or money. I answer from trusted sources and say so when I
            don&apos;t have one.
          </p>
        )}
        {msgs.map((m, i) =>
          m.role === "me" ? (
            <p key={i} className="ml-auto w-fit max-w-[85%] rounded-card bg-peach/40 px-4 py-2">
              {m.text}
            </p>
          ) : m.role === "error" ? (
            <p key={i} className="rounded-card bg-blush/25 p-4 text-sm">
              Nestling could not answer just now. Please try again in a moment. If it is urgent, call your
              doctor.
            </p>
          ) : (
            <Answer key={i} res={m.res} question={m.question} />
          ),
        )}
        {busy && <p className="text-sm text-ink-soft">Checking the sources…</p>}
        <div ref={end} />
      </div>
      <form onSubmit={send} className="mt-2 flex gap-2">
        <label className="sr-only" htmlFor="ask-input">
          Your question
        </label>
        <input
          id="ask-input"
          value={text}
          onChange={(e) => setText(e.target.value)}
          placeholder="Ask Nestling…"
          maxLength={2000}
          className="min-w-0 flex-1 rounded-full border border-ink/10 bg-white px-4 py-2.5"
        />
        <button
          type="submit"
          disabled={busy || !text.trim()}
          className="rounded-full bg-peach px-5 py-2.5 font-medium disabled:opacity-50"
        >
          Send
        </button>
      </form>
    </div>
  );
}
