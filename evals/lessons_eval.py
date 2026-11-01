"""Separate draft Little Lessons evaluation. No live generation unless --live is explicit.

    uv run python -m evals.lessons_eval --live --upload

The ₹20 ceiling includes routing and judge token costs. Human labels are never inferred.
"""

import csv
import hashlib
import json
import sys
import time
import uuid
from datetime import date
from pathlib import Path

import yaml

from evals import judge
from evals.evaluators import RESULTS_DIR
from nestling import guardian, llm, retrieval
from nestling.lessons import LESSONS, LESSONS_DIR, library
from nestling.tracing import USD_TO_INR, cost_inr, trace_metadata

DATASET = "nestling-lessons-v1"
PROJECT = "nestling-lessons"
GOLDEN = Path(__file__).with_name("lessons_golden_v1.csv")
PROMPT = Path(__file__).with_name("lessons_judge_prompt.md")
JUDGE_PRICE = (0.20, 0.60)  # USD/MTok; Nebius verbose model catalogue, 2026-11-01
CAP_INR = 20.0
JUDGE_PROMPT_VERSION = "lessons-judge-v2"


def load_cases() -> list[dict]:
    with GOLDEN.open(encoding="utf-8", newline="") as f:
        return list(csv.DictReader(f))


def score_route(actual: dict, expected: dict) -> dict:
    ok = not actual.get("error")
    return {"route_match": ok and (actual.get("lesson_id") or "none") == expected["expected_lesson_id"],
            "escalation_match": ok and bool(actual.get("escalate")) == (expected["expected_escalate"] == "Y")}


def evaluate_case(case: dict, matcher=None) -> dict:
    decision = guardian.decide(case["input"])
    usage, error, match = [], None, {"lesson_id": None}
    try:
        if not decision.escalate:
            match = matcher(case["input"]) if matcher else library.match(case["input"], usage=usage)
            if matcher is None and not usage:
                error = "matcher returned no usage; classification unavailable"
    except Exception as exc:
        error = type(exc).__name__
    costs = [cost_inr(u["model"], u.get("tokens_in", 0), u.get("tokens_out", 0)) for u in usage]
    actual = {"lesson_id": match.get("lesson_id"), "escalate": decision.escalate, "error": error}
    return {"case_id": case["case_id"], "label_status": case["label_status"],
            "expected_lesson_id": case["expected_lesson_id"], "expected_escalate": case["expected_escalate"],
            **actual, **score_route(actual, case), "cost_inr": round(sum(c or 0 for c in costs), 4),
            "tokens_in": sum(u.get("tokens_in", 0) for u in usage), "tokens_out": sum(u.get("tokens_out", 0) for u in usage)}


def review_summary(board: dict, review: dict) -> dict:
    expected = [s["step_no"] for s in board["scenes"]]
    scenes = review.get("scenes") or []
    current = review.get("version") == board["version"] and [s.get("step_no") for s in scenes] == expected
    reviewed = sum(s.get("passed") is not None for s in scenes) if current else 0
    done = current and reviewed == len(expected) and bool(expected)
    return {"status": "stale review" if not current else "reviewed" if done else "pending human review",
            "n_scenes": len(expected), "n_reviewed": reviewed,
            "pass_rate": sum(s.get("passed") is True for s in scenes) / len(expected) if done else None,
            "scenes": scenes, "approved": bool(done and review.get("approved") is True
                and all(s.get("passed") is True for s in scenes)
                and review.get("reviewer") and review.get("review_date"))}


def render_summary(folder: Path) -> dict:
    path = folder / "render_log.json"
    if not path.exists():
        return {"status": "not rendered yet", "cost_inr": None, "seconds": None}
    log = json.loads(path.read_text(encoding="utf-8"))
    return {"status": "rendered", "cost_inr": log.get("cost_inr"), "seconds": log.get("seconds"),
            "rendered_at": log.get("rendered_at"),
            **{k: log[k] for k in ("cost_basis", "cost_estimated", "storyboard_version", "reviewed_on", "render_history") if k in log}}


