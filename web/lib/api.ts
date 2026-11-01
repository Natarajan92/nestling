// Typed fetch helpers for the Nestling API. The server stores nothing personal.
export const API_URL = (process.env.NEXT_PUBLIC_API_URL?.trim() || "http://localhost:8000").replace(/\/+$/, "");

export const DISCLAIMER = "Nestling offers general information from trusted sources and is not a substitute for medical advice. In an emergency, contact your doctor or the nearest hospital.";

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
  tip: {
    id: string;
    text: string;
    source: string;
    page: string | null;
    source_chip: SourceChipData;
  } | null;
  cards: string[];
  tradition_card: boolean;
  disclaimer: string;
};

export type Checklist = {
  title: string;
  when: string;
  sections: {
    name: string;
    items: {
      id: string;
      item: string;
      source: SourceChipData | null;
    }[];
  }[];
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
  see_how: {
    label: string;
    url: string;
    publisher: string;
  } | null;
  reviewed_on: string | null;
};

export type AskResponse = {
  answer: string;
  escalate: boolean;
  refused: boolean;
  route: string | null;
  guardian: {
    level: "calm" | "amber" | "red";
    rules_fired: string[];
    unsafe: string[];
  };
  sources: SourceChipData[];
  how_i_answered: string[];
  verification: {
    verdict: string;
    unsupported: string[];
  } | null;
  save: boolean;
  error: boolean;
  lesson?: Lesson | null;
};

class HttpError extends Error {
  constructor(path: string, readonly status: number) {
    super(`Nestling API ${path} failed (${status})`);
  }
}

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const res = await fetch(`${API_URL}${path}`, {
    ...init,
    signal: init?.signal ?? AbortSignal.timeout(90000)
  });

  if (init?.method === "DELETE" && res.status === 404)
    return {} as T;

  if (!res.ok)
    throw new HttpError(path, res.status);

  return (await res.json()) as T;
}

const post = (body: unknown): RequestInit => ({
  method: "POST",

  headers: {
    "Content-Type": "application/json"
  },

  body: JSON.stringify(body)
});

export const getToday = (profile: ProfileBody) => request<Today>("/api/today", post(profile));
export const getChecklist = () => request<Checklist>("/api/checklist");

export const getHealth = () => request<{
  ok: boolean;
  disclaimer: string;
}>("/api/health");

export const deleteVoice = (voiceId: string) => request<{
  deleted: string;
}>(`/api/voice/${encodeURIComponent(voiceId)}`, {
  method: "DELETE"
});

const isRecord = (value: unknown): value is Record<string, unknown> => value !== null && typeof value === "object" && !Array.isArray(value);
const isStrings = (value: unknown): value is string[] => Array.isArray(value) && value.every(item => typeof item === "string");
const isSource = (value: unknown) => isRecord(value) && typeof value.id === "string"
  && [value.title, value.publisher, value.url, value.page].every(item => item === null || typeof item === "string")
  && (value.year === null || typeof value.year === "string" || typeof value.year === "number");

/** Network JSON is untrusted at runtime; malformed answers use Ask's inline retry state. */
function isAskResponse(value: unknown): value is AskResponse {
  if (!isRecord(value) || typeof value.answer !== "string" || typeof value.escalate !== "boolean"
    || typeof value.refused !== "boolean" || typeof value.save !== "boolean" || typeof value.error !== "boolean"
    || !(value.route === null || typeof value.route === "string") || !isStrings(value.how_i_answered)
    || !Array.isArray(value.sources) || !value.sources.every(isSource)) return false;
  const guardian = value.guardian;
  if (!isRecord(guardian) || typeof guardian.level !== "string" || !["calm", "amber", "red"].includes(guardian.level)
    || !isStrings(guardian.rules_fired) || !isStrings(guardian.unsafe)) return false;
  const verification = value.verification;
  if (verification !== null && (!isRecord(verification) || typeof verification.verdict !== "string"
    || !isStrings(verification.unsupported))) return false;
  const lesson = value.lesson;
  if (lesson !== undefined && lesson !== null) {
    if (!isRecord(lesson) || ![lesson.lesson_id, lesson.title, lesson.stage, lesson.video_url, lesson.thumbnail_url].every(item => typeof item === "string")
      || typeof lesson.version !== "number" || !(lesson.reviewed_on === null || typeof lesson.reviewed_on === "string")
      || !Array.isArray(lesson.sources) || !lesson.sources.every(isSource)
      || !Array.isArray(lesson.steps) || !lesson.steps.every(step => isRecord(step) && typeof step.step_no === "number"
        && [step.caption, step.narration_line, step.icon].every(item => typeof item === "string") && isStrings(step.safety_points))
      || !(lesson.see_how === null || (isRecord(lesson.see_how)
        && [lesson.see_how.label, lesson.see_how.url, lesson.see_how.publisher].every(item => typeof item === "string")))) return false;
  }
  return true;
}

