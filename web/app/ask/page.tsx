"use client";
import { Suspense, useEffect } from "react";
import { useSearchParams } from "next/navigation";
import Card from "@/components/Card";
import { useAskSheet } from "@/components/AskSheet";

/** /ask opens the same Ask sheet used everywhere else. */
export default function AskPage() {
  return <Suspense fallback={<p>Opening Ask…</p>}><AskRoute /></Suspense>;
}
function AskRoute() {
  const { open, setOpen } = useAskSheet();
  const { prefill } = useAskSheet();
  const query = useSearchParams().get("q");
  useEffect(() => { if (query) prefill(query); else setOpen(true); }, [query, setOpen, prefill]);
  return (
    <Card className="mt-6 text-center">
      <div className="text-5xl" aria-hidden>
        💬
      </div>
      <h1 className="mt-3 text-2xl font-semibold">Ask Nestling</h1>
      <p className="mt-2 text-ink-soft">Ask anything and get sourced, careful answers.</p>
      {!open && (
        <button type="button" onClick={() => setOpen(true)} className="mt-5 rounded-full bg-peach px-5 py-2 text-sm font-medium">
          Open the chat
        </button>
      )}
    </Card>
  );
}
