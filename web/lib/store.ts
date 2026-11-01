"use client";
// All browser state for Nestling. Every localStorage access is wrapped in try/catch.
import { useCallback, useMemo, useSyncExternalStore } from "react";

import { deleteVoice, type ProfileBody, type StudioPackage } from "./api";

// Every browser storage key MUST start with PREFIX: "Delete everything" clears by this prefix.
const PREFIX = "nestling:";

const KEYS = {
  profile: `${PREFIX}profile`,
  ticks: `${PREFIX}ticks`,
  voice: `${PREFIX}voice_id`,
  journal: `${PREFIX}journal`,
  letters: `${PREFIX}letters`,
  capture: `${PREFIX}capture`,
  voiceCleanupError: `${PREFIX}voice_cleanup_error`
} as const;

const SSR = "\u0000ssr"; // server snapshot sentinel: "not read yet"

export type Consent = {
  store_profile: boolean;
  save_journal: boolean;
  voice: boolean;
};

export type Profile = ProfileBody & {
  consent: Consent;
};

const listeners = new Set<() => void>();
const emit = () => listeners.forEach(l => l());
let privacyEpoch = 0;
const resetListeners = new Set<() => void>();
export const getPrivacyEpoch = () => privacyEpoch;
export function subscribePrivacyReset(listener: () => void) {
  resetListeners.add(listener);
  return () => { resetListeners.delete(listener); };
}
// If storage is unavailable, keep failed remote cleanup recoverable in this tab.
let retryVoiceId: string | null = null;
let voiceCleanupError = "";

function read(key: string): string {
  try {
    return localStorage.getItem(key) ?? "";
  } catch {
    return "";
  }
}

function write(key: string, value: string | null) {
  try {
    if (value === null)
      localStorage.removeItem(key);
    else
      localStorage.setItem(key, value);
  } catch {
    return false;
  }

  emit();
  return true;
}

function subscribe(cb: () => void) {
  listeners.add(cb);
  window.addEventListener("storage", cb);

  return () => {
    listeners.delete(cb);
    window.removeEventListener("storage", cb);
  };
}

function parse<T>(raw: string, fallback: T): T {
  try {
    return raw ? (JSON.parse(raw) as T) : fallback;
  } catch {
    return fallback;
  }
}

function useRaw(key: string) {
  return useSyncExternalStore(subscribe, () => read(key), () => SSR);
}

/** The fields the API accepts (everything except consent). */
export function profileBody(p: Profile): ProfileBody {
  const {
    due_date,
    birth_date,
    tradition,
    diet,
    city,
    insurer,
    parent_role
  } = p;

  return {
    due_date,
    birth_date,
    tradition,
    diet,
    city,
    insurer,
    parent_role
  };
}

/** `ready` is false until the browser has been read (avoids a flash of the wrong screen). */
export function useProfile() {
  const raw = useRaw(KEYS.profile);
  const profile = useMemo(() => (raw === SSR ? null : parse<Profile | null>(raw, null)), [raw]);

  return {
    profile,
    ready: raw !== SSR
  };
}

export const saveProfile = (p: Profile) => write(KEYS.profile, JSON.stringify(p));

export function useTicks() {
  const raw = useRaw(KEYS.ticks);
  const ticks = useMemo(() => new Set(raw === SSR ? [] : parse<string[]>(raw, [])), [raw]);

  const toggle = useCallback((id: string) => {
    const next = new Set(parse<string[]>(read(KEYS.ticks), []));

    if (!next.delete(id))
      next.add(id);

    write(KEYS.ticks, JSON.stringify([...next]));
  }, []);

  return {
    ticks,
    toggle
  };
}

export type JournalEntry = {
  id: string;
  saved_at: string;
  text: string;
};

/** Journal entries offered by Ask (`save` = true); kept only in this browser. */
export function addJournalEntry(text: string) {
  const all = parse<JournalEntry[]>(read(KEYS.journal), []);

  all.push({
    id: crypto.randomUUID(),
    saved_at: new Date().toISOString(),
    text
  });

  return write(KEYS.journal, JSON.stringify(all));
}

