"use client";
import Link from "next/link";
import { useEffect, useState, type FormEvent } from "react";
import Card from "./Card";
import SourceChip from "./SourceChip";

import {
  askPolicy,
  createInvitation,
  getChecklist,
  getLessons,
  getPlaybook,
  getToday,
  type Checklist,
  type Invitation,
  type Lesson,
  type Playbook,
  type Stage,
} from "@/lib/api";

import { profileBody, useProfile, useTicks } from "@/lib/store";
import { cardImage, downloadBlob } from "@/lib/cards";
import CaptureBudget from "./CaptureBudget";

export function Questions(
  {
    questions
  }: {
    questions: string[];
  }
) {
  return (
    <div className="flex flex-col gap-3">{questions.map(
        q => <Link key={q} className="rounded-card bg-white p-4 text-sm shadow-soft" href={`/ask?q=${encodeURIComponent(q)}`}>{q}</Link>
      )}</div>
  );
}

function LessonsRow(
  {
    stage
  }: {
    stage: string;
  }
) {
  const [lessons, setLessons] = useState<Lesson[] | null>(null);

  useEffect(() => {
    let alive = true;

    getLessons().then(l => {
      if (alive)
        setLessons(l);
    });

    return () => {
      alive = false;
    };
  }, []);

  const shown = lessons?.filter(l => l.stage === stage) ?? [];
  return <Card><h2 className="text-xl">{stage === "before_birth" ? "Watch before baby arrives" : "Little Lessons for the first weeks"}</h2>{lessons === null ? <p className="mt-3 text-sm">Loading reviewed lessons…</p> : shown.length ? <ul className="mt-3 space-y-3">{shown.map(l => <li key={l.lesson_id}><Link className="underline" href={`/lessons/${l.lesson_id}`}>{l.title}</Link></li>)}</ul> : <p className="mt-3 text-sm text-ink-soft">No approved lessons for this stage yet. <Link className="underline" href="/ask">Ask for written, sourced guidance.</Link></p>}<Link className="mt-4 inline-block text-sm underline" href="/lessons">All reviewed lessons</Link></Card>;
}

export function BodyJourney() {
  const {
    profile
  } = useProfile();

  return (
    <div className="space-y-5"><Questions
        questions={profile?.birth_date ? [
          "What should I ask at my postnatal check-up?",
          "How can I get help with breastfeeding?",
          "What warning signs after birth need urgent care?"
        ] : [
          "What should I ask at my next antenatal visit?",
          "What foods can help me eat a varied diet?",
          "What warning signs in pregnancy need urgent care?"
        ]} /><LessonsRow stage={profile?.birth_date ? "first_weeks" : "before_birth"} /></div>
  );
}

