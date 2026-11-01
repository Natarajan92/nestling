"""Library: the lessons on disk and which of them a parent may see (runtime lookup, no generation).

A lesson is approved only when its review.yaml says `approved: true`, the review's version equals the
storyboard's version, every scene is `passed: true` and renders/lesson.mp4 exists. Anything else is
never shown (constitution rule 8).
"""

import json
import re
from pathlib import Path

import yaml

from nestling.lessons import LESSONS_DIR


def _read_yaml(path: Path) -> dict:
    return yaml.safe_load(path.read_text(encoding="utf-8")) if path.exists() else {}


def _load(folder: Path) -> dict | None:
    board_path = folder / "storyboard.json"
    if not board_path.exists():
        return None
    return {
        "lesson_id": folder.name,
        "storyboard": json.loads(board_path.read_text(encoding="utf-8")),
        "review": _read_yaml(folder / "review.yaml"),
        "checklist": _read_yaml(folder / "checklist.yaml"),
        "phrasings": (_read_yaml(folder / "phrasings.yaml").get("phrasings") or []),
        "folder": folder,
    }


def load_all(root: Path | None = None) -> list[dict]:
    """Every lesson that has a storyboard, in folder-name order."""
    root = root or LESSONS_DIR
    return [lesson for folder in sorted(root.glob("*/")) if (lesson := _load(folder))]


def _approved(lesson: dict) -> bool:
    review, board = lesson["review"], lesson["storyboard"]
    return bool(
        review.get("approved") is True
        and review.get("version") == board.get("version")
        and review.get("scenes")
        and len(review["scenes"]) == len(board["scenes"])
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
