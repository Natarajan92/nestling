"use client";
import { createContext, useCallback, useContext, useEffect, useRef, useState, type ReactNode } from "react";
import AskPanel, { type Msg } from "./AskPanel";

type Ctx = { open: boolean; setOpen: (v: boolean) => void; prefill: (text: string) => void };
const AskCtx = createContext<Ctx>({ open: false, setOpen: () => {}, prefill: () => {} });
export const useAskSheet = () => useContext(AskCtx);

/** Mounts the Ask bottom sheet once for every page; the conversation survives closing it. */
export default function AskSheetProvider({ children }: { children: ReactNode }) {
  const [open, setOpen] = useState(false);
  const [msgs, setMsgs] = useState<Msg[]>([]);
  const [draft, setDraft] = useState("");
  const dialog = useRef<HTMLDivElement>(null);
  const prefill = useCallback((text: string) => { setDraft(text); setOpen(true); }, []);

  useEffect(() => {
    if (!open) return;
    const previous = document.activeElement as HTMLElement | null;
    const overflow = document.body.style.overflow;
    document.body.style.overflow = "hidden";
    const focusable = () => Array.from(dialog.current?.querySelectorAll<HTMLElement>('button:not(:disabled), input:not(:disabled), a[href], textarea, summary, [tabindex="0"]') ?? []);
    focusable()[0]?.focus();
    const onKey = (e: KeyboardEvent) => {
      if (e.key === "Escape") setOpen(false);
      if (e.key === "Tab") { const all = focusable(); const first = all[0], last = all.at(-1); if (e.shiftKey && document.activeElement === first) { e.preventDefault(); last?.focus(); } else if (!e.shiftKey && document.activeElement === last) { e.preventDefault(); first?.focus(); } }
    };
    window.addEventListener("keydown", onKey);
    return () => { window.removeEventListener("keydown", onKey); document.body.style.overflow = overflow; previous?.focus(); };
  }, [open]);

  return (
    <AskCtx.Provider value={{ open, setOpen, prefill }}>
      {children}
      {open && (
        <div className="fixed inset-0 z-20 flex items-end justify-center bg-ink/30" onClick={() => setOpen(false)}>
          <div
            ref={dialog}
            role="dialog"
            aria-modal="true"
            aria-label="Ask Nestling"
            onClick={(e) => e.stopPropagation()}
            className="flex h-[85dvh] w-full max-w-md flex-col rounded-t-[24px] bg-cream p-5 shadow-soft"
          >
            <div className="mb-2 flex items-center justify-between">
              <h2 className="text-xl font-semibold">Ask Nestling</h2>
              <button type="button" onClick={() => setOpen(false)} className="rounded-full px-3 py-1 text-sm text-ink-soft">
                Close
              </button>
            </div>
            <AskPanel msgs={msgs} setMsgs={setMsgs} initialText={draft} />
          </div>
        </div>
      )}
    </AskCtx.Provider>
  );
}
