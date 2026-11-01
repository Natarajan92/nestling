"""Offline contracts for the isolated, resumable v3 evaluation."""

import json
from copy import deepcopy

import pytest


def runner():
    from evals import v3_run
    return v3_run


@pytest.fixture
def case():
    from nestling import golden
    return golden.load()[0]


def answer():
    return {"answer": "Vegetarian protein foods [ICMR-NIN-DG].", "agent": "nourish", "route": "nourish",
            "escalate": False, "refused": False, "sources_cited": ["ICMR-NIN-DG"],
            "retrieved_source_ids": ["ICMR-NIN-DG"], "passages": [], "error": None,
            "model": "deepseek-ai/DeepSeek-V4-Pro", "latency_ms": 100, "cost_inr": .2,
            "tokens_in": 10, "tokens_out": 10}


def verdict(**updates):
    return {"claims": [{"claim": "Protein food", "verdict": "supported"}], "faithful": True,
            "expected_behavior_fulfilled": True, "must_include_fulfilled": True,
            "must_avoid_respected": True, "behavior_reason": "All requested behavior present.", **updates}


@pytest.mark.parametrize("updates", [{"claims": None}, {"faithful": "false"},
                                    {"must_avoid_respected": "true"},
                                    {"claims": [{"claim": "x", "verdict": "maybe"}]}])
def test_invalid_judge_response_is_an_error_not_a_pass(updates):
    with pytest.raises(ValueError):
        runner().parse_judge(verdict(**updates), faithfulness_eligible=True)


def test_missing_claims_is_rejected():
    data = verdict()
    del data["claims"]
    with pytest.raises(ValueError):
        runner().parse_judge(data, faithfulness_eligible=True)


def test_empty_claims_cannot_inflate_faithfulness():
    parsed = runner().parse_judge(verdict(claims=[]), faithfulness_eligible=True)
    assert parsed["faithful"] is None and parsed["score"] is None and parsed["zero_claim"]
    assert parsed["task_fulfilled"] is True


def test_unsupported_claim_overrides_judge_pass_and_behavior_requires_all_checks():
    data = verdict(claims=[{"claim": "Unsupported", "verdict": "unsupported"}], must_include_fulfilled=False)
    parsed = runner().parse_judge(data, faithfulness_eligible=True)
    assert parsed["faithful"] is False and parsed["score"] == 0
    assert parsed["task_fulfilled"] is False


def test_nonclinical_reply_has_task_score_but_no_faithfulness_score():
    parsed = runner().parse_judge(verdict(), faithfulness_eligible=False)
    assert parsed["faithful"] is None and parsed["score"] is None
    assert parsed["task_fulfilled"] is True


def test_resume_rejects_changed_provenance_and_does_not_overwrite(tmp_path, case):
    mod = runner()
    path = tmp_path / "baseline" / "checkpoint.json"
    mod.open_checkpoint(path, "baseline", "v7_vector_safe+lessons", [case], {"code": "first"})
    before = path.read_bytes()
    with pytest.raises(RuntimeError, match="provenance"):
        mod.open_checkpoint(path, "baseline", "v7_vector_safe+lessons", [case], {"code": "changed"}, resume=True)
    assert path.read_bytes() == before


def test_completed_pipeline_survives_judge_error_and_resume(tmp_path, monkeypatch, case):
    mod = runner()
    path = tmp_path / "checkpoint.json"
    cp = mod.open_checkpoint(path, "baseline", "v7_vector_safe+lessons", [case], {})
    calls = []
    monkeypatch.setattr(mod.graph, "ask", lambda *a, **kw: calls.append("pipeline") or answer())
    def failed_judge(*args):
        assert json.loads(path.read_text())["cases"][case["case_id"]]["output"]["answer"]
        raise TimeoutError("judge timeout")
    mod.process_case(cp, path, case, judge_call=failed_judge)
    assert cp["cases"][case["case_id"]]["judge_error"] == "TimeoutError: judge timeout"
    mod.process_case(cp, path, case, judge_call=lambda *a: mod.parse_judge(verdict(), faithfulness_eligible=True))
    assert calls == ["pipeline"]
    assert cp["cases"][case["case_id"]]["judge_attempts"] == 2
    assert cp["cases"][case["case_id"]]["judge"]["faithful"] is True


