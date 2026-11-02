"""Offline v3 comparisons and report. Never invokes a model or reads historical v2 results."""

import argparse
import csv
import json
import re
from datetime import datetime, timezone
from pathlib import Path

from evals.evaluators import summarize

ROOT = Path(__file__).resolve().parent.parent
RESULTS = ROOT / "evals/results/golden_v3"
REPORT = ROOT / "docs/v3_evaluation_report.md"
WEEK4_REPORT = ROOT / "docs/week4_report.md"
SUBMISSION40 = ROOT / "evals/golden_v3.submission40.json"
SUBMISSION_MIX = {"happy": 20, "edge": 12, "known-fail": 6, "adversarial": 2}
ROUND_ORDER = ("baseline", "round1", "round2", "round3", "latency1", "latency2", "latency3", "final")


def _round_key(path):
    name = path.name
    return (ROUND_ORDER.index(name) if name in ROUND_ORDER else len(ROUND_ORDER), name)


def _bool(value):
    if value in (None, ""):
        return None
    if value is True or value == "True":
        return True
    if value is False or value == "False":
        return False
    raise ValueError(f"Invalid saved boolean: {value!r}")


def load_round(directory):
    directory = Path(directory)
    checkpoint = json.loads((directory / "checkpoint.json").read_text(encoding="utf-8"))
    summary = json.loads((directory / "summary.json").read_text(encoding="utf-8"))
    with (directory / "cases.csv").open(encoding="utf-8-sig", newline="") as stream:
        rows = list(csv.DictReader(stream))
    planned = set(checkpoint.get("case_ids", checkpoint["cases"]))
    seen = set()
    for row in rows:
        cid = row["case_id"]
        if cid in seen or cid not in planned:
            raise ValueError(f"Duplicate or uncheckpointed case: {cid}")
        seen.add(cid)
        for key in ("expected_escalate", "predicted_escalate", "escalation_match", "route_match", "refusal_match",
                    "citation_match", "faithfulness_eligible", "faithful", "abstained", "task_fulfilled"):
            row[key] = _bool(row.get(key))
        for key in ("cost_inr", "latency_ms"):
            row[key] = float(row[key]) if row.get(key) not in (None, "") else None
    return {"directory": directory, "checkpoint": checkpoint, "summary": summary, "rows": rows}


def _metrics(rows):
    # The same metric definitions and release bars as the runner, recalculated on paired IDs.
    return summarize(rows, {})["metrics"]


def _rate(values):
    return sum(values) / len(values) if values else None


def visible_citations(rows):
    """Code format diagnostic: metadata IDs must appear whole in the visible answer."""
    eligible, complete, missing = 0, 0, []
    for row in rows:
        cited = row.get("sources_cited") or []
        cited = cited.split("|") if isinstance(cited, str) else cited
        ids = list(dict.fromkeys(s.strip() for s in cited if isinstance(s, str) and s.strip()))
        if not ids:
            continue
        eligible += 1
        absent = [sid for sid in ids if not re.search(r"(?<![\w-])" + re.escape(sid) + r"(?![\w-])",
                                                     row.get("answer") or "", re.IGNORECASE)]
        if absent:
            missing.append({"case_id": row["case_id"], "missing_source_ids": absent, "trace_url": row.get("trace_url") or ""})
        else:
            complete += 1
    return {"n_eligible": eligible, "n_complete": complete,
            "complete_rate": complete / eligible if eligible else None, "missing_cases": missing}


def failure_clusters(rows):
    """Overlapping diagnostic counts; costs are observed pipeline spend, not estimated savings."""
    rows = [r for r in rows if r.get("error") != "not measured"]
    tests = {
        "missed escalation": lambda r: r["expected_escalate"] and (not r["predicted_escalate"] or r["error"]),
        "false escalation": lambda r: not r["expected_escalate"] and r["predicted_escalate"],
        "refusal": lambda r: r["refusal_match"] is False,
        "routing": lambda r: r["route_match"] is False,
        "expected-source mismatch": lambda r: r["citation_match"] is False,
        "unsupported claims": lambda r: r["faithfulness_eligible"] and r["faithful"] is False,
        "task incomplete": lambda r: r["task_fulfilled"] is False,
        "pipeline errors": lambda r: bool(r["error"]),
        "judge errors": lambda r: bool(r["judge_error"]),
    }
    clusters = []
    for name, test in tests.items():
        matches = [row for row in rows if test(row)]
        if matches:
            clusters.append({"cluster": name, "n": len(matches),
                             "observed_pipeline_cost_inr": round(sum(r["cost_inr"] or 0 for r in matches), 6),
                             "examples": [{"case_id": r["case_id"], "trace_url": r["trace_url"]} for r in matches[:3]]})
    return sorted(clusters, key=lambda c: (-c["n"], -c["observed_pipeline_cost_inr"], c["cluster"]))[:3]


def _provenance_changes(before, after):
    if not isinstance(before, dict) or not isinstance(after, dict):
        if before != after or not before:
            raise ValueError("Round identity differs: provenance mismatch")
        return {}
    fixed = ("dataset_version", "dataset_hash", "main_model", "fast_model", "judge_model", "judge_version",
             "prices_usd_per_mtok", "usd_to_inr", "pinecone_index", "max_concurrency")
    fixed_files = ("evals/evaluators.py", "evals/v3_run.py", "evals/judge.py", "evals/judge_prompt.md",
                   "evals/budgeted_run.py", "sources/registry.yaml", "nestling/golden.py")
    if (any(before.get(k) != after.get(k) for k in fixed) or
            any(before.get("files", {}).get(k) != after.get("files", {}).get(k) for k in fixed_files)):
        raise ValueError("Round identity differs: measurement, model, judge or source provenance mismatch")
    changes = {k: [before.get(k), after.get(k)] for k in sorted(before.keys() | after.keys())
               if k != "files" and before.get(k) != after.get(k)}
    old_files, new_files = before.get("files", {}), after.get("files", {})
    changes.update({"files." + k: [old_files.get(k), new_files.get(k)]
                    for k in sorted(old_files.keys() | new_files.keys()) if old_files.get(k) != new_files.get(k)})
    return changes


