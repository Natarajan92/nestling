"""Verifier: checks each claim against its cited chunk; one rewrite, else "I don't know".

Runs on medical, diet and insurance answers (Care, Nourish, Money). Sonnet lists the factual
claims in the answer and marks each as supported or not by the passages. If any claim is
unsupported, the answer is rewritten once without it; if nothing useful is left, the answer
is replaced by the no-trusted-source line (constitution II). Round 1 also re-checked the
rewrite; that third Sonnet call was dropped in round 2 (latency and cost, see notebook 05).
"""

import re

from langsmith import traceable

from nestling.agents import NO_SOURCE_LINE, enforce_citations, main_json, passages_text

PROMPT_VERSION = "verifier-v2"
STRICT_PROMPT_VERSION = "verifier-v3"
COMPACT_STRICT_PROMPT_VERSION = "verifier-v4-compact"

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

COMPACT_CHECK_SCHEMA = {
    "type": "object",
    "properties": {
        "claims_checked": {"type": "integer", "minimum": 1},
        "unsupported_claims": {"type": "array", "uniqueItems": True,
                               "items": {"type": "string", "minLength": 1}},
    },
    "required": ["claims_checked", "unsupported_claims"],
    "additionalProperties": False,
}

CHECK_PROMPT = """You check a pregnancy companion's answer against the passages it was given.
List every factual claim about health, the body, food, medicines, insurance, schemes or law in the answer. Skip empathy, encouragement, and advice to see or ask a doctor, pharmacist, insurer or family.
Mark a claim supported only if the passages state it or directly imply it. Common sense is not support."""
# v3 (pipeline v6): the v5 judge flagged claims the v2 check skipped (practical advice, the parent's own
# week or trimester) and rewrites that rephrased a removed claim ("very common to worry about").
STRICT_CHECK_PROMPT = CHECK_PROMPT + """
Also list statements about the parent's own situation (their week or trimester) and practical advice (what to bring, ask, upload, check or do), unless it is only advice to see or ask a doctor, pharmacist, insurer or family. Mark them supported only if the passages state or directly imply them."""

COMPACT_STRICT_CHECK_PROMPT = STRICT_CHECK_PROMPT + """
Apply every check above to every claim internally, retaining the same scope and evidence rules.
Return only claims_checked (the total number of claims actually checked) and unsupported_claims
(a list of unique, nonempty unsupported claim texts). Do not echo supported claims or their text.
An empty unsupported_claims list means all checked claims were supported. Never invent a positive
claims_checked count when no claims were checked; an invalid or zero-count check cannot pass."""

REWRITE_SCHEMA = {
    "type": "object",
    "properties": {"answer": {"type": "string"}, "sources_cited": {"type": "array", "items": {"type": "string"}}},
    "required": ["answer", "sources_cited"],
    "additionalProperties": False,
}

REWRITE_PROMPT = """Rewrite a pregnancy companion's answer so that every factual claim is supported by the passages.
Remove the unsupported claims listed, keep the warm tone and the source IDs in the text, and keep any advice to see a doctor. If nothing useful is left, reply exactly: "{no_source}"
sources_cited lists the source IDs used, taken only from the passage labels."""

STRICT_REWRITE_PROMPT = REWRITE_PROMPT + """
Only delete: remove the unsupported sentences or phrases and keep every other word as written. Do not rephrase, soften or add anything, and never replace a removed claim with its opposite or a hedged version of it."""


_CITE = re.compile(r"\b([A-Z][A-Z0-9-]+),? p\. ?([0-9ivxlcdm]+)", re.IGNORECASE)


def cited_passages(answer: str, sources_cited: list[str], hits: list[dict]) -> list[dict]:
    """The passages the answer points to: by (source, page) when it cites pages, else by source."""
    pages = {(sid.upper(), page.lower()) for sid, page in _CITE.findall(answer)}
    by_page = [h for h in hits if (h["source_id"], str(h.get("page_label") or h.get("page")).lower()) in pages]
    if by_page:
        return by_page
    by_source = [h for h in hits if h["source_id"] in set(sources_cited)]
    return by_source or hits


