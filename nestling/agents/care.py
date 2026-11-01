"""Care: prenatal and postnatal questions answered from the source library (Sonnet + RAG).

Care also answers the Guardian's "safe redirect" topics (medicine questions, herbal remedies,
scans, diagnosis requests): it explains why a doctor or pharmacist must decide and shares
general sourced information, without naming a medicine, a dose or a diagnosis.
"""

from nestling.agents import answer_from_sources, retrieve

INSTRUCTIONS = """- Reassure where the passages support it, and say clearly when to see a doctor.
- Respect family traditions; where a custom conflicts with the evidence, explain gently what the source says."""

REDIRECT = """- The parent asked about {kinds}. Do not name or recommend any medicine, supplement brand, dose or remedy, do not say whether to take it, and do not interpret scans or diagnose.
- Explain kindly that their doctor or pharmacist should decide because it depends on their health and pregnancy, and share only general, sourced information that helps them ask the right questions."""


def answer(question: str, context: dict, mode: str = "reranked", redirect: list[str] | None = None) -> dict:
    hits = retrieve(question, context, "care", mode)
    instructions = INSTRUCTIONS
    if redirect:
        instructions += "\n" + REDIRECT.format(kinds=", ".join(k.replace("_", " ") for k in redirect))
    return {**answer_from_sources("Care", question, context, hits, instructions), "hits": hits, "agent": "care"}
