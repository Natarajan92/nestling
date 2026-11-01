"""Verifier: checks each claim against its cited chunk; one rewrite, else "I don't know".

Runs on medical, diet and insurance answers (Care, Nourish, Money). Sonnet lists the factual
claims in the answer and marks each as supported or not by the passages. If any claim is
unsupported, the answer is rewritten once without it; if nothing useful is left, the answer
is replaced by the no-trusted-source line (constitution II). Round 1 also re-checked the
rewrite; that third Sonnet call was dropped in round 2 (latency and cost, see notebook 05).
"""

import re

from langsmith import traceable

from nestling.agents import NO_SOURCE_LINE, passages_text, sonnet_json

PROMPT_VERSION = "verifier-v2"

CHECK_SCHEMA = {
    "type": "object",
    "properties": {
        "claims": {"type": "array", "items": {
            "type": "object",
            "properties": {"claim": {"type": "string"}, "supported": {"type": "boolean"}},
            "required": ["claim", "supported"], "additionalProperties": False}},
    },
    "required": ["claims"],
    "additionalProperties": False,
}

CHECK_PROMPT = """You check a pregnancy companion's answer against the passages it was given.
List every factual claim about health, the body, food, medicines, insurance, schemes or law in the answer. Skip empathy, encouragement, and advice to see or ask a doctor, pharmacist, insurer or family.
Mark a claim supported only if the passages state it or directly imply it. Common sense is not support."""

REWRITE_SCHEMA = {
    "type": "object",
    "properties": {"answer": {"type": "string"}, "sources_cited": {"type": "array", "items": {"type": "string"}}},
    "required": ["answer", "sources_cited"],
    "additionalProperties": False,
}

REWRITE_PROMPT = """Rewrite a pregnancy companion's answer so that every factual claim is supported by the passages.
Remove the unsupported claims listed, keep the warm tone and the source IDs in the text, and keep any advice to see a doctor. If nothing useful is left, reply exactly: "{no_source}"
sources_cited lists the source IDs used, taken only from the passage labels."""


_CITE = re.compile(r"\b([A-Z][A-Z0-9-]+),? p\. ?([0-9ivxlcdm]+)", re.IGNORECASE)


def cited_passages(answer: str, sources_cited: list[str], hits: list[dict]) -> list[dict]:
    """The passages the answer points to: by (source, page) when it cites pages, else by source."""
    pages = {(sid.upper(), page.lower()) for sid, page in _CITE.findall(answer)}
    by_page = [h for h in hits if (h["source_id"], str(h.get("page_label") or h.get("page")).lower()) in pages]
    if by_page:
        return by_page
    by_source = [h for h in hits if h["source_id"] in set(sources_cited)]
    return by_source or hits


def _check(answer: str, hits: list[dict]) -> tuple[list[dict], dict]:
    user = f"Answer:\n{answer}\n\nPassages:{passages_text(hits) or ' (none)'}"
    data, usage, _ = sonnet_json(CHECK_PROMPT, user, CHECK_SCHEMA, max_tokens=3000)
    return (data or {"claims": []})["claims"], usage


@traceable(name="verifier", run_type="chain")
def verify(answer: str, sources_cited: list[str], hits: list[dict]) -> dict:
    """{"answer", "sources_cited", "verdict": passed|rewritten|replaced, "unsupported": [...], "usage": [...]}"""
    usage = []
    hits = cited_passages(answer, sources_cited, hits)
    claims, u = _check(answer, hits)
    usage.append(u)
    unsupported = [c["claim"] for c in claims if not c["supported"]]
    if not unsupported:
        return {"answer": answer, "sources_cited": sources_cited, "verdict": "passed", "unsupported": [], "usage": usage}

    user = (f"Answer:\n{answer}\n\nUnsupported claims to remove:\n" + "\n".join(f"- {c}" for c in unsupported)
            + f"\n\nPassages:{passages_text(hits) or ' (none)'}")
    rewritten, u, _ = sonnet_json(REWRITE_PROMPT.format(no_source=NO_SOURCE_LINE), user, REWRITE_SCHEMA)
    usage.append(u)
    if rewritten and rewritten["answer"].strip() != NO_SOURCE_LINE:
        # One rewrite (plan §4); the sources are the ones still named in the rewritten text.
        named = {sid.upper() for sid, _ in _CITE.findall(rewritten["answer"])} | set(rewritten["sources_cited"])
        kept = [s for s in dict.fromkeys(sources_cited + rewritten["sources_cited"]) if s in named]
        return {"answer": rewritten["answer"], "sources_cited": kept, "verdict": "rewritten", "unsupported": unsupported, "usage": usage}
    return {"answer": NO_SOURCE_LINE, "sources_cited": [], "verdict": "replaced", "unsupported": unsupported, "usage": usage}
