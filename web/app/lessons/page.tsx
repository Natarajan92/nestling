"use client";
import Link from "next/link";
import { useEffect, useState } from "react";
import Card from "@/components/Card";
import { getLessons, mediaUrl, type Lesson } from "@/lib/api";
import { dateLabel } from "@/lib/format";

const FILTERS = [
  { id: "all", label: "All" },
  { id: "before_birth", label: "Before birth" },
  { id: "first_weeks", label: "First weeks" },
] as const;

const reviewedOn = (d: string | null) =>
  d ? `Reviewed on ${dateLabel(d)}` : "Reviewed";

export default function LessonsPage() {
  const [lessons, setLessons] = useState<Lesson[] | null>(null);
  const [failed, setFailed] = useState(false);
  const [attempt, setAttempt] = useState(0);
  const [filter, setFilter] = useState<(typeof FILTERS)[number]["id"]>("all");

  useEffect(() => {
    let alive = true;
    getLessons().then((l) => alive && setLessons(l)).catch(() => alive && setFailed(true));
    return () => {
      alive = false;
    };
  }, [attempt]);

  const shown = (lessons ?? []).filter((l) => filter === "all" || l.stage === filter);

  return (
    <div>
      <h1 className="text-3xl font-semibold">Little Lessons</h1>
      <p className="mt-1 text-ink-soft">Short how-to videos, each checked by a person against a trusted source.</p>
      <div role="group" aria-label="Filter by stage" className="mt-4 flex gap-2">
        {FILTERS.map((f) => (
          <button
            key={f.id}
            type="button"
            aria-pressed={filter === f.id}
            onClick={() => setFilter(f.id)}
            className={`rounded-full px-4 py-1.5 text-sm ${filter === f.id ? "bg-peach font-medium" : "bg-white shadow-soft"}`}
          >
            {f.label}
          </button>
        ))}
      </div>
      {failed ? (
        <Card className="mt-6 text-center">
          <p role="alert">We could not load the lessons. The service may be temporarily unavailable.</p>
          <button type="button" className="mt-4 rounded-full bg-peach px-5 py-2.5 font-medium" onClick={() => { setFailed(false); setLessons(null); setAttempt(n => n + 1); }}>Retry</button>
        </Card>
      ) : lessons === null ? (
        <p className="mt-10 text-center text-ink-soft">One moment…</p>
      ) : shown.length === 0 ? (
        <Card className="mt-6 text-center">
          <div className="text-4xl" aria-hidden>
            🎬
          </div>
          <p className="mt-3 font-medium">No lessons to show yet</p>
          <p className="mt-2 text-sm text-ink-soft">
            Lessons are published only after a person has reviewed every step against a trusted source. Until then,
            ask Nestling and you will get written, sourced steps.
          </p>
        </Card>
      ) : (
        <ul className="mt-5 grid grid-cols-2 gap-4">
          {shown.map((l) => (
            <li key={l.lesson_id}>
              <Link href={`/lessons/${l.lesson_id}`} className="block rounded-card bg-white p-2 shadow-soft">
                {/* eslint-disable-next-line @next/next/no-img-element */}
                <img
                  src={mediaUrl(l.thumbnail_url)}
                  alt=""
                  className="aspect-[9/16] w-full rounded-[18px] bg-sage/20 object-cover"
                />
                <p className="mt-2 px-1 font-display font-semibold leading-snug">{l.title}</p>
                <p className="px-1 pb-1 text-xs text-ink-soft">{reviewedOn(l.reviewed_on)}</p>
              </Link>
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}
