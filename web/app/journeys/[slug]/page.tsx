import { notFound } from "next/navigation";
import { BodyJourney, ReadyJourney, MoneyJourney, CelebrateJourney } from "@/components/JourneyContent";
import Link from "next/link";
import { JOURNEYS } from "@/components/JourneyCard";

export function generateStaticParams() {
  return JOURNEYS.map((j) => ({ slug: j.slug }));
}

export default async function JourneyPage({ params }: PageProps<"/journeys/[slug]">) {
  const { slug } = await params;
  const journey = JOURNEYS.find((j) => j.slug === slug);
  if (!journey) notFound();
  return <div className="space-y-5"><Link className="text-sm text-ink-soft" href="/journeys">← Journeys</Link><div><h1 className="text-3xl font-semibold">{journey.name}</h1><p className="mt-2 text-ink-soft">{journey.blurb}</p></div>{slug === "body" ? <BodyJourney /> : slug === "money" ? <MoneyJourney /> : slug === "celebrate" ? <CelebrateJourney /> : <ReadyJourney partner={slug === "partner"} />}</div>;
}
