"""Stitch: cards + narration + captions -> a vertical H.264/AAC MP4 and a thumbnail, with ffmpeg.

Each card stays on screen for its narration plus a short pause (at least MIN_CARD seconds), with a slow
zoom, slide transitions between cards and the narration burned in as a caption. No music.
`build_command` is pure (it only builds the argument list); `stitch` runs it.
"""

import glob
import os
import shutil
import subprocess
from pathlib import Path

FPS = 30
MIN_CARD = 2.0
LEAD = 0.2   # narration starts a moment after the card appears
PAUSE = 0.4  # breathing room after the narration ends
FADE = 0.45   # transition length
ZOOM = 0.05   # total slow zoom per card
CAPTION_Y = 1672


def find_ffmpeg() -> str:
    """ffmpeg on PATH, else the winget (Gyan.FFmpeg) install, else a clear error."""
    found = shutil.which("ffmpeg")
    if found:
        return found
    local = os.environ.get("LOCALAPPDATA", "")
    candidates = [os.path.join(local, "Microsoft", "WinGet", "Links", "ffmpeg.exe"),
                  *glob.glob(os.path.join(local, "Microsoft", "WinGet", "Packages", "Gyan.FFmpeg*", "**", "ffmpeg.exe"), recursive=True)]
    for path in candidates:
        if os.path.isfile(path):
            return path
    raise RuntimeError("ffmpeg was not found. Install it (winget install Gyan.FFmpeg) or put ffmpeg on PATH.")


def card_seconds(narration_seconds: list[float]) -> list[float]:
    """How long each card is on screen: lead + narration + pause, never under MIN_CARD."""
    return [round(max(MIN_CARD, s + LEAD + PAUSE), 3) for s in narration_seconds]


def build_command(ffmpeg: str, cards: list[Path], audios: list[Path], captions: list[Path],
                  narration_seconds: list[float], out: Path) -> list[str]:
    """The ffmpeg argument list. `cards`, `audios` and `captions` are parallel (title, steps..., closing)."""
    n = len(cards)
    assert n == len(audios) == len(captions) == len(narration_seconds) and n >= 2
    shown = card_seconds(narration_seconds)
    lengths = [d + FADE for d in shown[:-1]] + [shown[-1]]  # clips overlap by FADE inside xfade
    starts = [sum(shown[:i]) for i in range(n)]
    total = sum(shown)

    cmd = [ffmpeg, "-y", "-hide_banner", "-loglevel", "error"]
    for card, length in zip(cards, lengths):
        cmd += ["-loop", "1", "-framerate", str(FPS), "-t", f"{length:.3f}", "-i", str(card)]
    for audio in audios:
        cmd += ["-i", str(audio)]
    for cap, d in zip(captions, shown):
        cmd += ["-loop", "1", "-framerate", str(FPS), "-t", f"{d:.3f}", "-i", str(cap)]

    f = []
    for i, length in enumerate(lengths):
        frames = max(1, round(length * FPS))
        f.append(f"[{i}:v]scale=2160:3840,zoompan=z='1+{ZOOM}*on/{frames}':x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)'"
                 f":d=1:s=1080x1920:fps={FPS},setsar=1,format=yuv420p[z{i}]")
    prev = "z0"
    for i in range(1, n):
        label = "v" if i == n - 1 else f"x{i}"
        f.append(f"[{prev}][z{i}]xfade=transition=slideleft"
                 f":duration={FADE}:offset={sum(shown[:i]):.3f}[{label}]")
        prev = label
    for i, d in enumerate(shown):  # captions: fade in and out, then positioned at the card's start time
        f.append(f"[{2 * n + i}:v]format=rgba,fade=t=in:st=0:d=0.3:alpha=1,fade=t=out:st={max(0.3, d - FADE - 0.3):.3f}:d=0.3:alpha=1,"
                 f"setpts=PTS-STARTPTS+{starts[i]:.3f}/TB[c{i}]")
    src = "v"
    for i in range(n):
        label = "vout" if i == n - 1 else f"o{i}"
        f.append(f"[{src}][c{i}]overlay=0:{CAPTION_Y}:eof_action=pass[{label}]")
        src = label
    for i, d in enumerate(shown):  # narration: leading delay, padded to the card's length
        f.append(f"[{n + i}:a]adelay={int(LEAD * 1000)}:all=1,apad=whole_dur={d:.3f},atrim=0:{d:.3f},aresample=44100[a{i}]")
    f.append("".join(f"[a{i}]" for i in range(n)) + f"concat=n={n}:v=0:a=1[aout]")

    cmd += ["-filter_complex", ";".join(f), "-map", "[vout]", "-map", "[aout]", "-t", f"{total:.3f}",
            "-c:v", "libx264", "-preset", "medium", "-crf", "20", "-pix_fmt", "yuv420p", "-r", str(FPS),
            "-c:a", "aac", "-b:a", "160k", "-movflags", "+faststart", str(out)]
    return cmd


def build_thumbnail_command(ffmpeg: str, title_card: Path, out: Path) -> list[str]:
    """540x960 JPEG of the title card."""
    return [ffmpeg, "-y", "-hide_banner", "-loglevel", "error", "-i", str(title_card), "-vf", "scale=540:960", "-q:v", "3", str(out)]


def stitch(cards: list[Path], audios: list[Path], captions: list[Path], narration_seconds: list[float], out_dir: Path) -> dict:
    """Make lesson.mp4 and thumbnail.jpg in out_dir. Returns {"video", "thumbnail", "seconds"}."""
    ffmpeg = find_ffmpeg()
    video, thumb = out_dir / "lesson.mp4", out_dir / "thumbnail.jpg"
    for cmd in (build_command(ffmpeg, cards, audios, captions, narration_seconds, video),
                build_thumbnail_command(ffmpeg, cards[0], thumb)):
        result = subprocess.run(cmd, capture_output=True, text=True)
        if result.returncode:
            raise RuntimeError(f"ffmpeg failed ({result.returncode}): {result.stderr.strip()[-800:]}")
    return {"video": video, "thumbnail": thumb, "seconds": sum(card_seconds(narration_seconds))}
