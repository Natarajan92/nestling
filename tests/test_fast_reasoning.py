"""Offline caller-scoped FAST latency experiments; no hosted model calls."""

import copy
import json
from threading import Barrier, Lock
from types import SimpleNamespace

import pytest

from nestling import concierge, graph, guardian, llm


SCHEMA = {"type": "object", "properties": {"route": {"type": "string"}},
          "required": ["route"], "additionalProperties": False}


def response(data, model=llm.FAST, tokens_in=3, tokens_out=2):
    return SimpleNamespace(model=model, usage=SimpleNamespace(prompt_tokens=tokens_in, completion_tokens=tokens_out),
                           choices=[SimpleNamespace(message=SimpleNamespace(content=json.dumps(data)))])


class Rejected(Exception):
    status_code = 400


class Responses:
    def __init__(self, replies):
        self.replies = iter(replies)
        self.calls = []
        self.chat = SimpleNamespace(completions=SimpleNamespace(create=self.create))

    def create(self, **kwargs):
        self.calls.append(copy.deepcopy(kwargs))
        reply = next(self.replies)
        if isinstance(reply, Exception):
            raise reply
        return reply


@pytest.mark.parametrize("effort", [None, "none", "low"])
@pytest.mark.parametrize("fallback", [False, True])
def test_chat_json_preserves_explicit_effort_and_omits_default(monkeypatch, effort, fallback):
    replies = ([Rejected("json_schema is unsupported")] if fallback else []) + [response({"route": "care"})]
    fake = Responses(replies)
    monkeypatch.setattr(llm, "client", lambda: fake)
    kwargs = {} if effort is None else {"reasoning_effort": effort}
    parsed, usage, raw = llm.chat_json(llm.FAST, "system", "question", SCHEMA, max_tokens=71, **kwargs)
    assert parsed == {"route": "care"} and json.loads(raw) == parsed
    assert usage == {"model": llm.FAST, "tokens_in": 3, "tokens_out": 2}
    assert [c["response_format"]["type"] for c in fake.calls] == (
        ["json_schema", "json_object"] if fallback else ["json_schema"])
    for call in fake.calls:
        assert call["max_tokens"] == 71 and call["temperature"] == 0
        assert ({"reasoning_effort": call["reasoning_effort"]} if "reasoning_effort" in call else {}) == kwargs


@pytest.mark.parametrize("effort", ["medium", "high", "", False])
def test_invalid_effort_fails_before_provider_access(monkeypatch, effort):
    def unavailable():
        pytest.fail("invalid effort must be rejected before constructing a client")

    monkeypatch.setattr(llm, "client", unavailable)
    with pytest.raises(ValueError, match="reasoning_effort"):
        llm.chat_json(llm.FAST, "system", "question", SCHEMA, reasoning_effort=effort)


@pytest.mark.parametrize("error", [Rejected("unsupported reasoning_effort"), RuntimeError("transport unavailable"),
                                   Rejected("unsupported reasoning_effort with response_format=json_schema")])
def test_effort_errors_propagate_without_retrying_or_dropping_parameter(monkeypatch, error):
    fake = Responses([error, response({"route": "care"})])
    monkeypatch.setattr(llm, "client", lambda: fake)
    with pytest.raises(type(error)) as caught:
        llm.chat_json(llm.FAST, "system", "question", SCHEMA, reasoning_effort="none")
    assert caught.value is error
    assert len(fake.calls) == 1 and fake.calls[0]["reasoning_effort"] == "none"


def test_schema_fallback_effort_error_is_not_retried(monkeypatch):
    error = Rejected("unsupported reasoning_effort")
    fake = Responses([Rejected("no json_schema"), error, response({"route": "care"})])
    monkeypatch.setattr(llm, "client", lambda: fake)
    with pytest.raises(Rejected) as caught:
        llm.chat_json(llm.FAST, "system", "question", SCHEMA, reasoning_effort="low")
    assert caught.value is error
    assert [c["reasoning_effort"] for c in fake.calls] == ["low", "low"]


def test_main_and_explicit_none_keep_provider_default(monkeypatch):
    fake = Responses([response({"route": "care"}, model=llm.MAIN)])
    monkeypatch.setattr(llm, "client", lambda: fake)
    llm.chat_json(llm.MAIN, "system", "question", SCHEMA, reasoning_effort=None)
    assert "reasoning_effort" not in fake.calls[0]


