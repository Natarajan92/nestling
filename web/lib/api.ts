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

export type LessonStep = {
  step_no: number;
  caption: string;
  narration_line: string;
  icon: string;
  safety_points: string[];
};

/** The shared "API lesson payload" (/api/lessons, /api/lessons/{id}, `lesson` of /api/ask). */
export type Lesson = {
  lesson_id: string;
  title: string;
  version: number;
  stage: "before_birth" | "first_weeks";
  video_url: string;
  thumbnail_url: string;
  steps: LessonStep[];
  sources: SourceChipData[];
  see_how: { label: string; url: string; publisher: string } | null;
  reviewed_on: string | null;
};

export type AskResponse = {
  answer: string;
  escalate: boolean;
  refused: boolean;
  route: string | null;
  guardian: { level: "calm" | "amber" | "red"; rules_fired: string[]; unsafe: string[] };
  sources: SourceChipData[];
  how_i_answered: string[];
  verification: { verdict: string; unsupported: string[] } | null;
  save: boolean;
  error: boolean;
  lesson?: Lesson | null;
};

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const res = await fetch(`${API_URL}${path}`, { ...init, signal: init?.signal ?? AbortSignal.timeout(90000) });
  if (init?.method === "DELETE" && res.status === 404) return {} as T;
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
export const askNestling = (message: string, profile: ProfileBody | null, canSave: boolean) =>
  request<AskResponse>("/api/ask", post({ message, ...(profile ? { profile } : {}), can_save: canSave }));

/** Lesson media paths come back relative (/media/lessons/...); make them absolute for the browser. */
export const mediaUrl = (u: string) => (/^https?:/.test(u) ? u : `${API_URL}${u}`);

/** A missing or failing lessons endpoint means "no approved lessons yet": an empty library. */
export const getLessons = () => request<Lesson[]>("/api/lessons").catch(() => [] as Lesson[]);
export const getLesson = (id: string) =>
  request<Lesson>(`/api/lessons/${encodeURIComponent(id)}`).catch(() => null);

export type Playbook = { tradition: string; also_called: string[]; timing: string; note: string; rituals: { name: string; what: string }[]; checklist: string[]; menu_ideas: string[]; health_note: string };
export type Invitation = { title: string; ceremony: string; body: string; tradition: string };
export const getPlaybook = (tradition: string) => request<Playbook>(`/api/celebrate/${encodeURIComponent(tradition)}`);
export const createInvitation = (body: { tradition: string; host_names: string; mother_name?: string; date_text: string; time_text?: string; venue: string }) => request<Invitation>("/api/celebrate/invitation", post(body));
export const askPolicy = (file: File, question: string) => {
  const body = new FormData(); body.set("file", file); body.set("question", question);
  return request<{ answer: string; quotes: { text: string; page_start: number; page_end: number }[] }>("/api/policy/ask", { method: "POST", body });
};
export type StudioPackage = {
  studio_name: string; package_name: string | null; shoot_type: string; city: string | null;
  price_inr: number | null; price_text: string | null; price_assumptions: string[]; inclusions: string[];
  extras: { name: string; price_inr: number | null }[]; duration_hours: number | null;
  photos_taken: number | null; edited_photos: number | null; delivery_days: number | null;
  album: { offered: boolean | null; price_inr: number | null; type: string | null; size: string | null; pages: number | null; photos: number | null };
  frames: { size: string | null; count: number | null; price_inr: number | null }[];
  casting: { offered: boolean | null; price_inr: number | null; type: string | null };
  rating_summary: string | null; location: string | null; contact_url: string | null; source_url: string;
  checked_on: string; total_cost: number | null; cost_per_edited_photo: number | null;
};
export type CapturePicks = { edited_photos: number; album: boolean; album_pages: number; frames: number; frame_sizes: string; casting: boolean };
export type Estimate = { label: string; tiers: Record<string, { estimate: { low: number; high: number; typical: number } | null; confidence?: string; message?: string; n_studios: number; not_listed_components?: string[]; sources: { studio: string; package: string | null; url: string; checked_on: string; price_inr: number | null }[] }> };
export const searchCapture = (city: string, shoot_type: string) => request<{ packages: StudioPackage[]; checked_on: string; note: string }>("/api/capture/search", post({ city, shoot_type }));
export const estimateCapture = (packages: StudioPackage[], picks: CapturePicks) => request<Estimate>("/api/capture/estimate", post({ packages, album: picks.album, frames: picks.frames, casting: picks.casting }));
export const draftQuote = (studio: string, shoot_type: string, picks: CapturePicks, date_text: string, city: string) => request<{ draft: string; sent: boolean }>("/api/capture/quote", post({ studio, shoot_type, picks, date_text: date_text || null, city }));
export const transcribe = (file: Blob) => { const body = new FormData(); body.set("file", file, "journal.webm"); return request<{ text: string }>("/api/voice/transcribe", { method: "POST", body }); };
export const cloneVoice = (sample: Blob) => { const body = new FormData(); body.set("sample", sample, "my-voice.webm"); body.set("consent", "true"); body.set("name", "My voice"); return request<{ voice_id: string }>("/api/voice/clone", { method: "POST", body }); };
export async function speakLetter(text: string, voice_id: string | null) {
  const res = await fetch(`${API_URL}/api/voice/speak`, { ...post({ text, voice_id }), signal: AbortSignal.timeout(90000) });
  if (!res.ok) throw new Error("Read aloud is unavailable. Please try again.");
  return res.blob();
}
