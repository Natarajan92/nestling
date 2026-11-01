"""Citation normalization must preserve complete IDs and verifier evidence.

These regressions reproduce the baseline's multi-hyphen source corruption.
Fixtures contain neutral text; all source/page validation runs locally.
"""

from nestling.agents import enforce_citations
from nestling.verifier import cited_passages


HITS = [
    {"source_id": "ICMR-NIN-DG", "page_label": "36", "chunk_text": "Nutrition evidence."},
    {"source_id": "WHO-ANC", "page_label": "23", "chunk_text": "Antenatal evidence."},
]


def test_valid_multihyphen_parenthesized_citation_keeps_the_full_id():
    text, sources = enforce_citations("Nutrition evidence (ICMR-NIN-DG, p. 36).", [], HITS)
    assert text == "Nutrition evidence (ICMR-NIN-DG, p. 36)."
    assert sources == ["ICMR-NIN-DG"]


def test_valid_multihyphen_bracketed_citation_becomes_complete_canonical_marker():
    text, sources = enforce_citations("Nutrition evidence [icmr-nin-dg page 36].", [], HITS)
    assert text == "Nutrition evidence (ICMR-NIN-DG, p. 36)."
    assert sources == ["ICMR-NIN-DG"]


def test_valid_bare_multihyphen_citation_still_normalizes():
    text, sources = enforce_citations("Nutrition evidence ICMR-NIN-DG p. 36.", [], HITS)
    assert text == "Nutrition evidence (ICMR-NIN-DG, p. 36)."
    assert sources == ["ICMR-NIN-DG"]


def test_agent_then_verifier_normalization_is_idempotent():
    once = enforce_citations("Nutrition evidence ICMR-NIN-DG p. 36.", [], HITS)
    twice = enforce_citations(once[0], once[1], HITS)
    assert twice == once
    assert twice[0] == "Nutrition evidence (ICMR-NIN-DG, p. 36)."


def test_mixed_source_citations_preserve_both_pages_for_the_verifier():
    text, sources = enforce_citations(
        "Nutrition evidence (ICMR-NIN-DG, p. 36). Antenatal evidence (WHO-ANC, p. 23).",
        ["ICMR-NIN-DG", "WHO-ANC"], HITS)
    evidence = cited_passages(text, sources, HITS)
    assert {(hit["source_id"], hit["page_label"]) for hit in evidence} == {
        ("ICMR-NIN-DG", "36"), ("WHO-ANC", "23")}
    assert text == "Nutrition evidence (ICMR-NIN-DG, p. 36). Antenatal evidence (WHO-ANC, p. 23)."


def test_invalid_multihyphen_sources_and_unretrieved_pages_are_still_removed():
    text, sources = enforce_citations(
        "Unknown (BOGUS-SOURCE-ID, p. 36). Wrong page (ICMR-NIN-DG, p. 99).", [], HITS)
    assert text == "Unknown. Wrong page."
    assert sources == []
