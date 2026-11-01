"""Compact strict checking keeps the safety gate while omitting supported-claim echoes."""

import pytest

from nestling import graph, llm, verifier
from nestling.agents import NO_SOURCE_LINE

HITS = [{"source_id": "WHO-ANC", "page_label": "48", "chunk_text": "Supported statement."}]
ANSWER = "Supported statement. Extra statement. (WHO-ANC, p. 48)"


@pytest.mark.parametrize("data", [
    None, {}, {"claims_checked": 1}, {"unsupported_claims": []},
    {"claims_checked": True, "unsupported_claims": []},
    {"claims_checked": 0, "unsupported_claims": []},
    {"claims_checked": -1, "unsupported_claims": []},
    {"claims_checked": 1.0, "unsupported_claims": []},
    {"claims_checked": "1", "unsupported_claims": []},
    {"claims_checked": 1, "unsupported_claims": None},
    {"claims_checked": 1, "unsupported_claims": "Extra statement."},
    {"claims_checked": 1, "unsupported_claims": [None]},
    {"claims_checked": 1, "unsupported_claims": [""]},
    {"claims_checked": 1, "unsupported_claims": ["   "]},
    {"claims_checked": 2, "unsupported_claims": ["duplicate", "duplicate"]},
    {"claims_checked": 2, "unsupported_claims": ["duplicate", " duplicate "]},
    {"claims_checked": 1, "unsupported_claims": ["first", "second"]},
    {"claims_checked": 1, "unsupported_claims": [], "unexpected": True},
])
def test_invalid_compact_check_fails_closed_without_rewrite(monkeypatch, data):
    monkeypatch.setattr(verifier, "main_json", lambda *a, **kw: (data, {"model": llm.MAIN}, ""))
    out = verifier.verify(ANSWER, ["WHO-ANC"], HITS, strict=True, compact=True)
    assert out["verdict"] == "replaced" and out["answer"] == NO_SOURCE_LINE
    assert out["sources_cited"] == [] and len(out["usage"]) == 1


def test_positive_count_with_no_unsupported_claims_passes_without_rewrite(monkeypatch):
    def check_only(system, user, schema, max_tokens=3000):
        assert "practical advice" in system and "week or trimester" in system
        assert "Common sense is not support" in system
        assert "Supported statement." in user and "WHO-ANC" in user
        assert max_tokens == 3000
        assert set(schema["properties"]) == {"claims_checked", "unsupported_claims"}
        return {"claims_checked": 2, "unsupported_claims": []}, {"model": llm.MAIN}, ""
    monkeypatch.setattr(verifier, "main_json", check_only)
    # Compact mode always retains the complete strict scope, even if strict was omitted.
    out = verifier.verify(ANSWER, ["WHO-ANC"], HITS, compact=True)
    assert out["verdict"] == "passed" and out["answer"] == ANSWER
    assert out["unsupported"] == [] and len(out["usage"]) == 1
    assert out["usage"][0]["model"] == "deepseek-ai/DeepSeek-V4-Pro"


def test_unsupported_compact_claim_uses_one_unchanged_strict_rewrite(monkeypatch):
    calls = []
    def respond(system, user, schema, max_tokens=3000):
        calls.append(system)
        if len(calls) == 1:
            return {"claims_checked": 2, "unsupported_claims": ["Extra statement."]}, {"model": llm.MAIN}, ""
        assert system == verifier.STRICT_REWRITE_PROMPT.format(no_source=NO_SOURCE_LINE)
        assert "- Extra statement." in user
        return {"answer": "Supported statement. (WHO-ANC, p. 48)", "sources_cited": ["WHO-ANC"]}, {"model": llm.MAIN}, ""
    monkeypatch.setattr(verifier, "main_json", respond)
    out = verifier.verify(ANSWER, ["WHO-ANC"], HITS, strict=True, compact=True)
    assert out["verdict"] == "rewritten" and out["unsupported"] == ["Extra statement."]
    assert out["answer"] == "Supported statement. (WHO-ANC, p. 48)"
    assert len(calls) == len(out["usage"]) == 2


def test_compact_rewrite_with_invalid_source_still_fails_closed(monkeypatch):
    replies = iter([
        ({"claims_checked": 2, "unsupported_claims": ["Extra statement."]}, {"model": llm.MAIN}, ""),
        ({"answer": "Extra statement. (BOGUS-SOURCE, p. 99)", "sources_cited": ["BOGUS-SOURCE"]}, {"model": llm.MAIN}, ""),
    ])
    monkeypatch.setattr(verifier, "main_json", lambda *a, **kw: next(replies))
    out = verifier.verify(ANSWER, ["WHO-ANC"], HITS, strict=True, compact=True)
    assert out["verdict"] == "replaced" and out["answer"] == NO_SOURCE_LINE
    assert out["sources_cited"] == [] and len(out["usage"]) == 2


def test_plain_default_contract_still_accepts_claim_list(monkeypatch):
    monkeypatch.setattr(verifier, "main_json", lambda *a, **kw: (
        {"claims": [{"claim": "Supported statement.", "supported": True}]}, {"model": llm.MAIN}, ""))
    out = verifier.verify("Supported statement. (WHO-ANC, p. 48)", ["WHO-ANC"], HITS, strict=True)
    assert out["verdict"] == "passed" and len(out["usage"]) == 1


def test_explicit_app_flag_activates_compact_and_retained_app_keeps_old_signature(monkeypatch):
    seen = []
    def fake(answer, sources, hits, strict=False, **kwargs):
        seen.append(kwargs)
        return {"answer": answer, "sources_cited": sources, "verdict": "passed", "unsupported": [], "usage": []}
    monkeypatch.setattr(verifier, "verify", fake)
    state = {"result": {"answer": ANSWER, "sources_cited": ["WHO-ANC"], "hits": HITS}}
    graph.verifier_node({**state, "flags": {**graph.VERSIONS[graph.APP_VERSION], "compact_verifier": True}})
    graph.verifier_node({**state, "flags": graph.VERSIONS[graph.APP_VERSION]})
    assert seen == [{"compact": True}, {}]
