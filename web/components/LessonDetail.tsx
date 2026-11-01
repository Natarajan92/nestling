"use client";
import Link from "next/link";
import { useEffect, useState } from "react";
import Card from "@/components/Card";
import LessonCard from "@/components/LessonCard";
import { getLesson, type Lesson } from "@/lib/api";
import { dateLabel } from "@/lib/format";

export default function LessonDetail({ lessonId }: { lessonId: string }) {
  const [lesson, setLesson] = useState<Lesson | null | undefined>(undefined);
  const [failed, setFailed] = useState(false);
  const [attempt, setAttempt] = useState(0);

  useEffect(() => {
    let alive = true;
    getLesson(lessonId).then((l) => alive && setLesson(l)).catch(() => alive && setFailed(true));
    return () => {
      alive = false;
    };
  }, [lessonId, attempt]);

  if (failed) return (
    <Card className="mt-10 text-center">
      <p role="alert">We could not load this lesson. The service may be temporarily unavailable.</p>
      <button type="button" className="mt-4 rounded-full bg-peach px-5 py-2.5 font-medium" onClick={() => { setFailed(false); setLesson(undefined); setAttempt(n => n + 1); }}>Retry</button>
      <Link href="/lessons" className="mt-4 block underline">All lessons</Link>
    </Card>
  );
  if (lesson === undefined) return <p className="mt-20 text-center text-ink-soft">One moment…</p>;
  if (!lesson)
    return (
      <Card className="mt-10 text-center">
        <p>This lesson is not available. Lessons are published only after review.</p>
        <Link href="/lessons" className="mt-4 inline-block rounded-full bg-peach px-5 py-2 text-sm font-medium">
          All lessons
        </Link>
      </Card>
    );
  return (
    <div>
      <Link href="/lessons" className="text-sm text-ink-soft">
        ← All lessons
      </Link>
      <h1 className="mt-2 text-3xl font-semibold">{lesson.title}</h1>
      <p className="text-sm text-ink-soft">Reviewed{lesson.reviewed_on ? ` on ${dateLabel(lesson.reviewed_on)}` : ""}</p>
      <div className="mt-4">
        <LessonCard lesson={lesson} pageUrl={window.location.href} />
      </div>
    </div>
  );
}
