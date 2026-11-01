"""Runtime lessons stay reviewed, closed-set, and behind the app-only flag."""

import json

import pytest
import yaml

from nestling import concierge, graph, guardian, llm, retrieval
from nestling.lessons import library


@pytest.fixture
def lesson_root(monkeypatch, tmp_path):
    monkeypatch.setattr(library, "LESSONS_DIR", tmp_path)
    folder = tmp_path / "cord_care"
    (folder / "renders").mkdir(parents=True)
    board = {"lesson_id": "cord_care", "title": "Cord care", "version": 2, "stage": "first_weeks",
             "sources": ["WHO-POSTNATAL"], "see_how": None,
             "scenes": [{"step_no": n, "caption": "Keep clean and dry", "narration_line": "Keep the cord clean and dry.",
                         "source_id": "WHO-POSTNATAL", "page_label": "120", "icon": "drop", "safety_points": []}
                        for n in range(1, 5)]}
    (folder / "storyboard.json").write_text(json.dumps(board), encoding="utf-8")
    review = {"lesson_id": "cord_care", "version": 2, "approved": True, "reviewer": "Human",
              "review_date": "2026-11-01", "scenes": [{"step_no": n, "passed": True} for n in range(1, 5)]}
    (folder / "review.yaml").write_text(yaml.safe_dump(review), encoding="utf-8")
    (folder / "phrasings.yaml").write_text(yaml.safe_dump({"phrasings": ["How do I clean the cord?"]}), encoding="utf-8")
    (folder / "renders" / "lesson.mp4").write_bytes(b"video")
    (folder / "renders" / "thumbnail.jpg").write_bytes(b"image")
    return tmp_path


def test_payload_is_shared_public_schema(lesson_root):
    out = library.payload("cord_care")
    assert set(out) == {"lesson_id", "title", "version", "stage", "video_url", "thumbnail_url", "steps", "sources", "see_how", "reviewed_on"}
    assert out["version"] == 2 and out["reviewed_on"] == "2026-11-01"
    assert out["video_url"] == "/media/lessons/cord_care/lesson.mp4"
    assert out["sources"][0]["id"] == "WHO-POSTNATAL" and out["sources"][0]["page"] == "120"
    assert set(out["steps"][0]) == {"step_no", "caption", "narration_line", "icon", "safety_points"}


def test_review_must_cover_same_scenes_and_be_human(lesson_root):
    path = lesson_root / "cord_care" / "review.yaml"
    review = yaml.safe_load(path.read_text())
    review["scenes"][-1]["step_no"] = 3
    path.write_text(yaml.safe_dump(review))
    assert library.payload("cord_care") is None
    review["scenes"][-1]["step_no"] = 4
    review["reviewer"] = None
    path.write_text(yaml.safe_dump(review))
    assert library.payload("cord_care") is None


def test_all_six_phrasing_sets_are_indexed_without_connecting(monkeypatch):
    monkeypatch.setattr(retrieval, "get_index", lambda **kw: pytest.fail("dry-run contacted Pinecone"))
    out = library.index_phrasings()
    assert out["namespace"] == "lessons" and out["dry_run"] is True
    assert {r["lesson_id"] for r in out["records"]} == {"holding", "bathing", "burping", "swaddling", "latching", "cord_care"}
    assert 36 <= len(out["records"]) <= 48
    assert len({r["_id"] for r in out["records"]}) == len(out["records"])
    assert all(r["chunk_text"] and r["title"] for r in out["records"])


def test_upsert_only_targets_lessons(monkeypatch):
    calls = []
    class Documents:
        def upsert(self, **kw):
            calls.append(kw)
    class Index:
        documents = Documents()
    monkeypatch.setattr(retrieval, "get_index", lambda **kw: Index())
    out = library.index_phrasings(dry_run=False)
    assert out["dry_run"] is False and calls
    assert all(c["namespace"] == "lessons" for c in calls)
    assert sum(len(c["documents"]) for c in calls) == len(out["records"])


def test_match_is_closed_set_and_reads_unrendered_phrasings(monkeypatch):
    def fake(model, system, user, schema, **kwargs):
        assert model == llm.FAST and "burping" in system and "swaddling" in system
        assert "phrasings" in system and "none" in schema["properties"]["lesson_id"]["enum"]
        return {"lesson_id": "bathing"}, {}, ""
    monkeypatch.setattr(llm, "chat_json", fake)
    assert library.match("How do I bathe her?") == {"lesson_id": "bathing", "topic": "bathing"}
    monkeypatch.setattr(llm, "chat_json", lambda *a, **kw: ({"lesson_id": "private symptom text"}, {}, ""))
    assert library.match("Private symptom text") == {"lesson_id": None, "topic": "newborn_care"}


