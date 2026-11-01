"use client";
import { useRouter } from "next/navigation";
import { useState } from "react";
import { AnimatePresence, motion, useReducedMotion } from "motion/react";
import Card from "@/components/Card";
import { saveProfile, useProfile, type Profile } from "@/lib/store";

type Draft = {
  stage: "expecting" | "born";
  date: string;
  tradition: string;
  diet: string;
  city: string;
  insurer: string;
  parent_role: string;
  consent: boolean;
};

const TRADITIONS = [
  ["tamil_nadu", "Tamil Nadu"],
  ["kerala", "Kerala"],
  ["karnataka", "Karnataka"],
  ["other", "Other"],
];
const DIETS = [
  ["veg", "Vegetarian"],
  ["egg", "Eggetarian"],
  ["non_veg", "Non-vegetarian"],
  ["jain", "Jain"],
];
const ROLES = [
  ["mother", "I am the mother"],
  ["father", "I am the father"],
  ["partner", "I am a partner or family"],
];
const STEPS = 7;

function Choices({ options, value, onPick }: { options: string[][]; value: string; onPick: (v: string) => void }) {
  return (
    <div role="radiogroup" className="mt-6 flex flex-col gap-3">
      {options.map(([v, label]) => (
        <button
          key={v}
          type="button"
          role="radio"
          aria-checked={value === v}
          onClick={() => onPick(v)}
          className={`rounded-card border-2 px-5 py-4 text-left text-lg transition-colors ${
            value === v ? "border-peach bg-peach/30" : "border-transparent bg-white shadow-soft"
          }`}
        >
          {label}
        </button>
      ))}
    </div>
  );
}

const inputCls = "mt-6 w-full rounded-card border-2 border-peach/40 bg-white px-5 py-4 text-lg";

export default function WelcomePage() {
  const { profile, ready } = useProfile();
  if (!ready) return <p>Loading your answers…</p>;
  return <WelcomeForm profile={profile} />;
}