def test_judge_retries_stop_at_three_without_repeating_pipeline(tmp_path, monkeypatch, case):
    mod = runner()
    path = tmp_path / "checkpoint.json"
    cp = mod.open_checkpoint(path, "baseline", "v7_vector_safe+lessons", [case], {})
    monkeypatch.setattr(mod.graph, "ask", lambda *a, **kw: answer())
    def fail(*args):
        raise ValueError("bad JSON")
    for _ in range(5):
        mod.process_case(cp, path, case, judge_call=fail)
    saved = cp["cases"][case["case_id"]]
    assert saved["judge_attempts"] == 3
    assert mod.pending_cases(cp, [case["case_id"]]) == []


def test_summary_counts_errors_abstentions_and_paired_fields(tmp_path, case):
    mod = runner()
    second = deepcopy(case)
    second["case_id"] = "fixture-error"
    path = tmp_path / "checkpoint.json"
    cp = mod.open_checkpoint(path, "baseline", "v7_vector_safe+lessons", [case, second], {})
    cp["cases"] = {case["case_id"]: {"output": {**answer(), "answer": "I don't have a trusted source for that."},
                    "judge": mod.parse_judge(verdict(claims=[]), faithfulness_eligible=True),
                    "judge_attempts": 1, "judge_error": None, "trace_verified": False},
                   "fixture-error": {"output": {**answer(), "error": "timeout"}, "judge": None}}
    result = mod.export_round(cp, [case, second], tmp_path)
    assert result["progress"]["n_done"] == 2 and result["progress"]["n_errors"] == 1
    assert result["progress"]["complete"] is False
    assert result["judging"]["n_abstained"] == 1
    assert result["judging"]["n_faithfulness_valid"] == 0
    assert result["judging"]["faithfulness"] is None
    assert (tmp_path / "cases.csv").exists() and (tmp_path / "calibration.csv").exists()


def test_round_paths_cannot_escape_results_directory():
    with pytest.raises(ValueError):
        runner().round_directory("../old-results")


def test_new_ledger_does_not_touch_historical_cap(tmp_path):
    mod = runner()
    old = tmp_path / "phase3_v7_vector_spend.json"
    old.write_text('{"accounted_inr": 244.0804, "cap_inr": 249.99}')
    meter = mod.new_meter(tmp_path / "golden_v3")
    assert meter.cap == 350 and meter.spent == 0
    assert json.loads(old.read_text())["accounted_inr"] == 244.0804
    assert (tmp_path / "golden_v3" / "approval.json").exists()


def test_export_rejects_a_different_frozen_dataset_before_writing(tmp_path, case):
    mod = runner()
    cp = mod.open_checkpoint(tmp_path / "checkpoint.json", "baseline", "v7_vector_safe+lessons", [case], {})
    cp["dataset_hash"] = "different-golden"
    with pytest.raises(RuntimeError, match="dataset"):
        mod.export_round(cp, [case], tmp_path)
    assert not (tmp_path / "cases.csv").exists()


def test_calibration_grows_after_smoke_but_preserves_human_labels(tmp_path, case):
    import csv
    mod = runner()
    second = {**case, "case_id": "second"}
    cp = mod.open_checkpoint(tmp_path / "checkpoint.json", "baseline", "v7_vector_safe+lessons", [case, second], {})
    saved = {"output": answer(), "judge": mod.parse_judge(verdict(), faithfulness_eligible=True),
             "judge_passages": [{"source_id": "SNAPSHOT", "text": "Exact evidence"}], "judge_attempts": 1}
    cp["cases"][case["case_id"]] = deepcopy(saved)
    mod.export_round(cp, [case, second], tmp_path)
    cp["cases"]["second"] = deepcopy(saved)
    mod.export_round(cp, [case, second], tmp_path)
    path = tmp_path / "calibration.csv"
    with path.open(newline="") as stream:
        rows = list(csv.DictReader(stream))
    assert len(rows) == 2
    assert json.loads(rows[0]["passages_json"])[0]["source_id"] == "SNAPSHOT"
    rows[0]["human_faithful"] = "N"
    with path.open("w", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)
    before = path.read_bytes()
    mod.export_round(cp, [case, second], tmp_path)
    assert path.read_bytes() == before


