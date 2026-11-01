import csv
import json

import pytest

from evals import v3_compare as compare


def saved_round(root, name, cases, *, digest="hash", provenance="owner-attested human-authored"):
    directory = root / name
    directory.mkdir()
    rows = []
    checkpoint = {"dataset_version": "golden_v3", "dataset_hash": digest, "round_name": name,
                  "version": name, "provenance": provenance, "cases": {}}
    for cid, overrides in cases.items():
        row = {"case_id": cid, "scenario_type": "edge", "expected_route": "care", "expected_refusal": False,
               "expected_escalate": False, "predicted_escalate": False,
               "escalation_match": True, "route_match": True, "refusal_match": True,
               "citation_match": True, "cost_inr": 1, "latency_ms": 1000,
               "error": "", "trace_url": "https://trace/" + cid, "faithfulness_eligible": True,
               "faithful": True, "judge_error": "", "abstained": False, "task_fulfilled": True}
        row.update(overrides)
        rows.append(row)
        checkpoint["cases"][cid] = {"output": {}, "judge": {"faithful": row["faithful"]}}
    with (directory / "cases.csv").open("w", encoding="utf-8", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)
    (directory / "checkpoint.json").write_text(json.dumps(checkpoint))
    (directory / "summary.json").write_text(json.dumps({"progress": {"complete": True}}))
    return directory


def test_pairing_excludes_invalid_judges_and_reports_error_sensitivity(tmp_path):
    baseline = saved_round(tmp_path, "baseline", {"a": {}, "b": {"faithful": False},
                                               "c": {"faithful": "", "judge_error": "timeout"}})
    candidate = saved_round(tmp_path, "candidate", {"a": {}, "b": {"faithful": True}, "c": {}})
    result = compare.compare_rounds(baseline, candidate)
    pair = result["faithfulness"]
    assert pair["paired_valid_n"] == 2
    assert pair["baseline"] == 0.5
    assert pair["candidate"] == 1
    assert pair["delta_pp"] == 50
    assert pair["error_sensitivity_n"] == 3
    assert pair["baseline_errors_as_false"] == pytest.approx(1 / 3)
    assert pair["candidate_errors_as_false"] == 1


def test_candidate_subset_uses_same_ids_for_all_metrics(tmp_path):
    baseline = saved_round(tmp_path, "baseline", {"a": {"route_match": False}, "b": {}, "c": {}})
    candidate = saved_round(tmp_path, "candidate", {"a": {"cost_inr": 0.5, "abstained": True}})
    result = compare.compare_rounds(baseline, candidate)
    assert result["scope"] == "subset diagnostic"
    assert result["n_paired"] == 1
    assert result["baseline_metrics"]["routing_accuracy"]["value"] == 0
    assert result["candidate_metrics"]["routing_accuracy"]["value"] == 1
    assert result["candidate_metrics"]["mean_cost_inr"]["value"] == 0.5
    assert result["faithfulness"]["candidate_abstained"] == 1


def test_safety_denominator_and_nearest_rank_latency_on_saved_rows(tmp_path):
    cases = {"a": {"expected_escalate": True, "predicted_escalate": False, "cost_inr": 1},
             "b": {"predicted_escalate": True, "route_match": False, "cost_inr": 2, "latency_ms": 2000},
             "c": {"refusal_match": False, "cost_inr": 3, "latency_ms": 9000}}
    baseline = saved_round(tmp_path, "baseline", cases)
    candidate = saved_round(tmp_path, "candidate", cases)
    metrics = compare.compare_rounds(baseline, candidate)["candidate_metrics"]
    assert metrics["escalation_recall"]["n"] == 1
    assert metrics["escalation_recall"]["value"] == 0
    assert metrics["routing_accuracy"]["value"] == 0.6667
    assert metrics["refusal_accuracy"]["value"] == 0.6667
    assert metrics["p95_latency_s"]["value"] == 9
    assert metrics["p95_latency_s"]["passed"] is False
    assert metrics["mean_cost_inr"]["value"] == 2
    assert metrics["mean_cost_inr"]["passed"] is False


def test_task_coverage_uses_valid_pairs_and_does_not_reward_judge_errors(tmp_path):
    baseline = saved_round(tmp_path, "baseline", {"a": {"task_fulfilled": False},
                                               "b": {"judge_error": "timeout", "task_fulfilled": ""}})
    candidate = saved_round(tmp_path, "candidate", {"a": {}, "b": {}})
    result = compare.compare_rounds(baseline, candidate)
    assert result["task_fulfillment"] == {"paired_valid_n": 1, "baseline": 0, "candidate": 1,
                                          "baseline_judge_errors": 1, "candidate_judge_errors": 0}


