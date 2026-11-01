"""PregnancyProfile (due date, week, tradition, diet, city, insurer, language, consent flags) and the deterministic week engine (due date <-> week).

Code owns the week calculation (constitution III). A pregnancy is counted as 40 weeks
(280 days) from the first day of the last period, so week = 40 - weeks until the due date.
"""

from dataclasses import asdict, dataclass, field
from datetime import date, timedelta
from functools import cache
from pathlib import Path

import yaml

PREGNANCY_DAYS = 280
TIPS_FILE = Path(__file__).resolve().parent.parent / "playbooks" / "weekly_tips.yaml"
TRADITIONS = ("tamil_nadu", "kerala", "karnataka", "other")
DIETS = ("veg", "egg", "non_veg", "jain")

# Illustrative "about the size of" comparisons, not measurements. Familiar Indian produce where possible.
BABY_SIZE = {
    4: ("a poppy seed (khus khus)", "🌱"), 5: ("a sesame seed", "🌱"), 6: ("a grain of dal", "🌱"), 7: ("a jamun seed", "🫐"),
    8: ("a rajma bean", "🫘"), 9: ("a grape", "🍇"), 10: ("a ber", "🍒"), 11: ("an anjeer (fig)", "🟣"), 12: ("a lime", "🍋"),
    13: ("a pea pod", "🫛"), 14: ("a lemon", "🍋"), 15: ("an apple", "🍎"), 16: ("a chikoo", "🥝"), 17: ("a pomegranate", "🔴"),
    18: ("a capsicum", "🫑"), 19: ("a mango", "🥭"), 20: ("a banana", "🍌"), 21: ("a carrot", "🥕"), 22: ("a small papaya", "🥭"),
    23: ("a large mango", "🥭"), 24: ("a bhutta (corn cob)", "🌽"), 25: ("a cauliflower", "🥦"), 26: ("a lettuce", "🥬"),
    27: ("a cabbage", "🥬"), 28: ("an eggplant (brinjal)", "🍆"), 29: ("a bottle gourd", "🥒"), 30: ("a big cabbage", "🥬"),
    31: ("a coconut", "🥥"), 32: ("a sweet potato bunch", "🍠"), 33: ("a pineapple", "🍍"), 34: ("a muskmelon", "🍈"),
    35: ("a honeydew melon", "🍈"), 36: ("a large papaya", "🥭"), 37: ("a bunch of methi", "🌿"), 38: ("a jackfruit, small", "🍈"),
    39: ("a small watermelon", "🍉"), 40: ("a pumpkin", "🎃"),
}


@dataclass
class PregnancyProfile:
    due_date: date | None = None
    birth_date: date | None = None  # set once the baby is born
    tradition: str | None = None
    diet: str | None = None
    city: str | None = None
    insurer: str | None = None
    parent_role: str = "mother"
    language: str = "en"
    consent: dict = field(default_factory=lambda: {"store_profile": False, "save_journal": False, "voice": False})

    def as_dict(self) -> dict:
        d = asdict(self)
        for k in ("due_date", "birth_date"):
            d[k] = d[k].isoformat() if d[k] else None
        return d

    @classmethod
    def from_dict(cls, d: dict) -> "PregnancyProfile":
        d = {k: v for k, v in d.items() if k in cls.__dataclass_fields__}
        for k in ("due_date", "birth_date"):
            if isinstance(d.get(k), str) and d[k]:
                d[k] = date.fromisoformat(d[k])
        return cls(**d)


def week_from_due_date(due: date, today: date | None = None) -> tuple[int, int]:
    """(completed weeks, extra days) of pregnancy on `today`."""
    today = today or date.today()
    days_pregnant = PREGNANCY_DAYS - (due - today).days
    return days_pregnant // 7, days_pregnant % 7


def due_date_from_week(week: int, days: int = 0, today: date | None = None) -> date:
    today = today or date.today()
    return today + timedelta(days=PREGNANCY_DAYS - (week * 7 + days))


def trimester(week: int) -> int:
    return 1 if week < 14 else 2 if week < 28 else 3


def stage(profile: PregnancyProfile, today: date | None = None) -> dict:
    """Where the family is today: pregnancy week or baby's age, with the size comparison."""
    today = today or date.today()
    if profile.birth_date:
        days = (today - profile.birth_date).days
        return {"life_stage": "postpartum", "baby_age_days": days, "baby_age_weeks": days // 7, "week": None}
    if not profile.due_date:
        return {"life_stage": "general", "week": None}
    week, days = week_from_due_date(profile.due_date, today)
    if week > 42:  # well past the due date with no birth recorded: treat as newborn stage
        return {"life_stage": "postpartum", "baby_age_days": (today - profile.due_date).days,
                "baby_age_weeks": (today - profile.due_date).days // 7, "week": None}
    size, emoji = BABY_SIZE.get(min(max(week, 4), 40), BABY_SIZE[4])
    return {"life_stage": "pregnancy", "week": max(week, 0), "days": days, "trimester": trimester(week),
            "days_to_go": max((profile.due_date - today).days, 0), "baby_size": size, "baby_emoji": emoji,
            "progress": round(min(max(week * 7 + days, 0) / PREGNANCY_DAYS, 1), 3)}


@cache
def _tips() -> list[dict]:
    return yaml.safe_load(TIPS_FILE.read_text(encoding="utf-8"))["tips"]


def tip_for(st: dict, today: date | None = None) -> dict | None:
    """One tip for the day: tips matching the stage and week, rotated by date so it changes daily."""
    today = today or date.today()
    if st["life_stage"] == "pregnancy":
        n, life = st["week"], "pregnancy"
    elif st["life_stage"] == "postpartum":
        n, life = st["baby_age_weeks"], "postpartum"
    else:
        return None
    matching = [t for t in _tips() if t["stage"] == life and t["weeks"][0] <= n <= t["weeks"][1]]
    return matching[today.toordinal() % len(matching)] if matching else None
