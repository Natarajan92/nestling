"""Concierge: routes each message to the right specialist, or asks a clarifying question.

Haiku with explicit route definitions and few-shot examples (plan §9.5 lever 2). The examples
are written for this module and are not taken from the golden set. The Guardian runs first;
the Concierge only sees messages the Guardian did not answer itself, and Guardian-owned
topics (medicine questions, scans) arrive pre-routed, so they never reach it.
"""

import json
from functools import cache

from langsmith import traceable

MODEL = "claude-haiku-5-5"
PROMPT_VERSION = "concierge-v2"
ROUTES = ["care", "nourish", "ready", "money", "celebrate", "journal", "out_of_scope", "clarify"]

SYSTEM = """You route messages for Nestling, a companion app for expecting and new parents in India (mothers, fathers, partners). Pick the ONE specialist that should answer.

- care: health, safety and feelings of the mother or baby in pregnancy and after birth: symptoms, check-ups, tests, vaccines, travel and activity safety, sleep, recovery, emotions and relationships (including a partner asking how to support her feelings or health), breastfeeding and newborn care, and whether a food BELIEF, custom or myth is true or safe.
- nourish: what the mother should eat or drink: meal ideas, nutrients, diet by trimester, food habits (veg, egg, Jain, non-veg), and foods while breastfeeding.
- ready: logistics and planning: hospital bag, documents, birth plan paperwork, birth registration, transport, first steps for a new father or partner, scheduling visits around work, dividing chores and night duty.
- money: insurance cover and claims (including questions about the parent's own policy document, even when none is attached), government schemes and benefits, maternity or paternity leave, costs.
- celebrate: traditions and ceremonies (seemantham, valaikappu, seemantha, naming), baby showers, babymoons, photoshoots.
- journal: the parent asks the app to save, remember or note something (a memory, a mood, a preference).
- out_of_scope: not about pregnancy, babies or parenting.
- clarify: too vague to know what is being asked.

Feeding the BABY (breastmilk, formula, water, honey, first foods) is care, not nourish. Questions about whether a custom or family belief about food is true are care.
If a message asks about two topics, pick the topic of its first question; use clarify only when nothing specific is asked."""

EXAMPLES = [
    ("Which vegetables give the most folate in the first trimester?", "nourish"),
    ("What is a good dinner for a pregnant woman who eats eggs but no meat?", "nourish"),
    ("Is it true that eating ghee makes delivery easier?", "care"),
    ("How do I know my baby is getting enough breastmilk?", "care"),
    ("Can a three-week-old have gripe water?", "care"),
    ("When is the anomaly scan usually done?", "care"),
    ("I feel anxious about labour, is that normal?", "care"),
    ("What documents should we carry to the hospital for admission?", "ready"),
    ("I'm about to become a dad. What should I organise first?", "ready"),
    ("How do we split night feeds when I go back to the office?", "ready"),
    ("My wife seems anxious every evening. How can I support her?", "care"),
    ("Is it safe to drive long distances at 34 weeks?", "care"),
    ("Does a health policy cover a caesarean?", "money"),
    ("Read the maternity clause from my policy for me.", "money"),
    ("Which dal is best for protein, and when should we book the anomaly scan?", "nourish"),
    ("How many weeks of maternity leave can I take in a private company?", "money"),
    ("What gifts are usually given at a valaikappu?", "celebrate"),
    ("Note that the baby hiccuped for ten minutes tonight", "journal"),
    ("Which phone should I buy?", "out_of_scope"),
    ("What about that?", "clarify"),
]

SCHEMA = {
    "type": "object",
    "properties": {"route": {"type": "string", "enum": ROUTES}},
    "required": ["route"],
    "additionalProperties": False,
}


@cache
def _client():
    import anthropic
    from langsmith.wrappers import wrap_anthropic

    return wrap_anthropic(anthropic.Anthropic())


def _messages(text: str) -> list[dict]:
    shots = "\n".join(f'Message: "{q}" -> {r}' for q, r in EXAMPLES)
    return [{"role": "user", "content": f"Examples:\n{shots}\n\nMessage: \"{text}\""}]


@traceable(name="concierge", run_type="chain")
def route(text: str) -> dict:
    """{"route": one of ROUTES, "usage": {...}}. Falls back to clarify if the call fails."""
    try:
        response = _client().messages.create(
            model=MODEL,
            max_tokens=500,
            system=SYSTEM,
            messages=_messages(text),
            output_config={"effort": "low", "format": {"type": "json_schema", "schema": SCHEMA}},
        )
    except Exception as exc:
        return {"route": "clarify", "usage": None, "error": type(exc).__name__}
    usage = {"model": response.model, "tokens_in": response.usage.input_tokens, "tokens_out": response.usage.output_tokens}
    if response.stop_reason in ("refusal", "max_tokens"):
        return {"route": "clarify", "usage": usage}
    return {**json.loads("".join(b.text for b in response.content if b.type == "text")), "usage": usage}
