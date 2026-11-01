import ast
import pathlib
from types import SimpleNamespace

import pytest

from nestling import llm
from nestling.agents import policy

SCHEMA = {"type": "object", "properties": {"route": {"type": "string", "enum": ["a", "b"]}},
          "required": ["route"], "additionalProperties": False}


def reply(text):
    return SimpleNamespace(model="m", usage=SimpleNamespace(prompt_tokens=3, completion_tokens=2),
                           choices=[SimpleNamespace(message=SimpleNamespace(content=text))])


class FakeClient:
    def __init__(self, replies):
        self.replies, self.calls = list(replies), []
        self.chat = SimpleNamespace(completions=SimpleNamespace(create=self.create))

    def create(self, **kwargs):
        self.calls.append(kwargs)
        r = self.replies.pop(0)
        if isinstance(r, Exception):
            raise r
        return r


class Rejected(Exception):
    status_code = 400


def test_chat_json_schema_path(monkeypatch):
    fake = FakeClient([reply('{"route": "b"}')])
    monkeypatch.setattr(llm, "client", lambda: fake)
    data, usage, raw = llm.chat_json(llm.FAST, "sys", "user", SCHEMA)
    assert data == {"route": "b"} and raw == '{"route": "b"}'
    assert usage == {"model": "m", "tokens_in": 3, "tokens_out": 2}
    assert fake.calls[0]["response_format"]["type"] == "json_schema"


def test_chat_json_falls_back_to_json_mode(monkeypatch):
    fake = FakeClient([Rejected("no json_schema"), reply('{"route": "a"}')])
    monkeypatch.setattr(llm, "client", lambda: fake)
    data, _, _ = llm.chat_json(llm.MAIN, "sys", "user", SCHEMA)
    assert data == {"route": "a"}
    assert fake.calls[1]["response_format"] == {"type": "json_object"}
    assert "JSON schema" in fake.calls[1]["messages"][0]["content"]


def test_chat_json_invalid_reply_is_none(monkeypatch):
    monkeypatch.setattr(llm, "client", lambda: FakeClient([reply('{"route": "zzz"}')]))
    assert llm.chat_json(llm.FAST, "s", "u", SCHEMA)[0] is None


def test_chat_json_other_errors_raise(monkeypatch):
    err = Exception("boom")
    err.status_code = 500
    monkeypatch.setattr(llm, "client", lambda: FakeClient([err]))
    with pytest.raises(Exception, match="boom"):
        llm.chat_json(llm.FAST, "s", "u", SCHEMA)


def test_policy_quotes_must_appear_verbatim_on_their_page():
    pages = ["Maternity cover  starts after a\n24 month waiting period.", "Room rent is capped at 1% of the sum insured."]
    quotes = [
        {"text": "maternity cover starts after a 24 month waiting period", "page": 1},  # spacing and case differ: ok
        {"text": "Room rent is capped at 1% of the sum insured.", "page": 1},  # wrong page
        {"text": "NICU is fully covered", "page": 2},  # invented
        {"text": "Room rent is capped at 1% of the sum insured.", "page": 2},
        {"text": "x", "page": 9},
    ]
    kept = policy.verified_quotes(quotes, pages)
    assert [(q["page_start"], q["text"][:4]) for q in kept] == [(1, "mate"), (2, "Room")]


def test_policy_without_surviving_quote_says_none_found(monkeypatch):
    monkeypatch.setattr(policy, "read_pages", lambda pdf: ["Waiting period is 24 months."])
    monkeypatch.setattr(policy, "chat_json", lambda *a, **k: (
        {"answer": "Covered fully", "quotes": [{"text": "fully covered", "page": 1}]}, {"model": "m", "tokens_in": 1, "tokens_out": 1}, ""))
    out = policy.ask_policy("is NICU covered?", b"%PDF")
    assert out["quotes"] == [] and out["answer"].startswith("I couldn't find this in your policy")


def test_only_baseline_imports_anthropic():
    root = pathlib.Path(__file__).resolve().parents[1]
    offenders = []
    for path in [*root.glob("nestling/**/*.py"), *root.glob("api/**/*.py")]:
        for node in ast.walk(ast.parse(path.read_text(encoding="utf-8"))):
            names = [a.name for a in node.names] if isinstance(node, ast.Import) else [node.module or ""] if isinstance(node, ast.ImportFrom) else []
            if any(n.split(".")[0] == "anthropic" for n in names):
                offenders.append(path.name)
    assert set(offenders) <= {"baseline.py"}, offenders


HITS = [{"source_id": "WHO-ANC", "page_label": "34", "chunk_text": "x"}, {"source_id": "MOHFW-ANC", "page_label": "28", "chunk_text": "y"}]


def test_enforce_citations_normalises_and_keeps_real_ones():
    from nestling.agents import enforce_citations

    text, kept = enforce_citations("Rest well [who-anc page 34]. Pack the bag (MOHFW-ANC p. 28).", [], HITS)
    assert text == "Rest well (WHO-ANC, p. 34). Pack the bag (MOHFW-ANC, p. 28)."
    assert kept == ["WHO-ANC", "MOHFW-ANC"]


def test_enforce_citations_drops_invented_sources_and_pages():
    from nestling.agents import enforce_citations

    text, kept = enforce_citations(
        "Eat dal (ICMR-NIN-DG, p. 5). See a doctor (WHO-ANC, p. 99). Drink water (WHO-ANC, p. 34).",
        ["ICMR-NIN-DG", "WHO-ANC", "FAKE-ID"], HITS)
    assert text == "Eat dal. See a doctor. Drink water (WHO-ANC, p. 34)."
    assert kept == ["WHO-ANC"]


def test_enforce_citations_without_passages_cites_nothing():
    from nestling.agents import enforce_citations

    text, kept = enforce_citations("Fine (WHO-ANC, p. 34).", ["WHO-ANC"], [])
    assert kept == [] and "WHO-ANC" not in text


def test_answer_from_sources_enforces_citations(monkeypatch):
    from nestling import agents

    monkeypatch.setattr(agents, "main_json", lambda *a, **k: (
        {"answer": "Yes (WHO-ANC, p. 34) and (BOGUS-ID, p. 1).", "sources_cited": ["WHO-ANC", "BOGUS-ID"]}, {"model": "m"}, ""))
    out = agents.answer_from_sources("Care", "q", {}, HITS)
    assert out["sources_cited"] == ["WHO-ANC"] and "BOGUS" not in out["answer"]
