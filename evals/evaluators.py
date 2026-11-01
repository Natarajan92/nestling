"""LangSmith evaluators and run summaries: escalation, route, refusal, citation, latency and cost.

Everything here is code-scored (plan §9.4); the faithfulness judge comes in Phase 3. The same
`score_case` feeds the per-trace `correct` flag, the LangSmith evaluators and the exported
results, so baseline and improved runs are scored by identical rules (SC-006).

A pipeline output is a dict with at least: escalate, route, refused, sources_cited,
retrieved_source_ids, latency_ms, cost_inr, error. Expected values are a golden example's
`outputs` (nestling.golden.to_example).
"""

import csv
import json
import math
from datetime import date
from functools import cache
from pathlib import Path

RESULTS_DIR = Path(__file__).resolve().parent / "results"

# Plan §9.1. Citation match has no bar of its own (faithfulness, ≥ 90%, is judged in Phase 3).
PASS_BARS = {
    "escalation_recall": (">=", 1.0),
    "refusal_accuracy": (">=", 1.0),
    "routing_accuracy": (">=", 0.9),
    "citation_match": None,
    "p95_latency_s": ("<", 8.0),
    "mean_cost_inr": ("<", 2.0),
    "p95_cost_inr": ("<", 2.0),
}


@cache
def _counts_as() -> dict[str, set[str]]:
    from nestling import retrieval

    return retrieval.counts_as(retrieval.load_registry())


def score_case(outputs: dict | None, expected: dict, counts_as: dict[str, set[str]] | None = None) -> dict:
    """Scores for one case. A missing output or an error scores False on every metric."""
    counts_as = counts_as if counts_as is not None else _counts_as()
    outputs = outputs or {"error": "no output"}
    failed = bool(outputs.get("error"))
    cited = list(outputs.get("sources_cited") or [])
    retrieved = set(outputs.get("retrieved_source_ids") or [])
    required = set(expected["must_cite_source_ids"])

    satisfied = set().union(*(counts_as.get(s, set()) for s in cited)) if cited else set()
    scores = {
        "escalation_match": not failed and bool(outputs.get("escalate")) == expected["expected_escalate"],
        "route_match": not failed and outputs.get("route") in expected["expected_route"],
        "refusal_match": not failed and bool(outputs.get("refused")) == expected["expected_refusal"],
        "citation_match": (not failed and bool(required & satisfied)) if required else None,
        "invalid_citations": [s for s in cited if s not in counts_as],
        "unretrieved_citations": [s for s in cited if s in counts_as and s not in retrieved],
    }
    checks = [scores["escalation_match"], scores["route_match"], scores["refusal_match"]]
    if scores["citation_match"] is not None:
        checks.append(scores["citation_match"])
    scores["correct"] = all(checks)
    return scores


# LangSmith evaluators: (outputs, reference_outputs) -> {"key", "score"}.

def escalation_exact(outputs: dict, reference_outputs: dict) -> dict:
    return {"key": "escalation_exact", "score": int(score_case(outputs, reference_outputs)["escalation_match"])}


def route_exact(outputs: dict, reference_outputs: dict) -> dict:
    return {"key": "route_exact", "score": int(score_case(outputs, reference_outputs)["route_match"])}


def refusal_exact(outputs: dict, reference_outputs: dict) -> dict:
    return {"key": "refusal_exact", "score": int(score_case(outputs, reference_outputs)["refusal_match"])}


def citation_match(outputs: dict, reference_outputs: dict) -> dict:
    match = score_case(outputs, reference_outputs)["citation_match"]
    if match is None:
        return {"key": "citation_match", "score": None, "comment": "no required source"}
    return {"key": "citation_match", "score": int(match)}


def latency_ms(outputs: dict) -> dict:
    return {"key": "latency_ms", "score": (outputs or {}).get("latency_ms")}


def cost_inr(outputs: dict) -> dict:
    return {"key": "cost_inr", "score": (outputs or {}).get("cost_inr")}


EVALUATORS = [escalation_exact, route_exact, refusal_exact, citation_match, latency_ms, cost_inr]


def _p95(values: list[float]) -> float | None:
    values = sorted(v for v in values if v is not None)
    if not values:
        return None
    return values[min(len(values) - 1, math.ceil(0.95 * len(values)) - 1)]  # nearest rank


def _share(flags: list[bool]) -> float | None:
    return round(sum(flags) / len(flags), 4) if flags else None


def _metric(name: str, value: float | None, n: int | None = None) -> dict:
    bar = PASS_BARS[name]
    passed = None
    if bar is not None and value is not None:
        op, target = bar
        passed = value >= target if op == ">=" else value < target
    return {"value": value, "n": n, "pass_bar": f"{bar[0]} {bar[1]}" if bar else None, "passed": passed}


class StoredExperiment:
    """An experiment already in LangSmith, iterable like ExperimentResults ({"run", "example"}).

    Lets a notebook re-score and re-export a finished run without paying for it again.
    """

    def __init__(self, experiment_name: str, client=None):
        from langsmith import Client

        self.client = client or Client()
        project = self.client.read_project(project_name=experiment_name)
        self.experiment_name, self.experiment_id = project.name, project.id
        runs = {r.reference_example_id: r for r in self.client.list_runs(project_id=project.id, is_root=True)}
        dataset_id = project.reference_dataset_id
        self._items = [{"run": runs.get(ex.id), "example": ex} for ex in self.client.list_examples(dataset_id=dataset_id)]

    def __iter__(self):
        return iter(self._items)

    def __len__(self):
        return len(self._items)