def prompts(strict: bool) -> tuple[str, str]:
    """(check prompt, rewrite prompt) for the plain (v2) or strict (v3) Verifier."""
    return (STRICT_CHECK_PROMPT, STRICT_REWRITE_PROMPT) if strict else (CHECK_PROMPT, REWRITE_PROMPT)


def _check(answer: str, hits: list[dict], prompt: str = CHECK_PROMPT) -> tuple[list[dict] | None, dict]:
    user = f"Answer:\n{answer}\n\nPassages:{passages_text(hits) or ' (none)'}"
    data, usage, _ = main_json(prompt, user, CHECK_SCHEMA, max_tokens=3000)
    return data["claims"] if data is not None else None, usage


def _compact_check(answer: str, hits: list[dict]) -> tuple[list[str] | None, dict]:
    """Same strict MAIN check, returning only failed claims; invalid counts fail closed."""
    user = f"Answer:\n{answer}\n\nPassages:{passages_text(hits) or ' (none)'}"
    data, usage, _ = main_json(COMPACT_STRICT_CHECK_PROMPT, user, COMPACT_CHECK_SCHEMA, max_tokens=3000)
    if not isinstance(data, dict) or set(data) != {"claims_checked", "unsupported_claims"}:
        return None, usage
    count, unsupported = data["claims_checked"], data["unsupported_claims"]
    if type(count) is not int or count < 1 or not isinstance(unsupported, list) or len(unsupported) > count:
        return None, usage
    if any(not isinstance(claim, str) or not claim.strip() for claim in unsupported):
        return None, usage
    if len({claim.strip() for claim in unsupported}) != len(unsupported):
        return None, usage
    return unsupported, usage


@traceable(name="verifier", run_type="chain")
def verify(answer: str, sources_cited: list[str], hits: list[dict], strict: bool = False, compact: bool = False) -> dict:
    """{"answer", "sources_cited", "verdict": passed|rewritten|replaced, "unsupported": [...], "usage": [...]}"""
    usage = []
    check_prompt, rewrite_prompt = prompts(strict or compact)
    answer, sources_cited = enforce_citations(answer, sources_cited, hits)
    if not sources_cited:
        return {"answer": NO_SOURCE_LINE, "sources_cited": [], "verdict": "replaced", "unsupported": [], "usage": usage}
    hits = cited_passages(answer, sources_cited, hits)
    if compact:
        unsupported, u = _compact_check(answer, hits)
    else:
        claims, u = _check(answer, hits, check_prompt)
        unsupported = [c["claim"] for c in claims if not c["supported"]] if claims is not None else None
    usage.append(u)
    if unsupported is None:
        return {"answer": NO_SOURCE_LINE, "sources_cited": [], "verdict": "replaced", "unsupported": [], "usage": usage}
    if not unsupported:
        return {"answer": answer, "sources_cited": sources_cited, "verdict": "passed", "unsupported": [], "usage": usage}

    user = (f"Answer:\n{answer}\n\nUnsupported claims to remove:\n" + "\n".join(f"- {c}" for c in unsupported)
            + f"\n\nPassages:{passages_text(hits) or ' (none)'}")
    rewritten, u, _ = main_json(rewrite_prompt.format(no_source=NO_SOURCE_LINE), user, REWRITE_SCHEMA)
    usage.append(u)
    if rewritten and rewritten["answer"].strip() != NO_SOURCE_LINE:
        # One rewrite (plan §4); the sources are the ones still named in the rewritten text.
        text, listed = enforce_citations(rewritten["answer"], rewritten["sources_cited"], hits)
        if not listed:
            return {"answer": NO_SOURCE_LINE, "sources_cited": [], "verdict": "replaced", "unsupported": unsupported, "usage": usage}
        rewritten = {"answer": text, "sources_cited": listed}
        named = {sid.upper() for sid, _ in _CITE.findall(rewritten["answer"])} | set(rewritten["sources_cited"])
        kept = [s for s in dict.fromkeys(sources_cited + rewritten["sources_cited"]) if s in named]
        return {"answer": rewritten["answer"], "sources_cited": kept, "verdict": "rewritten", "unsupported": unsupported, "usage": usage}
    return {"answer": NO_SOURCE_LINE, "sources_cited": [], "verdict": "replaced", "unsupported": unsupported, "usage": usage}
