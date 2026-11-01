"use client";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { useState } from "react";
import Card from "@/components/Card";
import { deleteEverything, useProfile } from "@/lib/store";
import { dateLabel } from "@/lib/format";

export default function SettingsPage() {
  const router = useRouter();
  const { profile } = useProfile();
  const [confirming, setConfirming] = useState(false);
  const [busy, setBusy] = useState(false);
  const [voiceError, setVoiceError] = useState(false);

  async function wipe() {
    setBusy(true);
    const r = await deleteEverything();
    setBusy(false);
    setConfirming(false);
    if (r.voiceError) setVoiceError(true);
    else router.replace("/welcome");
  }

  return (
    <div className="space-y-6">
      <Link href="/" className="text-sm text-ink-soft">← Today</Link>
      <h1 className="text-3xl font-semibold">Settings</h1>

      {profile && (
        <Card>
          <h2 className="text-lg font-semibold">What Nestling remembers</h2>
          <p className="mt-2 text-sm text-ink-soft">
            Everything below lives only in this browser. Our server keeps nothing about you.
          </p>
          <dl className="mt-3 grid grid-cols-[auto_1fr] gap-x-4 gap-y-1 text-sm">
            <dt className="text-ink-soft">{profile.birth_date ? "Born" : "Due"}</dt>
            <dd>{dateLabel(profile.birth_date ?? profile.due_date)}</dd>
            <dt className="text-ink-soft">Tradition</dt><dd>{profile.tradition}</dd>
            <dt className="text-ink-soft">Food</dt><dd>{profile.diet}</dd>
            <dt className="text-ink-soft">City</dt><dd>{profile.city}</dd>
            {profile.insurer && (<><dt className="text-ink-soft">Insurer</dt><dd>{profile.insurer}</dd></>)}
          </dl>
          <Link href="/welcome" className="mt-3 inline-block text-sm underline">Change my answers</Link>
        </Card>
      )}

      <Card tone="blush">
        <h2 className="text-lg font-semibold">Delete everything</h2>
        <p className="mt-2 text-sm leading-relaxed">
          This clears your answers, checklist ticks, journal and letters from this browser, and deletes your cloned voice if you made one. It cannot be undone.
        </p>
        {voiceError && (
          <p role="alert" className="mt-3 text-sm font-medium">
            Your voice could not be deleted just now, so it was kept so you can try again. Everything else is cleared.
          </p>
        )}
        {confirming ? (
          <div className="mt-4 flex gap-3">
            <button type="button" disabled={busy} onClick={wipe} className="rounded-full bg-ink px-5 py-2.5 text-sm font-semibold text-cream disabled:opacity-50">
              {busy ? "Deleting…" : "Yes, delete everything"}
            </button>
            <button type="button" disabled={busy} onClick={() => setConfirming(false)} className="rounded-full px-5 py-2.5 text-sm">
              Keep it
            </button>
          </div>
        ) : (
          <button type="button" onClick={() => setConfirming(true)} className="mt-4 rounded-full bg-white px-5 py-2.5 text-sm font-semibold shadow-soft">
            Delete everything
          </button>
        )}
      </Card>
    </div>
  );
}