export function ReadyJourney(
  {
    partner = false
  }: {
    partner?: boolean;
  }
) {
  const {
    ticks,
    toggle
  } = useTicks();

  const [list, setList] = useState<Checklist | null>(null);
  const [failed, setFailed] = useState(false);
  const { profile } = useProfile();
  const partnerBody = partner && profile ? JSON.stringify(profileBody(profile)) : null;
  const [partnerToday, setPartnerToday] = useState<{ body: string; stage: Stage } | null>(null);
  const [partnerFailed, setPartnerFailed] = useState<string | null>(null);

  useEffect(() => {
    if (!partnerBody) return;
    let alive = true;
    getToday(JSON.parse(partnerBody)).then(today => {
      if (alive) {
        setPartnerToday({ body: partnerBody, stage: today.stage });
        setPartnerFailed(null);
      }
    }).catch(() => { if (alive) setPartnerFailed(partnerBody); });
    return () => { alive = false; };
  }, [partnerBody]);

  useEffect(() => {
    let alive = true;

    getChecklist().then(l => {
      if (alive)
        setList(l);
    }).catch(() => {
      if (alive)
        setFailed(true);
    });

    return () => {
      alive = false;
    };
  }, []);

  const items = list?.sections.flatMap(s => s.items) ?? [];
  const done = items.filter(i => ticks.has(i.id)).length;
  const stage = partnerToday?.body === partnerBody ? partnerToday?.stage : null;
  const postpartum = stage?.life_stage === "postpartum" || (!stage && !!profile?.birth_date);
  const weekLabel = stage?.life_stage === "postpartum" ? `Baby's week ${(stage.baby_age_weeks ?? 0) + 1}`
    : stage?.life_stage === "pregnancy" ? `Pregnancy week ${stage.week}`
    : postpartum ? "Supporting each other after birth" : "Getting ready together";

  return (
    <div className="space-y-5">{partner && <><Card tone="sage">
      <h2 className="text-xl">What can I do this week?</h2>
      <p className="mt-2 font-semibold">{weekLabel}</p>
      {!stage && <p className="mt-2 text-xs text-ink-soft">{partnerFailed === partnerBody && partnerBody ? "Your week could not load. These are general support ideas." : partnerBody ? "Loading your week. Here are a few practical ideas while you wait." : "Add your date in Settings for a weekly view. These are general support ideas."}</p>}
      <p className="mt-2">{postpartum ? "In the first weeks, ask what would make today easier and take responsibility for one practical job." : "Take one thing off their list. Ask what would help today, then own the follow-through."}</p>
      <ul className="mt-3 list-disc space-y-2 pl-5">
        <li>{postpartum ? "Rest and meals: agree on a household job or meal you can take care of today." : `Bag duty: ${list ? `${items.length - done} items remain on your shared packing list below.` : "check the shared packing list when it loads."}`}</li>
        <li>{postpartum ? "Paperwork: check which newborn documents or insurer forms still need attention." : "Paperwork: gather the policy, identity documents and hospital contacts."}</li>
        <li>Make room for a conversation about what support feels helpful this week.</li>
      </ul>
    </Card><Questions questions={postpartum ? ["How can a partner help in the first weeks?", "How do I add my newborn to health insurance?"] : ["What paperwork should we prepare for delivery?", "How can my partner help me prepare for birth?"]} /></>}{failed ? <Card><p role="alert">The checklist could not load. Reload this page to try again.</p></Card> : !list ? <p>Loading the checklist…</p> : <><Card tone="sage"><h2 className="text-xl">{list.title}</h2><p className="mt-2 text-sm">{list.when}</p><p className="mt-3 font-semibold">{done} of {items.length} packed</p><progress aria-label="Ready meter" max={items.length || 1} value={done} className="mt-2 w-full accent-[var(--sage)]" /><p className="mt-2 text-xs text-ink-soft">Ticks stay in this browser. You and your partner can use this same device.</p></Card>{list.sections.map(
          section => <Card key={section.name}><h2 className="text-xl">{section.name}</h2><ul className="mt-3 divide-y divide-ink/10">{section.items.map(i => <li key={i.id} className="py-3"><label className="flex gap-3"><input
                    type="checkbox"
                    checked={ticks.has(i.id)}
                    onChange={() => toggle(i.id)}
                    className="mt-1 size-5 shrink-0 accent-[var(--sage)]" /><span>{i.item}</span></label><div className="ml-8 mt-2">{i.source ? <SourceChip source={i.source} /> : <span className="text-xs text-ink-soft">Practical packing suggestion</span>}</div></li>)}</ul></Card>
        )}</>}<LessonsRow stage={partner && postpartum ? "first_weeks" : "before_birth"} /></div>
  );
}

