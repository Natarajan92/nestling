import { Suspense } from "react";
import LessonDetail from "@/components/LessonDetail";

async function Lesson({ params }: Pick<PageProps<"/lessons/[lessonId]">, "params">) {
  const { lessonId } = await params;
  return <LessonDetail key={lessonId} lessonId={lessonId} />;
}

export default function LessonPage({ params }: PageProps<"/lessons/[lessonId]">) {
  return (
    <Suspense fallback={<p className="mt-20 text-center text-ink-soft">One moment…</p>}>
      <Lesson params={params} />
    </Suspense>
  );
}
