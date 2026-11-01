"""Little Lessons: storyboard validation, card rendering, ffmpeg command, approval rules. No paid calls."""

import json
from pathlib import Path

import pytest
import yaml
from PIL import Image

from nestling.lessons import cards, icon_names, library, narrate, stitch
from nestling.lessons import storyboard as sb

ICONS = icon_names()


def hit(source_id="WHO-POSTNATAL", page="120", text="Clean, dry umbilical cord care is recommended for every newborn baby."):
    return {"id": f"{source_id}:{page}", "source_id": source_id, "page_label": page, "page": int(page), "chunk_text": text, "score": 0.9}


def scene(n, **over):
    base = {"step_no": n, "caption": "Keep the cord clean and dry", "narration_line": "Keep the cord clean and dry every day.",
            "icon": "hand", "source_id": "WHO-POSTNATAL", "page_label": "120",
            "evidence": "clean dry umbilical cord care is recommended", "safety_points": ["Wash your hands first."]}
    return {**base, **over}


HITS = [hit()]


def four(**over):
    return [scene(i, **over) for i in range(1, 5)]


# ---------- storyboard validation ----------

def test_valid_scenes_pass():
    assert sb.validate(four(), HITS, ICONS) == []


def test_bad_source_or_page_is_rejected():
    assert any("not one of the retrieved" in p for p in sb.validate(four(source_id="WHO-ANC"), HITS, ICONS))
    assert any("not one of the retrieved" in p for p in sb.validate(four(page_label="999"), HITS, ICONS))


def test_evidence_must_be_on_the_cited_page():
    assert any("evidence" in p for p in sb.validate(four(evidence="rub turmeric paste on the stump"), HITS, ICONS))


def test_unknown_icon_is_rejected():
    assert any("unknown icon" in p for p in sb.validate(four(icon="rocket"), HITS, ICONS))


def test_step_count_and_numbering():
    assert any("need 4-5" in p for p in sb.validate(four()[:3], HITS, ICONS))
    assert any("need 4-5" in p for p in sb.validate([scene(i) for i in range(1, 7)], HITS, ICONS))
    assert any("step_no" in p for p in sb.validate([scene(1), scene(1), scene(3), scene(4)], HITS, ICONS))


def test_length_limits():
    assert any("caption" in p for p in sb.validate(four(caption="one two three four five six seven eight nine"), HITS, ICONS))
    assert any("narration_line" in p for p in sb.validate(four(narration_line=" ".join(["word"] * 13)), HITS, ICONS))


@pytest.mark.parametrize("text", ["Give 5 ml twice a day.", "Use paracetamol if warm.", "Your baby has an infection."])
def test_doses_medicines_and_diagnoses_are_rejected(text):
    problems = sb.validate(four(narration_line=text), HITS, ICONS)
    assert any("mentions" in p for p in problems)


def llm_returns(monkeypatch, *replies):
    calls = []

    def fake(model, system, user, schema, max_tokens=3000):
        calls.append(user)
        data = replies[min(len(calls), len(replies)) - 1]
        return data, {"model": "m", "tokens_in": 1, "tokens_out": 1}, ""

    monkeypatch.setattr(sb, "chat_json", fake)
    return calls


def test_build_ok_strips_evidence_and_adds_curated_see_how(monkeypatch):
    llm_returns(monkeypatch, {"supported": True, "scenes": four()})
    out = sb.build("cord_care", hits=HITS)
    board = out["storyboard"]
    assert out["status"] == "ok" and board["sources"] == ["WHO-POSTNATAL"] and board["see_how"] is None
    assert all("evidence" not in s for s in board["scenes"])
    llm_returns(monkeypatch, {"supported": True, "scenes": four()})
    assert sb.build("bathing", hits=HITS)["storyboard"]["see_how"]["publisher"] == "NHS"


def test_unsupported_passages_return_no_trusted_source_and_write_nothing(monkeypatch, tmp_path):
    llm_returns(monkeypatch, {"supported": False, "scenes": []})
    out = sb.build("burping", hits=HITS)
    assert out["status"] == sb.NO_TRUSTED_SOURCE and out["storyboard"] is None


