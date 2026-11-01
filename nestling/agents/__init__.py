"""Specialist agents: care, nourish, ready, money, celebrate, journal.

Each specialist answers from passages of its own sources (registry `used_by`) with one
MAIN-model call, through `answer_from_sources`. Deterministic content (checklists, playbooks)
is passed in by the agent as extra context; the LLM explains it and never invents it.
Every call (Nebius open models, see nestling/llm.py) reports its token usage so the pipeline can total the cost.
"""

import re

from langsmith import traceable

from nestling import retrieval
from nestling.llm import MAIN, chat_json

NO_SOURCE_LINE = "I don't have a trusted source for that. Please ask your doctor."

ANSWER_SCHEMA = {
    "type": "object",
    "properties": {"answer": {"type": "string"}, "sources_cited": {"type": "array", "items": {"type": "string"}}},
    "required": ["answer", "sources_cited"],
    "additionalProperties": False,
}

BASE_PROMPT = """You are Nestling's {agent} specialist: a calm, warm companion for first-time parents in India (mothers, fathers, partners, every family shape), in pregnancy and after birth.

Rules:
- Base every medical, diet, insurance and legal statement only on the passages given, and mention the source ID in the text, e.g. "(WHO-ANC, p. 34)". If the passages do not cover the question, say: "{no_source}"
- sources_cited lists the source IDs you actually used, taken only from the passage labels.
- Never give medicine doses and never diagnose.
- You cannot see uploaded documents, scans, policies or records, and you cannot save anything; if the question needs one, say so and ask for it.
- Be kind and brief: at most about 180 words. Speak to the person who wrote (a father asking about his wife gets advice for both of them).
{instructions}"""


def main_json(system: str, user: str, schema: dict, max_tokens: int = 3000) -> tuple[dict | None, dict, str]:
    """One structured MAIN-model call. Returns (data, usage, raw text); data is None if the reply was not valid."""
    return chat_json(MAIN, system, user, schema, max_tokens)


def profile_line(context: dict) -> str:
    keys = ("week", "diet", "tradition", "parent_role", "life_stage")
    return "Parent context: " + ", ".join(f"{k}={context[k]}" for k in keys if context.get(k) not in (None, ""))


def retrieval_query(question: str, context: dict) -> str:
    """The question with the parent's life stage in front, so postnatal questions find postnatal sources."""
    stage = context.get("life_stage")
    if stage == "postpartum":
        return f"After birth (postnatal mother and newborn): {question}"
    if stage == "pregnancy" and context.get("week"):
        return f"Pregnancy, week {context['week']}: {question}"
    return question


def retrieve(question: str, context: dict, agent: str, mode: str) -> list[dict]:
    """mode 'plain' = baseline dense search; 'reranked' = agent sources + life stage + rerank (lever 3)."""
    if mode == "plain":
        return retrieval.search(question, top_k=6)
    return retrieval.search_reranked(retrieval_query(question, context), source_ids=retrieval.sources_for(agent))


_MARK = re.compile(r"[(\[]\s*([A-Z][A-Z0-9]*(?:-[A-Z0-9]+)+)\s*,?\s*(?:pp?\.|pages?)\s*([0-9ivxlcdm]+)\s*[)\]]", re.IGNORECASE)


def enforce_citations(answer: str, sources_cited: list[str], hits: list[dict]) -> tuple[str, list[str]]:
    """Make the citations real, in code. Every "(SOURCE-ID, p. N)" is rewritten to that exact format and kept
    only if that source and page are in the passages the model was given; any other marker is dropped from
    the text. sources_cited keeps only IDs of given passages (those the model listed, plus those cited in text)."""
    given = {(h["source_id"], str(h.get("page_label") or h.get("page")).lower()) for h in hits}
    ids = {sid for sid, _ in given}
    cited_in_text = []

    def fix(m):
        sid, page = m.group(2).upper(), m.group(3).lower()
        if (sid, page) not in given:
            return ""
        cited_in_text.append(sid)
        return f"{m.group(1)}({sid}, p. {m.group(3)})"

    cleaned = re.sub(r"( ?)" + _MARK.pattern, fix, answer, flags=re.IGNORECASE)
    cleaned = re.sub(r" +([.,;])", r"", cleaned)
    kept = [x for x in dict.fromkeys([*sources_cited, *cited_in_text]) if x in ids]
    return cleaned, kept


def passages_text(hits: list[dict]) -> str:
    return "\n".join(f"\n[{n}] {retrieval.format_citation(h)}\n{h['chunk_text']}" for n, h in enumerate(hits, 1))


@traceable(name="specialist_answer", run_type="chain")
def answer_from_sources(agent: str, question: str, context: dict, hits: list[dict], instructions: str = "",
                        extra: str = "") -> dict:
    """{"answer", "sources_cited", "usage": [..], "raw"} from one MAIN-model call over the passages."""
    system = BASE_PROMPT.format(agent=agent, no_source=NO_SOURCE_LINE, instructions=instructions)
    user = f"{profile_line(context)}\n\nParent's message: {question}\n"
    if extra:
        user += f"\nNestling's own checklist/playbook (code-owned; explain it, do not add to it):\n{extra}\n"
    user += f"\nPassages:{passages_text(hits) or ' (none found)'}"
    data, usage, raw = main_json(system, user, ANSWER_SCHEMA)
    if data is None:
        data = {"answer": NO_SOURCE_LINE, "sources_cited": []}
    data["answer"], data["sources_cited"] = enforce_citations(data["answer"], data["sources_cited"], hits)
    return {**data, "usage": [usage], "raw": raw}
