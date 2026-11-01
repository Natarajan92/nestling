import Link from "next/link";
import Card from "./Card";

export type Journey = { slug: string; icon: string; name: string; blurb: string; tone: "peach" | "sage" | "blush" | "white" };

export const JOURNEYS: Journey[] = [
  { slug: "partner", icon: "🤝", name: "Partner", blurb: "A little help, shared together", tone: "sage" },
  { slug: "body", icon: "🩺", name: "Body", blurb: "How you and baby are doing", tone: "blush" },
  { slug: "ready", icon: "🎒", name: "Ready", blurb: "Bag, home and what to learn", tone: "sage" },
  { slug: "money", icon: "💰", name: "Money", blurb: "Insurance and costs, explained", tone: "white" },
  { slug: "celebrate", icon: "🎉", name: "Celebrate", blurb: "Rituals, invitations, 📸 Capture", tone: "peach" },
];

export default function JourneyCard({ journey, hint }: { journey: Journey; hint?: string }) {
  return (
    <Link href={`/journeys/${journey.slug}`} className="block transition-transform active:scale-[0.98]">
      <Card tone={journey.tone} className="h-full">
        <div className="text-3xl" aria-hidden>
          {journey.icon}
        </div>
        <h3 className="mt-2 text-lg font-semibold">{journey.name}</h3>
        <p className="mt-1 text-sm text-ink-soft">{hint ?? journey.blurb}</p>
      </Card>
    </Link>
  );
}