def source_passages(board: dict) -> list[dict]:
    registry = retrieval.load_registry()
    wanted = {(s["source_id"], str(s["page_label"])) for s in board["scenes"]}
    hits = []
    for sid in board["sources"]:
        source = registry.get(sid)
        if not source:
            continue
        if source.get("file") and (retrieval.PDF_DIR / source["file"]).exists():
            hits.extend(h for h in retrieval.load_chunks(source) if (h["source_id"], str(h["page_label"])) in wanted)
        elif source.get("snapshot_file"):
            snapshot = retrieval.PDF_DIR.parent / source["snapshot_file"]
            if snapshot.exists():
                pages = json.loads(snapshot.read_text(encoding="utf-8")).get("local_pages", {})
                hits.extend({"source_id": sid, "page_label": page, "chunk_text": text}
                            for page, text in pages.items() if (sid, str(page)) in wanted)
    return hits


def judge_steps(board: dict, hits: list[dict]) -> dict:
    wanted = {(s["source_id"], str(s["page_label"])) for s in board["scenes"]}
    found = {(h["source_id"], str(h["page_label"])) for h in hits}
    if not wanted <= found:
        return {"status": "missing local source pages", "faithful": None, "cost_inr": 0.0}
    schema = {"type": "object", "properties": {
        "faithful": {"type": "boolean"}, "missing_steps": {"type": "array", "items": {"type": "string"}},
        "invented_steps": {"type": "array", "items": {"type": "string"}},
        "explanation": {"type": "string"}},
        "required": ["faithful", "missing_steps", "invented_steps", "explanation"], "additionalProperties": False}
    text = json.dumps({"storyboard": board, "source_passages": hits}, ensure_ascii=False)
    if len(text.encode("utf-8")) > 60_000:
        return {"status": "source pages exceed budget envelope", "faithful": None, "cost_inr": 0.0}
    data, usage, _ = llm.chat_json(judge.JUDGE_MODEL, PROMPT.read_text(encoding="utf-8"), text, schema, max_tokens=1000)
    if data:
        data["faithful"] = bool(data["faithful"] and not data["missing_steps"] and not data["invented_steps"])
    charge = round((usage["tokens_in"] * JUDGE_PRICE[0] + usage["tokens_out"] * JUDGE_PRICE[1]) / 1e6 * USD_TO_INR, 4)
    return {"status": "judged" if data else "invalid judge response", **(data or {"faithful": None}),
            "usage": usage, "cost_inr": charge, "prompt_version": JUDGE_PROMPT_VERSION,
            "prompt_sha256": hashlib.sha256(PROMPT.read_bytes()).hexdigest()}


def summarize(rows: list[dict], lessons: list[dict]) -> dict:
    judged = [x["fidelity"]["faithful"] for x in lessons if x["fidelity"].get("faithful") is not None]
    danger = [r for r in rows if r["expected_escalate"] == "Y"]
    return {"dataset": DATASET, "label_status": "draft; pending owner review", "n_cases": len(rows),
            "routing_accuracy": sum(r["route_match"] for r in rows) / len(rows) if rows else None,
            "danger_escalation_accuracy": sum(r["escalation_match"] for r in danger) / len(danger) if danger else None,
            "n_errors": sum(bool(r["error"]) for r in rows),
            "step_fidelity": sum(judged) / len(judged) if judged else None, "n_storyboards_judged": len(judged),
            "judge": judge.JUDGE_MODEL, "judge_prompt": str(PROMPT.relative_to(PROMPT.parent.parent)),
            "total_live_cost_inr": round(sum(r["cost_inr"] for r in rows) + sum(x["fidelity"].get("cost_inr", 0) for x in lessons), 4),
            "lessons": lessons}