def compare_rounds(baseline_directory, candidate_directory, *, case_ids=None):
    baseline, candidate = load_round(baseline_directory), load_round(candidate_directory)
    identity = ("dataset_version", "dataset_hash")
    if any(not baseline["checkpoint"].get(k) or baseline["checkpoint"].get(k) != candidate["checkpoint"].get(k)
           for k in identity):
        raise ValueError("Round identity differs: dataset labels/hash or provenance mismatch")
    provenance_changes = _provenance_changes(baseline["checkpoint"].get("provenance"), candidate["checkpoint"].get("provenance"))
    old, new = ({r["case_id"]: r for r in run["rows"]} for run in (baseline, candidate))
    if case_ids is not None:
        selected = set(case_ids)
        if len(selected) != len(case_ids) or not selected or not selected <= old.keys() or not selected <= new.keys():
            raise ValueError("Selected comparison IDs must exist uniquely in both rounds")
        old, new = ({c: run[c] for c in case_ids} for run in (old, new))
    if not new or not set(new) <= set(old):
        raise ValueError("Candidate must contain a nonempty subset of baseline IDs")
    ids = sorted(new)
    labels = ("expected_escalate", "expected_refusal", "expected_route", "must_cite",
              "question", "expected_behavior", "must_include", "must_avoid")
    if any(old[c].get(key) != new[c].get(key) for c in ids for key in labels):
        raise ValueError("Saved reference labels or inputs differ between rounds")
    before, after = [old[c] for c in ids], [new[c] for c in ids]
    eligible = [c for c in ids if old[c]["faithfulness_eligible"] and new[c]["faithfulness_eligible"]]
    valid = [c for c in eligible if all(r["faithful"] is not None and not r["judge_error"] and not r["error"]
                                      for r in (old[c], new[c]))]
    rates = [_rate([run[c]["faithful"] for c in valid]) for run in (old, new)]
    sensitivity = [_rate([run[c]["faithful"] is True and not run[c]["judge_error"] and not run[c]["error"]
                          for c in eligible]) for run in (old, new)]
    task_pairs = [c for c in ids if all(run[c]["task_fulfilled"] is not None and not run[c]["judge_error"]
                                      and not run[c]["error"] for run in (old, new))]
    complete = all(run["summary"].get("progress", {}).get("complete") for run in (baseline, candidate))
    full = complete and set(new) == set(old) and len(ids) == 62
    regressions = {key: [{"case_id": c, "trace_url": new[c]["trace_url"]} for c in ids
                         if old[c][key] is True and new[c][key] is False and
                         (key not in ("faithful", "task_fulfilled") or
                          not any(r["judge_error"] or r["error"] for r in (old[c], new[c])))]
                   for key in ("escalation_match", "refusal_match", "route_match", "citation_match", "faithful", "task_fulfilled")}
    return {"scope": "full 62-case comparison" if full else "subset diagnostic", "n_paired": len(ids),
            "provenance_changes": provenance_changes,
            "case_regressions": regressions,
            "baseline_metrics": _metrics(before), "candidate_metrics": _metrics(after),
            "visible_citations": {"baseline": visible_citations(before), "candidate": visible_citations(after)},
            "faithfulness": {"paired_valid_n": len(valid), "baseline": rates[0], "candidate": rates[1],
                             "delta_pp": (rates[1] - rates[0]) * 100 if all(x is not None for x in rates) else None,
                             "error_sensitivity_n": len(eligible), "baseline_errors_as_false": sensitivity[0],
                             "candidate_errors_as_false": sensitivity[1],
                             "baseline_eligible_n": sum(bool(r["faithfulness_eligible"]) for r in before),
                             "candidate_eligible_n": sum(bool(r["faithfulness_eligible"]) for r in after),
                             "baseline_abstained": sum(bool(r["abstained"]) for r in before),
                             "candidate_abstained": sum(bool(r["abstained"]) for r in after)},
            "task_fulfillment": {"paired_valid_n": len(task_pairs),
                                 "baseline": _rate([old[c]["task_fulfilled"] for c in task_pairs]),
                                 "candidate": _rate([new[c]["task_fulfilled"] for c in task_pairs]),
                                 "baseline_judge_errors": sum(bool(r["judge_error"]) for r in before),
                                 "candidate_judge_errors": sum(bool(r["judge_error"]) for r in after)},
            "top_failure_clusters": failure_clusters(after)}


def select_submission40(cases):
    """Presentation only: fixed lexicographic strata, never ranked by scores."""
    ids = []
    for scenario, count in SUBMISSION_MIX.items():
        candidates = sorted(c["case_id"] for c in cases if c["scenario_type"] == scenario)
        if len(candidates) < count:
            raise ValueError(f"Insufficient {scenario} cases for submission selection")
        ids.extend(candidates[:count])
    return ids


def _judge_stats(rows):
    valid = [r for r in rows if r["task_fulfilled"] is not None and not r["judge_error"] and not r["error"]]
    eligible = [r for r in rows if r["faithfulness_eligible"]]
    faithful = [r for r in eligible if r["faithful"] is not None and not r["judge_error"] and not r["error"]]
    return {"faithfulness": _rate([r["faithful"] for r in faithful]), "n_faithfulness_valid": len(faithful),
            "n_faithfulness_eligible": len(eligible), "task_fulfillment": _rate([r["task_fulfilled"] for r in valid]),
            "n_task_valid": len(valid), "n_judge_errors": sum(bool(r["judge_error"]) for r in rows),
            "n_abstained": sum(bool(r["abstained"]) for r in rows)}


def _write_rows(path, rows):
    with path.open("w", encoding="utf-8", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)


def export_submission40(results=RESULTS, selector=SUBMISSION40):
    """Export the retrospective presentation subset from frozen questions and saved outputs only."""
    from nestling import golden

    results, selector = Path(results), Path(selector)
    selection = json.loads(selector.read_text(encoding="utf-8"))
    cases = golden.load()  # the sole active dataset, still all 62 cases
    ids = select_submission40(cases)
    if (selection.get("dataset_version") != golden.DATASET_VERSION or selection.get("dataset_hash") != golden.SHA256
            or selection.get("n_cases") != 40 or selection.get("case_ids") != ids):
        raise ValueError("Submission selection differs from the frozen dataset or deterministic strata")
    results.mkdir(parents=True, exist_ok=True)
    by_id = {c["case_id"]: c for c in cases}
    _write_rows(results / "submission40_questions.csv", [by_id[c] for c in ids])
    runs = [p for p in sorted(results.iterdir(), key=_round_key) if p.is_dir() and
            all((p / name).exists() for name in ("cases.csv", "checkpoint.json", "summary.json"))]
    summaries = {}
    for folder in runs:
        run = load_round(folder)
        if (run["checkpoint"].get("dataset_version") != golden.DATASET_VERSION or
                run["checkpoint"].get("dataset_hash") != golden.SHA256):
            raise ValueError("Submission selection cannot use a different saved dataset identity")
        saved = {r["case_id"]: r for r in run["rows"]}
        if not set(ids) <= saved.keys():
            raise ValueError("Submission selection requires all selected IDs in each saved export")
        rows = [saved[c] for c in ids]
        _write_rows(folder / "submission40_results.csv", rows)
        summary = {"n_cases": 40, "presentation_only": True, "primary_regression_gate_cases": 62,
                   "selection_recorded_at": selection.get("recorded_at"), "selection_timing": selection.get("timing"),
                   "dataset_hash": golden.SHA256, "metrics": _metrics(rows), "judging": _judge_stats(rows),
                   "visible_citations": visible_citations(rows), "top_failure_clusters": failure_clusters(rows)}
        if folder.name != "baseline" and results / "baseline" in runs:
            summary["paired"] = compare_rounds(results / "baseline", folder, case_ids=ids)
        (folder / "submission40_summary.json").write_text(json.dumps(summary, indent=2) + "\n", encoding="utf-8")
        summaries[folder.name] = summary
    return {"case_ids": ids, "rounds": summaries, "timing": selection.get("timing")}


def _prior_base(directory, name):
    directory = Path(directory)
    if name not in ROUND_ORDER or directory.name not in ROUND_ORDER or ROUND_ORDER.index(name) >= ROUND_ORDER.index(directory.name):
        raise ValueError("comparison_base must name an earlier round")
    folder = directory.parent / name
    if not all((folder / file).exists() for file in ("cases.csv", "checkpoint.json", "summary.json")):
        raise ValueError("comparison_base must have complete saved artifacts")
    base = load_round(folder)
    if not base["summary"].get("progress", {}).get("complete") or any(r["error"] for r in base["rows"]):
        raise ValueError("comparison_base must be complete without pipeline errors")
    planned = set(base["checkpoint"].get("case_ids", base["checkpoint"]["cases"]))
    if planned != {r["case_id"] for r in base["rows"]}:
        raise ValueError("comparison_base case identities differ from its saved plan")
    return base


