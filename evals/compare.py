"""Phase 3 comparison from saved results only (no API calls): baseline vs v1...v5.

    uv run python -m evals.compare     # rewrites phase3_judge_round1.json and phase3_failure_analysis.json
"""

import csv
import json
from pathlib import Path

from evals import judge
from evals.evaluators import PASS_BARS, RESULTS_DIR

VERSIONS = ["baseline", "v1", "v2", "v3", "v4", "v5"]
FAITHFULNESS_BAR = (">=", 0.9)  # plan §9.1
METRICS = ["escalation_recall", "refusal_accuracy", "routing_accuracy", "citation_match", "faithfulness",
           "p95_latency_s", "mean_cost_inr", "p95_cost_inr"]
SHARES = {"escalation_recall", "refusal_accuracy", "routing_accuracy", "citation_match", "faithfulness"}
BARS = {**PASS_BARS, "faithfulness": FAITHFULNESS_BAR}
FAILURE_MODES = ["routing boundary", "refusal calibration", "wrong source family", "unsupported claim", "citation mismatch"]


def _prefix(version: str) -> str:
    return "baseline" if version == "baseline" else f"improved_{version}"


def _latest(directory: Path, pattern: str) -> Path:
    found = sorted(directory.glob(pattern))
    if not found:
        raise FileNotFoundError(f"{directory}/{pattern}")
    return found[-1]


def load_summary(version: str, results_dir: Path = RESULTS_DIR) -> dict:
    return json.loads(_latest(results_dir, f"{_prefix(version)}_*_summary.json").read_text(encoding="utf-8"))


def load_cases(version: str, results_dir: Path = RESULTS_DIR) -> list[dict]:
    with open(_latest(results_dir, f"{_prefix(version)}_*_cases.csv"), encoding="utf-8") as f:
        return list(csv.DictReader(f))


def load_judge(version: str, results_dir: Path = RESULTS_DIR) -> list[dict]:
    """Judge rows with `faithful` as True/False/None (empty = judge error) and `claim_support` as a float or None."""
    experiment = load_summary(version, results_dir)["run"]["experiment"]
    with open(_latest(results_dir, f"{experiment}_*_judge.csv"), encoding="utf-8") as f:
        rows = list(csv.DictReader(f))
    for r in rows:
        r["faithful"] = {"true": True, "false": False}.get(r["faithful"].strip().lower())
        r["claim_support"] = float(r["claim_support"]) if r["claim_support"].strip() else None
    return rows


def judge_summary(version: str, results_dir: Path = RESULTS_DIR) -> dict:
    return judge.summary(load_judge(version, results_dir))


def _passed(metric: str, value: float | None) -> bool | None:
    bar = BARS.get(metric)
    if bar is None or value is None:
        return None
    op, limit = bar
    return value >= limit if op == ">=" else value < limit


def comparison_table(results_dir: Path = RESULTS_DIR, versions: list[str] = VERSIONS) -> list[dict]:
    """One row per version: metric values, delta vs the previous row and vs the first, pass/fail vs the §9.1 bars."""
    values = []
    for v in versions:
        metrics = {k: m["value"] for k, m in load_summary(v, results_dir)["metrics"].items()}
        metrics["faithfulness"] = judge_summary(v, results_dir)["faithfulness"]
        values.append(metrics)

    def delta(a, b):
        return None if a is None or b is None else round(a - b, 4)

    table = []
    for i, (v, m) in enumerate(zip(versions, values)):
        table.append({
            "version": v,
            **{k: m.get(k) for k in METRICS},
            "delta_prev": {k: delta(m.get(k), values[i - 1].get(k)) if i else None for k in METRICS},
            "delta_baseline": {k: delta(m.get(k), values[0].get(k)) if i else None for k in METRICS},
            "passed": {k: _passed(k, m.get(k)) for k in METRICS},
        })
    return table


