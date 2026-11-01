"use client";
import { motion, useReducedMotion } from "motion/react";

/** A soft ring that fills with progress, with the baby's fruit in the middle. */
export default function WeekRing({
  progress,
  emoji,
  title,
  subtitle,
}: {
  progress: number;
  emoji: string;
  title: string;
  subtitle: string;
}) {
  const r = 70;
  const reduced = useReducedMotion();
  return (
    <div className="flex flex-col items-center text-center">
      <div className="relative h-44 w-44">
        <svg viewBox="0 0 180 180" className="h-full w-full -rotate-90" aria-hidden>
          <circle cx="90" cy="90" r={r} fill="none" stroke="var(--peach)" strokeOpacity="0.3" strokeWidth="12" />
          <motion.circle
            cx="90"
            cy="90"
            r={r}
            fill="none"
            stroke="var(--peach)"
            strokeWidth="12"
            strokeLinecap="round"
            initial={reduced ? false : { pathLength: 0 }}
            animate={{ pathLength: Math.min(Math.max(progress, 0.02), 1) }}
            transition={{ duration: reduced ? 0 : 1.2, ease: "easeOut" }}
          />
        </svg>
        <div className="absolute inset-0 flex items-center justify-center text-6xl" aria-hidden>
          {emoji}
        </div>
      </div>
      <h1 className="mt-4 text-2xl font-semibold">{title}</h1>
      <p className="mt-1 text-ink-soft">{subtitle}</p>
    </div>
  );
}
