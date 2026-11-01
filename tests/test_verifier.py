from nestling import graph, verifier

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
