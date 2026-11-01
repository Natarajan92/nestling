"""Celebrate: tradition playbooks and babymoon ideas (Tavily for live, non-medical lookups only).

Ceremonies come from the YAML playbooks (family customs, which vary). No medical claims:
health questions inside a celebration (food safety, herbal preparations) are pointed to
Nourish or the doctor.
"""

from functools import cache
from pathlib import Path

import yaml

from nestling.agents import answer_from_sources

PLAYBOOKS = Path(__file__).resolve().parents[2] / "playbooks"
FILES = {"tamil_nadu": "seemantham_tamilnadu.yaml", "kerala": "valaikappu_kerala.yaml", "karnataka": "seemantha_karnataka.yaml"}
KEYWORDS = {
    "tamil_nadu": ("tamil", "valaikappu", "seemantham"),
    "kerala": ("kerala", "pulikudi", "malayali"),
    "karnataka": ("karnataka", "kannada", "seemantha ", "kubusa"),
}

INSTRUCTIONS = """- Use Nestling's playbook for the tradition. These are family customs: say that customs vary between communities and families and suggest asking family elders.
- Make no health claims; for food safety or herbal preparations, suggest checking with Nourish or their doctor.
- sources_cited stays empty unless a passage was used."""


@cache
def playbook(tradition: str) -> dict:
    return yaml.safe_load((PLAYBOOKS / FILES[tradition]).read_text(encoding="utf-8"))


def pick_tradition(question: str, context: dict) -> str | None:
    text = question.lower() + " "
    for tradition, words in KEYWORDS.items():
        if any(w in text for w in words):
            return tradition
    return context.get("tradition") if context.get("tradition") in FILES else None


def answer(question: str, context: dict, mode: str = "reranked") -> dict:
    tradition = pick_tradition(question, context)
    books = [playbook(tradition)] if tradition else [playbook(t) for t in FILES]
    extra = "\n\n".join(yaml.safe_dump(b, allow_unicode=True, sort_keys=False) for b in books)
    out = answer_from_sources("Celebrate", question, context, [], INSTRUCTIONS, extra=extra)
    return {**out, "hits": [], "agent": "celebrate", "playbook": tradition}
