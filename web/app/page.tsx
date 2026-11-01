"use client";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { useEffect, useMemo, useState } from "react";
import Card from "@/components/Card";
import JourneyCard, { JOURNEYS } from "@/components/JourneyCard";
import SourceChip from "@/components/SourceChip";
import WeekRing from "@/components/WeekRing";
import CaptureBudget from "@/components/CaptureBudget";
import { getChecklist, getToday, type Today } from "@/lib/api";
import { profileBody, useProfile, useTicks } from "@/lib/store";

type Load = { today: Today | null; ids: string[]; failed: boolean };

export default function TodayPage() {
  const router = useRouter();
  const { profile, ready } = useProfile();
  const { ticks } = useTicks();
  const [load, setLoad] = useState<Load>({ today: null, ids: [], failed: false });
  const body = useMemo(() => (profile ? JSON.stringify(profileBody(profile)) : null), [profile]);

  useEffect(() => {
    if (ready && !profile) router.replace("/welcome");
  }, [ready, profile, router]);

  useEffect(() => {
    if (!body) return;
    let alive = true;
    Promise.all([getToday(JSON.parse(body)), getChecklist().catch(() => null)])
      .then(([today, list]) => {
        if (alive) setLoad({ today, ids: list?.sections.flatMap((s) => s.items.map((i) => i.id)) ?? [], failed: false });
      })
      .catch(() => alive && setLoad({ today: null, ids: [], failed: true }));
    return () => {
      alive = false;
    };
  }, [body]);

  if (!ready || !profile) return <p className="mt-20 text-center text-ink-soft">One moment…</p>;
  if (load.failed)
    return (
      <Card className="mt-10 text-center">
        <p>Nestling could not reach its server just now. Please check your connection and try again in a moment.</p>
      </Card>
    );
  if (!load.today) return <p className="mt-20 text-center text-ink-soft">Getting today ready…</p>;

  const { stage, tip } = load.today;
  const done = load.ids.filter((id) => ticks.has(id)).length;
  const pct = load.ids.length ? Math.round((done / load.ids.length) * 100) : 0;

  let ring;
  if (stage.life_stage === "pregnancy") {
    ring = (
      <WeekRing
        progress={stage.progress ?? 0}
        emoji={stage.baby_emoji ?? "🌱"}
        title={`Week ${stage.week}`}
        subtitle={`Your baby is about the size of ${stage.baby_size} ${stage.baby_emoji}`}
      />
    );
  } else if (stage.life_stage === "postpartum") {
    const w = stage.baby_age_weeks ?? 0;
    ring = (
      <WeekRing
        progress={Math.min((stage.baby_age_days ?? 0) / 365, 1)}
        emoji="👶"
        title={w < 1 ? `Day ${stage.baby_age_days ?? 0}` : `Week ${w}`}
        subtitle="Your little one is here. You are doing beautifully."
      />
    );
  } else {
    ring = <WeekRing progress={0} emoji="🌱" title="Welcome" subtitle="Add a date in Settings to see your week." />;
  }

  return (
    <div className="space-y-6">
      <div className="flex justify-end">
        <Link href="/settings" aria-label="Settings" className="rounded-full bg-white px-3 py-1.5 text-sm shadow-soft">
          ⚙️ Settings
        </Link>
      </div>
      {ring}

      <Card tone="peach">
        <h2 className="text-lg font-semibold">One little moment</h2>
        {tip ? (
          <>
            <p className="mt-2 leading-relaxed">{tip.text}</p>
            <div className="mt-3">
              <SourceChip source={tip.source_chip} />
            </div>
          </>
        ) : (
          <p className="mt-2 text-ink-soft">I don&apos;t have a trusted source for a tip today. Please ask your doctor if you wonder about anything.</p>
        )}
      </Card>

      <Link href="/journeys/ready" className="block">
        <Card>
          <div className="flex items-baseline justify-between">
            <h2 className="text-lg font-semibold">Ready meter</h2>
            <span className="text-sm text-ink-soft">
              {load.ids.length ? `${done} of ${load.ids.length}` : "Checklist unavailable"}
            </span>
          </div>
          <p className="mt-1 text-sm text-ink-soft">{load.ids.length ? `Hospital bag ${pct}% ready` : "Open Ready to try loading your checklist."}</p>
          <div
            className="mt-3 h-3 overflow-hidden rounded-full bg-sage/25"
            role="progressbar" aria-label="Hospital bag readiness" aria-valuemin={0} aria-valuemax={100} aria-valuenow={pct}
          >
            <div className="h-full rounded-full bg-sage transition-all duration-700" style={{ width: `${pct}%` }} />
          </div>
        </Card>
      </Link>

      <CaptureBudget />
      <div className="grid grid-cols-2 gap-4">
        {JOURNEYS.filter((j) => load.today?.cards.includes(j.slug)).map((j) => (
          <JourneyCard key={j.slug} journey={j} />
        ))}
      </div>
    </div>
  );
}