def test_concierge_lessons_route_does_not_change_measured_prompt(monkeypatch):
    seen = []
    def fake(model, system, user, schema, **kw):
        seen.append((system, user, schema))
        return {"route": "lessons" if "lessons" in schema["properties"]["route"]["enum"] else "care"}, {}, ""
    monkeypatch.setattr(concierge, "chat_json", fake)
    assert concierge.route("how to clean the cord")["route"] == "care"
    assert concierge.route("how to clean the cord", lessons=True)["route"] == "lessons"
    assert "lessons:" not in seen[0][0] and "lessons:" in seen[1][0]


def mock_graph(monkeypatch, lesson_id="cord_care", topic="cord_care"):
    monkeypatch.setattr(guardian, "screen", lambda q: (guardian.decide(q), None))
    monkeypatch.setattr(concierge, "route", lambda q, **kw: {"route": "lessons", "usage": None})
    monkeypatch.setattr(library, "match", lambda q, **kw: {"lesson_id": lesson_id, "topic": topic})


def test_approved_steps_skip_verifier(lesson_root, monkeypatch):
    mock_graph(monkeypatch)
    monkeypatch.setattr(graph.verifier, "verify", lambda *a, **kw: pytest.fail("approved lesson must not be rewritten"))
    out = graph.ask("How do I clean the cord?", version="v6+lessons")
    assert out["error"] is None and out["route"] == "lessons" and out["lesson"]["lesson_id"] == "cord_care"
    assert "1. Keep the cord clean and dry. [WHO-POSTNATAL, p. 120]" in out["answer"]
    assert out["sources_cited"] == ["WHO-POSTNATAL"] and out["verification"] is None


@pytest.mark.parametrize("lesson_id,topic", [("holding", "holding"), (None, "newborn_care")])
def test_unavailable_match_falls_back_and_logs_label_only(lesson_root, monkeypatch, lesson_id, topic):
    mock_graph(monkeypatch, lesson_id, topic)
    monkeypatch.setattr(graph.care, "answer", lambda *a, **kw: {"answer": "Sourced care", "sources_cited": ["WHO-POSTNATAL"],
                        "agent": "care", "hits": [{"source_id": "WHO-POSTNATAL", "chunk_text": "Trusted text", "page_label": "120"}], "usage": []})
    monkeypatch.setattr(graph.verifier, "verify", lambda *a, **kw: {"verdict": "passed", "answer": "Verified care", "sources_cited": ["WHO-POSTNATAL"], "unsupported": [], "usage": []})
    out = graph.ask("My private question", version="v6+lessons")
    assert out["error"] is None and out["answer"] == "Verified care" and out["route"] == "care"
    assert out["lesson"] is None and out["lesson_gap_topic"] == topic


def test_guardian_danger_sign_before_lesson_matching(monkeypatch):
    monkeypatch.setattr(library, "match", lambda q: pytest.fail("lesson matching before escalation"))
    monkeypatch.setattr(concierge, "route", lambda *a, **kw: pytest.fail("routing before red-flag rule"))
    monkeypatch.setattr(guardian, "screen", lambda q: (guardian.decide(q), None))
    out = graph.ask("How do I latch my newborn who is not feeding and feels cold to the touch?", version="v6+lessons")
    assert out["escalate"] and out["route"] == "guardian" and out["lesson"] is None


def test_absent_breathing_how_to_skips_all_paid_calls(monkeypatch):
    monkeypatch.setattr(llm, "chat_json", lambda *a, **kw: pytest.fail("paid call before emergency reply"))
    monkeypatch.setattr(guardian, "chat_json", lambda *a, **kw: pytest.fail("classifier before emergency reply"))
    monkeypatch.setattr(concierge, "route", lambda *a, **kw: pytest.fail("Concierge before emergency reply"))
    out = graph.ask("How do I bathe my baby who is not breathing?", version="v6+lessons")
    assert out["escalate"] and out["route"] == "guardian" and out["lesson"] is None


def test_recorded_versions_keep_lessons_off():
    assert all(graph.VERSIONS[v]["lessons"] is False for v in ("v1", "v2", "v3", "v4", "v5", "v6", "v7"))
    assert graph.VERSIONS["v6+lessons"] == {**graph.VERSIONS["v6"], "lessons": True}