def test_ready_judge_evidence_is_saved_before_provider_attempt(tmp_path, monkeypatch, case):
    mod = runner()
    path = tmp_path / "checkpoint.json"
    cp = mod.open_checkpoint(path, "baseline", "v7_vector_safe+lessons", [case], {})
    monkeypatch.setattr(mod.graph, "ask", lambda *a, **kw: {**answer(), "agent": "ready"})
    def fail(*args):
        saved = json.loads(path.read_text())["cases"][case["case_id"]]
        assert saved["judge_passages"][-1]["source_id"] == "NESTLING-CHECKLIST"
        assert saved["judge_passages"][-1]["text"]
        raise TimeoutError("unavailable")
    mod.process_case(cp, path, case, judge_call=fail)
    assert cp["cases"][case["case_id"]]["judge_error"] == "TimeoutError: unavailable"


def test_feedback_includes_applicable_code_and_valid_judge_scores(case):
    mod = runner()
    saved = {"judge": mod.parse_judge(verdict(), faithfulness_eligible=True), "judge_error": None}
    rows = mod.feedback_rows(case, answer(), saved, "v7_vector_safe+lessons")
    assert {r["key"] for r in rows} == {"escalation_exact", "route_exact", "refusal_exact",
                                       "citation_match", "faithfulness", "task_fulfillment"}
    assert all(r["source_info"]["dataset_hash"] for r in rows)
    assert all(r["source_info"]["judge_version"] == mod.JUDGE_VERSION for r in rows)
    saved["judge_error"] = "malformed judgment"
    rows = mod.feedback_rows(case, answer(), saved, "v7_vector_safe+lessons")
    assert {r["key"] for r in rows} == {"escalation_exact", "route_exact", "refusal_exact", "citation_match"}


def test_feedback_errors_are_recorded_without_losing_verified_scores_or_outputs(case):
    from types import SimpleNamespace
    mod = runner()
    class Client:
        def __init__(self):
            self.saved = {}
        def create_feedback(self, run_id, **row):
            if row["key"] == "route_exact":
                raise TimeoutError("feedback unavailable")
            result = SimpleNamespace(id=row["key"], run_id=run_id,
                                     feedback_source=SimpleNamespace(metadata=row["source_info"]), **row)
            self.saved[result.id] = result
            return result
        def read_feedback(self, feedback_id):
            return self.saved[feedback_id]
        def flush(self):
            pass
    rows = mod.feedback_rows(case, answer(), {"judge": None}, "v7_vector_safe+lessons")
    result = mod.publish_feedback(Client(), "case-root", rows)
    assert len(result) == 4
    assert [r["key"] for r in result if r["verified"]] == ["escalation_exact", "refusal_exact", "citation_match"]
    assert next(r for r in result if r["key"] == "route_exact")["error"] == "TimeoutError: feedback unavailable"


def test_judge_retry_trace_labels_the_successful_pipeline_as_cached():
    mod = runner()
    cp = {"cases": {"judge-retry": {"output": answer(), "judge_error": "timeout", "judge_attempts": 1},
                    "pipeline-retry": {"output": {**answer(), "error": "timeout"}}}}
    assert "judge-retry" in mod.pending_cases(cp, ["judge-retry", "pipeline-retry"])
    assert mod.replay_metadata(cp, "judge-retry")["cached_output_replay"] is True
    assert mod.replay_metadata(cp, "pipeline-retry")["cached_output_replay"] is False