def traced_fidelity(item: dict, project: str) -> dict:
    from langsmith import traceable, get_current_run_tree

    board = item["storyboard"]
    @traceable(name="lesson_step_fidelity", project_name=project)
    def target():
        started = time.perf_counter()
        result = judge_steps(board, source_passages(board))
        usage = result.get("usage") or {}
        rt = get_current_run_tree()
        prenatal = board.get("stage") == "before_birth"
        metadata = trace_metadata(case_id=f"{board['lesson_id']}:v{board['version']}",
                dataset_version="prenatal_lessons_v1-draft" if prenatal else "lessons_golden_v1-draft",
                scenario_type="source_fidelity", pipeline_version="prenatal-lessons-v1" if prenatal else "lessons-v1", prompt_version=JUDGE_PROMPT_VERSION,
                model=judge.JUDGE_MODEL, expected_route=board["lesson_id"], predicted_route=board["lesson_id"],
                sources_cited=board["sources"], correct=result.get("faithful"),
                latency_ms=round((time.perf_counter() - started) * 1000), tokens_in=usage.get("tokens_in"),
                tokens_out=usage.get("tokens_out"), cost_inr=result["cost_inr"],
                error=None if result["status"] == "judged" else result["status"])
        result["trace_metadata"] = metadata
        if rt:
            rt.add_metadata(metadata)
        return result
    return target()