@pytest.mark.parametrize("difference", [{"digest": "changed"}, {"provenance": "human"}])
def test_rejects_mixed_labels_or_provenance(tmp_path, difference):
    baseline = saved_round(tmp_path, "baseline", {"a": {}})
    candidate = saved_round(tmp_path, "candidate", {"a": {}}, **difference)
    with pytest.raises(ValueError, match="identity"):
        compare.compare_rounds(baseline, candidate)


def test_rejects_changed_reference_labels_even_if_checkpoint_hash_is_reused(tmp_path):
    baseline = saved_round(tmp_path, "baseline", {"a": {}})
    candidate = saved_round(tmp_path, "candidate", {"a": {"expected_route": "money"}})
    with pytest.raises(ValueError, match="labels"):
        compare.compare_rounds(baseline, candidate)


def test_pipeline_provenance_changes_are_disclosed_but_judge_changes_rejected(tmp_path):
    pinned = {"pipeline_version": "base", "judge_model": "judge", "judge_version": "v3",
              "main_model": "main", "fast_model": "fast", "prices_usd_per_mtok": {},
              "files": {"nestling/agents/care.py": "old", "evals/evaluators.py": "score"}}
    baseline = saved_round(tmp_path, "baseline", {"a": {}}, provenance=pinned)
    changed = {**pinned, "pipeline_version": "new", "files": {**pinned["files"], "nestling/agents/care.py": "new"}}
    candidate = saved_round(tmp_path, "candidate", {"a": {}}, provenance=changed)
    result = compare.compare_rounds(baseline, candidate)
    assert result["provenance_changes"]["pipeline_version"] == ["base", "new"]
    changed["judge_model"] = "another judge"
    checkpoint = json.loads((candidate / "checkpoint.json").read_text())
    checkpoint["provenance"] = changed
    (candidate / "checkpoint.json").write_text(json.dumps(checkpoint))
    with pytest.raises(ValueError, match="identity"):
        compare.compare_rounds(baseline, candidate)


def test_load_partial_round_accepts_unmeasured_planned_rows(tmp_path):
    run = saved_round(tmp_path, "baseline", {"a": {}, "b": {"error": "not measured"}})
    checkpoint = json.loads((run / "checkpoint.json").read_text())
    checkpoint["case_ids"] = ["a", "b"]
    del checkpoint["cases"]["b"]
    (run / "checkpoint.json").write_text(json.dumps(checkpoint))
    assert len(compare.load_round(run)["rows"]) == 2


def test_failure_clusters_use_observed_pipeline_cost_and_trace_examples(tmp_path):
    run = saved_round(tmp_path, "baseline", {"a": {"route_match": False, "cost_inr": 2},
                                           "b": {"route_match": False, "citation_match": False}})
    clusters = compare.failure_clusters(compare.load_round(run)["rows"])
    assert clusters[0]["cluster"] == "routing"
    assert clusters[0]["n"] == 2
    assert clusters[0]["observed_pipeline_cost_inr"] == 3
    assert clusters[0]["examples"][0]["trace_url"] == "https://trace/a"


def test_unmeasured_rows_are_pending_not_observed_failure_clusters(tmp_path):
    run = saved_round(tmp_path, "baseline", {"a": {"error": "not measured", "route_match": False,
                                                       "refusal_match": False, "citation_match": False}})
    assert compare.failure_clusters(compare.load_round(run)["rows"]) == []


def test_visible_citations_require_whole_case_insensitive_ids_not_prefixes():
    rows = [{"case_id": "H01", "sources_cited": "ICMR-NIN-DG", "answer": "Foods (ICMR-).", "trace_url": "trace-H01"},
            {"case_id": "ok", "sources_cited": ["WHO-ANC", "MOHFW-ANC"],
             "answer": "[who-anc], MOHFW-ANC: advice.", "trace_url": "trace-ok"},
            {"case_id": "prefix", "sources_cited": "WHO-ANC|MOHFW-ANC",
             "answer": "XWHO-ANC WHO-ANC-OTHER MOHFW-ANC", "trace_url": "trace-prefix"},
            {"case_id": "none", "sources_cited": "", "answer": "No citations", "trace_url": ""}]
    result = compare.visible_citations(rows)
    assert result["n_eligible"] == 3
    assert result["n_complete"] == 1
    assert result["complete_rate"] == pytest.approx(1 / 3)
    assert result["missing_cases"] == [
        {"case_id": "H01", "missing_source_ids": ["ICMR-NIN-DG"], "trace_url": "trace-H01"},
        {"case_id": "prefix", "missing_source_ids": ["WHO-ANC"], "trace_url": "trace-prefix"}]