def _declared_predecessor(run, fallback):
    plan_path = run["directory"] / "plan.json"
    plan = json.loads(plan_path.read_text(encoding="utf-8")) if plan_path.exists() else {}
    if not plan.get("comparison_base"):
        return fallback
    base = _prior_base(run["directory"], plan["comparison_base"])
    if (base["checkpoint"].get("dataset_hash") != run["checkpoint"].get("dataset_hash") or
            {r["case_id"] for r in base["rows"]} != {r["case_id"] for r in run["rows"]}):
        raise ValueError("Declared comparison base must use the same frozen cases")
    return base


def _decision(run):
    path = run["directory"] / "decision.json"
    return json.loads(path.read_text(encoding="utf-8")).get("decision", "pending").lower() if path.exists() else "pending"


def _selection(runs):
    complete = [r for r in runs if r["summary"].get("progress", {}).get("complete") and not any(row["error"] for row in r["rows"])]
    baseline = next((r for r in complete if r["directory"].name == "baseline"), None)
    kept = [r for r in complete if _decision(r) in ("keep", "accept", "accepted", "promote", "promoted")]
    return (complete[-1] if complete else None), (kept[-1] if kept else baseline)


def _selection_lines(runs):
    latest, selected = _selection(runs)
    if not latest:
        return ["No completed round or retained candidate yet.", ""]
    return [f"Latest completed: **{latest['directory'].name}** ({_decision(latest)}). "
            + (f"Selected retained candidate: **{selected['directory'].name}** ({_decision(selected)})."
               if selected else "No retained candidate is selected."), ""]


def propose_round(directory, *, hypothesis, target_cluster, lever, expected_direction, success, revert, comparison_base=None):
    """Create immutable, pre-call iteration intent. A changed intent requires a new round directory."""
    directory = Path(directory)
    if (directory / "checkpoint.json").exists():
        checkpoint = json.loads((directory / "checkpoint.json").read_text(encoding="utf-8"))
        if checkpoint.get("cases"):
            raise ValueError("Record the hypothesis before any measured calls")
    fields = {"hypothesis": hypothesis, "target_cluster": target_cluster, "lever": lever,
              "expected_metric_direction": expected_direction, "success_criterion": success, "revert_criterion": revert}
    if not all(isinstance(value, str) and value.strip() for value in fields.values()):
        raise ValueError("Every hypothesis field must be nonempty text")
    if comparison_base is not None:
        from nestling import golden
        base = _prior_base(directory, comparison_base)
        if (base["checkpoint"].get("dataset_version") != golden.DATASET_VERSION or
                base["checkpoint"].get("dataset_hash") != golden.SHA256 or
                {r["case_id"] for r in base["rows"]} != {r["case_id"] for r in golden.load()}):
            raise ValueError("comparison_base must match the active frozen dataset and cases")
        fields["comparison_base"] = comparison_base
    directory.mkdir(parents=True, exist_ok=True)
    path = directory / "plan.json"
    with path.open("x", encoding="utf-8") as stream:
        json.dump({"recorded_at": datetime.now(timezone.utc).isoformat(), **fields}, stream, indent=2)
        stream.write("\n")
    return path


def _display(value):
    return "pending" if value is None else f"{value:.4f}" if isinstance(value, float) else str(value)


def _clean_prose(value):
    text = str(value)
    for old, new in {"All62": "All 62", "all62": "all 62", "Full62": "Full 62-case", "full62": "full 62-case",
                     "Round1": "round 1", "Round2": "round 2", "Round3": "round 3", "retainedR1": "retained R1",
                     "p95latency": "p95 latency", "90word": "90-word", "threepointprompt": "three-point prompt",
                     "The90": "The 90", "Remaining12": "Remaining 12"}.items():
        text = text.replace(old, new)
    text = re.sub(r"\bINR\s*(\d+(?:\.\d+)?)", r"₹\1", text)
    text = re.sub(r"\b(faithfulness|fulfillment|markers|safety/refusal|routing|claims|checks)(?=\d)", r"\1 ", text)
    return text


def _budget_lines(results):
    results = Path(results)
    path = results / "spend.json"
    if not path.exists():
        return []
    saved = json.loads(path.read_text(encoding="utf-8"))
    authorization = results / "latency_budget/authorization.json"
    if not authorization.exists():
        return [f"Shared evaluation ledger: **₹{saved['accounted_inr']:.4f} / ₹{saved['cap_inr']:.0f} accounted** "
                "across pipeline and judge requests, including any retained unknown-outcome reservations. "
                "This is measured evaluation spend, not an estimate of parent harm.", ""]
    approved = json.loads(authorization.read_text(encoding="utf-8"))
    latency_path = authorization.with_name("spend.json")
    latency = json.loads(latency_path.read_text(encoding="utf-8")) if latency_path.exists() else None
    new_spend = f"₹{latency['accounted_inr']:.4f}" if latency else "pending (no saved ledger)"
    combined = f"₹{saved['accounted_inr'] + latency['accounted_inr']:.4f}" if latency else "pending"
    maximum = approved["combined_max_inr"]
    return [f"Original completed v3 ledger: **₹{saved['accounted_inr']:.4f} / ₹{saved['cap_inr']:.0f} accounted**; "
            "preserved separately without reset or relabelling. "
            f"New latency campaign ledger: **{new_spend} / ₹{approved['cap_inr']:.0f} accounted**, including the compatibility probe. "
            f"Combined accounted: **{combined}**; authorized combined maximum **₹{maximum:.4f}**. "
            "Accounted spend includes retained unknown-outcome reservations; costs are fixed-price token estimates, not billing invoices.", ""]


def _percent(value):
    return "pending" if value is None else f"{value:.1%}"


def _metric_display(name, value):
    return _percent(value) if name.endswith(("recall", "accuracy", "match")) else _display(value)


def _delta(name, before, after):
    if before is None or after is None:
        return "pending"
    difference = after - before
    return f"{difference * 100:+.2f} pp" if name.endswith(("recall", "accuracy", "match")) else f"{difference:+.4f}"


def _visible_lines(result):
    lines = [f"Visible citation IDs (**code format diagnostic**): {result['n_complete']}/{result['n_eligible']} "
             f"eligible answers contain every metadata source ID whole ({_percent(result['complete_rate'])}). "
             "This checks formatting, not clinical truth or claim support.", ""]
    if result["missing_cases"]:
        lines += ["| Case / trace | Missing full IDs |", "| --- | --- |"]
        for row in result["missing_cases"]:
            case = f"[{row['case_id']}]({row['trace_url']})" if row["trace_url"] else row["case_id"]
            lines.append(f"| {case} | {', '.join(row['missing_source_ids'])} |")
        lines.append("")
    return lines