export function MoneyJourney() {
  const [file, setFile] = useState<File | null>(null);
  const [question, setQuestion] = useState("");
  const [consent, setConsent] = useState(false);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const [result, setResult] = useState<Awaited<ReturnType<typeof askPolicy>> | null>(null);

  async function submit(e: FormEvent) {
    e.preventDefault();

    if (!file || !consent)
      return;

    setBusy(true);
    setError("");
    setResult(null);

    try {
      setResult(await askPolicy(file, question));
    } catch {
      setError("The policy could not be read. Check your connection or ask your insurer or TPA.");
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="space-y-5"><Card><h2 className="text-xl">Understand your own policy</h2><p className="mt-2 text-sm text-ink-soft">Your PDF is processed in memory, never stored or indexed. Answers show clauses checked against your document, with page numbers.</p><form onSubmit={submit} className="mt-4 space-y-4"><label className="block">Policy PDF (up to 20 MB)<input
              className="field"
              type="file"
              accept="application/pdf,.pdf"
              required
              onChange={e => {
                const f = e.target.files?.[0] ?? null;

                if (f && f.size > 20 * 1024 * 1024) {
                  setError("Choose a PDF smaller than 20 MB.");
                  setFile(null);
                } else {
                  setFile(f);
                  setError("");
                }
              }} /></label><label className="block">Your question<textarea
              className="field"
              maxLength={1000}
              required
              value={question}
              onChange={e => setQuestion(e.target.value)}
              placeholder="What does my policy say about maternity cover?" /></label><label className="flex gap-2 text-sm"><input type="checkbox" checked={consent} onChange={e => setConsent(e.target.checked)} />I agree to send this PDF and question for this answer.</label><button className="button" disabled={busy || !file || !consent || !question.trim()}>{busy ? "Checking the clauses…" : "Read my policy"}</button></form>{error && <p role="alert" className="mt-3">{error}</p>}</Card>{result && <Card><h2 className="text-xl">From your policy</h2><p className="mt-3 whitespace-pre-line">{result.answer}</p>{result.quotes.map(
          (q, i) => <blockquote key={i} className="mt-4 border-l-4 border-sage pl-4"><p>“{q.text}”</p><cite className="mt-1 block text-sm not-italic text-ink-soft">Your uploaded policy · page {q.page_start}{q.page_end !== q.page_start ? `–${q.page_end}` : ""}</cite></blockquote>
        )}<p className="mt-4 text-xs text-ink-soft">Confirm cover and claims with your insurer or TPA.</p></Card>}<Questions questions={["What should I ask my insurer before delivery?", "How do I add my newborn to health insurance?"]} /></div>
  );
}

export function CelebrateJourney() {
  const {
    profile
  } = useProfile();

  const [choice, setChoice] = useState<string | null>(null);
  const tradition = choice ?? (profile?.tradition === "other" ? "tamil_nadu" : profile?.tradition || "tamil_nadu");
  const [book, setBook] = useState<Playbook | null>(null);
  const [failed, setFailed] = useState(false);
  const [invite, setInvite] = useState<Invitation | null>(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const [sendConsent, setSendConsent] = useState(false);

  useEffect(() => {
    let alive = true;

    getPlaybook(tradition).then(b => {
      if (alive) {
        setBook(b);
        setFailed(false);
      }
    }).catch(() => {
      if (alive)
        setFailed(true);
    });

    return () => {
      alive = false;
    };
  }, [tradition]);

  async function invitation(e: FormEvent<HTMLFormElement>) {
    e.preventDefault();
    const f = new FormData(e.currentTarget);
    setBusy(true);
    setError("");

    try {
      setInvite(await createInvitation({
        tradition,
        host_names: String(f.get("hosts")),
        mother_name: String(f.get("name")),
        date_text: String(f.get("date")),
        time_text: String(f.get("time")),
        venue: String(f.get("venue"))
      }));
    } catch {
      setError("The invitation could not be made. Please try again.");
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="space-y-5"><label className="block">Your family tradition<select
          className="field"
          value={tradition}
          onChange={e => {
            setChoice(e.target.value);
            setInvite(null);
          }}><option value="tamil_nadu">Tamil Nadu</option><option value="kerala">Kerala</option><option value="karnataka">Karnataka</option></select></label>{failed ? <p role="alert">The playbook could not load. Try another tradition or reload.</p> : book && <><Card tone="peach"><h2 className="text-2xl">{book.tradition}</h2><p className="mt-3 text-sm">{book.note}</p><p className="mt-3 text-sm">{book.timing}</p><p className="mt-3 text-xs text-ink-soft">Family customs, not medical guidance.</p></Card><Card><h2 className="text-xl">Make it your family&apos;s day</h2>{book.rituals.map(
            r => <div key={r.name} className="mt-4"><h3 className="font-semibold">{r.name}</h3><p className="mt-1 text-sm text-ink-soft">{r.what}</p></div>
          )}<h3 className="mt-5 font-semibold">A little planning list</h3><ul className="mt-2 list-disc space-y-2 pl-5 text-sm">{book.checklist.map(c => <li key={c}>{c}</li>)}</ul><h3 className="mt-5 font-semibold">Menu ideas</h3><ul className="mt-2 list-disc pl-5 text-sm">{book.menu_ideas.map(c => <li key={c}>{c}</li>)}</ul><Link
            className="mt-4 inline-block text-sm underline"
            href="/ask?q=What%20food%20safety%20should%20we%20consider%20for%20a%20pregnancy%20celebration%3F">Ask for sourced food safety guidance</Link></Card></>}<Card><h2 className="text-xl">An invitation from the heart</h2><form onSubmit={invitation} className="mt-4 space-y-3">{[
            ["hosts", "Host names", true],
            ["name", "Celebrating (optional)", false],
            ["date", "Date", true],
            ["time", "Time (optional)", false],
            ["venue", "Venue", true]
          ].map(
            ([name, label, required]) => <label className="block text-sm" key={String(name)}>{String(label)}<input className="field" name={String(name)} required={Boolean(required)} maxLength={120} /></label>
          )}<label className="flex gap-2 text-sm"><input type="checkbox" checked={sendConsent} onChange={e => setSendConsent(e.target.checked)} />I agree to send these details to make the invitation. They are not stored on the server.</label><button className="button" disabled={busy || !sendConsent}>{busy ? "Making your invitation…" : "Make invitation"}</button></form>{error && <p role="alert" className="mt-3">{error}</p>}</Card>{invite && <Card tone="blush"><h2 className="text-2xl">{invite.title}</h2><p className="mt-5 whitespace-pre-line leading-relaxed">{invite.body}</p><button
          type="button"
          className="button mt-5"
          onClick={async () => {
            try {
              downloadBlob(await cardImage(invite.title, [invite.body], "With joy and blessings"), "nestling-invitation.png");
            } catch {
              setError("Could not download the invitation in this browser.");
            }
          }}>Download invitation PNG</button></Card>}<CaptureBudget /><Link className="button w-full" href="/celebrate/capture">Plan a photoshoot with Capture</Link></div>
  );
}