def test_visible_citations_pair_on_candidate_ids_without_changing_core_metrics(tmp_path):
    baseline = saved_round(tmp_path, "baseline", {
        "a": {"sources_cited": "ICMR-NIN-DG", "answer": "(ICMR-)"},
        "b": {"sources_cited": "WHO-ANC", "answer": "WHO-ANC"}})
    candidate = saved_round(tmp_path, "candidate", {"a": {"sources_cited": "ICMR-NIN-DG", "answer": "[ICMR-NIN-DG]"}})
    result = compare.compare_rounds(baseline, candidate)
    assert result["visible_citations"]["baseline"]["n_eligible"] == 1
    assert result["visible_citations"]["baseline"]["n_complete"] == 0
    assert result["visible_citations"]["candidate"]["n_complete"] == 1
    assert result["baseline_metrics"]["citation_match"]["value"] == 1
    assert result["candidate_metrics"]["citation_match"]["value"] == 1


def test_proposal_is_immutable_and_must_precede_measurement(tmp_path):
    path = tmp_path / "next"
    compare.propose_round(path, hypothesis="narrow retrieval improves support", target_cluster="unsupported claims",
                          lever="retrieval filter", expected_direction="faithfulness increases",
                          success="safety holds and faithfulness improves", revert="safety regression")
    with pytest.raises(FileExistsError):
        compare.propose_round(path, hypothesis="changed", target_cluster="x", lever="x", expected_direction="x",
                              success="x", revert="x")
    run = saved_round(tmp_path, "started", {"a": {}})
    with pytest.raises(ValueError, match="before"):
        compare.propose_round(run, hypothesis="late", target_cluster="x", lever="x", expected_direction="x",
                              success="x", revert="x")


def test_pending_report_does_not_invent_measurements(tmp_path):
    output = tmp_path / "report.md"
    compare.write_report(tmp_path / "runs", output)
    report = output.read_text(encoding="utf-8")
    assert "Baseline pending" in report
    assert "owner-attested human-authored" in report
    assert "not independently verified" in report
    assert "not an unseen holdout" in report


def test_report_renders_saved_subset_failures_and_preserves_hypothesis(tmp_path):
    saved_round(tmp_path, "baseline", {"a": {"route_match": False}, "b": {}})
    candidate = saved_round(tmp_path, "candidate", {"a": {"faithful": False}})
    (candidate / "plan.json").write_text(json.dumps({"hypothesis": "one declared lever"}))
    output = tmp_path / "report.md"
    compare.write_report(tmp_path, output)
    report = output.read_text(encoding="utf-8")
    assert "subset diagnostic" in report
    assert "unsupported claims: 1 cases" in report
    assert "[a](https://trace/a)" in report
    assert "one declared lever" in report


def test_report_formats_counts_and_deltas_without_dumping_judging_json(tmp_path):
    baseline = saved_round(tmp_path, "baseline", {"a": {"sources_cited": "ICMR-NIN-DG", "answer": "(ICMR-)"}})
    saved_round(tmp_path, "candidate", {"a": {"sources_cited": "ICMR-NIN-DG", "answer": "[ICMR-NIN-DG]"}})
    summary = json.loads((baseline / "summary.json").read_text())
    summary["judging"] = {"n_eligible": 1, "n_valid": 1, "n_faithfulness_eligible": 1,
                          "n_faithfulness_valid": 1, "faithfulness": 1, "task_fulfillment": 1,
                          "n_errors": 0, "n_zero_claim": 0, "n_abstained": 0}
    (baseline / "summary.json").write_text(json.dumps(summary))
    output = tmp_path / "report.md"
    compare.write_report(tmp_path, output)
    report = output.read_text(encoding="utf-8")
    assert "| Delta |" in report
    assert "Faithfulness: 100.0%" in report
    assert "code format diagnostic" in report
    assert "ICMR-NIN-DG" in report
    assert '"n_faithfulness_eligible"' not in report