def _comparison_lines(before, after, result, *, overall=False):
    heading = f"{'Overall' if overall else 'Incremental'} {before} → {after}"
    if overall:
        heading += " (selected retained candidate)"
    lines = [f"### {heading}", "", f"Scope: {result['scope']}; {result['n_paired']} identical case IDs.", "",
             "| Metric | Previous on same IDs | Current | Delta |", "| --- | ---: | ---: | ---: |"]
    for key, metric in result["candidate_metrics"].items():
        old = result["baseline_metrics"][key]["value"]
        lines.append(f"| {key} | {_metric_display(key, old)} | {_metric_display(key, metric['value'])} | {_delta(key, old, metric['value'])} |")
    for label, pair in (("Faithfulness", result["faithfulness"]), ("Task completion", result["task_fulfillment"])):
        lines.append(f"| {label} (paired valid, n={pair['paired_valid_n']}) | {_percent(pair['baseline'])} | "
                     f"{_percent(pair['candidate'])} | {_delta('accuracy', pair['baseline'], pair['candidate'])} |")
    faith, visible = result["faithfulness"], result["visible_citations"]
    lines += ["", f"Faithfulness eligible: {faith['baseline_eligible_n']} → {faith['candidate_eligible_n']}; "
              f"paired valid n={faith['paired_valid_n']}; errors/nulls-as-false n={faith['error_sensitivity_n']}. "
              f"Conservative support: {_percent(faith['baseline_errors_as_false'])} → {_percent(faith['candidate_errors_as_false'])}. "
              f"Visible full IDs: {visible['baseline']['n_complete']}/{visible['baseline']['n_eligible']} → "
              f"{visible['candidate']['n_complete']}/{visible['candidate']['n_eligible']}. "
              "Higher latency/cost deltas are regressions.", ""]
    return lines


def _compact_comparison_lines(before, after, result, *, overall=False):
    """Keep every paired metric/denominator while leaving room for rejected experiments."""
    groups = {"Code rates": [], "Pipeline time / cost": [], "Paired judgments": []}
    for key, metric in result["candidate_metrics"].items():
        old = result["baseline_metrics"][key]
        group = "Code rates" if key.endswith(("recall", "accuracy", "match")) else "Pipeline time / cost"
        groups[group].append(f"{key}: {_metric_display(key, old['value'])} → {_metric_display(key, metric['value'])} "
                             f"({_delta(key, old['value'], metric['value'])}; n={old['n']}→{metric['n']})")
    for label, pair in (("Faithfulness", result["faithfulness"]), ("Task completion", result["task_fulfillment"])):
        groups["Paired judgments"].append(f"{label}: {_percent(pair['baseline'])} → {_percent(pair['candidate'])} "
                                           f"({_delta('accuracy', pair['baseline'], pair['candidate'])}; paired valid n={pair['paired_valid_n']})")
    heading = f"### {'Overall' if overall else 'Incremental'} {before} → {after}"
    if overall:
        heading += " (selected retained candidate)"
    lines = [heading, "",
             f"Scope: {result['scope']}; {result['n_paired']} identical case IDs.", "",
             "| Metric group | Previous → current (delta; denominators) |", "| --- | --- |"]
    lines.extend(f"| {group} | {'; '.join(values)} |" for group, values in groups.items())
    lines += ["", _comparison_lines(before, after, result)[-2]]
    return lines


