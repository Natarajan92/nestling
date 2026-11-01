"""Money: maternity cover, claims and newborn add-on, with exact clause quotes from the user's policy.

Until the parent uploads their policy (Phase 10), Money cannot see it: for questions about
"my policy" it says it cannot verify the cover, asks for the policy PDF, and explains only
what the IRDAI rules and government schemes in the library say.
"""

from nestling.agents import answer_from_sources, retrieve

INSTRUCTIONS = """- You cannot see the parent's own insurance policy. If they ask what their policy covers, say you cannot verify their cover without the policy document, ask them to upload it (or check with their insurer or TPA), and then share only what the IRDAI rules or schemes in the passages say in general. Never pretend to quote a policy you have not seen.
- For schemes and leave, give eligibility and amounts only as the passages state them, and suggest confirming with the local health worker, employer or insurer."""


def answer(question: str, context: dict, mode: str = "reranked") -> dict:
    hits = retrieve(question, context, "money", mode)
    return {**answer_from_sources("Money", question, context, hits, INSTRUCTIONS), "hits": hits, "agent": "money"}
