"""Source-client startup uses the search cache without querying or writing documents."""

import os
from types import SimpleNamespace
from unittest.mock import Mock

os.environ["LANGSMITH_TRACING"] = "false"

import pytest
from fastapi.testclient import TestClient

from api import main
from nestling import graph, llm, retrieval


@pytest.fixture
def source_client(monkeypatch):
    retrieval._search_index.cache_clear()
    documents = Mock()
    documents.search.return_value = SimpleNamespace(matches=[])
    index = SimpleNamespace(documents=documents)
    pc = SimpleNamespace(has_index=Mock(return_value=True),
                         describe_index=Mock(return_value=SimpleNamespace(host="trusted-source-host")),
                         index=Mock(return_value=index), inference=Mock(), indexes=Mock())
    constructor = Mock(return_value=pc)
    monkeypatch.setattr(retrieval, "Pinecone", constructor)
    monkeypatch.setenv("PINECONE_INDEX", "trusted-sources")
    try:
        yield constructor, pc, documents
    finally:
        retrieval._search_index.cache_clear()


def test_repeated_warmup_and_search_share_one_client_without_warmup_queries(source_client):
    constructor, pc, documents = source_client

    assert retrieval.warm_sources() is None
    assert retrieval.warm_sources() is None
    assert documents.mock_calls == []
    assert pc.inference.mock_calls == []
    assert pc.indexes.mock_calls == []

    assert retrieval.search("registered evidence", source_ids=["WHO-POSTNATAL"]) == []
    constructor.assert_called_once_with()
    pc.has_index.assert_called_once_with("trusted-sources")
    pc.describe_index.assert_called_once_with("trusted-sources")
    pc.index.assert_called_once_with(host="trusted-source-host")
    documents.search.assert_called_once_with(
        namespace="sources", top_k=5,
        score_by=[{"type": "embed", "fields": ["chunk_text"], "query": "registered evidence"}],
        include_fields=retrieval.CITATION_FIELDS,
        filter={"source_id": {"$in": ["WHO-POSTNATAL"]}},
    )
    assert [call[0] for call in documents.mock_calls] == ["search"]


def test_failed_warmup_can_be_retried_without_caching_failure(source_client):
    constructor, pc, documents = source_client
    pc.describe_index.side_effect = [TimeoutError("provider details"), SimpleNamespace(host="trusted-source-host")]

    with pytest.raises(TimeoutError):
        retrieval.warm_sources()
    assert retrieval.warm_sources() is None
    assert retrieval.search("registered evidence") == []
    assert constructor.call_count == 2
    assert pc.describe_index.call_count == 2
    assert [call[0] for call in documents.mock_calls] == ["search"]


@pytest.mark.parametrize("flag,expected", [(None, "skipped"), (False, "skipped"), (True, "ready")])
def test_startup_only_warms_when_selected_version_enables_it(monkeypatch, flag, expected):
    flags = {**graph.VERSIONS[graph.APP_VERSION]}
    flags.pop("prewarm_sources", None)
    if flag is not None:
        flags["prewarm_sources"] = flag
    monkeypatch.setitem(graph.VERSIONS, graph.APP_VERSION, flags)
    warmup = Mock(return_value=None)
    monkeypatch.setattr(main, "warm_sources", warmup, raising=False)

    with TestClient(main.app) as client:
        assert client.get("/api/health").json()["ok"] is True
        assert main.app.state.sources_warmup == expected
    assert warmup.call_count == (1 if flag else 0)


def test_current_app_startup_does_not_warm_sources(monkeypatch):
    warmup = Mock(side_effect=AssertionError("default startup contacted Pinecone"))
    monkeypatch.setattr(main, "warm_sources", warmup, raising=False)

    with TestClient(main.app) as client:
        assert client.get("/api/health").status_code == 200
        assert main.app.state.sources_warmup == "skipped"
    warmup.assert_not_called()


def test_warmup_outage_keeps_health_and_rule_owned_escalation_available(monkeypatch, caplog, capsys):
    monkeypatch.setitem(graph.VERSIONS, graph.APP_VERSION,
                        {**graph.VERSIONS[graph.APP_VERSION], "prewarm_sources": True})
    private_error = "provider-private-details-must-not-be-retained"
    monkeypatch.setattr(main, "warm_sources", Mock(side_effect=TimeoutError(private_error)), raising=False)
    monkeypatch.setattr(llm, "chat_json", lambda *a, **kw: pytest.fail("red flag called a model"))
    monkeypatch.setattr(retrieval, "search", lambda *a, **kw: pytest.fail("red flag searched sources"))

    with TestClient(main.app) as client:
        assert main.app.state.sources_warmup == "degraded"
        assert client.get("/api/health").json()["ok"] is True
        response = client.post("/api/ask", json={"message": "I am bleeding heavily right now"})
        assert response.status_code == 200
        assert response.json()["escalate"] is True
        assert response.json()["guardian"]["rules_fired"]
        assert response.json()["sources"]
        assert private_error not in response.text
        assert private_error not in repr(main.app.state._state)
    captured = capsys.readouterr()
    assert private_error not in caplog.text + captured.out + captured.err