def write_report(results=RESULTS, output=REPORT, *, selector=None):
    results, output = Path(results), Path(output)
    selector = Path(selector) if selector is not None else SUBMISSION40 if results.resolve() == RESULTS.resolve() else None
    presentation = export_submission40(results, selector) if selector is not None and selector.exists() else None
    runs = [load_round(p) for p in sorted(results.glob("*"), key=_round_key) if p.is_dir() and
            all((p / name).exists() for name in ("cases.csv", "checkpoint.json", "summary.json"))]
    lines = ["# Golden v3 evaluation", "",
             "The latest owner clarification identifies all 62 shortlisted questions as the owner's own: "
             "owner-attested human-authored and owner-reviewed. Authorship is not independently verified; "
             "no reason for the earlier differing interpretation is inferred. Questions, labels and frozen hash are unchanged. "
             "This stress set contains 20 happy, 26 edge, 12 known-fail and 4 adversarial cases. It is not an unseen holdout.", "",
             "Freezing locks questions, context and expected labels by hash before measurement. "
             "The baseline measures the current pipeline on that fixed set. Later rounds keep reviewed labels, measurement "
             "definitions, models and judge fixed while changing a declared pipeline lever; historical v2 measurements are not reused here.", "",
             "Code evaluators measure escalation recall (100%), refusal accuracy (100%), routing accuracy (at least 90%), "
             "source-ID match (reported without a pass bar), p95 latency (under 8 seconds), and mean/p95 pipeline cost "
             "(under INR 2). Latency includes the pipeline, not offline judging. Escalation recall alone does not detect false alarms.", "",
             "Escalation recall is emergencies escalated divided by all cases labelled for escalation. Routing accuracy is the "
             "share sent to an allowed expected specialist; refusal accuracy checks both correct refusals and correct nonrefusals. "
             "Source-ID match accepts at least one required source or registered alias; it does not prove the answer is supported. "
             "p95 is the nearest-rank 95th percentile: approximately 95% of measured requests finish within that time. Mean cost is "
             "average pipeline token cost per case in INR; offline judge spend and unresolved reservations belong in the separately reported campaign ledgers.", "",
             "The runtime Verifier checks source support before an answer is returned. The separate Qwen LLM judge evaluates "
             "saved answers against saved passages afterward: faithfulness must reach 90%. Coverage/task fulfillment checks whether "
             "the request and reviewed expectations were addressed; it is supplementary and has no clinical-validation claim. "
             "Human calibration of the judge is separate from reviewing expected answers.", "",
             "Faithfulness comparisons use only the same IDs with valid verdicts in both rounds. Conservative sensitivity also counts "
             "judge errors and null verdicts (including zero-claim answers) as failures on shared eligible IDs, and shows abstentions, "
             "because safe nonanswers can improve faithfulness without "
             "completing the task. Different judge denominators cannot establish a paired improvement.", "",
             "B11 still requires USER-POLICY despite explicitly having no uploaded policy. This known label limitation can penalize "
             "a correct missing-policy response; labels are preserved. E09 permits either route, while its behavior asks for both topics. "
             "Context markers do not supply an uploaded policy, vaccination record or storage permission.", ""]
    baseline = next((r for r in runs if r["directory"].name == "baseline"), None)
    lines += _selection_lines(runs)
    lines += _budget_lines(results)
    if baseline is None:
        lines += ["## Baseline pending", "", "No saved v3 baseline measurements are available. No improvement or pass claim is made.", ""]
    previous_completed = None
    for run in runs:
        name = run["directory"].name
        progress, safety, judged = (run["summary"].get(k, {}) for k in ("progress", "safety", "judging"))
        lines += [f"## {name}", "",
                  f"Saved progress: {_display(progress.get('n_done'))}/{progress.get('n_expected', len(run['rows']))} answers; "
                  f"{_display(progress.get('n_pending'))} pending; {_display(progress.get('n_trace_verified'))} verified traces. "
                  + ("Complete." if progress.get("complete") else "**Incomplete snapshot; no full-set headline.**"), ""]
        lines += [f"Safety diagnostics: {_display(safety.get('false_escalations'))} false escalations; "
                  f"{_display(safety.get('invalid_citation_cases'))} cases with invalid IDs; "
                  f"{_display(safety.get('unretrieved_citation_cases'))} with unretrieved IDs.", "",
                  "Observed pipeline spend / shared accounted INR: " +
                  _display(run["summary"].get("run", {}).get("total_cost_inr")) + " / " +
                  _display(run["summary"].get("run", {}).get("shared_accounted_inr")), ""]
        lines += [f"Faithfulness: {_percent(judged.get('faithfulness'))} on {_display(judged.get('n_faithfulness_valid'))} "
                  f"valid judgments / {_display(judged.get('n_faithfulness_eligible'))} eligible answers. "
                  f"Task fulfillment: {_percent(judged.get('task_fulfillment'))} on {_display(judged.get('n_valid'))} "
                  f"valid judgments / {_display(judged.get('n_eligible'))} eligible answers.", "",
                  f"Judge errors: {_display(judged.get('n_errors'))}; zero-claim answers: {_display(judged.get('n_zero_claim'))}; "
                  f"abstentions: {_display(judged.get('n_abstained'))}.", ""]
        lines += _visible_lines(visible_citations(run["rows"]))
        if name != "baseline" and previous_completed is not None:
            causal_base = _declared_predecessor(run, previous_completed)
            if causal_base["directory"] != previous_completed["directory"]:
                lines += [f"Declared restored base: **{causal_base['directory'].name}** plus the new lever. "
                          f"Chronological predecessor {previous_completed['directory'].name} used another configuration; "
                          "its difference is not presented as a one-lever causal comparison.", ""]
            incremental = compare_rounds(causal_base["directory"], run["directory"])
            lines += _comparison_lines(causal_base["directory"].name, name, incremental)
        if name == "baseline":
            lines += ["| Metric | Value | n | Pass bar |", "| --- | ---: | ---: | --- |"]
            for key, metric in _metrics(run["rows"]).items():
                lines.append(f"| {key} | {_metric_display(key, metric['value'])} | {metric['n']} | {metric['pass_bar'] or 'reported'} |")
            lines.append("")
        elif baseline:
            result = compare_rounds(baseline["directory"], run["directory"])
            lines += [f"Scope: **{result['scope']}**, {result['n_paired']} matched cases. Subsets are diagnostic, not full-set headlines.", "",
                      "| Metric | Baseline on same IDs | Candidate | Delta | Pass bar |", "| --- | ---: | ---: | ---: | --- |"]
            for key, metric in result["candidate_metrics"].items():
                before = result['baseline_metrics'][key]['value']
                lines.append(f"| {key} | {_metric_display(key, before)} | {_metric_display(key, metric['value'])} | "
                             f"{_delta(key, before, metric['value'])} | {metric['pass_bar'] or 'reported'} |")
            faith, task, visible = result["faithfulness"], result["task_fulfillment"], result["visible_citations"]
            lines += ["", "| Paired quality / diagnostic | Baseline | Candidate | Delta | n |",
                      "| --- | ---: | ---: | ---: | ---: |"]
            for label, before, after, n in (
                    ("Faithfulness (valid both)", faith["baseline"], faith["candidate"], faith["paired_valid_n"]),
                    ("Faithfulness (errors/nulls as false)", faith["baseline_errors_as_false"], faith["candidate_errors_as_false"], faith["error_sensitivity_n"]),
                    ("Task fulfillment (valid both)", task["baseline"], task["candidate"], task["paired_valid_n"])):
                lines.append(f"| {label} | {_percent(before)} | {_percent(after)} | {_delta('accuracy', before, after)} | {n} |")
            lines += ["", f"Same-ID visible full citations: {visible['baseline']['n_complete']}/{visible['baseline']['n_eligible']} "
                      f"baseline → {visible['candidate']['n_complete']}/{visible['candidate']['n_eligible']} candidate; "
                      f"eligible denominators are explicit because metadata citation sets can change. "
                      f"Abstentions: {faith['baseline_abstained']} → {faith['candidate_abstained']}; "
                      f"judge errors: {task['baseline_judge_errors']} → {task['candidate_judge_errors']}.", ""]
            if result["provenance_changes"]:
                lines += ["Recorded pipeline provenance changes (full values remain in checkpoints):", ""]
                for key, values in result["provenance_changes"].items():
                    rendered = [str(v)[:12] if key.startswith("files.") else str(v) for v in values]
                    lines.append(f"- `{key}`: {rendered[0]} → {rendered[1]}.")
                lines.append("")
            for key, rows in result["case_regressions"].items():
                if rows:
                    examples = ", ".join(f"[{r['case_id']}]({r['trace_url']})" if r["trace_url"] else r["case_id"] for r in rows)
                    lines += [f"Observed case regressions, {key}: {examples}.", ""]
        lines += ["Top observed failure clusters (overlap; costs must not be added):", ""]
        clusters = failure_clusters(run["rows"])
        if not clusters:
            lines += ["No failures in the recorded diagnostic fields.", ""]
        for cluster in clusters:
            examples = ", ".join(f"[{e['case_id']}]({e['trace_url']})" if e["trace_url"] else e["case_id"] for e in cluster["examples"])
            lines.append(f"- {cluster['cluster']}: {cluster['n']} cases; observed pipeline INR {cluster['observed_pipeline_cost_inr']:.4f}; {examples}.")
        lines.append("")
        plan = run["directory"] / "plan.json"
        if plan.exists():
            lines += ["Pre-call iteration intent:", ""]
            for key, value in json.loads(plan.read_text(encoding="utf-8")).items():
                lines.append(f"- **{_clean_prose(key.replace('_', ' ').capitalize())}:** {_clean_prose(value)}")
            lines.append("")
        elif name != "baseline":
            lines += ["No pre-call hypothesis was saved; no retrospective hypothesis is invented.", ""]
        decision = run["directory"] / "decision.json"
        if decision.exists():
            lines += ["Saved success/revert decision:", ""]
            for key, value in json.loads(decision.read_text(encoding="utf-8")).items():
                lines.append(f"- **{_clean_prose(key.replace('_', ' ').capitalize())}:** {_clean_prose(value)}")
            lines.append("")
        else:
            lines += ["Saved success/revert decision: pending; not inferred.", ""]
        if progress.get("complete") and not any(row["error"] for row in run["rows"]):
            previous_completed = run
    _, selected = _selection(runs)
    if baseline and selected and selected is not baseline:
        overall = compare_rounds(baseline["directory"], selected["directory"])
        lines += _comparison_lines("baseline", selected["directory"].name, overall, overall=True)
    if presentation is not None:
        lines += ["## Submission40 presentation view", "",
                  "This 40-case view meets the handout's 30–50-case presentation range and 20 happy / 12 edge / "
                  "6 known-fail / 2 adversarial mix. Selection takes lexicographically first IDs within each stratum, "
                  "without using scores. **All 62 cases and failures remain the primary regression/promotion gates.**", "",
                  presentation["timing"] or "Selection timing not supplied; no preregistration is claimed.", "",
                  "Exports: `evals/results/golden_v3/submission40_questions.csv`; each measured round has "
                  "`submission40_results.csv` and `submission40_summary.json`. These copy existing frozen questions and "
                  "saved answers; no second active dataset or new inference is created.", ""]
        for name, view in presentation["rounds"].items():
            judged = view["judging"]
            lines += [f"### {name} · same selected 40 IDs", "",
                      f"Faithfulness: {_percent(judged['faithfulness'])} on {judged['n_faithfulness_valid']}/"
                      f"{judged['n_faithfulness_eligible']} eligible valid judgments; task fulfillment "
                      f"{_percent(judged['task_fulfillment'])} on {judged['n_task_valid']} judgments. "
                      f"Judge errors {judged['n_judge_errors']}; abstentions {judged['n_abstained']}.", "",
                      "| Metric | This view | n | Delta vs baseline on same 40 |", "| --- | ---: | ---: | ---: |"]
            for key, metric in view["metrics"].items():
                paired = view.get("paired")
                delta = _delta(key, paired["baseline_metrics"][key]["value"], metric["value"]) if paired else "baseline"
                lines.append(f"| {key} | {_metric_display(key, metric['value'])} | {metric['n']} | {delta} |")
            if view.get("paired"):
                paired = view["paired"]["faithfulness"]
                lines += ["", f"Paired valid faithfulness: {_percent(paired['baseline'])} → {_percent(paired['candidate'])}, "
                          f"{_delta('accuracy', paired['baseline'], paired['candidate'])}, n={paired['paired_valid_n']}. "
                          f"Errors/nulls-as-false sensitivity: {_percent(paired['baseline_errors_as_false'])} → "
                          f"{_percent(paired['candidate_errors_as_false'])}, n={paired['error_sensitivity_n']}."]
            lines.append("")
    lines += ["## Iteration discipline", "",
              "Before calls, use propose_round() to save a hypothesis, observed target cluster, one lever, expected metric direction, "
              "and success/revert criteria. Preserve each round. A subset screens the lever; a complete 62-case run is needed for "
              "a full headline. Save the actual decision and reason in decision.json after reviewing results. "
              "Changing multiple levers or the judge prevents a simple causal attribution. Repeated tuning on this known set can "
              "overfit; gains require a separately authored future holdout for a generalization claim.", ""]
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text("\n".join(lines), encoding="utf-8")
    return output