def _run(live=False, upload=False, meter=None) -> dict:
    cases, rows, lessons, spent = load_cases(), [], [], 0.0
    client, experiment = None, None
    if upload:
        from langsmith import Client
        client = Client()
        dataset = client.read_dataset(dataset_name=DATASET) if client.has_dataset(dataset_name=DATASET) else client.create_dataset(DATASET, description="Draft labels; owner review pending; separate from frozen Ask set")
        existing = {str(e.id) for e in client.list_examples(dataset_id=dataset.id)}
        for case in cases:
            eid = uuid.uuid5(uuid.NAMESPACE_URL, f"{DATASET}:{case['case_id']}")
            if str(eid) not in existing:
                client.create_example(example_id=eid, dataset_id=dataset.id, inputs={"question": case["input"]},
                                      outputs={k: case[k] for k in ("expected_lesson_id", "expected_escalate")}, metadata={"case_id": case["case_id"], "label_status": "draft"})
        project = client.create_project(PROJECT + "-" + str(uuid.uuid4())[:8], reference_dataset_id=dataset.id,
                                        description="Draft lesson routing; safety rules run before matcher")
        experiment = project.name
    if live:
        from langsmith import traceable
        for case in cases:
            if spent + 1.0 > CAP_INR:  # conservative envelope for one FAST request including catalogue
                raise RuntimeError(f"Budget stop before routing case {case['case_id']}: {spent:.2f} spent")
            @traceable(name="lesson_eval", project_name=experiment or PROJECT)
            def target():
                from langsmith import get_current_run_tree
                row = evaluate_case(case)
                run_tree = get_current_run_tree()
                if run_tree:
                    run_tree.add_metadata(trace_metadata(case_id=case["case_id"], dataset_version="lessons_golden_v1-draft",
                        scenario_type="danger" if case["expected_escalate"] == "Y" else "how_to", pipeline_version="lessons-v1",
                        prompt_version=library.MATCH_PROMPT_VERSION, model=llm.FAST, expected_escalate=case["expected_escalate"] == "Y",
                        predicted_escalate=row["escalate"], expected_route=case["expected_lesson_id"], predicted_route=row["lesson_id"] or "none",
                        refused=False, sources_cited=[], correct=row["route_match"] and row["escalation_match"],
                        latency_ms=None, tokens_in=row["tokens_in"], tokens_out=row["tokens_out"], cost_inr=row["cost_inr"], error=row["error"]))
                return row
            row = target(langsmith_extra={"reference_example_id": uuid.uuid5(uuid.NAMESPACE_URL, f"{DATASET}:{case['case_id']}")})
            spent += row["cost_inr"] if not row["error"] else max(1.0, row["cost_inr"])
            rows.append(row)
    for lesson_id in sorted(LESSONS):
        item = library.get(lesson_id)
        if not item:
            lessons.append({"lesson_id": lesson_id, "review": {"status": "no storyboard"}, "render": render_summary(LESSONS_DIR / lesson_id / "renders"),
                            "fidelity": {"status": "no storyboard", "faithful": None, "cost_inr": 0.0}})
            continue
        fidelity = {"status": "not run (offline)", "faithful": None, "cost_inr": 0.0}
        if live and spent + 2.0 <= CAP_INR:
            try:
                fidelity = traced_fidelity(item, experiment or PROJECT)
                spent += fidelity["cost_inr"]
            except Exception as exc:
                spent += 2.0  # retain conservative charge when provider usage was unavailable
                fidelity = {"status": type(exc).__name__, "faithful": None, "cost_inr": 2.0, "cost_estimated": True}
        lessons.append({"lesson_id": lesson_id, "version": item["storyboard"]["version"],
                        "review": review_summary(item["storyboard"], item["review"]), "render": render_summary(item["folder"] / "renders"), "fidelity": fidelity})
    result = {**summarize(rows, lessons), "live": live, "experiment": experiment, "budget_cap_inr": CAP_INR,
              "budget_accounted_inr": round(meter.spent if meter else spent, 4), "cases": rows}
    if meter:
        result["budget_ledger"] = meter.path.relative_to(GOLDEN.parent.parent).as_posix()
    path = RESULTS_DIR / f"lessons_v1_{date.today().isoformat()}{'' if live else '_offline'}_summary.json"
    path.write_text(json.dumps(result, indent=2, default=str) + "\n", encoding="utf-8")
    if rows:
        with path.with_name(path.name.replace("_summary.json", "_cases.csv")).open("w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=list(rows[0])); writer.writeheader(); writer.writerows(rows)
    if client:
        client.flush()
    return result


def refresh_fidelity(meter) -> dict:
    """Judge changed versions only; preserve original verdicts and all 39 routing results."""
    paths = sorted(p for p in RESULTS_DIR.glob("lessons_v1_*_summary.json") if "_offline_" not in p.name)
    if not paths:
        raise RuntimeError("Run the live draft evaluation before refreshing changed storyboards")
    path = paths[-1]
    result = json.loads(path.read_text(encoding="utf-8"))
    for prior in result["lessons"]:
        item = library.get(prior["lesson_id"])
        if not item or item["storyboard"]["version"] == prior.get("version"):
            continue
        verdict = traced_fidelity(item, result["experiment"] or PROJECT)
        result.setdefault("version_history", []).append(json.loads(json.dumps(prior)))
        prior.update(version=item["storyboard"]["version"], fidelity=verdict,
                     review=review_summary(item["storyboard"], item["review"]),
                     render=render_summary(item["folder"] / "renders"))
        # Persist each verdict immediately; a retry never repeats a completed version.
        result.update(summarize(result["cases"], result["lessons"]))
        result["budget_accounted_inr"] = round(meter.spent, 4)
        result["total_live_cost_inr"] = round(meter.spent, 4)
        result["cost_note"] = "Cumulative ledger includes earlier storyboard versions retained in version_history"
        path.write_text(json.dumps(result, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    return result


def run(live=False, upload=False, refresh=False) -> dict:
    if upload and not live:
        raise ValueError("Upload requires --live; offline runs never create empty experiments")
    if not live:
        return _run()
    from evals.budgeted_run import Meter

    meter = Meter(RESULTS_DIR / "lessons_v1_spend.json", cap=CAP_INR)
    sdk = llm.client()
    original, retries = sdk.chat.completions.create, sdk.max_retries
    sdk.max_retries = 0
    sdk.chat.completions.create = lambda **kw: meter.call(original, **kw)
    try:
        return refresh_fidelity(meter) if refresh else _run(live=True, upload=upload, meter=meter)
    finally:
        sdk.chat.completions.create = original
        sdk.max_retries = retries


def latest() -> dict:
    paths = sorted(RESULTS_DIR.glob("lessons_v1_*_summary.json"))
    live = [p for p in paths if "_offline_" not in p.name]
    return json.loads((live or paths)[-1].read_text(encoding="utf-8"))


if __name__ == "__main__":
    from dotenv import load_dotenv
    load_dotenv(Path(__file__).resolve().parent.parent / ".env")
    result = run(live="--live" in sys.argv, upload="--upload" in sys.argv, refresh="--refresh-fidelity" in sys.argv)
    print(json.dumps({k: v for k, v in result.items() if k not in ("cases", "lessons")}, indent=2))
