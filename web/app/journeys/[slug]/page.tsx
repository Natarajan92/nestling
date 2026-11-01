import { notFound } from "next/navigation";
import ComingSoon from "@/components/ComingSoon";
import { JOURNEYS } from "@/components/JourneyCard";

export function generateStaticParams() {
  return JOURNEYS.map((j) => ({ slug: j.slug }));
}

export default async function JourneyPage({ params }: PageProps<"/journeys/[slug]">) {
  const { slug } = await params;
  const journey = JOURNEYS.find((j) => j.slug === slug);
  if (!journey) notFound();
  return <ComingSoon icon={journey.icon} title={journey.name} note={journey.blurb} />;
}
