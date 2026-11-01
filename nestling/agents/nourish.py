"""Nourish: diet by week, food habit and region, based on ICMR-NIN (Sonnet + RAG)."""

from nestling.agents import answer_from_sources, retrieve

INSTRUCTIONS = """- Fit suggestions to the parent's food habit: veg (no egg, meat or fish), egg (veg plus eggs), non-veg, or Jain (vegetarian, no root vegetables such as onion, garlic, potato or carrot).
- Prefer familiar Indian foods and the parent's region where the passages allow.
- Do not give supplement doses; say the doctor will advise on iron, folic acid or calcium tablets."""


def answer(question: str, context: dict, mode: str = "reranked") -> dict:
    hits = retrieve(question, context, "nourish", mode)
    return {**answer_from_sources("Nourish", question, context, hits, INSTRUCTIONS), "hits": hits, "agent": "nourish"}
