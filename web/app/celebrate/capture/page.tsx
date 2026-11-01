"use client";
import Link from "next/link";
import { useState, type FormEvent } from "react";
import Card from "@/components/Card";
import { draftQuote, estimateCapture, searchCapture, type CapturePicks, type Estimate, type StudioPackage } from "@/lib/api";
import { dateLabel, inr, safeLink } from "@/lib/format";
import { saveCapture, useCapture, useProfile } from "@/lib/store";
const MISSING = "Not listed — ask the studio";
const show = (value: number | string | null | undefined, unit = "") => value == null || value === "" ? MISSING : `${value}${unit}`;

const offered = (
  item: {
    offered: boolean | null;
    price_inr: number | null;
  }
) => item.offered === false ? "Not offered" : item.price_inr != null ? inr(item.price_inr) : item.offered ? "Included as listed" : MISSING;

const rows: {
  label: string;
  value: (p: StudioPackage) => string;
}[] = [{
  label: "Total listed cost",
  value: p => inr(p.total_cost)
}, {
  label: "Per edited photo",
  value: p => inr(p.cost_per_edited_photo)
}, {
  label: "Duration",
  value: p => show(p.duration_hours, " hours")
}, {
  label: "Photos taken",
  value: p => show(p.photos_taken)
}, {
  label: "Edited copies",
  value: p => show(p.edited_photos)
}, {
  label: "Delivery",
  value: p => show(p.delivery_days, " days")
}, {
  label: "Album",
  value: p => `${offered(p.album)}${p.album.pages ? ` · ${p.album.pages} pages` : ""}${p.album.size ? ` · ${p.album.size}` : ""}${p.album.type ? ` · ${p.album.type}` : ""}`
}, {
  label: "Frames",
  value: p => p.frames.length ? p.frames.map(f => `${show(f.count)} × ${show(f.size)} (${inr(f.price_inr)})`).join("; ") : MISSING
}, {
  label: "Casting",
  value: p => offered(p.casting)
}];