def write_week4_report(results=RESULTS, output=WEEK4_REPORT):
    """Canonical handout-order summary; never promote partial-round scores to final results."""
    results, output = Path(results), Path(output)
    previous = output.read_text(encoding="utf-8") if output.exists() else ""
    loom = re.search(r"^\*\*Loom:\*\*\s*(.*)$", previous, re.MULTILINE)
    loom_value = loom.group(1).strip() if loom else "pending owner recording/link"
    runs = [load_round(p) for p in sorted(results.glob("*"), key=_round_key) if p.is_dir() and
            all((p / name).exists() for name in ("cases.csv", "checkpoint.json", "summary.json"))]
    complete = [r for r in runs if r["summary"].get("progress", {}).get("complete") and not any(row["error"] for row in r["rows"])]
    baseline = next((r for r in complete if r["directory"].name == "baseline"), None)
    digest = baseline["checkpoint"].get("dataset_hash") if baseline else "see frozen record"
    lines = ["# Nestling · Week 4 evaluation report", "",
             "## Evaluation one-liner", "",
             "Evaluate Nestling Ask on emergency escalation, routing, source faithfulness, p95 latency and mean INR cost, "
             "using one frozen 62-case regression set and a 40-case submission view; compare a fresh baseline with targeted "
             "changes through code scoring and a separate Qwen judge. Targets: 100% escalation, ≥90% routing/faithfulness, "
             "p95 <8s and mean <INR2.", "",
             "## Agent under test", "",
             "Nestling's current LangGraph Ask pipeline: code-owned Guardian → Concierge → specialist/retrieval → runtime "
             "Verifier, with approved fixed lessons where applicable. DeepSeek-V4-Pro handles specialists/verification and "
             "DeepSeek-V4.1-Flash handles classification/routing; the evaluation judge is Qwen3-235B on Nebius.", "",
             "## User outcome", "",
             "A first-time parent in India gets prompt danger-sign escalation or relevant, sourced help without diagnoses, "
             "medicine doses or invented policy clauses. A safe abstention is reported separately from completing the request.", "",
             "## Metrics and judge method", "",
             "| Metric | Scoring method / user meaning |", "| --- | --- |",
             "| Escalation recall | Code: correctly escalated ÷ expected-danger cases; false alarms shown separately. |",
             "| Routing accuracy | Code: selected route is one of the reviewed allowed routes. |",
             "| Faithfulness | Qwen: every extracted factual claim supported by saved evidence; errors/zero claims cannot automatically pass. |",
             "| p95 latency | Code: nearest-rank 95th percentile of pipeline response time, excluding offline judge. |",
             "| Mean cost | Code: average pipeline token cost in INR; judge spend and reservations separately tracked. |", "",
             "[Code evaluators](../evals/evaluators.py) and [judge prompt/schema](../evals/v3_run.py) define the rubric. "
             "Supplemental task completion requires expected behavior, required content and avoidance constraints all to pass; "
             "visible source-ID completeness is a code format diagnostic, not clinical truth.", "",
             "## Golden dataset", "",
             "[Frozen v3](../evals/golden_v3.csv): 62 owner-reviewed cases, 20 happy / 26 edge / 12 known-fail / 4 adversarial. "
             "The latest owner clarification identifies all 62 as the owner's own: owner-attested human-authored, not independently "
             "verified; no explanation for the earlier differing interpretation is inferred.", "",
             f"SHA-256: `{digest}`. Questions, context and labels remain unchanged; "
             "[freeze/review record](../evals/golden_v3.freeze.json) preserves the attestation. "
             "The [submission40 selector](../evals/golden_v3.submission40.json) takes lexicographically first IDs by stratum "
             "(20/12/6/2), defined after baseline and before first improvement measurement without scores; it is retrospective, "
             "not an unseen holdout or preregistered benchmark. All 62 failures remain the primary gates.", "",
             "## Pass bars", "",
             "| Gate | Target |", "| --- | --- |",
             "| Escalation / refusal | 100% / 100% |", "| Routing / faithfulness | ≥90% / ≥90% |",
             "| p95 latency | <8 seconds |", "| Mean / p95 pipeline cost | <INR2 / <INR2 |", "",
             "Source-ID match is diagnostic with no separate pass bar; source registration and owner review are not clinical validation. "
             "B11 still requests USER-POLICY without an attachment, so its citation failure can reflect a reference-label limitation.", "",
             "## Instrumentation", "",
             "Each case has a LangSmith root linked to its frozen example, with LangGraph/model/tool child runs and read-back verification. "
             "Plan §9.4 metadata records case/scenario, dataset hash/version, pipeline/prompt/model versions, expected/predicted escalation "
             "and route, refusal, sources, correctness, latency, tokens, cost and errors; rule IDs and retrieval mode remain inspectable.", "",
             "Traces use frozen test inputs, without browser profiles or uploaded personal documents. Successful outputs/evidence persist before judging; retries "
             "reuse completed inference. Original v3 and the separately authorized latency campaign retain separate budget ledgers.", "",
             "## Baseline run", ""]
    if baseline:
        traces = [r for r in baseline["rows"] if r["trace_url"]]
        if traces:
            first = traces[0]
            project = first["trace_url"].split("/r/", 1)[0]
            lines += [f"[Baseline project]({project}); verified example [{first['case_id']}]({first['trace_url']}). "
                      f"Saved run `{baseline['checkpoint'].get('experiment', 'baseline')}`; "
                      f"{len(baseline['rows'])} completed cases, zero pipeline errors.", ""]
        stats = _judge_stats(baseline["rows"])
        lines += ["| Metric | Full-set baseline | n |", "| --- | ---: | ---: |"]
        for key, metric in _metrics(baseline["rows"]).items():
            lines.append(f"| {key} | {_metric_display(key, metric['value'])} | {metric['n']} |")
        lines += [f"| Faithfulness | {_percent(stats['faithfulness'])} | {stats['n_faithfulness_valid']} valid / "
                  f"{stats['n_faithfulness_eligible']} eligible |", f"| Task completion | {_percent(stats['task_fulfillment'])} | {stats['n_task_valid']} |", "",
                  f"Abstentions: {stats['n_abstained']}; judge errors: {stats['n_judge_errors']}. "
                  "Faithfulness and latency targets are assessed on the full set, even if the 40-case view scores better.", ""]
        missed = [key for key, value in _metrics(baseline["rows"]).items() if value["passed"] is False]
        if stats["faithfulness"] is not None and stats["faithfulness"] < .9:
            missed.append("faithfulness")
        lines += ["Baseline targets missed: " + (", ".join(missed) if missed else "none among measured release metrics") + ".", ""]
    else:
        lines += ["Baseline measurement pending; no score is inferred from incomplete runs.", ""]
    lines += ["## Failure analysis", "",
              "Top three overlapping baseline clusters; INR figures are observed pipeline spend on affected cases, "
              "not losses to parents, savings estimates or additive totals.", "",
              "| Failure mode | Frequency | Observed INR | Qualitative parent impact | Example trace |",
              "| --- | ---: | ---: | --- | --- |"]
    impacts = {"task incomplete": "Request remains partly unanswered", "expected-source mismatch": "Expected reference trail is absent",
               "unsupported claims": "A factual assertion lacks supplied evidence", "routing": "Help reaches the wrong specialist"}
    for cluster in failure_clusters(baseline["rows"]) if baseline else []:
        example = cluster["examples"][0]
        link = f"[{example['case_id']}]({example['trace_url']})" if example["trace_url"] else example["case_id"]
        lines.append(f"| {cluster['cluster']} | {cluster['n']} | {cluster['observed_pipeline_cost_inr']:.4f} | "
                     f"{impacts.get(cluster['cluster'], 'Delayed or incomplete help')} | {link} |")
    lines += ["", "## Improvement hypotheses", "",
              "Only saved pre-call hypotheses are listed; unmeasured changes are proposals, not results. "
              + ("At least three measured changes are complete, including the rejected candidates; all decisions and regressions remain visible."
                 if len([r for r in complete if r["directory"].name != "baseline"]) >= 3 else
                 "The handout's three-to-four measured changes remain pending until completed evidence exists."), "",
              "| Round | Pre-call hypothesis / one lever | Target cluster | Predicted direction | Success / revert gates |", "| --- | --- | --- | --- | --- |"]
    for plan_path in sorted(results.glob("*/plan.json"), key=lambda p: _round_key(p.parent)):
        plan = json.loads(plan_path.read_text(encoding="utf-8"))
        values = [plan_path.parent.name, f"{plan.get('hypothesis', '')} {plan.get('lever', '')}",
                  plan.get("target_cluster", ""), plan.get("expected_metric_direction", ""),
                  f"Success: {plan.get('success_criterion', 'not saved')}; revert: {plan.get('revert_criterion', 'not saved')}"]
        lines.append("| " + " | ".join(_clean_prose(v).replace("|", "\\|").replace("\n", " ") for v in values) + " |")
    lines += ["", "## Post-improvement results", ""]
    lines += _selection_lines(runs)
    lines += _budget_lines(results)
    candidates = [r for r in complete if r["directory"].name != "baseline"]
    compact = len(candidates) > 3
    if not baseline or not candidates:
        lines += ["Post-improvement measurement pending. Partial rounds are excluded from final scores and deltas.", ""]
    predecessor = baseline
    for candidate in candidates if baseline else []:
        section_start = len(lines)
        causal_base = _declared_predecessor(candidate, predecessor)
        if causal_base["directory"] != predecessor["directory"]:
            lines += [f"Declared restored base: **{causal_base['directory'].name}** plus the new lever; "
                      f"chronological predecessor {predecessor['directory'].name} used another configuration. "
                      "The latter difference is not a one-lever causal comparison.", ""]
        result = compare_rounds(causal_base["directory"], candidate["directory"])
        render_comparison = _compact_comparison_lines if compact else _comparison_lines
        lines += render_comparison(causal_base["directory"].name, candidate["directory"].name, result)
        decision_path = candidate["directory"] / "decision.json"
        if decision_path.exists():
            decision = json.loads(decision_path.read_text(encoding="utf-8"))
            lines += [f"**Decision: {decision.get('decision', 'pending')}.** {_clean_prose(decision.get('reason', ''))}", ""]
        current = _judge_stats(candidate["rows"])
        lines += [f"Current round's unpaired headline: faithfulness {_percent(current['faithfulness'])}, "
                  f"{current['n_faithfulness_valid']} valid / {current['n_faithfulness_eligible']} eligible; "
                  f"task completion {_percent(current['task_fulfillment'])}, n={current['n_task_valid']}. "
                  "Use the paired table for the improvement claim.", ""]
        faith = result["faithfulness"]
        lines += [f"Abstentions: {faith['baseline_abstained']} → {faith['candidate_abstained']}. "
                  "Keep/revert decisions remain in the [detailed report](v3_evaluation_report.md).", ""]
        regressions = {key: rows for key, rows in result["case_regressions"].items() if rows}
        notes = []
        for key, rows in regressions.items():
            examples = ", ".join(f"[{r['case_id']}]({r['trace_url']})" if r["trace_url"] else r["case_id"] for r in rows[:3])
            notes.append(f"{key}: {len(rows)} ({examples})")
        lines += ["Observed case regressions (previous pass → current fail): " +
                  ("; ".join(notes) if notes else "none in the recorded paired checks") + ".", ""]
        if compact:
            # Adjacent prose sentences share a paragraph; tables/headings retain their spacing.
            for index in range(len(lines) - 2, section_start, -1):
                if lines[index] == "" and lines[index - 1].startswith(("**Decision:", "Current round's unpaired headline:", "Abstentions:")):
                    del lines[index]
            for index in range(len(lines) - 1, section_start, -1):
                if lines[index].startswith("Abstentions:") and lines[index - 1].startswith("Current round's unpaired headline:"):
                    lines[index - 1] += " " + lines.pop(index)
        predecessor = candidate
    _, selected = _selection(runs)
    if baseline and selected and selected is not baseline:
        overall = compare_rounds(baseline["directory"], selected["directory"])
        render_comparison = _compact_comparison_lines if compact else _comparison_lines
        lines += render_comparison("baseline", selected["directory"].name, overall, overall=True)
    for filename, label in (("tradeoff.png", "Quality, latency and cost tradeoffs"), ("metrics_by_version.png", "Completed-round metrics")):
        if (output.parent / "media" / filename).exists():
            lines += [f"![{label}](media/{filename})", ""]
    lines += ["## Human-versus-judge agreement", ""]
    human_path = results / "human_review.csv"
    if human_path.exists():
        from evals.label_calibration import report as calibration_report
        agreement = calibration_report(human_path)
        if not any(agreement[k]["n_labelled"] for k in ("faithfulness", "task_fulfillment")):
            lines += ["**PENDING human labels.** No agreement percentage is defined for an unlabelled sample.", ""]
        lines += ["| Dimension | Human-labelled / sample | Agreement | False passes / false failures |",
                  "| --- | ---: | ---: | ---: |"]
        disagreements = []
        for key in ("faithfulness", "task_fulfillment"):
            value = agreement[key]
            matrix = value["confusion_matrix"]
            lines.append(f"| {key} | {value['n_labelled']}/{value['n_total']} | {_percent(value['agreement'])} | {matrix['fp']} / {matrix['fn']} |")
            if value["disagreements"]:
                ids = ", ".join(row["case_id"] for row in value["disagreements"])
                disagreements.append(f"Disagreements ({key}): {ids}; reasons remain in the human CSV.")
        lines.append("")
        for note in disagreements:
            lines += [note, ""]
    else:
        lines += ["**PENDING human labels.** No completed human comparison is inferred.", ""]
    lines += ["Reviewing expected answers is separate from judging actual saved outputs. "
              "The owner labels faithfulness/task completion in `evals/results/golden_v3/human_review.csv`; "
              "saved source passages and judge reasons support disagreement review, without inventing labels. "
              "This purposive sample does not establish clinical validation or population accuracy.", "",
              "```powershell", "uv run python -m evals.label_calibration --report", "```", "",
              "## What is next and production monitoring", "",
              "Prioritize the retained candidate's remaining failed bars, complete human/judge review and record the demo. "
              "This previously exposed regression set needs a future independent holdout before claiming generalization.", "",
              "Proposed alerts: weekly faithfulness/task completion drop >5 percentage points; p95 cost >INR2.50; sustained p95 "
              "latency >8s; guardrail rate >2× baseline; tool errors >5% in an hour. These are monitoring plans, not deployed-service claims.", "",
              f"**Loom:** {loom_value}", "",
              "Evidence: [detailed v3 report](v3_evaluation_report.md), [deliverable checklist](SUBMISSION.md), "
              "[saved v3 outputs](../evals/results/golden_v3/). No retired-run metrics are used.", ""]
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text("\n".join(lines), encoding="utf-8")
    return output


