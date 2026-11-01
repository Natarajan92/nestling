import JourneyCard, { JOURNEYS } from "@/components/JourneyCard";

export default function JourneysPage() {
  return (
    <>
      <h1 className="text-3xl font-semibold">Journeys</h1>
      <p className="mt-1 text-ink-soft">Pick a path. Each one is gentle and sourced.</p>
      <div className="mt-6 grid grid-cols-2 gap-4">
        {JOURNEYS.map((j) => (
          <JourneyCard key={j.slug} journey={j} />
        ))}
      </div>
    </>
  );
}