def test_submission40_exports_fixed_strata_from_saved_full_rounds(tmp_path):
    from nestling import golden
    cases = golden.load()
    selected = compare.select_submission40(cases)
    assert len(selected) == 40
    assert selected[:4] == ["F01", "F02", "F07", "H01"]
    assert selected[20:23] == ["B09", "B12", "B13"]
    assert selected[-2:] == ["A01", "A02"]
    rows = {case["case_id"]: {"scenario_type": case["scenario_type"], "question": case["input"],
                             "expected_route": case["expected_route"], "expected_behavior": case["expected_behavior"],
                             "must_include": case["must_include"], "must_avoid": case["must_avoid"],
                             "expected_escalate": case["expected_escalate"] == "Y",
                             "expected_refusal": case["expected_refusal"] == "Y",
                             "must_cite": case["must_cite_source_ids"]} for case in cases}
    saved_round(tmp_path, "baseline", rows, digest=golden.SHA256)
    saved_round(tmp_path, "round1", rows, digest=golden.SHA256)
    selector = tmp_path / "selector.json"
    selector.write_text(json.dumps({"dataset_version": golden.DATASET_VERSION, "dataset_hash": golden.SHA256,
                                    "n_cases": 40, "case_ids": selected,
                                    "timing": "after baseline; before round1", "recorded_at": "2026-11-02"}))
    result = compare.export_submission40(tmp_path, selector)
    assert result["rounds"]["baseline"]["n_cases"] == 40
    assert result["rounds"]["round1"]["paired"]["n_paired"] == 40
    assert result["rounds"]["round1"]["paired"]["scope"] == "subset diagnostic"
    with (tmp_path / "submission40_questions.csv").open(encoding="utf-8-sig", newline="") as stream:
        questions = list(csv.DictReader(stream))
    assert [q["case_id"] for q in questions] == selected
    by_id = {c["case_id"]: c for c in cases}
    assert all(q["input"] == by_id[q["case_id"]]["input"] for q in questions)
    with (tmp_path / "round1/submission40_results.csv").open(encoding="utf-8-sig", newline="") as stream:
        assert len(list(csv.DictReader(stream))) == 40
    bad = json.loads(selector.read_text())
    bad["case_ids"][0] = "B11"
    selector.write_text(json.dumps(bad))
    with pytest.raises(ValueError, match="selection"):
        compare.export_submission40(tmp_path, selector)


def test_week4_report_excludes_partial_metrics_and_preserves_manual_loom(tmp_path):
    saved_round(tmp_path, "baseline", {"a": {"cost_inr": 0.5}, "b": {"cost_inr": 0.5}})
    partial = saved_round(tmp_path, "round1", {"a": {"cost_inr": 99}})
    summary = json.loads((partial / "summary.json").read_text())
    summary["progress"]["complete"] = False
    (partial / "summary.json").write_text(json.dumps(summary))
    (partial / "plan.json").write_text(json.dumps({"hypothesis": "one prospective lever",
        "lever": "citation parser", "target_cluster": "broken markers", "expected_metric_direction": "fewer missing IDs"}))
    output = tmp_path / "week4_report.md"
    output.write_text("**Loom:** https://www.loom.com/share/manual-link\n")
    compare.write_week4_report(tmp_path, output)
    report = output.read_text(encoding="utf-8")
    assert "https://www.loom.com/share/manual-link" in report
    assert "one prospective lever" in report
    assert "99.0000" not in report
    assert "Post-improvement measurement pending" in report
    assert "uv run python -m evals.label_calibration --report" in report
    assert "owner-attested human-authored" in report
    assert len(report.splitlines()) < 250


def test_completed_comparison_reports_actual_case_regressions(tmp_path):
    baseline = saved_round(tmp_path, "baseline", {"a": {}, "b": {"faithful": False}})
    candidate = saved_round(tmp_path, "round1", {"a": {"route_match": False, "faithful": False}, "b": {}})
    result = compare.compare_rounds(baseline, candidate)
    assert [r["case_id"] for r in result["case_regressions"]["route_match"]] == ["a"]
    assert [r["case_id"] for r in result["case_regressions"]["faithful"]] == ["a"]
    output = tmp_path / "week4_report.md"
    compare.write_week4_report(tmp_path, output)
    report = output.read_text(encoding="utf-8")
    assert "Observed case regressions" in report
    assert "[a](https://trace/a)" in report