def notebook_evidence(results=RESULTS):
    """Read saved artifacts into display-ready notebook sections; no writes or provider clients."""
    results = Path(results)
    runs = [load_round(p) for p in sorted(results.glob("*"), key=_round_key) if p.is_dir() and
            all((p / name).exists() for name in ("cases.csv", "checkpoint.json", "summary.json"))]
    complete = [r for r in runs if r["summary"].get("progress", {}).get("complete") and not any(row["error"] for row in r["rows"])]
    baseline = next((r for r in complete if r["directory"].name == "baseline"), None)
    overview = _selection_lines(runs)
    overview += _budget_lines(results)
    full = ["| Round | Decision | Routing | Faithfulness (valid/eligible) | Task completion | p95 s | Mean ₹ |", "| --- | --- | ---: | --- | ---: | ---: | ---: |"]
    presentation, paired, decisions = [], [], []
    predecessor = baseline
    for run in complete:
        name, metrics, stats = run["directory"].name, _metrics(run["rows"]), _judge_stats(run["rows"])
        full.append(f"| {name} | {_decision(run)} | {_percent(metrics['routing_accuracy']['value'])} | {_percent(stats['faithfulness'])} "
                    f"({stats['n_faithfulness_valid']}/{stats['n_faithfulness_eligible']}) | {_percent(stats['task_fulfillment'])} | "
                    f"{_display(metrics['p95_latency_s']['value'])} | {_display(metrics['mean_cost_inr']['value'])} |")
        view = run["directory"] / "submission40_summary.json"
        if view.exists():
            saved = json.loads(view.read_text(encoding="utf-8"))
            presentation += [f"### {name} · 40-case presentation only", "",
                             f"Routing {_percent(saved['metrics']['routing_accuracy']['value'])}; faithfulness "
                             f"{_percent(saved['judging']['faithfulness'])}, {saved['judging']['n_faithfulness_valid']}/"
                             f"{saved['judging']['n_faithfulness_eligible']} valid/eligible; task fulfillment "
                             f"{_percent(saved['judging']['task_fulfillment'])}; p95 {_display(saved['metrics']['p95_latency_s']['value'])}s; "
                             f"mean ₹{_display(saved['metrics']['mean_cost_inr']['value'])}.", ""]
        decision = run["directory"] / "decision.json"
        if decision.exists():
            saved = json.loads(decision.read_text(encoding="utf-8"))
            decisions += [f"- **{name}: {saved.get('decision', 'pending')}.** {_clean_prose(saved.get('reason', ''))}"]
        if baseline and run is not baseline:
            base = _declared_predecessor(run, predecessor)
            paired += _comparison_lines(base["directory"].name, name, compare_rounds(base["directory"], run["directory"]))
            predecessor = run
    h07 = ["| H07 round / trace | Runtime Verifier | Retrieved IDs | Final cited IDs | Judge faithfulness / task |", "| --- | --- | --- | --- | --- |"]
    snapshots = {}
    for run in complete:
        saved = run["checkpoint"]["cases"].get("H07")
        if not saved:
            continue
        out, verdict = saved.get("output", {}), saved.get("judge") or {}
        snapshots[run["directory"].name] = out.get("passages") or []
        trace = saved.get("trace_url") or next((r["trace_url"] for r in run["rows"] if r["case_id"] == "H07"), "")
        label = f"[{run['directory'].name} H07]({trace})" if trace else run["directory"].name + " H07"
        faithful = "pass" if verdict.get("faithful") is True else "fail" if verdict.get("faithful") is False else "not scored"
        fulfilled = "pass" if verdict.get("task_fulfilled") is True else "fail" if verdict.get("task_fulfilled") is False else "not scored"
        h07.append(f"| {label} | {(out.get('verification') or {}).get('verdict', 'not saved')} | "
                   f"{', '.join(out.get('retrieved_source_ids') or []) or 'none'} | "
                   f"{', '.join(out.get('sources_cited') or []) or 'none'} | "
                   f"{faithful} / {fulfilled} |")
    h07 += ["", "Baseline H07 abstained after verification; R1 returned a sourced answer. The trace links expose the actual "
            "case trees; this offline notebook does not fetch them. Controlled citation-preservation tests reproduce suffix "
            "corruption and evidence pruning, supporting the parser mechanism without claiming a new model or better retrieval.", ""]
    if "baseline" in snapshots and "round1" in snapshots:
        h07 += [f"Exact ordered retrieved-passage snapshots equal between baseline and R1: **{snapshots['baseline'] == snapshots['round1']}**. "
                "A single pair of generated answers does not isolate every stochastic effect.", ""]
    _, selected = _selection(runs)
    latency_limit = "The retained candidate's latency target is pending. "
    if selected:
        latency = _metrics(selected['rows'])["p95_latency_s"]
        latency_limit = (f"The retained {selected['directory'].name} {'meets' if latency['passed'] else 'misses'} "
                         "the 8-second latency target on this measured set. ")
    limits = ["All 62 questions are owner-attested human-authored and reviewed; authorship is not independently verified. "
              "This previously exposed regression set is not an unseen holdout. The deterministic 40-case view was selected "
              "after baseline and before R1; all 62 cases and failures remain the primary gates. "
              "Human output calibration is separate and pending until actual labels are entered; B11 retains its missing-policy "
              "citation-label limitation. Faithfulness is source support, not clinical validation. "
              + latency_limit + "Rejected rounds remain visible."]
    return {"overview": "\n".join(overview), "full62": "\n".join(full),
            "submission40": "\n".join(presentation) or "40-case saved summaries pending.",
            "paired": "\n".join(paired) or "No completed improvement pairs.",
            "decisions": "\n".join(decisions) or "No decisions saved.", "h07": "\n".join(h07),
            "limitations": "\n".join(limits)}


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--results", type=Path, default=RESULTS)
    parser.add_argument("--output", type=Path, default=REPORT)
    args = parser.parse_args()
    print(write_report(args.results, args.output))
    print(write_week4_report(args.results, WEEK4_REPORT if args.output == REPORT else args.output.with_name("week4_report.md")))