export async function askNestling(message: string, profile: ProfileBody | null, canSave: boolean): Promise<AskResponse> {
  const answer = await request<unknown>("/api/ask", post({ message, ...(profile ? { profile } : {}), can_save: canSave }));
  if (!isAskResponse(answer)) throw new Error("Nestling returned an invalid answer. Please try again.");
  return answer;
}

/** Lesson media paths come back relative (/media/lessons/...); make them absolute for the browser. */
export const mediaUrl = (u: string) => (/^https?:/.test(u) ? u : `${API_URL}${u}`);

/** A real empty library stays empty; unavailable services remain retryable errors. */
export const getLessons = () => request<Lesson[]>("/api/lessons");

export const getLesson = (id: string) => request<Lesson>(`/api/lessons/${encodeURIComponent(id)}`).catch(error => {
  if (error instanceof HttpError && error.status === 404) return null;
  throw error;
});

export type Playbook = {
  tradition: string;
  also_called: string[];
  timing: string;
  note: string;
  rituals: {
    name: string;
    what: string;
  }[];
  checklist: string[];
  menu_ideas: string[];
  health_note: string;
};

export type Invitation = {
  title: string;
  ceremony: string;
  body: string;
  tradition: string;
};

export const getPlaybook = (tradition: string) => request<Playbook>(`/api/celebrate/${encodeURIComponent(tradition)}`);

export const createInvitation = (
  body: {
    tradition: string;
    host_names: string;
    mother_name?: string;
    date_text: string;
    time_text?: string;
    venue: string;
  }
) => request<Invitation>("/api/celebrate/invitation", post(body));

export const askPolicy = (file: File, question: string) => {
  const body = new FormData();
  body.set("file", file);
  body.set("question", question);

  return request<{
    answer: string;
    quotes: {
      text: string;
      page_start: number;
      page_end: number;
    }[];
  }>("/api/policy/ask", {
    method: "POST",
    body
  });
};

export type StudioPackage = {
  studio_name: string;
  package_name: string | null;
  shoot_type: string;
  city: string | null;
  price_inr: number | null;
  price_text: string | null;
  price_assumptions: string[];
  inclusions: string[];
  extras: {
    name: string;
    price_inr: number | null;
  }[];
  duration_hours: number | null;
  photos_taken: number | null;
  edited_photos: number | null;
  delivery_days: number | null;
  album: {
    offered: boolean | null;
    price_inr: number | null;
    type: string | null;
    size: string | null;
    pages: number | null;
    photos: number | null;
  };
  frames: {
    size: string | null;
    count: number | null;
    price_inr: number | null;
  }[];
  casting: {
    offered: boolean | null;
    price_inr: number | null;
    type: string | null;
  };
  rating_summary: string | null;
  location: string | null;
  contact_url: string | null;
  source_url: string;
  checked_on: string;
  total_cost: number | null;
  cost_per_edited_photo: number | null;
};

export type CapturePicks = {
  edited_photos: number;
  album: boolean;
  album_pages: number;
  frames: number;
  frame_sizes: string;
  casting: boolean;
};

export type Estimate = {
  label: string;
  tiers: Record<string, {
    estimate: {
      low: number;
      high: number;
      typical: number;
    } | null;
    confidence?: string;
    message?: string;
    n_studios: number;
    not_listed_components?: string[];
    sources: {
      studio: string;
      package: string | null;
      url: string;
      checked_on: string;
      price_inr: number | null;
    }[];
  }>;
};

export const searchCapture = (city: string, shoot_type: string) => request<{
  packages: StudioPackage[];
  checked_on: string;
  note: string;
}>("/api/capture/search", post({
  city,
  shoot_type
}));

export const estimateCapture = (packages: StudioPackage[], picks: CapturePicks) => request<Estimate>("/api/capture/estimate", post({
  packages,
  album: picks.album,
  frames: picks.frames,
  casting: picks.casting
}));

export const draftQuote = (studio: string, shoot_type: string, picks: CapturePicks, date_text: string, city: string) => request<{
  draft: string;
  sent: boolean;
}>("/api/capture/quote", post({
  studio,
  shoot_type,
  picks,
  date_text: date_text || null,
  city
}));

const audioExtension = (blob: Blob) => blob.type.includes("mp4") ? "mp4" : blob.type.includes("ogg") ? "ogg" : "webm";

export const transcribe = (file: Blob) => {
  const body = new FormData();
  body.set("file", file, `journal.${audioExtension(file)}`);

  return request<{
    text: string;
  }>("/api/voice/transcribe", {
    method: "POST",
    body
  });
};

export const cloneVoice = (sample: Blob) => {
  const body = new FormData();
  body.set("sample", sample, `my-voice.${audioExtension(sample)}`);
  body.set("consent", "true");
  body.set("name", "My voice");

  return request<{
    voice_id: string;
  }>("/api/voice/clone", {
    method: "POST",
    body
  });
};

export async function speakLetter(text: string, voice_id: string | null) {
  const res = await fetch(`${API_URL}/api/voice/speak`, {
    ...post({
      text,
      voice_id
    }),

    signal: AbortSignal.timeout(90000)
  });

  if (!res.ok)
    throw new Error("Read aloud is unavailable. Please try again.");

  return res.blob();
}
