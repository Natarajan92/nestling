"""Closing-card citations and disclaimers must stay clear of the video captions."""
import pytest
from PIL import ImageDraw

from nestling.lessons import cards
from nestling.lessons.stitch import CAPTION_Y


@pytest.mark.parametrize("reviewed_on", [None, "2026-11-01"])
def test_three_long_citations_keep_all_text_above_video_caption(monkeypatch, reviewed_on):
    sources = [
        ("Prenatal and postnatal yoga video. NHS; workout produced by InstructorLive (2025)", "p. 1"),
        ("Physiotherapy Advice in Pregnancy. Norfolk and Norwich University Hospitals NHS Foundation Trust (2021)", "p. 1"),
        ("Caring for your body in pregnancy. Royal Berkshire NHS Foundation Trust (2025)", "p. 1"),
    ]
    monkeypatch.setattr(cards, "source_lines", lambda board: sources)
    painted = []
    original = ImageDraw.ImageDraw.text

    def record(draw, xy, text, *args, **kwargs):
        painted.append((text, draw.textbbox(xy, text, font=kwargs.get("font"), anchor=kwargs.get("anchor"))))
        return original(draw, xy, text, *args, **kwargs)

    monkeypatch.setattr(ImageDraw.ImageDraw, "text", record)
    image = cards.render_closing({"scenes": [{}, {}, {}, {}, {}]}, reviewed_on)
    assert image.size == (1080, 1920)
    text = " ".join(line for line, _ in painted)
    for title, _ in sources:
        assert title in text
    assert cards.DISCLAIMER in text
    assert (f"Reviewed on {reviewed_on}" if reviewed_on else "Pending review") in text
    for line, (x0, y0, x1, y1) in painted:
        assert 0 <= x0 < x1 <= cards.W, line
        assert 0 <= y0 < y1 <= CAPTION_Y - 24, (line, y1)


def test_long_source_citation_is_never_silently_truncated(monkeypatch):
    title = "Antenatal physiotherapy and preparation guidance from the specialist maternity team. " * 4
    monkeypatch.setattr(cards, "source_lines", lambda board: [(title.strip(), "p. 1")])
    painted = []
    original = ImageDraw.ImageDraw.text

    def record(draw, xy, text, *args, **kwargs):
        painted.append(text)
        return original(draw, xy, text, *args, **kwargs)

    monkeypatch.setattr(ImageDraw.ImageDraw, "text", record)
    cards.render_closing({"scenes": [{}, {}, {}, {}]}, None)
    assert title.strip() in " ".join(painted)
