import Link from "next/link";
import Card from "./Card";

/** Calm placeholder for screens that later tasks build. */
export default function ComingSoon({ title, icon, note }: { title: string; icon: string; note: string }) {
  return (
    <Card className="mt-6 text-center">
      <div className="text-5xl" aria-hidden>
        {icon}
      </div>
      <h1 className="mt-3 text-2xl font-semibold">{title}</h1>
      <p className="mt-2 text-ink-soft">{note}</p>
      <p className="mt-4 text-sm text-ink-soft">Coming soon.</p>
      <Link href="/" className="mt-5 inline-block rounded-full bg-peach px-5 py-2 text-sm font-medium">
        Back to Today
      </Link>
    </Card>
  );
}
