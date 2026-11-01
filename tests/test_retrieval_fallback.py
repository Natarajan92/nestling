"""The app can fall back on rerank outages; measured versions fail loudly."""

from concurrent.futures import ThreadPoolExecutor
from types import SimpleNamespace

import pytest

from nestling import graph, retrieval
from nestling import agents
from nestling import concierge, guardian
from nestling.agents import ready


class RerankError(Exception):
    def __init__(self, status):
        self.status = status


def mock_rerank(monkeypatch, status=429):
    # Four A passages lead vector order: the fourth must be skipped for diversity.
    hits = [{"id": str(n), "source_id": "A" if n < 4 else "B", "chunk_text": "public source", "score": 1 - n / 10}
            for n in range(8)]
    def search(query, source_ids=None, **kw):
        assert source_ids == ["A", "B"]
        return hits
    def rerank(**kw):
        raise RerankError(status)
    monkeypatch.setattr(retrieval, "search", search)
    monkeypatch.setattr(retrieval, "_search_index", lambda: (SimpleNamespace(inference=SimpleNamespace(rerank=rerank)), None))


@pytest.mark.parametrize("status", [429, 500, 502, 503, 504])
def test_app_outage_fallback_keeps_vector_order_and_diversity(monkeypatch, status):
    mock_rerank(monkeypatch, status)
    with retrieval.app_rerank_fallback():
        hits = retrieval.search_reranked("q", source_ids=["A", "B"], top_k=5)
    assert [h["id"] for h in hits] == ["0", "1", "2", "4", "5"]
    assert all(h["retrieval_fallback"] == "vector_order" for h in hits)
    assert all(h["chunk_text"] == "public source" for h in hits)


def test_evals_raise_even_after_app_request(monkeypatch):
    mock_rerank(monkeypatch)
    with retrieval.app_rerank_fallback():
        retrieval.search_reranked("q", source_ids=["A", "B"])
    with pytest.raises(RerankError):
        retrieval.search_reranked("q", source_ids=["A", "B"])


def test_app_does_not_hide_auth_errors_or_search_failure(monkeypatch):
    mock_rerank(monkeypatch, 401)
    with retrieval.app_rerank_fallback(), pytest.raises(RerankError):
        retrieval.search_reranked("q", source_ids=["A", "B"])
    monkeypatch.setattr(retrieval, "search", lambda *a, **kw: (_ for _ in ()).throw(RuntimeError("search failed")))
    with retrieval.app_rerank_fallback(), pytest.raises(RuntimeError, match="search failed"):
        retrieval.search_reranked("q", source_ids=["A", "B"])


def test_fallback_context_does_not_leak_across_threads(monkeypatch):
    mock_rerank(monkeypatch)
    with ThreadPoolExecutor(2) as pool, retrieval.app_rerank_fallback():
        app_hits = retrieval.search_reranked("q", source_ids=["A", "B"])
        strict = pool.submit(retrieval.search_reranked, "q", source_ids=["A", "B"])
        with pytest.raises(RerankError):
            strict.result()
    assert app_hits[0]["retrieval_fallback"] == "vector_order"


def test_graph_only_scopes_fallback_to_app_versions(monkeypatch):
    class Graph:
        def invoke(self, state):
            assert retrieval._APP_RERANK_FALLBACK.get() == state["flags"]["lessons"]
            return {"screening": {"sources": [], "escalate": False, "refuse": False, "red_flags": [], "unsafe": [], "classifier_flags": []},
                    "route": "care", "result": {"answer": "Sourced", "sources_cited": ["WHO-POSTNATAL"], "agent": "care",
                    "hits": [{"source_id": "WHO-POSTNATAL", "chunk_text": "source", "retrieval_fallback": "vector_order"}]}}
    monkeypatch.setattr(graph, "compiled", lambda: Graph())
    app = graph.ask("q", version="v6+lessons")
    assert app["retrieval_fallback"] == "vector_order" and any("vector order" in step for step in app["steps"])
    assert graph.ask("q", version="v6")["error"] is None


def test_vector_variant_uses_stage_filters_and_never_attempts_rerank(monkeypatch):
    hits = [{"id": str(n), "source_id": "A" if n < 4 else "B", "chunk_text": "source", "score": 1 - n / 10}
            for n in range(8)]
    seen = []
    monkeypatch.setattr(retrieval, "search", lambda query, **kw: seen.append(kw) or hits)
    monkeypatch.setattr(retrieval, "_search_index", lambda: pytest.fail("vector path attempted rerank"))
    result = agents.retrieve("q", {"life_stage": "pregnancy", "week": 20}, "care", graph.VERSIONS["v7_vector"]["retrieval"])
    assert [h["id"] for h in result] == ["0", "1", "2", "4", "5", "6"]
    assert "WHO-ANC" in seen[0]["source_ids"] and "WHO-POSTNATAL" not in seen[0]["source_ids"]
    assert graph.VERSIONS["v7_vector"]["lessons"] is False
    assert graph.VERSIONS["v7_vector"]["strict_verifier"] is True


def test_real_graph_preserves_app_fallback_scope_and_verifier(monkeypatch):
    mock_rerank(monkeypatch)
    monkeypatch.setattr(guardian, "screen", lambda q: (guardian.decide(q), None))
    monkeypatch.setattr(concierge, "route", lambda *a, **kw: {"route": "care", "usage": None})
    def care(*a, **kw):
        hits = retrieval.search_reranked("q", source_ids=["A", "B"])
        return {"answer": "Sourced answer", "sources_cited": ["A"], "hits": hits, "usage": [], "agent": "care"}
    monkeypatch.setattr(graph.care, "answer", care)
    monkeypatch.setattr(graph.verifier, "verify", lambda *a, **kw: {"verdict": "passed", "answer": "Verified answer", "sources_cited": ["A"], "unsupported": [], "usage": []})
    app = graph.ask("question", version="v6+lessons")
    assert app["error"] is None and app["answer"] == "Verified answer" and app["retrieval_fallback"] == "vector_order"
    assert app["verification"]["verdict"] == "passed" and any("vector order" in step for step in app["steps"])
    strict = graph.ask("question", version="v6")
    assert "RerankError" in strict["error"] and strict["retrieval_fallback"] is None


def test_ready_vector_variant_preserves_ready_and_staged_care_sources(monkeypatch):
    seen = []
    def vector(query, source_ids=None, **kw):
        seen.append(source_ids)
        return []
    monkeypatch.setattr(retrieval, "search_vector", vector)
    monkeypatch.setattr(retrieval, "search_reranked", lambda *a, **kw: pytest.fail("Ready vector mode attempted rerank"))
    monkeypatch.setattr(ready, "answer_from_sources", lambda *a, **kw: {"answer": "checklist", "sources_cited": []})
    out = ready.answer("What should I pack?", {"life_stage": "pregnancy", "week": 30}, mode="staged_vector")
    assert out["agent"] == "ready"
    assert set(retrieval.sources_for("ready")) <= set(seen[0])
    assert "WHO-ANC" in seen[0] and "WHO-POSTNATAL" not in seen[0]
