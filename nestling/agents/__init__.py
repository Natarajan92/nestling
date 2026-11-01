"""Specialist agents: care, nourish, ready, money, celebrate, journal.

Each specialist answers from passages of its own sources (registry `used_by`) with one
MAIN-model call, through `answer_from_sources`. Deterministic content (checklists, playbooks)
is passed in by the agent as extra context; the LLM explains it and never invents it.
Every call (Nebius open models, see nestling/llm.py) reports its token usage so the pipeline can total the cost.
"""

import re
from functools import cache

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
    """mode 'plain' = baseline dense search; 'reranked' = agent sources + life stage + rerank (lever 3); 'staged' = reranked, with sources limited to the life stage (lever A)."""
    if mode == "plain":
        return retrieval.search(question, top_k=6)
    stage = context.get("life_stage") if mode == "staged" else None  # "staged" = lever A (v7)
    return retrieval.search_reranked(retrieval_query(question, context), source_ids=retrieval.sources_for(agent, stage))


_ID = r"[A-Za-z][A-Za-z0-9]*(?:-[A-Za-z0-9]+)+"
_PAGES = r"(?:pp?\.?|pages?)\s*([0-9ivxlcdm]+(?:\s*[-–]\s*[0-9ivxlcdm]+)?)"
_ITEM = rf"({_ID})(?:\s*,?\s*{_PAGES})?"
_GROUP = re.compile(rf"( ?)[(\[]\s*{_ITEM}(?:\s*[;,]\s*{_ITEM})*\s*[)\]]", re.IGNORECASE)
_BARE = re.compile(rf"( ?)(?<![(\[])\b({_ID})\s*,?\s*{_PAGES}", re.IGNORECASE)
_ITEM_RE = re.compile(_ITEM, re.IGNORECASE)


@cache
def _registry_ids() -> frozenset[str]:
    return frozenset(retrieval.load_registry())


def _page_list(spec: str | None) -> list[str]:
    """'34' -> ['34']; '34-36' -> ['34', '35', '36'] (numeric ranges, at most 30 pages)."""
    if not spec:
        return []
    parts = [p.strip().lower() for p in re.split(r"[-–]", spec)]
    if len(parts) == 2 and all(p.isdigit() for p in parts) and 0 <= int(parts[1]) - int(parts[0]) < 30:
        return [str(n) for n in range(int(parts[0]), int(parts[1]) + 1)]
    return parts


def enforce_citations(answer: str, sources_cited: list[str], hits: list[dict]) -> tuple[str, list[str]]:
    """Make the citations real, in code. Every source-ID citation in the text, in any common form
    ("(WHO-ANC, p. 34)", "[who-anc page 34]", "(WHO-ANC, pp. 34-35)", "(A, p. 3; B, p. 5)", bare "WHO-ANC p. 99",
    "(WHO-ANC)"), is replaced by canonical "(SOURCE-ID, p. N)" markers, one per (source, page) pair that is in the
    passages the model was given; every other pair is dropped. sources_cited keeps only IDs of given passages
    (those the model listed, plus those cited in text). The Verifier and the citation metric read this form."""
    given = {(h["source_id"], str(h.get("page_label") or h.get("page")).lower()) for h in hits}
    label = {(h["source_id"], str(h.get("page_label") or h.get("page")).lower()): h.get("page_label") or h.get("page") for h in hits}
    ids = {sid for sid, _ in given}
    cited_in_text = []

    def canonical(m):
        pairs = []
        for item in _ITEM_RE.finditer(m.group(0)):
            sid = item.group(1).upper()
            if not (sid in _registry_ids() or item.group(1).isupper() or item.group(2)):
                return m.group(0)  # not a source ID (e.g. a hyphenated word): leave the text alone
            for page in _page_list(item.group(2)):
                if (sid, page) in given and (sid, page) not in pairs:
                    pairs.append((sid, page))
        cited_in_text.extend(sid for sid, _ in pairs)
        shown = " ".join(f"({sid}, p. {label[(sid, page)]})" for sid, page in pairs)
        return (m.group(1) + shown) if shown else ""

    cleaned = _GROUP.sub(canonical, answer)
    cleaned = _BARE.sub(canonical, cleaned)
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
