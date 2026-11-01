"use client";
import { createContext, useContext, useEffect, useState, type ReactNode } from "react";
import AskPanel, { type Msg } from "./AskPanel";

type Ctx = { open: boolean; setOpen: (v: boolean) => void };
const AskCtx = createContext<Ctx>({ open: false, setOpen: () => {} });
export const useAskSheet = () => useContext(AskCtx);

/** Mounts the Ask bottom sheet once for every page; the conversation survives closing it. */
export default function AskSheetProvider({ children }: { children: ReactNode }) {
  const [open, setOpen] = useState(false);
  const [msgs, setMsgs] = useState<Msg[]>([]);

  useEffect(() => {
    if (!open) return;
    const onKey = (e: KeyboardEvent) => e.key === "Escape" && setOpen(false);
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [open]);

  return (
    <AskCtx.Provider value={{ open, setOpen }}>
      {children}
      {open && (
        <div className="fixed inset-0 z-20 flex items-end justify-center bg-ink/30" onClick={() => setOpen(false)}>
          <div
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
            <AskPanel msgs={msgs} setMsgs={setMsgs} />
          </div>
        </div>
      )}
    </AskCtx.Provider>
  );
}
