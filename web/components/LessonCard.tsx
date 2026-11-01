import { mediaUrl, type Lesson } from "@/lib/api";
import SourceChip from "./SourceChip";

/** wa.me link carrying the title and the lesson link. */
export const whatsappLink = (lesson: Lesson, pageUrl: string) =>
  `https://wa.me/?text=${encodeURIComponent(`${lesson.title} (Nestling Little Lesson): ${pageUrl}`)}`;

function StepStrip({ lesson }: { lesson: Lesson }) {
  return (
    <ol aria-label="Steps" className="-mx-1 mt-4 flex snap-x snap-mandatory gap-3 overflow-x-auto px-1 pb-2">
      {lesson.steps.map((s) => (
        <li key={s.step_no} className="w-60 shrink-0 snap-center rounded-card bg-cream p-4 shadow-soft">
          <div className="flex items-center gap-2">
            <span
              aria-hidden
              className="flex size-8 items-center justify-center rounded-full bg-peach/50 text-sm font-semibold"
            >
              {s.step_no}
            </span>
            {/* eslint-disable-next-line @next/next/no-img-element */}
            <img alt="" src={`/icons/${/^[a-z-]+$/.test(s.icon) ? s.icon : "sparkle"}.svg`} className="size-9" />
          </div>
          <p className="mt-2 font-display text-lg font-semibold leading-snug">{s.caption}</p>
          <p className="mt-2 text-sm">{s.narration_line}</p>
          {s.safety_points.length > 0 && (
            <ul className="mt-2 list-disc space-y-1 pl-4 text-sm text-ink-soft">
              {s.safety_points.map((p) => (
                <li key={p}>{p}</li>
              ))}
            </ul>
          )}
        </li>
      ))}
    </ol>
  );
}

/** Vertical lesson: video, swipeable steps, sources, optional external page and WhatsApp share. */
export default function LessonCard({ lesson, pageUrl }: { lesson: Lesson; pageUrl: string }) {
  return (
    <div>
      <video
        controls
        playsInline
        preload="metadata"
        poster={mediaUrl(lesson.thumbnail_url)}
        src={mediaUrl(lesson.video_url)}
        className="mx-auto aspect-[9/16] max-h-[70vh] w-full max-w-xs rounded-card bg-ink/90 object-contain"
      >
        Your browser cannot play this video. The steps below say the same thing.
      </video>
      <StepStrip lesson={lesson} />
      <div className="mt-2 flex flex-wrap gap-2">
        {lesson.sources.map((s) => (
          <SourceChip key={s.id} source={s} />
        ))}
      </div>
      <div className="mt-4 flex flex-wrap gap-2">
        {lesson.see_how && (
          <a
            href={lesson.see_how.url}
            target="_blank"
            rel="noopener noreferrer"
            className="rounded-full border border-sage bg-sage/20 px-4 py-2 text-sm font-medium"
          >
            See how it&apos;s done ({lesson.see_how.publisher})
          </a>
        )}
        <a
          href={whatsappLink(lesson, pageUrl)}
          target="_blank"
          rel="noopener noreferrer"
          className="rounded-full bg-peach px-4 py-2 text-sm font-medium"
        >
          Share on WhatsApp
        </a>
      </div>
    </div>
  );
}
