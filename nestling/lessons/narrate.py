"""Narration: one ElevenLabs clip per card (card_<n>.mp3) and its length in seconds.

Reuses nestling/voice.py (calm premade voice). A clip is reused when its text has not changed
(narration.json), so a re-render only pays for the lines that changed.
"""

import json
import re
import subprocess
from pathlib import Path

from nestling import voice
from nestling.lessons.cards import card_plan
from nestling.lessons.stitch import find_ffmpeg

COST_INR_PER_CHAR = 0.02  # rough: ElevenLabs credits at about $0.24 per 1,000 characters
PACE = 1.1  # a touch quicker than natural, so a lesson stays near 20 seconds


def duration(mp3: Path) -> float:
    """Length of an audio file in seconds, read from ffmpeg's banner."""
    out = subprocess.run([find_ffmpeg(), "-hide_banner", "-i", str(mp3)], capture_output=True, text=True).stderr
    h, m, s = re.search(r"Duration: (\d+):(\d+):([\d.]+)", out).groups()
    return int(h) * 3600 + int(m) * 60 + float(s)


def narrate(board: dict, out_dir: Path, speak=None) -> dict:
    """Write card_<n>.mp3 for every card. Returns {"seconds": [per card], "characters_billed": int}."""
    speak = speak or (lambda text: voice.speak(text, speed=PACE))
    out_dir.mkdir(parents=True, exist_ok=True)
    log_path = out_dir / "narration.json"
    done = json.loads(log_path.read_text(encoding="utf-8")) if log_path.exists() else {}
    seconds, billed, log = [], 0, {}
    for n, card in enumerate(card_plan(board), 1):
        mp3, text = out_dir / f"card_{n}.mp3", card["narration"]
        prior = done.get(str(n), {})
        if mp3.exists() and prior.get("text") == text and prior.get("pace") == PACE:
            length = prior["seconds"]
        else:
            mp3.write_bytes(speak(text))
            length, billed = duration(mp3), billed + len(text)
        log[str(n)] = {"text": text, "pace": PACE, "seconds": length}
        seconds.append(length)
    log_path.write_text(json.dumps(log, indent=2), encoding="utf-8")
    return {"seconds": seconds, "characters_billed": billed}