export const getVoiceId = () => read(KEYS.voice) || retryVoiceId;
export function setVoiceId(id: string | null) {
  const saved = write(KEYS.voice, id);
  retryVoiceId = saved ? null : id;
  if (!id) {
    voiceCleanupError = "";
    write(KEYS.voiceCleanupError, null);
  }
  emit();
  return saved;
}

export function useVoiceId() {
  const raw = useSyncExternalStore(subscribe, () => getVoiceId() || "", () => SSR);
  return raw === SSR ? null : raw || null;
}

export function useVoiceCleanupError() {
  return useSyncExternalStore(subscribe, () => read(KEYS.voiceCleanupError) || voiceCleanupError, () => "");
}

/** A late clone must be removed remotely, even after its page has gone away. */
export async function finishVoiceClone(id: string, epoch: number, active: boolean) {
  if (active && epoch === privacyEpoch && setVoiceId(id)) return "ready";
  try {
    await deleteVoice(id);
    if (getVoiceId() === id) setVoiceId(null);
    return "discarded";
  } catch {
    setVoiceId(id);
    const message = "A voice created by an earlier request could not be deleted. Keep this tab open and retry Delete everything in Settings.";
    voiceCleanupError = write(KEYS.voiceCleanupError, message) ? "" : message;
    emit();
    return "retry";
  }
}

export function useJournal() {
  const raw = useRaw(KEYS.journal);
  return useMemo(() => parse<JournalEntry[]>(raw === SSR ? "" : raw, []), [raw]);
}

export function removeJournalEntry(id: string) {
  write(KEYS.journal, JSON.stringify(parse<JournalEntry[]>(read(KEYS.journal), []).filter(e => e.id !== id)));
}

export type Letter = JournalEntry & {
  title: string;
};

export function useLetters() {
  const raw = useRaw(KEYS.letters);
  return useMemo(() => parse<Letter[]>(raw === SSR ? "" : raw, []), [raw]);
}

export function addLetter(title: string, text: string) {
  const all = parse<Letter[]>(read(KEYS.letters), []);

  all.push({
    id: crypto.randomUUID(),
    title,
    text,
    saved_at: new Date().toISOString()
  });

  return write(KEYS.letters, JSON.stringify(all));
}

export function removeLetter(id: string) {
  write(KEYS.letters, JSON.stringify(parse<Letter[]>(read(KEYS.letters), []).filter(e => e.id !== id)));
}

export type SavedCapture = {
  package: StudioPackage;
  quote: string;
  budget: number | null;
  saved_at: string;
};

export function useCapture() {
  const raw = useRaw(KEYS.capture);
  return useMemo(() => parse<SavedCapture | null>(raw === SSR ? "" : raw, null), [raw]);
}

export const saveCapture = (value: SavedCapture | null) => write(KEYS.capture, value ? JSON.stringify(value) : null);

/** Clears everything Nestling keeps in this browser, and deletes a cloned voice if one exists. */
export async function deleteEverything(): Promise<{
  voiceDeleted: boolean;
  voiceError: boolean;
}> {
  const voiceId = getVoiceId();
  let voiceDeleted = false;
  let voiceError = false;
  privacyEpoch++;
  resetListeners.forEach(listener => listener());
  retryVoiceId = null;
  voiceCleanupError = "";

  try {
    const mine: string[] = [];

    for (let i = 0; i < localStorage.length; i++) {
      const k = localStorage.key(i);

      if (k?.startsWith(PREFIX))
        mine.push(k);
    }

    for (const k of mine) localStorage.removeItem(k);
  } catch {}

  emit();

  // Clear local data before waiting: a late clone cleanup may need to retain a
  // new retry ID, which must not be removed by this already-started deletion.
  if (voiceId) {
    try {
      await deleteVoice(voiceId);
      voiceDeleted = true;
    } catch {
      voiceError = true;
      setVoiceId(voiceId);
    }
  }

  return {
    voiceDeleted,
    voiceError
  };
}