def format_table(table: list[dict]) -> str:
    """Plain text: value (delta vs previous) with X where a pass bar is missed."""
    short = {"escalation_recall": "esc", "refusal_accuracy": "refuse", "routing_accuracy": "route", "citation_match": "cite",
             "faithfulness": "faith", "p95_latency_s": "p95 s", "mean_cost_inr": "mean Rs", "p95_cost_inr": "p95 Rs"}
    lines = ["version " + "".join(f"{short[k]:>19}" for k in METRICS)]
    for row in table:
        cells = []
        for k in METRICS:
            v, d, ok = row[k], row["delta_prev"][k], row["passed"][k]
            share = k in SHARES
            text = "-" if v is None else (f"{v:.1%}" if share else f"{v}")
            if d is not None:
                text += f" ({d:+.1%})" if share else f" ({d:+g})"
            cells.append(f"{text + (' X' if ok is False else ''):>19}")
        lines.append(f"{row['version']:8}" + "".join(cells))
    lines.append("X = misses the §9.1 pass bar (citation match has no bar of its own); deltas are vs the previous row")
    return "\n".join(lines)


def faithfulness_regressions(a: str, b: str, results_dir: Path = RESULTS_DIR) -> list[dict]:
    """Cases judged faithful in run `a` and unfaithful in run `b`, with the judge's unsupported claims."""
    before = {r["case_id"]: r for r in load_judge(a, results_dir)}
    out = []
    for r in load_judge(b, results_dir):
        old = before.get(r["case_id"])
        if old and old["faithful"] is True and r["faithful"] is False:
            out.append({"case_id": r["case_id"], "agent": r["agent"], "scenario_type": r["scenario_type"],
                        "unsupported": r["unsupported"], "question": r["question"]})
    return sorted(out, key=lambda x: x["case_id"])


def failure_modes(version: str, results_dir: Path = RESULTS_DIR) -> dict[str, list[str]]:
    """Failing case IDs per category (a case can sit in more than one):

    routing boundary = route mismatch; refusal calibration = refused or answered wrongly;
    wrong source family = required source missed while other sources were cited;
    citation mismatch = required source missed with nothing cited, or a citation that was invalid or never retrieved;
    unsupported claim = the judge found an unsupported claim.
    """
    modes: dict[str, list[str]] = {m: [] for m in FAILURE_MODES}
    for r in load_cases(version, results_dir):
        if r["route_match"].strip() == "False":
            modes["routing boundary"].append(r["case_id"])
        if r["refusal_match"].strip() == "False":
            modes["refusal calibration"].append(r["case_id"])
        missed = r["citation_match"].strip() == "False"
        if missed and r["sources_cited"].strip():
            modes["wrong source family"].append(r["case_id"])
        if (missed and not r["sources_cited"].strip()) or r["invalid_citations"].strip() or r["unretrieved_citations"].strip():
            modes["citation mismatch"].append(r["case_id"])
    modes["unsupported claim"] = [r["case_id"] for r in load_judge(version, results_dir) if r["faithful"] is False]
    return {k: sorted(v) for k, v in modes.items()}


def top_failure_modes(version: str, n: int = 3, results_dir: Path = RESULTS_DIR) -> list[dict]:
    modes = failure_modes(version, results_dir)
    ranked = sorted(modes.items(), key=lambda kv: (-len(kv[1]), FAILURE_MODES.index(kv[0])))
    return [{"mode": k, "count": len(v), "case_ids": v} for k, v in ranked[:n] if v]


def citation_misses(version: str, results_dir: Path = RESULTS_DIR) -> list[dict]:
    return [{"case_id": r["case_id"], "scenario_type": r["scenario_type"], "must_cite": r["must_cite"], "sources_cited": r["sources_cited"]}
            for r in load_cases(version, results_dir) if r["citation_match"].strip() == "False"]


def write_artifacts(results_dir: Path = RESULTS_DIR) -> tuple[Path, Path]:
    """Add baseline and v5 to the judge round-1 file (same method as v1-v4) and write the v5 failure analysis."""
    round1_path = results_dir / "phase3_judge_round1.json"
    round1 = {v: judge_summary(v, results_dir) for v in VERSIONS}
    round1_path.write_text(json.dumps(round1, indent=1) + "\n", encoding="utf-8")

    analysis = {
        "experiment": load_summary("v5", results_dir)["run"]["experiment"],
        "faithfulness_regressions_v4_to_v5": faithfulness_regressions("v4", "v5", results_dir),
        "citation_misses_v5": citation_misses("v5", results_dir),
        "top_failure_modes_v5": top_failure_modes("v5", 3, results_dir),
    }
    analysis_path = results_dir / "phase3_failure_analysis.json"
    analysis_path.write_text(json.dumps(analysis, indent=1) + "\n", encoding="utf-8")
    return round1_path, analysis_path


if __name__ == "__main__":
    for p in write_artifacts():
        print("wrote", p)
