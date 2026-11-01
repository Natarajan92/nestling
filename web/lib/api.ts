// Typed fetch helpers for the Nestling API. The server stores nothing personal.
export const API_URL = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

export const DISCLAIMER =
  "Nestling offers general information from trusted sources and is not a substitute for medical advice. In an emergency, contact your doctor or the nearest hospital.";

export type SourceChipData = {
  id: string;
  title: string | null;
  publisher: string | null;
  year: number | string | null;
  url: string | null;
  page: string | null;
};

export type ProfileBody = {
  due_date: string | null;
  birth_date: string | null;
  tradition: string | null;
  diet: string | null;
  city: string | null;
  insurer: string | null;
  parent_role: string;
};

export type Stage = {
  life_stage: "pregnancy" | "postpartum" | "general";
  week: number | null;
  days?: number;
  trimester?: number;
  days_to_go?: number;
  baby_size?: string;
  baby_emoji?: string;
  progress?: number;
  baby_age_days?: number;
  baby_age_weeks?: number;
};

export type Today = {
  stage: Stage;
  tip: { id: string; text: string; source: string; page: string | null; source_chip: SourceChipData } | null;
  cards: string[];
  tradition_card: boolean;
  disclaimer: string;
};

export type Checklist = {
  title: string;
  when: string;
  sections: { name: string; items: { id: string; item: string; source: SourceChipData | null }[] }[];
};

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const res = await fetch(`${API_URL}${path}`, init);
  if (!res.ok) throw new Error(`Nestling API ${path} failed (${res.status})`);
  return (await res.json()) as T;
}

const post = (body: unknown): RequestInit => ({
  method: "POST",
  headers: { "Content-Type": "application/json" },
  body: JSON.stringify(body),
});

export const getToday = (profile: ProfileBody) => request<Today>("/api/today", post(profile));
export const getChecklist = () => request<Checklist>("/api/checklist");
export const getHealth = () => request<{ ok: boolean; disclaimer: string }>("/api/health");
export const deleteVoice = (voiceId: string) =>
  request<{ deleted: string }>(`/api/voice/${encodeURIComponent(voiceId)}`, { method: "DELETE" });