def test_invalid_script_is_retried_with_the_problems_then_given_up(monkeypatch):
    calls = llm_returns(monkeypatch, {"supported": True, "scenes": four(page_label="999")})
    out = sb.build("cord_care", hits=HITS)
    assert out["status"] == sb.NO_TRUSTED_SOURCE and len(calls) == 3
    assert "previous script had these problems" in calls[1]


def test_write_keeps_an_approved_review(monkeypatch, tmp_path):
    monkeypatch.setattr(sb, "LESSONS_DIR", tmp_path)
    board = {"version": 1, "scenes": four()}
    sb.write("cord_care", board)
    review = tmp_path / "cord_care" / "review.yaml"
    assert yaml.safe_load(review.read_text())["approved"] is False
    review.write_text("approved: true\n")
    sb.write("cord_care", board)
    assert review.read_text() == "approved: true\n"


# ---------- cards ----------

def full_board(n=4):
    return {"lesson_id": "cord_care", "title": "Caring for the umbilical cord", "version": 1, "stage": "first_weeks", "language": "en",
            "sources": ["WHO-POSTNATAL"], "see_how": None,
            "scenes": [{k: v for k, v in scene(i, icon=ICONS[i]).items() if k != "evidence"} for i in range(1, n + 1)]}


def test_every_vendored_icon_rasterises():
    for name in ICONS:
        mask = cards.icon_mask(name, 64)
        assert mask.getbbox() is not None, name


def test_cards_are_1080_by_1920(tmp_path):
    paths = cards.render_cards(full_board(), tmp_path)
    assert [p.name for p in paths] == [f"card_{i}.png" for i in range(1, 7)]  # title + 4 steps + closing
    for p in paths:
        assert Image.open(p).size == (1080, 1920)
    assert Image.open(tmp_path / "caption_2.png").size == cards.CAPTION_BOX


def test_card_plan_has_title_steps_closing():
    plan = cards.card_plan(full_board(5))
    assert [c["kind"] for c in plan] == ["title", "step", "step", "step", "step", "step", "closing"]
    assert plan[1]["narration"] == scene(1)["narration_line"]


def test_closing_card_shows_review_state(tmp_path):
    pending = cards.render_closing(full_board(), None)
    reviewed = cards.render_closing(full_board(), "2026-11-02")
    assert pending.tobytes() != reviewed.tobytes()


# ---------- stitch ----------

def command(n=6, seconds=None):
    seconds = seconds or [2.0] * n
    return stitch.build_command("ffmpeg", [Path(f"c{i}.png") for i in range(n)], [Path(f"a{i}.mp3") for i in range(n)],
                                [Path(f"cap{i}.png") for i in range(n)], seconds, Path("lesson.mp4"))


def test_card_seconds_has_a_minimum_and_adds_pause():
    shown = stitch.card_seconds([0.5, 4.0])
    assert shown[0] == stitch.MIN_CARD and shown[1] == pytest.approx(4.0 + stitch.LEAD + stitch.PAUSE)


def test_build_command_is_vertical_h264_aac_faststart():
    cmd = command()
    joined = " ".join(cmd)
    assert cmd[0] == "ffmpeg" and cmd[-1] == "lesson.mp4"
    for token in ("libx264", "aac", "+faststart", "yuv420p", "zoompan", "xfade", "overlay", "concat=n=6"):
        assert token in joined
    assert cmd.count("-i") == 18  # cards + narration + captions
    assert "1080x1920" in joined


def test_total_length_is_the_sum_of_card_times():
    cmd = command(seconds=[1.5, 3.0, 3.0, 3.0, 3.0, 3.0])
    total = float(cmd[cmd.index("[aout]") + 2])  # "-map [aout] -t <total>"
    assert total == pytest.approx(sum(stitch.card_seconds([1.5, 3.0, 3.0, 3.0, 3.0, 3.0])))


