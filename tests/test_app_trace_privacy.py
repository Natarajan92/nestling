"""Inspect real SDK export payloads without contacting LangSmith or providers."""

import copy
from concurrent.futures import ThreadPoolExecutor
from threading import Barrier

import pytest
from fastapi.testclient import TestClient
from langsmith import Client, traceable, tracing_context

from api import main
from nestling import tracing

PRIVATE = "PRIVATE_SENTINEL due date 2027-01-02 and policy health details"


@pytest.fixture
def exports(monkeypatch):
    captured = []
    monkeypatch.setattr(Client, "request_with_retries", lambda *a, **kw: pytest.fail("unexpected LangSmith network call"))

    class OfflineClient(Client):
        def __init__(self, **kwargs):
            super().__init__(api_url="http://localhost:1", api_key="offline-only", auto_batch_tracing=False, **kwargs)

        def _create_run(self, data, **kwargs):
            captured.append((self, "create", copy.deepcopy(data)))

        def _update_run(self, data, **kwargs):
            captured.append((self, "update", copy.deepcopy(data)))

    # Before the fix the request inherits this ordinary eval client; afterwards
    # the app factory constructs its separate client through the same SDK boundary.
    monkeypatch.setattr(main, "Client", OfflineClient, raising=False)
    if hasattr(main, "app_trace_client"):
        main.app_trace_client.cache_clear()
    yield captured, OfflineClient(hide_inputs=False, hide_outputs=False)
    if hasattr(main, "app_trace_client"):
        main.app_trace_client.cache_clear()


def test_nested_app_failure_exports_no_private_inputs_outputs_or_error(exports, monkeypatch):
    captured, eval_client = exports

    @traceable(name="private_policy_provider")
    def provider(question, pdf):
        raise RuntimeError(PRIVATE)

    from nestling.agents import policy
    monkeypatch.setattr(policy, "ask_policy", provider)
    with tracing_context(enabled=True, client=eval_client):
        response = TestClient(main.app, raise_server_exceptions=False).post(
            "/api/policy/ask", data={"question": PRIVATE},
            files={"file": ("private-policy.pdf", PRIVATE.encode(), "application/pdf")})
    assert response.status_code >= 500
    assert PRIVATE not in response.text
    assert captured, "the app must retain sanitized failure traces"
    assert PRIVATE not in repr([data for _, _, data in captured])
    assert any(data.get("error") == "pipeline_error" for _, _, data in captured)


def test_real_graph_child_failure_uses_app_export_policy(exports, monkeypatch):
    from nestling import concierge, guardian
    captured, eval_client = exports

    def provider(*args, **kwargs):
        raise RuntimeError(PRIVATE)

    monkeypatch.setattr(guardian, "chat_json", provider)
    monkeypatch.setattr(concierge, "chat_json", lambda *a, **kw: ({"route": "clarify"}, None, ""))
    with tracing_context(enabled=True, client=eval_client):
        response = TestClient(main.app).post("/api/ask", json={"message": PRIVATE})
    assert response.status_code == 200 and response.json()["route"] == "clarify"
    assert PRIVATE not in repr([data for _, _, data in captured])
    assert any(data.get("name") == "guardian_classifier" for _, _, data in captured)
    assert any(data.get("error") == "pipeline_error" for _, _, data in captured)


def test_app_success_keeps_safe_ask_metadata_and_hides_nested_content(exports, monkeypatch):
    from test_api import answer
    captured, eval_client = exports

    @traceable(name="private_nested_answer")
    def nested(message, context, **kwargs):
        return answer(answer=PRIVATE)

    monkeypatch.setattr(main.graph, "ask", nested)
    with tracing_context(enabled=True, client=eval_client):
        response = TestClient(main.app).post("/api/ask", json={"message": PRIVATE})
    assert response.status_code == 200 and response.json()["answer"] == PRIVATE
    assert PRIVATE not in repr([data for _, _, data in captured])
    metadata = [data.get("extra", {}).get("metadata", {}) for _, _, data in captured]
    assert any(set(tracing.METADATA_KEYS) <= set(m) and m["predicted_route"] == "care" for m in metadata)


