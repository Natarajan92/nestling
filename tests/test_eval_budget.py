from types import SimpleNamespace

import pytest


def test_budget_refuses_before_provider_call(tmp_path):
    from evals.budgeted_run import Meter

    meter = Meter(tmp_path / "cost.json", cap=0.001)
    called = []
    with pytest.raises(RuntimeError, match="budget"):
        meter.call(lambda **kw: called.append(kw), model="zai-org/GLM-5.3", messages=[{"content": "x"}], max_tokens=3000)
    assert called == [] and meter.spent == 0


def test_budget_records_actual_usage_and_keeps_unknown_failure_reserve(tmp_path):
    from evals.budgeted_run import Meter

    meter = Meter(tmp_path / "cost.json", cap=10)
    response = SimpleNamespace(model="zai-org/GLM-5.3", usage=SimpleNamespace(prompt_tokens=100, completion_tokens=20))
    meter.call(lambda **kw: response, model="zai-org/GLM-5.3", messages=[{"content": "test"}], max_tokens=3000)
    first = meter.spent
    assert 0 < first < 0.1
    def fail(**kw):
        raise TimeoutError("provider outcome unknown")
    with pytest.raises(TimeoutError):
        meter.call(fail, model="zai-org/GLM-5.3", messages=[{"content": "test"}], max_tokens=3000)
    assert meter.spent > first + 1


def test_resume_retains_pending_reservations_and_saved_cap(tmp_path):
    import json
    from evals.budgeted_run import Meter

    path = tmp_path / "cost.json"
    path.write_text(json.dumps({"cap_inr": 2, "calls": [{"cost_inr": .25}],
                                "pending": {"in-flight": {"model": "x", "cost_inr": .5}}}))
    meter = Meter(path, cap=250)
    assert meter.cap == 2 and meter.spent == .75
    meter._write()
    assert Meter(path).spent == .75  # reopening must not charge the reservation twice


def test_resume_skips_complete_cases_and_reuses_pipeline_after_judge_error():
    from evals.budgeted_run import pending_cases

    answer = {"agent": "care", "answer": "A sourced answer", "escalate": False, "refused": False}
    checkpoint = {"cases": {
        "complete": {"output": answer, "judge": {"faithful": True}},
        "judge-error": {"output": answer, "judge_error": "timeout"},
        "missing-judge": {"output": answer, "judge": None},
        "escalated": {"output": {**answer, "escalate": True}, "judge": None},
        "failed": {"output": {"error": "quota"}},
    }}
    assert pending_cases(checkpoint, ["complete", "judge-error", "missing-judge", "escalated", "failed", "absent"]) == [
        "judge-error", "missing-judge", "failed", "absent"]


def test_reused_nonclinical_case_still_gets_its_own_variant_trace():
    from evals.budgeted_run import pending_cases

    saved = {"output": {"agent": "guardian", "escalate": True},
             "provenance": {"reused_unaffected_nonclinical": True}}
    checkpoint = {"cases": {"old": saved}}
    assert pending_cases(checkpoint, ["old"]) == ["old"]
    saved["provenance"]["traced_in_variant"] = True
    assert pending_cases(checkpoint, ["old"]) == []


def test_persistent_judge_errors_stop_after_existing_three_attempt_policy():
    from evals.budgeted_run import pending_cases

    saved = {"output": {"agent": "care", "answer": "A sourced answer"},
             "judge": None, "judge_error": "invalid JSON", "judge_attempts": 2}
    assert pending_cases({"cases": {"case": saved}}, ["case"]) == ["case"]
    saved["judge_attempts"] = 3
    assert pending_cases({"cases": {"case": saved}}, ["case"]) == []


def test_default_model_preparation_reuses_only_guardian_and_concierge(tmp_path, monkeypatch):
    import json
    from evals import budgeted_run

    path = tmp_path / "phase3_v7_vector_safe_checkpoint.json"
    original = {"model": "zai-org/GLM-5.3", "experiment": "partial-glm", "cases": {
        cid: {"output": {"agent": agent}} for cid, agent in
        [("rule", "guardian"), ("route", "concierge"), ("medical", "care"), ("party", "celebrate"), ("note", "journal")]}}
    original["cases"]["rule"]["output"].update(model="rules", tokens_in=0, tokens_out=0)
    original["cases"]["route"]["output"].update(model="deepseek-ai/DeepSeek-V4.1-Flash", tokens_in=10, tokens_out=5)
    path.write_text(json.dumps(original))
    monkeypatch.setattr(budgeted_run, "CHECKPOINT", path)
    monkeypatch.setattr(budgeted_run.llm, "MAIN", "deepseek-ai/DeepSeek-V4-Pro")
    monkeypatch.setattr(budgeted_run, "code_provenance", lambda: {"test": "hash"})
    budgeted_run.prepare_default()
    prepared = json.loads(path.read_text())
    assert set(prepared["cases"]) == {"rule", "route"}
    assert prepared["model"] == "deepseek-ai/DeepSeek-V4-Pro"
    assert prepared["cases"]["rule"]["output"]["model"] == "rules"
    assert json.loads((tmp_path / "phase3_v7_vector_safe_glm_checkpoint.json").read_text())["cases"] == original["cases"]


def test_local_export_uses_existing_scorers_and_leaves_trace_links_empty(tmp_path, monkeypatch):
    import csv
    import json
    from evals import budgeted_run
    from nestling import golden

    case = golden.load()[0]
    expected = golden.to_example(case)["outputs"]
    output = {"answer": "Fixture answer", "agent": "care", "route": expected["expected_route"][0],
        "escalate": expected["expected_escalate"], "refused": expected["expected_refusal"],
        "sources_cited": expected["must_cite_source_ids"], "retrieved_source_ids": expected["must_cite_source_ids"],
        "model": "deepseek-ai/DeepSeek-V4-Pro", "latency_ms": 10, "cost_inr": .02, "error": None}
    checkpoint = {"local_run_id": "local-test", "trace_upload_status": "pending", "code_provenance": {},
        "data_provenance": {}, "cases": {case["case_id"]: {"output": output,
            "judge": {"faithful": True, "score": 1, "claims": []}, "judge_error": None}}}
    monkeypatch.setattr(budgeted_run.evaluators, "RESULTS_DIR", tmp_path)
    monkeypatch.setattr(budgeted_run.judge, "RESULTS_DIR", tmp_path)
    for filename in ("phase3_experiments.json", "phase3_judge_round1.json"):
        (tmp_path / filename).write_text("{}")
    budgeted_run.export_local(checkpoint, [case])
    summary = json.loads(next(tmp_path.glob("improved_*_summary.json")).read_text())
    assert summary["run"]["experiment"] == "local-test" and summary["metrics"]["routing_accuracy"]["value"] == 1
    with next(tmp_path.glob("improved_*_cases.csv")).open() as stream:
        assert list(csv.DictReader(stream))[0]["trace_url"] == ""