def test_reports_incremental_predecessor_deltas_and_put_final_last(tmp_path):
    saved_round(tmp_path, "baseline", {"a": {"route_match": False}})
    saved_round(tmp_path, "round1", {"a": {"route_match": True}})
    saved_round(tmp_path, "round2", {"a": {"route_match": False}})
    final = saved_round(tmp_path, "final", {"a": {"route_match": True}})
    (final / "decision.json").write_text(json.dumps({"decision": "keep", "reason": "fixture decision"}))
    deep = tmp_path / "deep.md"
    canonical = tmp_path / "week4_report.md"
    compare.write_report(tmp_path, deep)
    compare.write_week4_report(tmp_path, canonical)
    for output in (deep, canonical):
        report = output.read_text(encoding="utf-8")
        assert "Incremental round1 → round2" in report
        assert "Incremental round2 → final" in report
        incremental = report.split("Incremental round1 → round2", 1)[1].split("Incremental round2 → final", 1)[0]
        assert "| routing_accuracy | 100.0% | 0.0% | -100.00 pp |" in incremental
        assert "Overall baseline → final" in report
        assert report.index("Incremental baseline → round1") < report.index("Incremental round1 → round2")


def test_proposed_base_must_be_an_earlier_complete_matching_frozen_round(tmp_path):
    from nestling import golden
    rows = {case["case_id"]: {} for case in golden.load()}
    saved_round(tmp_path, "round1", rows, digest=golden.SHA256)
    fields = {"hypothesis": "compact verifier", "target_cluster": "latency", "lever": "output contract",
              "expected_direction": "lower latency", "success": "coverage holds", "revert": "coverage falls"}
    plan = compare.propose_round(tmp_path / "round3", comparison_base="round1", **fields)
    assert json.loads(plan.read_text())["comparison_base"] == "round1"
    with pytest.raises(ValueError, match="earlier"):
        compare.propose_round(tmp_path / "round2", comparison_base="round3", **fields)
    summary_path = tmp_path / "round1/summary.json"
    summary_path.write_text(json.dumps({"progress": {"complete": False}}))
    with pytest.raises(ValueError, match="complete"):
        compare.propose_round(tmp_path / "round2", comparison_base="round1", **fields)


def test_declared_base_and_selected_keep_are_separate_from_latest_rejected_round(tmp_path):
    saved_round(tmp_path, "baseline", {"a": {"route_match": False}})
    retained = saved_round(tmp_path, "round1", {"a": {"route_match": True}})
    rejected = saved_round(tmp_path, "round2", {"a": {"route_match": False}})
    future = saved_round(tmp_path, "round3", {"a": {"route_match": True}})
    (retained / "decision.json").write_text(json.dumps({"decision": "keep"}))
    (rejected / "decision.json").write_text(json.dumps({"decision": "reject"}))
    (future / "plan.json").write_text(json.dumps({"comparison_base": "round1", "hypothesis": "new flag on restored R1"}))
    # Model the saved declaration independently: report comparisons still validate each pair's labels and identity.
    for writer, output in ((compare.write_report, tmp_path / "deep.md"),
                           (compare.write_week4_report, tmp_path / "week4.md")):
        writer(tmp_path, output)
        report = output.read_text(encoding="utf-8")
        assert "Incremental round1 → round3" in report
        assert "Overall baseline → round1" in report
        assert "Overall baseline → round2" not in report
        assert "Latest completed: **round3**" in report
        assert "Selected retained candidate: **round1**" in report
        assert "restored base" in report


def test_notebook_evidence_is_saved_only_and_distinguishes_rejected_latest(tmp_path):
    saved_round(tmp_path, "baseline", {"H07": {"route_match": False}})
    kept = saved_round(tmp_path, "round1", {"H07": {}})
    rejected = saved_round(tmp_path, "round2", {"H07": {"faithful": False}})
    (kept / "decision.json").write_text(json.dumps({"decision": "keep", "reason": "coverage improved"}))
    (rejected / "decision.json").write_text(json.dumps({"decision": "reject", "reason": "coverage fell"}))
    (tmp_path / "spend.json").write_text(json.dumps({"accounted_inr": 183.9041, "cap_inr": 350}))
    evidence = compare.notebook_evidence(tmp_path)
    assert "Selected retained candidate: **round1**" in evidence["overview"]
    assert "183.9041" in evidence["overview"]
    assert "round1 → round2" in evidence["paired"]
    assert "coverage fell" in evidence["decisions"]
    assert "H07" in evidence["h07"]
    assert "not independently verified" in evidence["limitations"]
