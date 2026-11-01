from nestling import graph, verifier
from nestling.agents import NO_SOURCE_LINE

HITS = [{"source_id": "WHO-ANC", "page_label": "48", "chunk_text": "Women with high blood sugar need referral."}]


def test_prompts_strict_extends_plain():
    check, rewrite = verifier.prompts(False)
    s_check, s_rewrite = verifier.prompts(True)
    assert (check, rewrite) == (verifier.CHECK_PROMPT, verifier.REWRITE_PROMPT)
    assert s_check.startswith(check) and "practical advice" in s_check
    assert s_rewrite.startswith(rewrite) and "Only delete" in s_rewrite


def test_v6_is_v5_plus_strict_verifier_and_v5_unchanged():
    assert graph.VERSIONS["v5"] == {"concierge": True, "retrieval": "reranked", "verifier": True, "lessons": False}
    assert graph.VERSIONS["v6"] == {**graph.VERSIONS["v5"], "strict_verifier": True}
    assert graph.PROMPT_VERSIONS["v6"] != graph.PROMPT_VERSIONS["v5"]


def test_verify_passes_chosen_prompts(monkeypatch):
    seen = []

    def fake(system, user, schema, max_tokens=3000):
        seen.append(system)
        return {"claims": [{"claim": "x", "supported": False}]} if len(seen) == 1 else \
            {"answer": "kept (WHO-ANC, p. 48)", "sources_cited": ["WHO-ANC"]}, {"model": "m"}, "end_turn"

    monkeypatch.setattr(verifier, "main_json", fake)
    out = verifier.verify("a (WHO-ANC, p. 48)", ["WHO-ANC"], HITS, strict=True)
    assert out["verdict"] == "rewritten"
    assert seen[0] == verifier.STRICT_CHECK_PROMPT and seen[1].startswith(verifier.STRICT_REWRITE_PROMPT[:50])


def test_invalid_checker_cannot_pass_a_clinical_claim(monkeypatch):
    monkeypatch.setattr(verifier, "main_json", lambda *a, **kw: (None, {"model": "m"}, "invalid JSON"))
    out = verifier.verify("This condition is harmless. (WHO-ANC, p. 48)", ["WHO-ANC"], HITS, strict=True)
    assert out["verdict"] == "replaced"
    assert out["answer"] == NO_SOURCE_LINE and out["sources_cited"] == []
    assert len(out["usage"]) == 1


def test_valid_empty_claims_is_separate_from_invalid_checker(monkeypatch):
    monkeypatch.setattr(verifier, "main_json", lambda *a, **kw: ({"claims": []}, {"model": "m"}, ""))
    out = verifier.verify("Please ask your doctor. (WHO-ANC, p. 48)", ["WHO-ANC"], HITS)
    assert out["verdict"] == "passed" and out["sources_cited"] == ["WHO-ANC"]


def test_rewrite_losing_its_last_valid_citation_is_replaced(monkeypatch):
    replies = iter([({"claims": [{"claim": "unsafe claim", "supported": False}]}, {"model": "m"}, ""),
                    ({"answer": "Drink this herb. [FAKE-SOURCE, p. 99]", "sources_cited": ["FAKE-SOURCE"]}, {"model": "m"}, "")])
    monkeypatch.setattr(verifier, "main_json", lambda *a, **kw: next(replies))
    out = verifier.verify("unsafe claim (WHO-ANC, p. 48)", ["WHO-ANC"], HITS, strict=True)
    assert out["verdict"] == "replaced" and out["answer"] == NO_SOURCE_LINE
    assert out["sources_cited"] == []