def test_ordinary_fast_call_shapes_do_not_gain_new_kwargs(monkeypatch):
    def unchanged_chat(model, system, user, schema, max_tokens=3000):
        data = {"route": "ready"} if "route" in schema["properties"] else {"red_flags": [], "unsafe": []}
        return data, {"model": model, "tokens_in": 3, "tokens_out": 2}, ""

    monkeypatch.setattr(guardian, "chat_json", unchanged_chat)
    monkeypatch.setattr(concierge, "chat_json", unchanged_chat)
    assert guardian.classify("Pack a charger")["unsafe"] == []
    assert concierge.route("Pack a charger")["route"] == "ready"
    monkeypatch.setattr(guardian, "classify", lambda text: {"red_flags": [], "unsafe": [], "usage": None})
    assert guardian.screen("Pack a charger")[0].escalate is False


@pytest.mark.parametrize("version,effort", [
    ("v7_vector_safe+lessons", None), ("v7", None),
    ("latency_fast_direct", "none"), ("latency_fast_low", "low"),
    ("latency_fast_direct_warm", "none"), ("latency_fast_low_warm", "low"),
])
def test_graph_runs_both_fast_roles_in_parallel_and_counts_usage_once(monkeypatch, version, effort):
    # A serialized implementation cannot complete this rendezvous. Mock only the external SDK.
    together = Barrier(2)
    lock, calls = Lock(), []

    def create(**kwargs):
        with lock:
            calls.append(kwargs)
        together.wait(timeout=3)
        if kwargs["messages"][0]["content"].startswith("You screen"):
            return response({"red_flags": [], "unsafe": []})
        return response({"route": "out_of_scope"}, tokens_in=5, tokens_out=4)

    monkeypatch.setattr(llm, "client", lambda: SimpleNamespace(chat=SimpleNamespace(completions=SimpleNamespace(create=create))))
    out = graph.ask("Which phone should I buy?", version=version)
    assert out["error"] is None and out["route"] == "out_of_scope"
    assert out["tokens_in"] == 8 and out["tokens_out"] == 6
    assert len(calls) == 2 and all(c["model"] == llm.FAST for c in calls)
    assert out["cost_inr"] == 0.0009  # independently: per-call rounded INR 0.0003 + 0.0006
    assert [c.get("reasoning_effort") for c in calls] == [effort, effort]
    if effort is None:
        assert all("reasoning_effort" not in c for c in calls)


@pytest.mark.parametrize("version,effort", [("latency_fast_direct", "none"), ("latency_fast_low", "low")])
def test_deferred_concierge_uses_candidate_effort_without_losing_usage(monkeypatch, version, effort):
    fake = Responses([response({"route": "ready"})])
    monkeypatch.setattr(llm, "client", lambda: fake)
    state = {"question": "Pack a charger", "flags": graph.VERSIONS[version], "proposed_route": None}
    out = graph.concierge_node(state)
    assert out["route"] == "ready" and out["usage"] == [{"model": llm.FAST, "tokens_in": 3, "tokens_out": 2}]
    assert fake.calls[0]["reasoning_effort"] == effort


@pytest.mark.parametrize("effort", ["none", "low"])
def test_candidate_classifier_still_checks_quotes_and_unsafe_labels_in_code(monkeypatch, effort):
    fake = Responses([response({"red_flags": [
        {"sign": "RF-BLEEDING", "quote": "bleeding"},  # invented quote cannot escalate
        {"sign": "RF-FEVER", "quote": "head feels hot"},  # verbatim with matching family is accepted
        {"sign": "RF-BREATHING", "quote": "head feels hot"}], "unsafe": ["prescription"]})])
    monkeypatch.setattr(llm, "client", lambda: fake)
    decision, usage = guardian.screen("My head feels hot today", reasoning_effort=effort)
    assert decision.escalate and decision.red_flags == ["RF-FEVER"]
    assert decision.classifier_flags == ["RF-FEVER"] and not decision.refuse and decision.unsafe == []
    assert decision.sources and "MOHFW-ANC" in decision.reply
    assert usage == {"model": llm.FAST, "tokens_in": 3, "tokens_out": 2}
    assert fake.calls[0]["reasoning_effort"] == effort


