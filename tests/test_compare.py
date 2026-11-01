import csv
import json

import pytest

from evals import compare

CASE_FIELDS = ["case_id", "scenario_type", "route_match", "refusal_match", "must_cite", "sources_cited", "citation_match",
               "invalid_citations", "unretrieved_citations"]
JUDGE_FIELDS = ["case_id", "scenario_type", "agent", "faithful", "claim_support", "unsupported", "question", "answer"]


def _metrics(**over):
    base = {"escalation_recall": 1.0, "refusal_accuracy": 1.0, "routing_accuracy": 0.95, "citation_match": 0.8,
            "p95_latency_s": 5.0, "mean_cost_inr": 1.0, "p95_cost_inr": 1.5}
    base.update(over)
    return {k: {"value": v, "n": 10} for k, v in base.items()}


def _write(path, fields, rows):
    with open(path, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=fields)
        w.writeheader()
        w.writerows({k: r.get(k, "") for k in fields} for r in rows)


def _version(d, version, metrics, cases, judged):
    prefix = "baseline" if version == "baseline" else f"improved_{version}"
    experiment = f"exp-{version}"
    (d / f"{prefix}_2026-11-01_summary.json").write_text(json.dumps({"run": {"experiment": experiment}, "metrics": metrics}), encoding="utf-8")
    _write(d / f"{prefix}_2026-11-01_cases.csv", CASE_FIELDS, cases)
    _write(d / f"{experiment}_2026-11-01_judge.csv", JUDGE_FIELDS, judged)


def _judge_row(case_id, faithful, unsupported="", agent="care"):
    return {"case_id": case_id, "scenario_type": "happy", "agent": agent, "faithful": faithful,
            "claim_support": "" if faithful == "" else ("1.0" if faithful == "True" else "0.5"),
            "unsupported": unsupported, "question": f"q {case_id}", "answer": "a"}


@pytest.fixture
def results(tmp_path):
    ok = {"route_match": "True", "refusal_match": "True", "citation_match": "True", "sources_cited": "WHO-ANC"}
    _version(tmp_path, "baseline", _metrics(routing_accuracy=0.8, p95_latency_s=9.0),
             [{"case_id": "A1", **ok}, {"case_id": "A2", **ok}],
             [_judge_row("A1", "True"), _judge_row("A2", "True"), _judge_row("A3", "")])
    _version(tmp_path, "v1", _metrics(),
             [{"case_id": "A1", **ok},
              {"case_id": "A2", **ok, "route_match": "False"},
              {"case_id": "A3", **ok, "refusal_match": "False"},
              {"case_id": "A4", **ok, "citation_match": "False", "must_cite": "WHO-ANC", "sources_cited": "MOHFW-ANC"},
              {"case_id": "A5", **ok, "citation_match": "False", "must_cite": "WHO-ANC", "sources_cited": ""},
              {"case_id": "A6", **ok, "unretrieved_citations": "IRDAI"}],
             [_judge_row("A1", "True"), _judge_row("A2", "False", "claim X | claim Y", agent="nourish"), _judge_row("A3", "False")])
    return tmp_path


def test_comparison_table_values_deltas_and_bars(results):
    table = compare.comparison_table(results, versions=["baseline", "v1"])
    base, v1 = table
    assert base["faithfulness"] == 1.0 and base["delta_prev"]["faithfulness"] is None  # the empty judge row is excluded
    assert v1["faithfulness"] == pytest.approx(0.3333, abs=1e-4)
    assert v1["delta_prev"]["routing_accuracy"] == 0.15 and v1["delta_baseline"]["p95_latency_s"] == -4.0
    assert v1["passed"]["routing_accuracy"] is True and base["passed"]["routing_accuracy"] is False
    assert base["passed"]["p95_latency_s"] is False and v1["passed"]["p95_latency_s"] is True
    assert v1["passed"]["faithfulness"] is False and v1["passed"]["citation_match"] is None
    assert "baseline" in compare.format_table(table)


def test_faithfulness_regressions(results):
    found = compare.faithfulness_regressions("baseline", "v1", results)
    assert [r["case_id"] for r in found] == ["A2"]
    assert found[0]["unsupported"] == "claim X | claim Y" and found[0]["agent"] == "nourish"
    assert compare.faithfulness_regressions("v1", "baseline", results) == []


def test_failure_modes_group_case_ids(results):
    modes = compare.failure_modes("v1", results)
    assert modes["routing boundary"] == ["A2"]
    assert modes["refusal calibration"] == ["A3"]
    assert modes["wrong source family"] == ["A4"]
    assert modes["citation mismatch"] == ["A5", "A6"]
    assert modes["unsupported claim"] == ["A2", "A3"]
    top = compare.top_failure_modes("v1", 1, results)
    assert top == [{"mode": "unsupported claim", "count": 2, "case_ids": ["A2", "A3"]}]  # ties keep the category order