function WelcomeForm({ profile }: { profile: Profile | null }) {
  const reduced = useReducedMotion();
  const router = useRouter();
  const [step, setStep] = useState(0);
  const [d, setD] = useState<Draft>({
    stage: profile?.birth_date ? "born" : "expecting", date: profile?.birth_date ?? profile?.due_date ?? "", tradition: profile?.tradition ?? "", diet: profile?.diet ?? "", city: profile?.city ?? "", insurer: profile?.insurer ?? "", parent_role: profile?.parent_role ?? "", consent: profile?.consent.store_profile ?? false,
  });
  const set = (patch: Partial<Draft>) => setD((p) => ({ ...p, ...patch }));

  const canNext = [
    d.date !== "",
    d.tradition !== "",
    d.diet !== "",
    d.city.trim() !== "",
    true, // insurer is optional
    d.parent_role !== "",
    d.consent,
  ][step];

  function finish() {
    saveProfile({
      due_date: d.stage === "expecting" ? d.date : null,
      birth_date: d.stage === "born" ? d.date : null,
      tradition: d.tradition,
      diet: d.diet,
      city: d.city.trim(),
      insurer: d.insurer.trim() || null,
      parent_role: d.parent_role,
      consent: { store_profile: true, save_journal: profile?.consent.save_journal ?? false, voice: profile?.consent.voice ?? false },
    });
    router.replace("/");
  }

  const next = () => (step === STEPS - 1 ? finish() : setStep(step + 1));

  const screens = [
    <div key="when">
      <h1 className="text-3xl font-semibold">{d.stage === "expecting" ? "When is your little one due?" : "When was your baby born?"}</h1>
      <input
        type="date"
        aria-label={d.stage === "expecting" ? "Due date" : "Birth date"}
        value={d.date}
        onChange={(e) => set({ date: e.target.value })}
        className={inputCls}
      />
      <button
        type="button"
        className="mt-4 text-sm text-ink-soft underline"
        onClick={() => set({ stage: d.stage === "expecting" ? "born" : "expecting", date: "" })}
      >
        {d.stage === "expecting" ? "My baby is already here" : "I am still expecting"}
      </button>
    </div>,
    <div key="tradition">
      <h1 className="text-3xl font-semibold">Which tradition is your family&apos;s?</h1>
      <Choices options={TRADITIONS} value={d.tradition} onPick={(tradition) => set({ tradition })} />
    </div>,
    <div key="diet">
      <h1 className="text-3xl font-semibold">What are your food habits?</h1>
      <Choices options={DIETS} value={d.diet} onPick={(diet) => set({ diet })} />
    </div>,
    <div key="city">
      <h1 className="text-3xl font-semibold">Which city are you in?</h1>
      <input
        aria-label="City" autoComplete="off" placeholder="Bengaluru" value={d.city}
        onChange={(e) => set({ city: e.target.value })} className={inputCls}
      />
    </div>,
    <div key="insurer">
      <h1 className="text-3xl font-semibold">Who is your health insurer?</h1>
      <p className="mt-2 text-ink-soft">Optional. It helps with questions about cover. You can skip this.</p>
      <input
        aria-label="Insurer (optional)" autoComplete="off" placeholder="Optional" value={d.insurer}
        onChange={(e) => set({ insurer: e.target.value })} className={inputCls}
      />
    </div>,
    <div key="role">
      <h1 className="text-3xl font-semibold">Who is using Nestling?</h1>
      <Choices options={ROLES} value={d.parent_role} onPick={(parent_role) => set({ parent_role })} />
    </div>,
    <div key="consent">
      <h1 className="text-3xl font-semibold">One last thing: your privacy</h1>
      <Card className="mt-6 space-y-3 text-ink">
        <p><strong>Stored in this browser only:</strong> your answers here, your checklist ticks, and later your journal, letters and voice ID.</p>
        <p><strong>Sent to our server:</strong> your due or birth date, tradition, food habits, city, insurer and role, only when you ask for today&apos;s tip or ask a question. Nothing is saved there, and it is never put in logs.</p>
        <p>You can wipe everything any time with <em>Delete everything</em> in Settings.</p>
      </Card>
      <label className="mt-6 flex items-start gap-3 text-lg">
        <input
          type="checkbox" checked={d.consent} onChange={(e) => set({ consent: e.target.checked })}
          className="mt-1.5 h-5 w-5 accent-[var(--peach)]"
        />
        <span>I understand, and I am happy for Nestling to keep this in my browser.</span>
      </label>
    </div>,
  ];

  return (
    <div className="flex min-h-[80dvh] flex-col">
      <div className="mb-8 flex items-center gap-3">
        <span className="font-display text-xl font-semibold">Nestling</span>
        <div className="h-1.5 flex-1 overflow-hidden rounded-full bg-peach/30" role="progressbar" aria-valuemin={1} aria-valuemax={STEPS} aria-valuenow={step + 1}>
          <div className="h-full rounded-full bg-peach transition-all duration-500" style={{ width: `${((step + 1) / STEPS) * 100}%` }} />
        </div>
      </div>
      <div className="flex-1">
        <AnimatePresence mode="wait">
          <motion.div key={step} initial={reduced ? false : { opacity: 0, y: 16 }} animate={{ opacity: 1, y: 0 }} exit={{ opacity: 0, y: reduced ? 0 : -8 }} transition={{ duration: reduced ? 0 : 0.3 }}>
            {screens[step]}
          </motion.div>
        </AnimatePresence>
      </div>
      <div className="mt-8 flex gap-3">
        {step > 0 && (
          <button type="button" onClick={() => setStep(step - 1)} className="rounded-full px-6 py-3 text-ink-soft">
            Back
          </button>
        )}
        <button
          type="button" disabled={!canNext} onClick={next}
          className="flex-1 rounded-full bg-peach px-6 py-3 text-lg font-semibold shadow-soft disabled:opacity-40"
        >
          {step === STEPS - 1 ? "Start Nestling" : step === 4 && !d.insurer.trim() ? "Skip" : "Continue"}
        </button>
      </div>
    </div>
  );
}