@pytest.mark.parametrize("version", ["latency_fast_direct", "latency_fast_low_warm"])
def test_code_escalation_skips_all_model_calls_in_candidate(monkeypatch, version):
    monkeypatch.setattr(llm, "client", lambda: pytest.fail("code escalation must skip both FAST roles"))
    out = graph.ask("My baby is not breathing", version=version)
    assert out["error"] is None and out["escalate"] and out["route"] == "guardian"
    assert "RF-ABSENT-BREATHING" in out["rules_fired"]
    assert out["sources_cited"] == ["NHS-CHILD-CPR"] and out["tokens_in"] == 0 and out["tokens_out"] == 0


def test_candidates_are_isolated_and_keep_full_strict_verifier(monkeypatch):
    assert graph.APP_VERSION == "v7_vector_safe+lessons"
    assert graph.VERSIONS[graph.APP_VERSION] == {"concierge": True, "retrieval": "staged_vector", "verifier": True,
                                               "strict_verifier": True, "lessons": True}
    candidates = {"latency_fast_direct", "latency_fast_low", "latency_fast_direct_warm", "latency_fast_low_warm"}
    tags = [graph.PROMPT_VERSIONS[v] for v in candidates]
    assert len(set(tags)) == 4 and not (set(tags) & {t for v, t in graph.PROMPT_VERSIONS.items() if v not in candidates})
    for version, flags in graph.VERSIONS.items():
        if version not in candidates:
            assert "fast_reasoning_effort" not in flags and "prewarm_sources" not in flags
    calls = []

    def verify(answer, source_ids, hits, **kwargs):
        calls.append(kwargs)
        return {"verdict": "passed", "answer": answer, "sources_cited": source_ids, "unsupported": [], "usage": []}

    monkeypatch.setattr(graph.verifier, "verify", verify)
    for version in sorted(candidates):
        flags = graph.VERSIONS[version]
        assert flags["retrieval"] == "staged_vector" and flags["lessons"] and flags["verifier"]
        assert flags.get("prewarm_sources", False) == version.endswith("_warm")
        graph.verifier_node({"flags": flags, "result": {"answer": "Sourced answer", "sources_cited": [], "hits": []}})
    assert calls == [{"strict": True}] * 4


@pytest.mark.parametrize("version,effort", [("latency_fast_direct", "none"), ("latency_fast_low_warm", "low")])
def test_care_candidate_leaves_specialist_and_full_strict_main_checker_unchanged(monkeypatch, version, effort):
    passage = {"source_id": "WHO-ANC", "page_label": "34", "chunk_text": "Discuss concerns at antenatal visits.", "score": 1.0}
    monkeypatch.setattr(graph.retrieval, "search", lambda *args, **kwargs: [passage])
    calls = []

    def create(**kwargs):
        calls.append(kwargs)
        properties = kwargs["response_format"]["json_schema"]["schema"]["properties"]
        if "red_flags" in properties:
            return response({"red_flags": [], "unsafe": []})
        if "route" in properties:
            return response({"route": "care"})
        if "claims" in properties:
            return response({"claims": [{"claim": "Discuss concerns at antenatal visits.", "supported": True}]}, model=llm.MAIN)
        return response({"answer": "Discuss concerns at antenatal visits. (WHO-ANC, p. 34)", "sources_cited": ["WHO-ANC"]}, model=llm.MAIN)

    monkeypatch.setattr(llm, "client", lambda: SimpleNamespace(chat=SimpleNamespace(completions=SimpleNamespace(create=create))))
    out = graph.ask("What happens at routine antenatal visits?", version=version)
    assert out["error"] is None and out["route"] == "care"
    assert out["answer"] == "Discuss concerns at antenatal visits. (WHO-ANC, p. 34)"
    assert out["verification"] == {"verdict": "passed", "unsupported": []}
    assert out["sources_cited"] == ["WHO-ANC"] and out["tokens_in"] == 12 and out["tokens_out"] == 8
    fast_calls, main_calls = [c for c in calls if c["model"] == llm.FAST], [c for c in calls if c["model"] == llm.MAIN]
    assert len(fast_calls) == len(main_calls) == 2
    assert all(c["reasoning_effort"] == effort for c in fast_calls)
    assert all("reasoning_effort" not in c for c in main_calls)
    assert main_calls[-1]["messages"][0]["content"] == graph.verifier.STRICT_CHECK_PROMPT
    assert main_calls[-1]["response_format"]["json_schema"]["schema"] == graph.verifier.CHECK_SCHEMA
