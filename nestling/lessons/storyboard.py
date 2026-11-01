"""Storyboard: sourced steps for one lesson, written by the MAIN model and checked in code.

    uv run python -m nestling.lessons.storyboard <lesson_id>

Passages come from the registered sources (Pinecone reads only). The model writes 4-5 step scenes;
code then checks that every (source_id, page_label) is one of the retrieved passages, that the step's
evidence quote really appears on that page, that the icon exists, and that there are no doses or
diagnoses. If the passages do not support the steps, nothing is written (`no_trusted_source`).
"""

import json
import re
import sys

from nestling import retrieval
from nestling.lessons import LESSONS, LESSONS_DIR, icon_names
from nestling.llm import MAIN, chat_json

MAX_CAPTION_WORDS = 8
MAX_NARRATION_WORDS = 12
MAX_SAFETY_WORDS = 12
NO_TRUSTED_SOURCE = "no_trusted_source"

_DOSE = re.compile(r"\b\d+(?:\.\d+)?\s*(?:mg|mcg|µg|ml|iu|units?|drops?|tablets?|tabs?|capsules?|teaspoons?|tsp)\b", re.I)
_DIAGNOSIS = re.compile(r"\b(?:diagnos\w*|your baby has|baby has (?:a |an )?\w+ (?:infection|disease|jaundice)|is suffering)\b", re.I)
_MEDICINE = re.compile(r"\b(?:paracetamol|ibuprofen|antibiotic\w*|ointment|syrup|medicine|medication|dose|dosage)\b", re.I)


def schema(icons: list[str]) -> dict:
    scene = {
        "type": "object",
        "properties": {
            "step_no": {"type": "integer"},
            "caption": {"type": "string"},
            "narration_line": {"type": "string"},
            "icon": {"type": "string", "enum": icons},
            "source_id": {"type": "string"},
            "page_label": {"type": "string"},
            "evidence": {"type": "string"},
            "safety_points": {"type": "array", "items": {"type": "string"}},
        },
        "required": ["step_no", "caption", "narration_line", "icon", "source_id", "page_label", "evidence", "safety_points"],
        "additionalProperties": False,
    }
    return {"type": "object",
            "properties": {"supported": {"type": "boolean"}, "scenes": {"type": "array", "items": scene}},
            "required": ["supported", "scenes"], "additionalProperties": False}


SYSTEM = """You write the script for "Little Lessons": a calm ~15-second step-card video that teaches first-time parents in India one newborn-care skill.

Rules:
- Use ONLY the passages given. Every step must be something the passages say. Do not add steps from general knowledge.
- If the passages do not clearly give 4 practical steps for this skill, reply {{"supported": false, "scenes": []}}.
- Otherwise write 4 or 5 scenes in order. For each scene:
  - caption: at most {cap} words, imperative and plain (e.g. "Support the head and neck").
  - narration_line: ONE short sentence, at most {nar} words, warm and spoken-style, saying the same thing as the caption.
  - icon: the single icon from the list that best matches the step.
  - source_id and page_label: copied exactly from the [source_id=... | page_label=...] label above the passage the step comes from (page_label is only the page, e.g. 114).
  - evidence: a short phrase (4 to 12 words) copied word for word from that passage.
  - safety_points: one or two short safety reminders (at most {saf} words each) taken from the passages, else [].
- Never give medicine doses or diagnose. Never mention medicines.
- Say "your baby" or "they", never "he" or "she". Speak to every parent (mothers, fathers, partners). The baby is always dressed, wrapped or in a nappy; do not describe a bare baby."""


def _norm(text: str) -> str:
    return re.sub(r"[^a-z0-9]+", " ", text.lower()).strip()


def _words(text: str) -> int:
    return len(text.split())


def validate(scenes: list[dict], hits: list[dict], icons: list[str]) -> list[str]:
    """Problems with the scenes (empty list = valid). Every check is code, not the model."""
    problems = []
    if not 4 <= len(scenes) <= 5:
        problems.append(f"need 4-5 scenes, got {len(scenes)}")
    pages: dict[tuple[str, str], str] = {}
    for h in hits:
        key = (h["source_id"], str(h.get("page_label") or h.get("page")))
        pages[key] = pages.get(key, "") + " " + _norm(h["chunk_text"])
    for i, s in enumerate(scenes, 1):
        tag = f"step {i}"
        if s.get("step_no") != i:
            problems.append(f"{tag}: step_no must be {i}")
        key = (s.get("source_id"), str(s.get("page_label")))
        if key not in pages:
            problems.append(f"{tag}: {key[0]} p. {key[1]} is not one of the retrieved passages")
        else:
            ev = _norm(s.get("evidence", ""))
            if len(ev.split()) < 3 or ev not in pages[key]:
                problems.append(f"{tag}: evidence quote not found on {key[0]} p. {key[1]}")
        if s.get("icon") not in icons:
            problems.append(f"{tag}: unknown icon {s.get('icon')!r}")
        if not s.get("caption") or _words(s["caption"]) > MAX_CAPTION_WORDS:
            problems.append(f"{tag}: caption must be 1-{MAX_CAPTION_WORDS} words")
        if not s.get("narration_line") or _words(s["narration_line"]) > MAX_NARRATION_WORDS:
            problems.append(f"{tag}: narration_line must be 1-{MAX_NARRATION_WORDS} words")
        for p in s.get("safety_points", []):
            if _words(p) > MAX_SAFETY_WORDS:
                problems.append(f"{tag}: safety point longer than {MAX_SAFETY_WORDS} words")
        text = " ".join([s.get("caption", ""), s.get("narration_line", ""), *s.get("safety_points", [])])
        for pattern, what in ((_DOSE, "a dose"), (_MEDICINE, "a medicine"), (_DIAGNOSIS, "a diagnosis")):
            if pattern.search(text):
                problems.append(f"{tag}: mentions {what}")
    return problems


