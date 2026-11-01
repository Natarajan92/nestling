"""Render one lesson: cards -> narration -> stitch -> render_log.json.

    uv run python -m nestling.lessons.render <lesson_id>

Output goes to lessons/<lesson_id>/renders/ (gitignored). Rendering never approves a lesson:
that is review.yaml, filled in by a human.
"""

import json
import sys
from datetime import datetime, timezone

from nestling.lessons import LESSONS, LESSONS_DIR, library
from nestling.lessons.cards import render_cards
from nestling.lessons.narrate import COST_INR_PER_CHAR, narrate
from nestling.lessons.stitch import stitch


def render(lesson_id: str) -> dict:
    lesson = library.get(lesson_id)
    if not lesson:
        raise SystemExit(f"{lesson_id}: no storyboard.json yet (run nestling.lessons.storyboard first)")
    board, out = lesson["storyboard"], lesson["folder"] / "renders"
    review = lesson["review"]
    reviewed_on = str(review["review_date"]) if review.get("approved") is True and review.get("review_date") else None
    started = datetime.now(timezone.utc)
    cards = render_cards(board, out, reviewed_on)
    audio = narrate(board, out)
    made = stitch(cards, [out / f"card_{i}.mp3" for i in range(1, len(cards) + 1)],
                  [out / f"caption_{i}.png" for i in range(1, len(cards) + 1)], audio["seconds"], out)
    log = {"cost_inr": round(audio["characters_billed"] * COST_INR_PER_CHAR, 2), "seconds": round(made["seconds"], 1),
           "rendered_at": started.isoformat(timespec="seconds")}
    (out / "render_log.json").write_text(json.dumps(log, indent=2) + "\n", encoding="utf-8")
    return log


if __name__ == "__main__":
    from dotenv import find_dotenv, load_dotenv

    load_dotenv(find_dotenv(usecwd=True))
    lesson = sys.argv[1] if len(sys.argv) > 1 else ""
    if lesson not in LESSONS:
        sys.exit(f"usage: python -m nestling.lessons.render <{'|'.join(LESSONS)}>")
    print(lesson, render(lesson), "->", LESSONS_DIR / lesson / "renders" / "lesson.mp4")
