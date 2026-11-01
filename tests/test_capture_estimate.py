"""Capture maths from plan §9.8 (C06, C07, C11, C12): exact numbers, computed in code."""

from datetime import date

from nestling.capture.estimate import NOT_ENOUGH, cost_per_edited_photo, estimate_tier, parse_inr, quote_request, total_cost
from nestling.schemas.studio_package import Album, Extra, StudioPackage

TODAY = date(2026, 11, 1)


def pkg(name, price, edited=None, album=None, extras=()):
    return StudioPackage(studio_name=name, shoot_type="maternity", price_inr=price, edited_photos=edited,
                         album=album or Album(), extras=list(extras), source_url=f"https://example.com/{name}", checked_on=TODAY)


def test_c06_cost_per_edited_photo():
    a = pkg("A", 25_000, edited=40)
    b = pkg("B", 18_000, edited=20, extras=[Extra(name="Album", price_inr=3_000)])
    assert cost_per_edited_photo(a) == 625
    assert total_cost(b, album=True) == 21_000
    assert cost_per_edited_photo(b, album=True) == 1_050


def test_c07_inr_with_gst():
    amount, assumptions = parse_inr("₹30k + 18% GST")
    assert amount == 35_400
    assert assumptions and "18% GST" in assumptions[0]


def test_c11_mid_tier_estimate():
    group = [pkg(f"S{i}", base, album=Album(offered=True, price_inr=alb))
             for i, (base, alb) in enumerate([(18_000, 4_000), (22_000, 6_000), (26_000, 8_000), (30_000, 10_000)])]
    result = estimate_tier(group, album=True)
    assert result["estimate"] == {"low": 22_000, "high": 40_000, "typical": 31_000}
    assert result["confidence"] == "Medium" and result["n_studios"] == 4


def test_c12_low_data_shows_no_number():
    result = estimate_tier([pkg("A", 20_000), pkg("B", 25_000)])
    assert result["estimate"] is None and result["message"] == NOT_ENOUGH


def test_missing_price_is_not_guessed():
    assert total_cost(pkg("A", None)) is None
    assert cost_per_edited_photo(pkg("A", 20_000, edited=None)) is None


def test_quote_lists_only_picked_components():
    draft = quote_request("Studio X", "maternity", {"edited_photos": 30, "album": True})
    assert "30 edited photos" in draft and "album" in draft
    assert "casting" not in draft.lower() and "frame" not in draft.lower()