def passages_text(hits: list[dict]) -> str:
    """Passages with machine-readable labels, so the model copies source_id and page_label exactly."""
    return "\n".join(
        f"\n[source_id={h['source_id']} | page_label={h.get('page_label') or h.get('page')}]\n{h['chunk_text']}" for h in hits)


def retrieve(lesson_id: str) -> list[dict]:
    """Passages for the lesson, de-duplicated across its queries."""
    cfg, seen, hits = LESSONS[lesson_id], set(), []
    for query in cfg["queries"]:
        for h in retrieval.search_reranked(query, source_ids=cfg["sources"], top_k=6, candidates=20, per_source=4):
            if h["id"] not in seen:
                seen.add(h["id"])
                hits.append(h)
    return hits


def build(lesson_id: str, hits: list[dict] | None = None, version: int = 1) -> dict:
    """{"status": "ok", "storyboard", "problems", "usage"} or {"status": "no_trusted_source", ...}. Writes nothing."""
    cfg, icons = LESSONS[lesson_id], icon_names()
    hits = retrieve(lesson_id) if hits is None else hits
    usage, problems, scenes = [], [], []
    user = f"Lesson: {cfg['title']}\nIcons you may use: {', '.join(icons)}\n\nPassages:{passages_text(hits) or ' (none found)'}"
    system = SYSTEM.format(cap=MAX_CAPTION_WORDS, nar=MAX_NARRATION_WORDS, saf=MAX_SAFETY_WORDS)
    for _ in range(3):  # two retries, with the code's complaints fed back
        prompt = user if not problems else user + "\n\nYour previous script had these problems, fix them:\n- " + "\n- ".join(problems)
        data, u, _ = chat_json(MAIN, system, prompt, schema(icons), max_tokens=3000)
        usage.append(u)
        if data is None or not data["supported"] or not data["scenes"]:
            return {"status": NO_TRUSTED_SOURCE, "storyboard": None, "problems": ["model: passages do not support the steps"], "usage": usage}
        scenes = data["scenes"]
        problems = validate(scenes, hits, icons)
        if not problems:
            break
    if problems:
        return {"status": NO_TRUSTED_SOURCE, "storyboard": None, "problems": problems, "usage": usage}
    clean = [{k: v for k, v in s.items() if k != "evidence"} for s in scenes]
    board = {"lesson_id": lesson_id, "title": cfg["title"], "version": version, "stage": cfg["stage"], "language": "en",
             "sources": sorted({s["source_id"] for s in clean}), "see_how": cfg["see_how"], "scenes": clean}
    return {"status": "ok", "storyboard": board, "problems": [], "usage": usage}


def _dump(board: dict) -> str:
    return json.dumps(board, indent=2, ensure_ascii=False) + "\n"


def write(lesson_id: str, board: dict) -> dict:
    """Save storyboard.json and return the board as written.

    Identical content: nothing changes and the review (and any approval) stays. Changed content: the
    version goes up by one and review.yaml is reset to unreviewed, so an approval never carries over
    to content nobody reviewed.
    """
    folder = LESSONS_DIR / lesson_id
    folder.mkdir(parents=True, exist_ok=True)
    path = folder / "storyboard.json"
    if path.exists():
        prior = json.loads(path.read_text(encoding="utf-8"))
        board = {**board, "version": prior["version"]}
        if path.read_text(encoding="utf-8") == _dump(board):
            return board
        board["version"] = prior["version"] + 1
    path.write_text(_dump(board), encoding="utf-8")
    scenes = "\n".join(f'  - {{step_no: {s["step_no"]}, passed: null, notes: ""}}' for s in board["scenes"])
    (folder / "review.yaml").write_text(f"lesson_id: {lesson_id}\nversion: {board['version']}\napproved: false\nreviewer: null\n"
                                        f"review_date: null\nscenes:\n{scenes}\n", encoding="utf-8")
    return board


if __name__ == "__main__":
    from dotenv import find_dotenv, load_dotenv

    load_dotenv(find_dotenv(usecwd=True))
    lesson = sys.argv[1] if len(sys.argv) > 1 else ""
    if lesson not in LESSONS:
        sys.exit(f"usage: python -m nestling.lessons.storyboard <{'|'.join(LESSONS)}>")
    out = build(lesson)
    tokens = sum(u["tokens_in"] + u["tokens_out"] for u in out["usage"])
    if out["status"] != "ok":
        print(f"{lesson}: {NO_TRUSTED_SOURCE} ({tokens} tokens)\n  " + "\n  ".join(out["problems"]))
        sys.exit(1)
    board = write(lesson, out["storyboard"])
    print(f"{lesson}: wrote storyboard v{board['version']} ({len(board['scenes'])} steps, {tokens} tokens)")
