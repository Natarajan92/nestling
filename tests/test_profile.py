from datetime import date, timedelta

from nestling import profile


def test_week_from_due_date():
    today = date(2026, 11, 1)
    assert profile.week_from_due_date(today + timedelta(days=84), today) == (28, 0)  # 12 weeks to go
    assert profile.week_from_due_date(today, today) == (40, 0)
    assert profile.week_from_due_date(today + timedelta(days=280 - 7 * 20 - 3), today) == (20, 3)


def test_due_date_round_trip():
    today = date(2026, 11, 1)
    due = profile.due_date_from_week(28, 2, today)
    assert profile.week_from_due_date(due, today) == (28, 2)


def test_stage_pregnancy_has_size_and_tip():
    today = date(2026, 11, 1)
    p = profile.PregnancyProfile(due_date=today + timedelta(days=84))
    st = profile.stage(p, today)
    assert st["life_stage"] == "pregnancy" and st["week"] == 28 and st["trimester"] == 3
    assert "eggplant" in st["baby_size"]
    tip = profile.tip_for(st, today)
    assert tip and tip["source"] and tip["page"]


def test_stage_postpartum():
    today = date(2026, 11, 1)
    p = profile.PregnancyProfile(due_date=today - timedelta(days=20), birth_date=today - timedelta(days=14))
    st = profile.stage(p, today)
    assert st["life_stage"] == "postpartum" and st["baby_age_weeks"] == 2
    assert profile.tip_for(st, today)["stage"] == "postpartum"


def test_every_tip_cites_a_registered_source():
    from nestling.retrieval import load_registry

    registry = load_registry()
    for tip in profile._tips():
        assert tip["source"] in registry and tip["page"], tip["id"]