def test_app_trace_client_isolated_from_concurrent_full_eval_trace(exports, monkeypatch):
    captured, eval_client = exports
    barrier = Barrier(2)
    from nestling.agents import policy

    @traceable(name="private_policy_provider")
    def provider(question, pdf):
        barrier.wait(timeout=15)
        raise RuntimeError(PRIVATE)

    @traceable(name="eval_control")
    def evaluation(value):
        barrier.wait(timeout=15)
        return value

    monkeypatch.setattr(policy, "ask_policy", provider)

    def app_request():
        with tracing_context(enabled=True, client=eval_client):
            return TestClient(main.app, raise_server_exceptions=False).post(
                "/api/policy/ask", data={"question": PRIVATE},
                files={"file": ("p.pdf", b"pdf", "application/pdf")})

    def eval_request():
        with tracing_context(enabled=True, client=eval_client):
            return evaluation("eval-visible-control")

    with ThreadPoolExecutor(2) as pool:
        app_future, eval_future = pool.submit(app_request), pool.submit(eval_request)
        assert app_future.result().status_code >= 500
        assert eval_future.result() == "eval-visible-control"
    assert PRIVATE not in repr([data for _, _, data in captured])
    eval_payloads = [data for owner, _, data in captured if owner is eval_client]
    assert any(data.get("inputs", {}).get("value") == "eval-visible-control" for data in eval_payloads)
    assert any(data.get("outputs", {}).get("output") == "eval-visible-control" for data in eval_payloads)


def test_capture_worker_preserves_app_client_metadata_and_error_redaction(exports, monkeypatch):
    import langsmith.run_trees as run_trees
    from nestling.capture import search

    captured, fallback_client = exports
    # A lost context must remain visible as an unsafe default-client export,
    # rather than disappear because the worker's environment disables tracing.
    monkeypatch.setenv("LANGSMITH_TRACING", "true")
    monkeypatch.setattr(run_trees, "get_cached_client", lambda **kw: fallback_client)
    page = {"url": "https://example.test/package", "title": "Public studio",
            "raw_content": "Public studio package description. " * 30}
    monkeypatch.setattr(search, "search_studios", lambda *a, **kw: [page])

    def provider(*args, **kwargs):
        raise RuntimeError(PRIVATE)

    monkeypatch.setattr(search, "chat_json", provider)
    with tracing_context(enabled=True, client=fallback_client):
        response = TestClient(main.app).post("/api/capture/search", json={"city": "Bengaluru", "shoot_type": "maternity"})
    assert response.status_code == 200 and response.json()["packages"] == []
    assert PRIVATE not in repr([data for _, _, data in captured])
    workers = [(owner, data) for owner, _, data in captured if data.get("name") == "extract_package"]
    assert workers, "actual extraction worker must remain traced"
    assert all(owner is main.app_trace_client() for owner, _ in workers)
    assert all(set(tracing.METADATA_KEYS) <= set(data.get("extra", {}).get("metadata", {})) for _, data in workers)
    assert any(data.get("error") == "pipeline_error" for _, _, data in captured)


def test_code_owned_emergency_exports_rule_ids_and_promoted_app_provenance(exports, monkeypatch):
    from nestling import concierge, guardian
    captured, fallback_client = exports
    message = "My newborn is not breathing"

    def paid(*args, **kwargs):
        pytest.fail("code-owned emergency must not call a provider")

    monkeypatch.setattr(guardian, "chat_json", paid)
    monkeypatch.setattr(concierge, "route", paid)
    with tracing_context(enabled=True, client=fallback_client):
        response = TestClient(main.app).post("/api/ask", json={"message": message})
    assert response.status_code == 200 and response.json()["escalate"]
    root = [data for _, op, data in captured if op == "update" and data.get("name") == "nestling_app_ask"][-1]
    metadata = root["extra"]["metadata"]
    assert metadata["rules_fired"] == ["RF-ABSENT-BREATHING"]
    assert metadata["predicted_route"] == "guardian" and metadata["model"] == "rules"
    assert metadata["sources_cited"] == ["NHS-CHILD-CPR"]
    assert metadata["pipeline_version"] == "v7_vector_safe+lessons"
    assert metadata["prompt_version"] == "app-v7-vector-safe-lessons-v2-prenatal"
    assert root.get("outputs") == {} and message not in repr([data for _, _, data in captured])


@pytest.mark.parametrize("rules,want", [(["RF-BLUE-LIPS", PRIVATE, "RF-BLUE-LIPS"], ["RF-BLUE-LIPS"]), ([], [])])
def test_app_rule_metadata_is_a_deduplicated_closed_id_list(exports, monkeypatch, rules, want):
    from test_api import answer
    captured, fallback_client = exports
    monkeypatch.setattr(main.graph, "ask", lambda *a, **kw: answer(rules_fired=rules))
    with tracing_context(enabled=True, client=fallback_client):
        response = TestClient(main.app).post("/api/ask", json={"message": "A general question"})
    assert response.status_code == 200
    metadata = [data["extra"]["metadata"] for _, op, data in captured
                if op == "update" and data.get("name") == "nestling_app_ask"][-1]
    assert metadata["rules_fired"] == want
    assert PRIVATE not in repr([data for _, _, data in captured])
