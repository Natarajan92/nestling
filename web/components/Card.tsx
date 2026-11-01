import type { ReactNode } from "react";

export default function Card({
  children,
  className = "",
  tone = "white",
}: {
  children: ReactNode;
  className?: string;
  tone?: "white" | "peach" | "sage" | "blush";
}) {
  const bg = { white: "bg-white", peach: "bg-peach/25", sage: "bg-sage/25", blush: "bg-blush/25" }[tone];
  return <section className={`rounded-card p-5 shadow-soft ${bg} ${className}`}>{children}</section>;
}
