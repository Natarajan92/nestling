import pytest
from PIL import ImageDraw

from nestling.lessons import cards


@pytest.mark.parametrize("text", [
    "Keep the baby's arms comfortable beside their body while leaving hips and knees free to bend naturally without restricting movement.",
    "Left arm beside body, elbow bent; cross right corner over it and tuck under baby's body.",
    "Support their head and neck.",
])
def test_burned_caption_preserves_all_narration_inside_strip(monkeypatch, text):
    drawn = []
    original = ImageDraw.ImageDraw.text

    def record(draw, xy, line, *args, **kwargs):
        drawn.append((line, draw.textbbox(xy, line, font=kwargs["font"], anchor=kwargs["anchor"])))
        return original(draw, xy, line, *args, **kwargs)

    monkeypatch.setattr(ImageDraw.ImageDraw, "text", record)
    strip = cards.render_caption(text)
    assert " ".join(line for line, _ in drawn) == text
    assert all(0 <= x0 < x1 <= strip.width and 0 <= y0 < y1 <= strip.height
               for _, (x0, y0, x1, y1) in drawn)


def test_unrenderable_caption_fails_instead_of_clipping():
    with pytest.raises(ValueError, match="caption.*fit"):
        cards.render_caption("verylongword" * 100)
