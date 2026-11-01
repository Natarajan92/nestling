"use client";
import { useEffect, useMemo, useState } from "react";
import Card from "./Card";
import SourceChip from "./SourceChip";
import { getToday, type Today } from "@/lib/api";
import { profileBody, useProfile } from "@/lib/store";
import { cardImage, downloadBlob } from "@/lib/cards";

export default function WeeklyCard() {
  const {
    profile
  } = useProfile();

  const body = useMemo(() => profile ? JSON.stringify(profileBody(profile)) : null, [profile]);
  const [today, setToday] = useState<Today | null>(null);
  const [failed, setFailed] = useState(false);
  const [busy, setBusy] = useState(false);
  const [status, setStatus] = useState("");

  useEffect(() => {
    if (!body)
      return;

    let alive = true;

    getToday(JSON.parse(body)).then(t => {
      if (alive)
        setToday(t);
    }).catch(() => {
      if (alive)
        setFailed(true);
    });

    return () => {
      alive = false;
    };
  }, [body]);

  const tip = today?.tip;
  const stage = today?.stage;
  const title = stage?.life_stage === "pregnancy" ? `Week ${stage.week}` : stage?.life_stage === "postpartum" ? `Baby's week ${(stage.baby_age_weeks ?? 0) + 1}` : "A little moment";
  const size = stage?.life_stage === "pregnancy" && stage.baby_size ? `About the size of ${stage.baby_size}` : "Growing together, one day at a time";

  async function exportCard(share: boolean) {
    if (!tip?.source_chip)
      return;

    setBusy(true);
    setStatus("");

    try {
      const s = tip.source_chip;

      const blob = await cardImage(
        title,
        [size, tip.text],
        `${s.id} · ${s.title ?? s.id}${s.page ? ` · p. ${s.page}` : ""}${s.url ? `\n${s.url}` : ""}`
      );

      const file = new File([blob], "nestling-week.png", {
        type: "image/png"
      });

      if (share && navigator.canShare?.({
        files: [file]
      })) {
        await navigator.share({
          title: `${title} · Nestling`,
          files: [file]
        });

        setStatus("Card shared.");
      } else {
        downloadBlob(blob, "nestling-week.png");

        setStatus(
          share ? "Image sharing is unavailable here. Your card was downloaded so you can share it." : "Your weekly card was downloaded."
        );
      }
    } catch (e) {
      if (!(e instanceof DOMException && e.name === "AbortError"))
        setStatus("The card could not be created. Please try downloading again.");
    } finally {
      setBusy(false);
    }
  }

  if (!profile)
    return <Card><h2 className="text-xl">Your weekly card</h2><p className="mt-2 text-sm">Add your date in Settings to make a sourced card for this week.</p></Card>;

  return (
    <Card tone="peach"><h2 className="text-xl">Your weekly card</h2>{failed ? <p className="mt-3 text-sm">The weekly card could not load. Reload to try again.</p> : !today ? <p className="mt-3 text-sm">Finding this week&apos;s little moment…</p> : !tip?.source_chip ? <p className="mt-3 text-sm">There is no trusted fact for this week yet. A card will be available when a sourced fact is ready.</p> : <><div className="my-5 rounded-card bg-cream p-5"><p className="text-center text-5xl" aria-hidden>{stage?.baby_emoji ?? "🌱"}</p><h3 className="mt-4 text-center text-3xl">{title}</h3><p className="mt-2 text-center text-sm">{size}</p><p className="mt-5 leading-relaxed">{tip.text}</p><div className="mt-3"><SourceChip source={tip.source_chip} /></div><p className="mt-5 text-center font-display text-sm">Nestling</p></div><p className="mb-3 text-xs text-ink-soft">Sharing includes your week and this sourced fact. Your name and dates are left out.</p><div className="flex flex-wrap gap-2"><button className="button text-sm" disabled={busy} onClick={() => exportCard(false)}>Download PNG</button><button className="quiet-button text-sm" disabled={busy} onClick={() => exportCard(true)}>Share image</button><a
            className="quiet-button text-sm"
            target="_blank"
            rel="noopener noreferrer"
            href={`https://wa.me/?text=${encodeURIComponent(
  `${title} · ${size}\n${tip.text}\nSource: ${tip.source_chip.id}${tip.source_chip.page ? ` p. ${tip.source_chip.page}` : ""} ${tip.source_chip.url ?? ""}\nMade with Nestling`
)}`}>Share on WhatsApp</a></div><p className="mt-3 text-xs text-ink-soft">WhatsApp opens a sourced text card. To send the image, download it or use Share image.</p></>}{status && <p className="mt-3 text-sm" role="status">{status}</p>}</Card>
  );
}