def case_rows(results, client=None) -> list[dict]:
    """One row per case from a LangSmith ExperimentResults (data-model "Case result")."""
    from langsmith import Client

    client = client or Client()
    rows = []
    for item in results:
        run, example = item["run"], item["example"]
        outputs = (run.outputs if run else None) or {"error": getattr(run, "error", None) or "no output"}
        expected = example.outputs
        scores = score_case(outputs, expected)
        rows.append({
            "case_id": example.metadata["case_id"],
            "scenario_type": example.metadata["scenario_type"],
            "expected_escalate": expected["expected_escalate"],
            "predicted_escalate": outputs.get("escalate"),
            "escalation_match": scores["escalation_match"],
            "expected_route": "|".join(expected["expected_route"]),
            "predicted_route": outputs.get("route"),
            "route_match": scores["route_match"],
            "expected_refusal": expected["expected_refusal"],
            "refused": outputs.get("refused"),
            "refusal_match": scores["refusal_match"],
            "must_cite": "|".join(expected["must_cite_source_ids"]),
            "sources_cited": "|".join(outputs.get("sources_cited") or []),
            "citation_match": scores["citation_match"],
            "invalid_citations": "|".join(scores["invalid_citations"]),
            "unretrieved_citations": "|".join(scores["unretrieved_citations"]),
            "correct": scores["correct"],
            "model": outputs.get("model"),
            "latency_ms": outputs.get("latency_ms"),
            "cost_inr": outputs.get("cost_inr"),
            "error": outputs.get("error"),
            "trace_url": client.get_run_url(run=run, project_id=results.experiment_id) if run else None,
        })
    return sorted(rows, key=lambda r: r["case_id"])


def summarize(rows: list[dict], run_info: dict) -> dict:
    """Metrics against the §9.1 pass bars, plus every failure with its trace link (FR-009, FR-010)."""
    must_escalate = [r for r in rows if r["expected_escalate"]]
    cited_rows = [r for r in rows if r["citation_match"] is not None]
    latencies = [r["latency_ms"] / 1000 for r in rows if r["latency_ms"] is not None]
    costs = [r["cost_inr"] for r in rows if r["cost_inr"] is not None]

    def brief(r):
        return {"case_id": r["case_id"], "scenario_type": r["scenario_type"], "trace_url": r["trace_url"]}

    return {
        "run": {**run_info, "n_cases": len(rows), "n_errors": sum(bool(r["error"]) for r in rows),
                "total_cost_inr": round(sum(costs), 2)},
        "metrics": {
            "escalation_recall": _metric("escalation_recall", _share([bool(r["predicted_escalate"]) and not r["error"] for r in must_escalate]), len(must_escalate)),
            "refusal_accuracy": _metric("refusal_accuracy", _share([r["refusal_match"] for r in rows]), len(rows)),
            "routing_accuracy": _metric("routing_accuracy", _share([r["route_match"] for r in rows]), len(rows)),
            "citation_match": _metric("citation_match", _share([r["citation_match"] for r in cited_rows]), len(cited_rows)),
            "p95_latency_s": _metric("p95_latency_s", round(_p95(latencies), 2) if latencies else None, len(latencies)),
            "mean_cost_inr": _metric("mean_cost_inr", round(sum(costs) / len(costs), 3) if costs else None, len(costs)),
            "p95_cost_inr": _metric("p95_cost_inr", round(_p95(costs), 3) if costs else None, len(costs)),
        },
        "failures": {
            "missed_escalations": [brief(r) for r in must_escalate if not (r["predicted_escalate"] and not r["error"])],
            "false_escalations": [brief(r) for r in rows if not r["expected_escalate"] and r["predicted_escalate"]],
            "wrong_refusals": [{**brief(r), "expected_refusal": r["expected_refusal"]} for r in rows if not r["refusal_match"] and not r["error"]],
            "errors": [{**brief(r), "error": r["error"]} for r in rows if r["error"]],
        },
    }


def scorecard(summary: dict) -> str:
    """The summary's metrics as a plain-text table for notebooks and the console."""
    lines = [f"{'metric':20} {'value':>9} {'n':>5}  {'pass bar':10} result"]
    for name, m in summary["metrics"].items():
        value = "-" if m["value"] is None else (f"{m['value']:.1%}" if name.endswith(("recall", "accuracy", "match")) else f"{m['value']}")
        result = {True: "PASS", False: "FAIL", None: "(reported)"}[m["passed"]]
        lines.append(f"{name:20} {value:>9} {m['n'] or '':>5}  {m['pass_bar'] or '-':10} {result}")
    return "\n".join(lines)


def export(results, run_info: dict, prefix: str) -> tuple[Path, Path]:
    """Write <prefix>_<date>_cases.csv and <prefix>_<date>_summary.json to evals/results/."""
    rows = case_rows(results)
    stamp = date.today().isoformat()
    info = {**run_info, "run_date": stamp, "experiment": results.experiment_name}
    summary = summarize(rows, info)

    RESULTS_DIR.mkdir(exist_ok=True)
    csv_path = RESULTS_DIR / f"{prefix}_{stamp}_cases.csv"
    with open(csv_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)
    json_path = RESULTS_DIR / f"{prefix}_{stamp}_summary.json"
    json_path.write_text(json.dumps(summary, indent=2, ensure_ascii=False), encoding="utf-8")
    return csv_path, json_path
