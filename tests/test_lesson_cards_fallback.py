from nestling.lessons import cards


def test_title_icon_remains_distinct_when_five_preferred_icons_are_used(monkeypatch):
    used = ["hand-heart", "baby", "heart", "sparkle", "smiley"]
    captured = []
    monkeypatch.setattr(cards, "_blob_with_icon", lambda img, tone, icon, **kw: captured.append(icon))
    cards.render_title({"title": "A short lesson", "scenes": [{"icon": x} for x in used]})
    assert captured[0] not in used
