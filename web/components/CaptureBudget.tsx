"use client";
import Link from "next/link";
import Card from "./Card";
import { useCapture } from "@/lib/store";
import { inr } from "@/lib/format";

export default function CaptureBudget() {
  const saved = useCapture();

  if (!saved)
    return null;

  return <Link className="block" href="/celebrate/capture"><Card tone="peach"><h2 className="text-xl">Photoshoot budget</h2><p className="mt-2">{saved.package.studio_name}</p><p className="mt-1 text-sm">Listed package: {inr(saved.package.total_cost ?? saved.package.price_inr)}</p>{saved.budget != null && <p className="mt-1 text-sm">Your budget: {inr(saved.budget)}</p>}<p className="mt-3 text-sm underline">View saved package and quote</p></Card></Link>;
}