def test_thumbnail_command():
    cmd = stitch.build_thumbnail_command("ffmpeg", Path("card_1.png"), Path("thumbnail.jpg"))
    assert cmd[-1] == "thumbnail.jpg" and "card_1.png" in cmd


def test_missing_ffmpeg_gives_a_clear_error(monkeypatch):
    monkeypatch.setattr(stitch.shutil, "which", lambda name: None)
    monkeypatch.setenv("LOCALAPPDATA", str(Path("nowhere-at-all")))
    with pytest.raises(RuntimeError, match="ffmpeg was not found"):
        stitch.find_ffmpeg()


def test_narrate_reuses_unchanged_clips(monkeypatch, tmp_path):
    board = full_board()
    spoken = []
    monkeypatch.setattr(narrate, "duration", lambda mp3: 3.0)
    first = narrate.narrate(board, tmp_path, speak=lambda t: spoken.append(t) or b"mp3")
    again = narrate.narrate(board, tmp_path, speak=lambda t: spoken.append(t) or b"mp3")
    assert len(spoken) == 6 and again["characters_billed"] == 0 and first["characters_billed"] > 0
    assert first["seconds"] == [3.0] * 6


# ---------- library and approval ----------

def make_lesson(root, lesson_id="cord_care", *, approved=True, version=1, passed=True, video=True, scenes=4):
    folder = root / lesson_id
    (folder / "renders").mkdir(parents=True)
    (folder / "storyboard.json").write_text(json.dumps({**full_board(scenes), "lesson_id": lesson_id, "version": 1}), encoding="utf-8")
    review = {"lesson_id": lesson_id, "version": version, "approved": approved, "reviewer": "R", "review_date": "2026-11-02",
              "scenes": [{"step_no": i, "passed": passed, "notes": ""} for i in range(1, scenes + 1)]}
    (folder / "review.yaml").write_text(yaml.safe_dump(review), encoding="utf-8")
    (folder / "phrasings.yaml").write_text(yaml.safe_dump({"lesson_id": lesson_id, "phrasings": ["how to clean the cord"]}), encoding="utf-8")
    if video:
        (folder / "renders" / "lesson.mp4").write_bytes(b"x")


def test_fully_reviewed_lesson_is_approved(tmp_path):
    make_lesson(tmp_path)
    assert library.is_approved("cord_care", tmp_path)
    assert [x["lesson_id"] for x in library.approved(tmp_path)] == ["cord_care"]
    assert library.get("cord_care", tmp_path)["phrasings"] == ["how to clean the cord"]


@pytest.mark.parametrize("flaw", [{"approved": False}, {"version": 2}, {"passed": False}, {"video": False}])
def test_any_gap_means_not_approved(tmp_path, flaw):
    make_lesson(tmp_path, **flaw)
    assert not library.is_approved("cord_care", tmp_path)
    assert library.approved(tmp_path) == []


def test_unreviewed_scene_and_missing_lessons(tmp_path):
    make_lesson(tmp_path)
    review = tmp_path / "cord_care" / "review.yaml"
    data = yaml.safe_load(review.read_text())
    data["scenes"][2]["passed"] = None
    review.write_text(yaml.safe_dump(data))
    assert not library.is_approved("cord_care", tmp_path)
    assert not library.is_approved("nope", tmp_path) and library.get("../x", tmp_path) is None


def test_shipped_lessons_are_unapproved_with_full_files():
    for lesson_id in ("holding", "bathing", "burping", "swaddling", "latching", "cord_care"):
        folder = library.LESSONS_DIR / lesson_id
        review = yaml.safe_load((folder / "review.yaml").read_text())
        assert review["approved"] is False and review["reviewer"] is None
        assert "Card and icon match the narration" in yaml.safe_load((folder / "checklist.yaml").read_text())["items"]
        assert 6 <= len(yaml.safe_load((folder / "phrasings.yaml").read_text())["phrasings"]) <= 8
        assert not library.is_approved(lesson_id)