export default function CapturePage() {
  const {
    profile
  } = useProfile();

  const saved = useCapture();
  const [cityDraft, setCity] = useState<string | null>(null);
  const city = cityDraft ?? profile?.city ?? "Bengaluru";
  const [shoot, setShoot] = useState("maternity");
  const [budget, setBudget] = useState("");
  const [date, setDate] = useState("");
  const [packages, setPackages] = useState<StudioPackage[] | null>(null);

  const [context, setContext] = useState({
    city: "",
    shoot: ""
  });

  const [busy, setBusy] = useState("");
  const [error, setError] = useState("");
  const [message, setMessage] = useState("");

  const [picks, setPicks] = useState<CapturePicks>({
    edited_photos: 10,
    album: false,
    album_pages: 20,
    frames: 0,
    frame_sizes: "",
    casting: false
  });

  const [estimate, setEstimate] = useState<Estimate | null>(null);
  const [selected, setSelected] = useState<StudioPackage | null>(null);
  const [draft, setDraft] = useState("");
  const [approved, setApproved] = useState(false);
  const [reply, setReply] = useState("");
  const [storeConsent, setStoreConsent] = useState(false);

  const changePicks = (patch: Partial<CapturePicks>) => {
    setPicks(p => ({
      ...p,
      ...patch
    }));

    setEstimate(null);
    setDraft("");
    setApproved(false);
  };

  async function search(e: FormEvent) {
    e.preventDefault();
    setBusy("search");
    setError("");
    setMessage("");
    setPackages(null);
    setEstimate(null);
    setDraft("");
    setSelected(null);

    try {
      const result = await searchCapture(city.trim(), shoot);
      setPackages(result.packages);

      setContext({
        city: city.trim(),
        shoot
      });
    } catch {
      setError("Studios could not be found just now. Check your connection and try again.");
    } finally {
      setBusy("");
    }
  }

  async function calculate() {
    if (!packages)
      return;

    setBusy("estimate");
    setError("");

    try {
      setEstimate(await estimateCapture(packages, picks));
    } catch {
      setError("The estimate could not be calculated. Please try again.");
    } finally {
      setBusy("");
    }
  }

  async function quote(p: StudioPackage) {
    setSelected(p);
    setBusy("quote");
    setDraft("");
    setApproved(false);
    setError("");

    try {
      setDraft(
        (await draftQuote(p.studio_name, context.shoot || p.shoot_type, picks, date, context.city || p.city || city)).draft
      );
    } catch {
      setError("The quote draft could not be prepared. Please try again.");
    } finally {
      setBusy("");
    }
  }

  const shown = packages?.filter(p => !budget || p.total_cost == null || p.total_cost <= Number(budget)) ?? [];

  return (
    <div className="space-y-5"><Link className="text-sm text-ink-soft" href="/journeys/celebrate">← Celebrate</Link><div><h1 className="text-3xl font-semibold">Capture</h1><p className="mt-2 text-ink-soft">Make room for the memories. Compare what a shoot really includes.</p></div>
      <Card><form className="space-y-4" onSubmit={search}><label className="block">Shoot type<select className="field" value={shoot} onChange={e => setShoot(e.target.value)}><option value="maternity">Maternity</option><option value="baby_shower">Baby shower / seemantham</option><option value="newborn">Newborn</option><option value="casting">Hand & foot casting</option></select></label><label className="block">City<input className="field" required maxLength={60} value={city} onChange={e => setCity(e.target.value)} /></label><div className="grid grid-cols-2 gap-3"><label className="block text-sm">Budget (INR, optional)<input className="field" type="number" min="1" value={budget} onChange={e => setBudget(e.target.value)} /></label><label className="block text-sm">Preferred date<input
                className="field"
                type="date"
                value={date}
                onChange={e => {
                  setDate(e.target.value);
                  setDraft("");
                  setApproved(false);
                }} /></label></div><p className="text-xs text-ink-soft">Search sends the city and shoot type. Your date and budget stay here until you request a quote draft.</p><button className="button w-full" disabled={!!busy}>{busy === "search" ? "Finding studio listings…" : "Find studios"}</button></form></Card>
      {error && <p className="rounded-card bg-blush/25 p-4 text-sm" role="alert">{error}</p>}{message && <p role="status" className="rounded-card bg-sage/25 p-4 text-sm">{message}</p>}
      {packages && <><div><h2 className="text-2xl">{context.city}studios</h2><p className="mt-2 text-sm text-ink-soft">Prices as listed on each studio&apos;s site. Confirm availability, inclusions and final cost directly.</p>{budget && <p className="mt-2 text-xs">Showing packages within {inr(Number(budget))}, plus packages with unlisted prices. Estimates use all found listings.</p>}</div>{shown.length === 0 ? <Card><p>No listed packages match yet. Try a wider budget or a nearby city.</p></Card> : shown.map(
          (p, i) => <Card key={`${p.source_url}-${i}`}><div className="flex items-start justify-between gap-2"><h3 className="text-xl">{p.studio_name}</h3><span className="text-sm font-semibold">{inr(p.price_inr)}</span></div>{p.package_name && <p className="mt-1 text-sm">{p.package_name}</p>}<p className="mt-3 text-xs text-ink-soft">As listed on the studio&apos;s site · checked {dateLabel(p.checked_on)}</p>{p.price_text && <p className="mt-2 text-sm">Listed as: {p.price_text}</p>}{p.price_assumptions.map(a => <p key={a} className="mt-1 text-xs">{a}</p>)}<p className="mt-3 text-sm">Location: {p.location ?? MISSING}</p><p className="mt-1 text-sm">Reviews: {p.rating_summary ?? MISSING}</p><ul className="mt-3 list-disc pl-5 text-sm">{p.inclusions.map(v => <li key={v}>{v}</li>)}</ul><div className="mt-4 flex flex-wrap gap-2"><a className="quiet-button text-sm" href={safeLink(p.source_url)} target="_blank" rel="noopener noreferrer">Studio listing</a><button className="button text-sm" disabled={!!busy} onClick={() => quote(p)}>Request quote</button></div></Card>
        )}
        {shown.length > 0 && <section><h2 className="text-2xl">Side by side</h2><p className="mt-2 text-xs text-ink-soft">Scroll across to compare. Each column links to the listing and checked date.</p><div
            className="mt-3 overflow-x-auto rounded-card bg-white shadow-soft"
            tabIndex={0}
            role="region"
            aria-label="Studio comparison"><table className="w-full text-left text-sm"><thead><tr><th className="min-w-32 p-3">Package</th>{shown.map(
                    (p, i) => <th key={i} className="min-w-48 p-3 align-top"><a className="underline" href={safeLink(p.source_url)} target="_blank" rel="noopener noreferrer">{p.studio_name}</a><span className="mt-1 block font-normal">{p.package_name}<br />Checked {dateLabel(p.checked_on)}</span></th>
                  )}</tr></thead><tbody>{rows.map(
                  r => <tr className="border-t border-ink/10" key={r.label}><th className="p-3 align-top font-medium">{r.label}</th>{shown.map((p, i) => <td key={i} className="p-3 align-top">{r.value(p)}</td>)}</tr>
                )}</tbody></table></div></section>}
        <Card tone="sage"><h2 className="text-2xl">Estimate my budget</h2><p className="mt-2 text-sm">Choose the extras you want to ask about. Ranges are calculated from listed prices, never guessed.</p><div className="mt-4 space-y-3"><label className="block text-sm">Edited photos requested<input
                className="field"
                type="number"
                min="1"
                max="500"
                value={picks.edited_photos}
                onChange={e => changePicks({
                  edited_photos: Number(e.target.value)
                })} /></label><label className="flex gap-2"><input
                type="checkbox"
                checked={picks.album}
                onChange={e => changePicks({
                  album: e.target.checked
                })} />Printed album</label>{picks.album && <label className="block text-sm">Album pages<input
                className="field"
                type="number"
                min="1"
                max="200"
                value={picks.album_pages}
                onChange={e => changePicks({
                  album_pages: Number(e.target.value)
                })} /></label>}<label className="block text-sm">Number of frames<input
                className="field"
                type="number"
                min="0"
                max="10"
                value={picks.frames}
                onChange={e => changePicks({
                  frames: Number(e.target.value)
                })} /></label>{picks.frames > 0 && <label className="block text-sm">Frame sizes<input
                className="field"
                value={picks.frame_sizes}
                maxLength={100}
                onChange={e => changePicks({
                  frame_sizes: e.target.value
                })}
                placeholder="For example, 12 × 18 inches" /></label>}<label className="flex gap-2"><input
                type="checkbox"
                checked={picks.casting}
                onChange={e => changePicks({
                  casting: e.target.checked
                })} />Hand & foot casting</label><p className="text-xs text-ink-soft">Photo count, album pages and frame sizes go into your quote request. The estimate uses listed base packages and available add-on prices; extra edits, size/page changes and travel need the studio&apos;s quote.</p><button className="button" disabled={!!busy} onClick={calculate}>{busy === "estimate" ? "Calculating…" : "Estimate my budget"}</button></div></Card>
        {estimate && <Card><p className="text-sm font-medium">{estimate.label}</p>{Object.entries(estimate.tiers).map(
            ([tier, result]) => <div className="mt-5 border-t border-ink/10 pt-4" key={tier}><h3 className="text-xl">{tier}</h3>{result.estimate ? <><p className="mt-2 text-2xl">{inr(result.estimate.low)}–{inr(result.estimate.high)}</p><p className="mt-1 text-sm">Confidence: {result.confidence}· {result.n_studios}studios</p></> : <p className="mt-2">{result.message ?? "Not enough data for a reliable estimate — request quotes."}</p>}{!!result.not_listed_components?.length && <p className="mt-2 text-sm">Prices missing for: {result.not_listed_components.join(", ")}. Request a quote.</p>}<details className="mt-3 text-sm"><summary className="cursor-pointer underline">How we estimated</summary><p className="mt-2">Listed base prices are grouped by tier. Available component ranges are added in code. Fewer than three studios or unknown requested costs cannot support a reliable estimate.</p><ul className="mt-3 space-y-2">{result.sources.map(
                    (s, i) => <li key={i}><a className="underline" href={safeLink(s.url)} target="_blank" rel="noopener noreferrer">{s.studio}· {s.package ?? "Listed package"}</a><p className="text-xs">{inr(s.price_inr)}· checked {dateLabel(s.checked_on)}</p></li>
                  )}</ul></details></div>
          )}</Card>}
      </>}
      {selected && <Card tone="peach"><h2 className="text-xl">Quote request for {selected.studio_name}</h2><p className="mt-2 text-sm">Review the draft. Nothing is sent automatically.</p>{busy === "quote" ? <p className="mt-3">Preparing draft…</p> : draft && <><label className="mt-3 block text-sm">Your message<textarea
              className="field min-h-64"
              value={draft}
              onChange={e => {
                setDraft(e.target.value);
                setApproved(false);
              }} /></label><label className="mt-4 flex gap-2 text-sm"><input type="checkbox" checked={approved} onChange={e => setApproved(e.target.checked)} />I approve this message and am ready to share it.</label>{approved && <div className="mt-4 flex flex-wrap gap-2"><button
              className="button text-sm"
              onClick={async () => {
                try {
                  await navigator.clipboard.writeText(draft);
                  setMessage("Quote request copied. You choose where to send it.");
                } catch {
                  setError("Copy is unavailable. Select and copy the draft text above.");
                }
              }}>Copy message</button><a
              className="quiet-button text-sm"
              href={`https://wa.me/?text=${encodeURIComponent(draft)}`}
              target="_blank"
              rel="noopener noreferrer">Open WhatsApp</a><a
              className="quiet-button text-sm"
              href={`mailto:?subject=${encodeURIComponent("Photoshoot quote request")}&body=${encodeURIComponent(draft)}`}>Open email</a></div>}</>}<label className="mt-5 block text-sm">Studio reply (optional)<textarea
            className="field"
            value={reply}
            onChange={e => setReply(e.target.value)}
            maxLength={6000}
            placeholder="Paste the studio's reply to compare it with the estimate." /></label><p className="mt-2 text-xs text-ink-soft">The reply stays on this page until you save this package.</p><label className="mt-4 flex gap-2 text-sm"><input type="checkbox" checked={storeConsent} onChange={e => setStoreConsent(e.target.checked)} />Keep this package, budget and reply in this browser.</label><button
          className="button mt-3"
          disabled={!storeConsent}
          onClick={() => {
            saveCapture({
              package: selected,
              quote: reply,
              budget: budget ? Number(budget) : null,
              saved_at: new Date().toISOString()
            });

            setMessage("Photoshoot budget saved to Today and Celebrate.");
          }}>Save selected package</button></Card>}
      {saved && <Card><h2 className="text-xl">Your saved photoshoot budget</h2><p className="mt-2">{saved.package.studio_name}· {saved.package.package_name}</p><p className="mt-2 text-sm">Listed total: {inr(saved.package.total_cost ?? saved.package.price_inr)}· checked {dateLabel(saved.package.checked_on)}</p>{saved.budget != null && <p className="mt-2 text-sm">Your budget: {inr(saved.budget)}</p>}<a
          className="mt-3 inline-block text-sm underline"
          href={safeLink(saved.package.source_url)}
          target="_blank"
          rel="noopener noreferrer">View the source listing</a>{saved.quote && <div className="mt-4"><h3 className="font-semibold">Studio&apos;s reply</h3><p className="mt-2 whitespace-pre-line text-sm">{saved.quote}</p></div>}<button className="quiet-button mt-4 text-sm" onClick={() => saveCapture(null)}>Remove saved package</button></Card>}
    </div>
  );
}
