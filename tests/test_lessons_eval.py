"""Lesson evaluation must distinguish missing evidence from passing scores."""

import json

import pytest


def test_routing_errors_do_not_count_as_correct_none():
    from evals.lessons_eval import score_route

    expected = {"expected_lesson_id": "none", "expected_escalate": "N"}
    assert score_route({"lesson_id": None, "escalate": False}, expected)["route_match"]
    assert not score_route({"lesson_id": None, "escalate": False, "error": "offline"}, expected)["route_match"]


def test_danger_sign_skips_lesson_even_if_matcher_would_match():
    from evals.lessons_eval import evaluate_case

    def forbidden(_):
        pytest.fail("Matcher must not run after code escalation")

    case = {"case_id": "D1", "input": "How do I bathe my baby who has rapid breathing?",
            "expected_lesson_id": "none", "expected_escalate": "Y", "label_status": "draft"}
    row = evaluate_case(case, matcher=forbidden)
    assert row["escalation_match"] and row["route_match"]
    assert row["label_status"] == "draft"


def test_unreviewed_scenes_and_stale_review_do_not_pass():
    from evals.lessons_eval import review_summary

    board = {"version": 3, "scenes": [{"step_no": 1}, {"step_no": 2}]}
    review = {"version": 3, "approved": False, "scenes": [{"step_no": 1, "passed": True}, {"step_no": 2, "passed": None}]}
    result = review_summary(board, review)
    assert result["status"] == "pending human review"
    assert result["pass_rate"] is None and result["n_reviewed"] == 1
    review.update(version=2, approved=True)
    assert review_summary(board, review)["status"] == "stale review"


def test_missing_render_is_unknown_cost_not_free(tmp_path):
    from evals.lessons_eval import render_summary

    assert render_summary(tmp_path) == {"status": "not rendered yet", "cost_inr": None, "seconds": None}
    (tmp_path / "render_log.json").write_text(json.dumps({"cost_inr": 4.2, "seconds": 18.5}))
    assert render_summary(tmp_path)["cost_inr"] == 4.2


def test_empty_and_unjudged_results_are_not_perfect():
    from evals.lessons_eval import summarize

    result = summarize([], [])
    assert result["routing_accuracy"] is None
    assert result["step_fidelity"] is None
    assert result["label_status"] == "draft; pending owner review"


def test_failed_scene_cannot_be_reported_as_approved():
    from evals.lessons_eval import review_summary

    board = {"version": 1, "scenes": [{"step_no": 1}]}
    review = {"version": 1, "approved": True, "reviewer": "human", "review_date": "2026-11-01",
              "scenes": [{"step_no": 1, "passed": False}]}
    result = review_summary(board, review)
    assert result["pass_rate"] == 0 and not result["approved"]


def test_source_fidelity_can_read_registered_snapshot_without_pdf(tmp_path, monkeypatch):
    from evals import lessons_eval

    (tmp_path / "snapshots").mkdir()
    (tmp_path / "snapshots" / "source.json").write_text(json.dumps({"local_pages": {"2": "Exact sourced instruction"}}))
    monkeypatch.setattr(lessons_eval.retrieval, "PDF_DIR", tmp_path / "pdfs")
    monkeypatch.setattr(lessons_eval.retrieval, "load_registry", lambda: {
        "SOURCE": {"id": "SOURCE", "file": "absent.pdf", "snapshot_file": "snapshots/source.json"}})
    board = {"sources": ["SOURCE"], "scenes": [{"source_id": "SOURCE", "page_label": "2"}]}
    assert lessons_eval.source_passages(board) == [{"source_id": "SOURCE", "page_label": "2", "chunk_text": "Exact sourced instruction"}]


def test_judge_cannot_pass_when_it_lists_missing_safety_steps(monkeypatch):
    from evals import lessons_eval

    monkeypatch.setattr(lessons_eval.llm, "chat_json", lambda *args, **kwargs: (
        {"faithful": True, "missing_steps": ["Head support omitted"], "invented_steps": [], "explanation": "inconsistent verdict"},
        {"tokens_in": 100, "tokens_out": 50}, ""))
    board = {"scenes": [{"source_id": "SOURCE", "page_label": "1"}]}
    result = lessons_eval.judge_steps(board, [{"source_id": "SOURCE", "page_label": "1", "chunk_text": "Support the head"}])
    assert result["status"] == "judged" and result["faithful"] is False


def test_fidelity_refresh_preserves_routing_and_old_verdicts(tmp_path, monkeypatch):
    from types import SimpleNamespace
    from evals import lessons_eval

    rows = [{"route_match": True, "expected_escalate": "N", "escalation_match": True,
             "error": None, "cost_inr": .01} for _ in range(39)]
    original = {"cases": rows, "live": True, "experiment": "draft-lessons", "lessons": [
        {"lesson_id": "latching", "version": 1, "fidelity": {"faithful": False}, "review": {}, "render": {}}]}
    path = tmp_path / "lessons_v1_2026-11-01_summary.json"
    path.write_text(json.dumps(original))
    monkeypatch.setattr(lessons_eval, "RESULTS_DIR", tmp_path)
    monkeypatch.setattr(lessons_eval.library, "get", lambda _: {
        "storyboard": {"version": 2, "scenes": [{"step_no": 1}]},
        "review": {"version": 2, "scenes": [{"step_no": 1, "passed": None}]}, "folder": tmp_path})
    calls = []
    monkeypatch.setattr(lessons_eval, "traced_fidelity", lambda *args: calls.append(args) or {"faithful": True, "cost_inr": .05})
    refreshed = lessons_eval.refresh_fidelity(SimpleNamespace(spent=1.2))
    assert refreshed["cases"] == rows and refreshed["n_cases"] == 39
    assert refreshed["version_history"][0]["fidelity"]["faithful"] is False
    assert refreshed["lessons"][0]["version"] == 2
    lessons_eval.refresh_fidelity(SimpleNamespace(spent=1.2))
    assert len(calls) == 1
