"""Library: the lessons on disk and which of them a parent may see (runtime lookup, no generation).

A lesson is approved only when its review.yaml says `approved: true`, the review's version equals the
storyboard's version, every scene is `passed: true` and renders/lesson.mp4 exists. Anything else is
never shown (constitution rule 8).
"""

import json
import re
from pathlib import Path

import yaml
from langsmith import traceable

from nestling import llm, retrieval
from nestling.lessons import LESSONS, LESSONS_DIR

MATCH_PROMPT_VERSION = "lesson-match-v2-prenatal"


def _read_yaml(path: Path) -> dict:
    return yaml.safe_load(path.read_text(encoding="utf-8")) if path.exists() else {}


def _load(folder: Path) -> dict | None:
    board_path = folder / "storyboard.json"
    if not board_path.exists():
        return None
    try:
        return {
        "lesson_id": folder.name,
        "storyboard": json.loads(board_path.read_text(encoding="utf-8")),
        "review": _read_yaml(folder / "review.yaml"),
        "checklist": _read_yaml(folder / "checklist.yaml"),
        "phrasings": (_read_yaml(folder / "phrasings.yaml").get("phrasings") or []),
        "folder": folder,
        }
    except (OSError, ValueError, yaml.YAMLError):
        return None  # damaged content fails closed


def load_all(root: Path | None = None) -> list[dict]:
    """Every lesson that has a storyboard, in folder-name order."""
    root = root or LESSONS_DIR
    return [lesson for folder in sorted(root.glob("*/")) if (lesson := _load(folder))]


def _approved(lesson: dict) -> bool:
    review, board = lesson["review"], lesson["storyboard"]
    return bool(
        review.get("approved") is True
        and review.get("lesson_id") == board.get("lesson_id") == lesson["lesson_id"]
        and bool(review.get("reviewer")) and bool(review.get("review_date"))
        and review.get("version") == board.get("version")
        and review.get("scenes")
        and len(review["scenes"]) == len(board["scenes"])
        and [s.get("step_no") for s in review["scenes"]] == [s.get("step_no") for s in board["scenes"]]
        and all(s.get("passed") is True for s in review["scenes"])
        and (lesson["folder"] / "renders" / "lesson.mp4").exists()
    )


def approved(root: Path | None = None) -> list[dict]:
    """Approved lessons only."""
    return [lesson for lesson in load_all(root) if _approved(lesson)]


def get(lesson_id: str, root: Path | None = None) -> dict | None:
    """The lesson (storyboard, review, checklist, phrasings, folder) or None if it does not exist."""
    root = root or LESSONS_DIR
    if not re.fullmatch(r"[a-z0-9_]+", lesson_id or ""):
        return None
    return _load(root / lesson_id) if (root / lesson_id).is_dir() else None


def is_approved(lesson_id: str, root: Path | None = None) -> bool:
    lesson = get(lesson_id, root)
    return bool(lesson) and _approved(lesson)


def payload(lesson_id: str, root: Path | None = None) -> dict | None:
    """The shared public payload, only for a current human-reviewed lesson."""
    lesson = get(lesson_id, root)
    if not lesson or not _approved(lesson):
        return None
    board, review = lesson["storyboard"], lesson["review"]
    registry = retrieval.load_registry()
    source_ids = list(dict.fromkeys(s["source_id"] for s in board["scenes"]))
    if not source_ids or any(sid not in registry for sid in source_ids):
        return None
    chips = []
    for sid in source_ids:
        source = registry[sid]
        pages = list(dict.fromkeys(str(s["page_label"]) for s in board["scenes"] if s["source_id"] == sid))
        chips.append({"id": sid, "title": source.get("title"), "publisher": source.get("publisher"),
                      "year": source.get("year"), "url": source.get("url") or source.get("pdf"), "page": ", ".join(pages)})
    return {"lesson_id": lesson_id, "title": board["title"], "version": board["version"], "stage": board["stage"],
            "video_url": f"/media/lessons/{lesson_id}/lesson.mp4",
            "thumbnail_url": f"/media/lessons/{lesson_id}/thumbnail.jpg",
            "steps": [{key: scene[key] for key in ("step_no", "caption", "narration_line", "icon", "safety_points")}
                      for scene in board["scenes"]], "sources": chips, "see_how": board.get("see_how"),
            "reviewed_on": str(review["review_date"])}


def _catalogue(root: Path | None = None) -> list[dict]:
    """Include unfinished lessons: a matching topic can still be a review/source gap."""
    root = root or LESSONS_DIR
    return [{"lesson_id": lesson_id, "title": info["title"], "stage": info["stage"],
             "phrasings": _read_yaml(root / lesson_id / "phrasings.yaml").get("phrasings") or []}
            for lesson_id, info in sorted(LESSONS.items())]


@traceable(name="lesson_match", run_type="chain")
def match(question: str, *, usage: list | None = None) -> dict:
    """Closed-set FAST classifier. Topics are code-owned labels, never question text."""
    schema = {"type": "object", "properties": {"lesson_id": {"type": "string", "enum": [*sorted(LESSONS), "none"]}},
              "required": ["lesson_id"], "additionalProperties": False}
    system = ("Match a practical before-birth preparation or newborn-care how-to to one lesson from this catalogue. Symptoms, danger signs, general "
              "questions and unrelated requests are none. Never answer the question. Return the lesson_id only.\n" +
              json.dumps(_catalogue(), ensure_ascii=False))
    try:
        data, used, _ = llm.chat_json(llm.FAST, system, question, schema, max_tokens=200)
        if usage is not None and used:
            usage.append(used)
        lesson_id = data.get("lesson_id") if data else None
    except Exception:
        lesson_id = None
    lesson_id = lesson_id if lesson_id in LESSONS else None
    return {"lesson_id": lesson_id, "topic": lesson_id or "newborn_care"}


def index_phrasings(dry_run: bool = True, root: Path | None = None) -> dict:
    """Prepare integrated-embedding records; the only write target is the lessons namespace."""
    records = [{"_id": f"{item['lesson_id']}:phrasing:{n}", "lesson_id": item["lesson_id"],
                "title": item["title"], "stage": item["stage"], "chunk_text": text}
               for item in _catalogue(root) for n, text in enumerate(item["phrasings"], 1)]
    if not dry_run:
        index = retrieval.get_index(create=False)
        for start in range(0, len(records), retrieval.UPSERT_BATCH):
            index.documents.upsert(namespace="lessons", documents=records[start:start + retrieval.UPSERT_BATCH])
    return {"namespace": "lessons", "dry_run": dry_run, "records": records}
