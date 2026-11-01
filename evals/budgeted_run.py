"""Resumable, per-request budgeted v7_vector experiment and the unchanged judge-v1.

Run only after setting NESTLING_MAIN_MODEL before Python starts. A checkpoint saves every
finished case, including its passages and judge verdict. --resume retries failed cases only.
Every provider response is charged by usage, including failed pipeline cases. Unknown provider
outcomes retain a conservative reservation. Schema rejections (400/422) are not generation.
"""

import json
import os
import hashlib
import csv
from concurrent.futures import ThreadPoolExecutor
from types import SimpleNamespace
import sys
import threading
import uuid
from datetime import date
from pathlib import Path

from evals import evaluators, judge
from nestling import golden, graph, llm
from nestling.tracing import PRICE_USD_PER_MTOK, USD_TO_INR, trace_metadata

VERSION = "v7_vector_safe"
CHECKPOINT = evaluators.RESULTS_DIR / f"phase3_{VERSION}_checkpoint.json"
LEDGER = evaluators.RESULTS_DIR / "phase3_v7_vector_spend.json"
PAUSE = evaluators.RESULTS_DIR / f"phase3_{VERSION}.pause"
PRICES = {**PRICE_USD_PER_MTOK, judge.JUDGE_MODEL: (0.20, 0.60)}
ASK_CAP_INR = 249.99  # below saved 250 cap and owner's precise +226.16 continuation limit


def write_json(path: Path, value: dict):
    """Replace a complete JSON file, so interruption cannot truncate the ledger."""
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(json.dumps(value, indent=2) + "\n", encoding="utf-8")
    os.replace(temporary, path)


def code_provenance() -> dict:
    root = Path(__file__).resolve().parent.parent
    paths = [root / "nestling" / name for name in
             ("guardian.py", "graph.py", "llm.py", "concierge.py", "retrieval.py", "verifier.py", "tracing.py")]
    paths += sorted((root / "nestling" / "agents").glob("*.py"))
    return {p.relative_to(root).as_posix(): hashlib.sha256(p.read_bytes()).hexdigest() for p in paths}


def prepare_safe() -> dict:
    """Seed only unaffected nonclinical outputs; never relabel old clinical answers."""
    if CHECKPOINT.exists():
        raise RuntimeError("Safe checkpoint already exists; inspect it and use --resume")
    prior_path = evaluators.RESULTS_DIR / "phase3_v7_vector_checkpoint.json"
    prior = json.loads(prior_path.read_text(encoding="utf-8"))
    prior["status"] = "interrupted before safety fixes; incomplete; not a benchmark"
    write_json(prior_path, prior)
    reused = {}
    for cid, saved in prior["cases"].items():
        out = saved["output"]
        if (out.get("agent") in {"guardian", "celebrate", "journal", "concierge"}
                and not out.get("error") and not saved.get("judge_error")):
            reused[cid] = {**saved, "provenance": {"origin_version": "v7_vector",
                "origin_experiment": prior.get("experiment"), "reused_unaffected_nonclinical": True,
                "note": "No medical/diet/insurance/Ready answer reused; frozen Guardian decisions checked unchanged"}}
    checkpoint = {"version": VERSION, "model": prior["model"], "cases": reused,
                  "code_provenance": code_provenance(), "status": "prepared; incomplete",
                  "prior_incomplete_experiment": prior.get("experiment")}
    write_json(CHECKPOINT, checkpoint)
    return {"version": VERSION, "reused_case_ids": sorted(reused), "remaining_cases": 104 - len(reused)}


def prepare_default() -> dict:
    if llm.MAIN != "deepseek-ai/DeepSeek-V4-Pro":
        raise RuntimeError("Default-model preparation requires owner MAIN DeepSeek-V4-Pro")
    prior = json.loads(CHECKPOINT.read_text(encoding="utf-8"))
    if prior["model"] != "zai-org/GLM-5.3":
        raise RuntimeError("Only the interrupted GLM checkpoint can be archived here")
    archive = CHECKPOINT.with_name("phase3_v7_vector_safe_glm_checkpoint.json")
    if archive.exists():
        raise RuntimeError("GLM archive already exists; inspect it before preparing another run")
    prior["status"] = "incomplete model validation failure: GLM verifier exhausted 3000 tokens with empty content"
    write_json(archive, prior)
    reused = {}
    for cid, saved in prior["cases"].items():
        out = saved["output"]
        if out.get("agent") in {"guardian", "concierge"} and not out.get("error") and not saved.get("judge_error"):
            reused[cid] = {**saved, "output": dict(out), "provenance": {
                "origin_version": VERSION, "origin_model_configuration": prior["model"],
                "origin_experiment": prior.get("experiment"), "reused_unaffected_nonclinical": True,
                "note": "Guardian/Concierge uses unchanged code rules and FAST only; no MAIN-generated answer reused"}}
    checkpoint = {"version": VERSION, "model": llm.MAIN, "cases": reused, "code_provenance": code_provenance(),
                  "status": "prepared default MAIN; incomplete", "prior_incomplete_experiment": prior.get("experiment")}
    write_json(CHECKPOINT, checkpoint)
    return {"model": llm.MAIN, "reused_case_ids": sorted(reused), "remaining_cases": 104 - len(reused)}


def pending_cases(checkpoint: dict, case_ids: list[str]) -> list[str]:
    """Reuse completed pipeline and judge outputs; retry errors and absent cases only."""
    return [cid for cid in case_ids if not (saved := checkpoint["cases"].get(cid))
            or saved["output"].get("error") or (saved.get("judge_error") and saved.get("judge_attempts", 0) < 3)
            or (saved.get("provenance", {}).get("reused_unaffected_nonclinical")
                and not (saved["provenance"].get("traced_in_variant") or saved["provenance"].get("recorded_in_variant")))
            or (needs_judge(saved["output"]) and saved.get("judge") is None and saved.get("judge_attempts", 0) < 3)]


def needs_judge(out: dict) -> bool:
    return bool(out.get("agent") in judge.JUDGED_AGENTS and not out.get("escalate")
                and not out.get("refused") and out.get("answer") and not out.get("error"))


def readiness() -> dict:
    """Inspect local progress without credentials, network requests or paid calls."""
    cases = golden.load()
    checkpoint = json.loads(CHECKPOINT.read_text(encoding="utf-8")) if CHECKPOINT.exists() else {"cases": {}}
    meter = Meter(LEDGER, cap=ASK_CAP_INR)
    ids = [c["case_id"] for c in cases]
    pending = pending_cases(checkpoint, ids)
    return {"version": VERSION, "model": checkpoint.get("model"), "n_frozen_cases": len(ids),
            "n_saved": len(checkpoint["cases"]), "n_complete": len(ids) - len(pending),
            "remaining_case_ids": pending, "accounted_inr": round(meter.spent, 4),
            "remaining_budget_inr": round(meter.cap - meter.spent, 4),
            "pause_requested": PAUSE.exists(),
            "status": "interrupted; no complete result" if pending else "ready to export"}


class Meter:
    def __init__(self, path: Path, cap=250.0):
        self.path, self.cap, self.lock = path, cap, threading.RLock()
        saved = json.loads(path.read_text(encoding="utf-8")) if path.exists() else {}
        self.cap = min(cap, saved.get("cap_inr", cap))
        self.rows = saved.get("calls", [])
        self.rows.extend({**p, "estimated": True, "error": "interrupted provider request; maximum reservation retained"}
                         for p in saved.get("pending", {}).values())
        self.pending = {}
        self.reserved = 0.0

    @property
    def spent(self):
        return sum(r["cost_inr"] for r in self.rows)

    def _write(self):
        write_json(self.path, {"cap_inr": self.cap, "accounted_inr": round(self.spent, 4), "pending": self.pending,
            "actual_response_cost_inr": round(sum(r["cost_inr"] for r in self.rows if not r.get("estimated")), 4),
            "calls": self.rows})

    def call(self, original, **kwargs):
        model = kwargs["model"]
        pin, pout = PRICES[model]  # unknown price is a hard error before a request
        # A UTF-8 byte is a conservative token bound; allow chat/schema framing too.
        inputs = len(json.dumps({k: kwargs.get(k) for k in ("messages", "response_format")}, ensure_ascii=False).encode("utf-8")) + 1024
        outputs = kwargs["max_tokens"]
        ceiling = (inputs * pin + outputs * pout) / 1e6 * USD_TO_INR
        call_id = str(uuid.uuid4())
        with self.lock:
            if self.spent + self.reserved + ceiling > self.cap:
                raise RuntimeError(f"budget stop: {self.spent:.4f} spent, {self.reserved:.4f} reserved, {ceiling:.4f} needed")
            self.reserved += ceiling
            self.pending[call_id] = {"model": model, "cost_inr": ceiling}
            self._write()
        row = None
        try:
            response = original(**kwargs)
            usage = llm.usage_of(response)
            row = {**usage, "cost_inr": round((usage["tokens_in"] * pin + usage["tokens_out"] * pout) / 1e6 * USD_TO_INR, 6)}
            return response
        except BaseException as exc:
            if getattr(exc, "status_code", None) not in (400, 422):
                row = {"model": model, "cost_inr": ceiling, "estimated": True, "error": type(exc).__name__}
            raise
        finally:
            with self.lock:
                self.reserved -= ceiling
                self.pending.pop(call_id, None)
                if row:
                    self.rows.append(row)
                self._write()


def metered_judge(question: str, out: dict) -> dict | None:
    if not needs_judge(out):
        return None
    passages = list(out.get("passages") or [])
    if out["agent"] == "ready":
        from nestling.agents.ready import checklist_text
        passages.append({"source_id": "NESTLING-CHECKLIST", "page_label": None, "text": checklist_text()})
    system, template = judge._prompt()
    text = "\n\n".join(f"[{p['source_id']}, p. {p.get('page_label')}] {p['text']}" for p in passages) or "(none)"
    response = llm.client().chat.completions.create(model=judge.JUDGE_MODEL, temperature=0, max_tokens=2000,
        response_format={"type": "json_object"}, messages=[{"role": "system", "content": system},
        {"role": "user", "content": template.replace("{question}", question).replace("{passages}", text).replace("{answer}", out["answer"])}])
    result = json.loads(response.choices[0].message.content)
    claims = result.get("claims", [])
    supported = sum(c.get("verdict") == "supported" for c in claims)
    return {**result, "score": round(supported / len(claims), 3) if claims else 1.0,
            "faithful": bool(result.get("faithful")) and supported == len(claims)}


def checkpoint_judge_rows(checkpoint: dict, examples) -> list[dict]:
    rows = []
    for ex in examples:
        saved = checkpoint["cases"].get(ex.metadata["case_id"])
        if not saved or (saved.get("judge") is None and not saved.get("judge_error")):
            continue
        out, verdict = saved["output"], saved.get("judge") or {}
        rows.append({"case_id": ex.metadata["case_id"], "scenario_type": ex.metadata["scenario_type"], "agent": out["agent"],
            "faithful": verdict.get("faithful"), "claim_support": verdict.get("score"),
            "unsupported": " | ".join(c["claim"] for c in verdict.get("claims", []) if c.get("verdict") != "supported"),
            "question": ex.inputs["question"], "answer": out["answer"], "error": saved.get("judge_error")})
    return sorted(rows, key=lambda r: r["case_id"])


def run_local(resume=False):
    """Same pipeline/scoring, with local metadata and exports while LangSmith quota is blocked."""
    from langsmith import tracing_context
    checkpoint = json.loads(CHECKPOINT.read_text(encoding="utf-8"))
    if checkpoint["model"] != llm.MAIN or checkpoint["code_provenance"] != code_provenance():
        raise RuntimeError("Model or pipeline changed; cannot mix local measurements")
    if not resume:
        raise RuntimeError("Local continuation requires --resume to preserve existing progress and spend")
    root = Path(__file__).resolve().parent.parent
    public_data = [root / "sources" / "registry.yaml", *sorted((root / "playbooks").glob("*.yaml"))]
    data_hashes = {p.relative_to(root).as_posix(): hashlib.sha256(p.read_bytes()).hexdigest() for p in public_data}
    if checkpoint.get("data_provenance", data_hashes) != data_hashes:
        raise RuntimeError("Public playbook/source data changed during this local run; inspect before resuming")
    checkpoint["data_provenance"] = data_hashes
    if not checkpoint.get("local_run_id"):
        checkpoint["langsmith_attempted_experiment"] = checkpoint.pop("experiment", None)
        checkpoint["local_run_id"] = f"local-nestling-ask-{VERSION}-{date.today().isoformat()}-{str(uuid.uuid4())[:8]}"
        checkpoint["experiment"] = checkpoint["local_run_id"]
    checkpoint["trace_upload_status"] = "pending: LangSmith monthly trace limit exceeded"
    checkpoint["status"] = "local measurement in progress; incomplete"
    write_json(CHECKPOINT, checkpoint)
    PAUSE.unlink(missing_ok=True)
    frozen = golden.load()
    by_id = {c["case_id"]: c for c in frozen}
    unfinished = set(pending_cases(checkpoint, list(by_id)))
    pending = [cid for cid in by_id if cid in unfinished or not checkpoint["cases"].get(cid, {}).get("local_trace_metadata")]
    meter = Meter(LEDGER, cap=ASK_CAP_INR)
    sdk = llm.client()
    original, retries = sdk.chat.completions.create, sdk.max_retries
    sdk.max_retries = 0
    sdk.chat.completions.create = lambda **kw: meter.call(original, **kw)
    lock = threading.RLock()

    def work(cid):
        if PAUSE.exists():
            return
        with tracing_context(enabled=False):
            case = by_id[cid]
            example = golden.to_example(case)
            old = checkpoint["cases"].get(cid) or {}
            out = old["output"] if old.get("output") and not old["output"].get("error") else graph.ask(
                example["inputs"]["question"], example["inputs"], version=VERSION)
            cached_verdict = old.get("judge") if not old.get("judge_error") else None
            provenance = {**(old.get("provenance") or {"origin_version": VERSION, "measured_current_code": True}),
                          "recorded_in_variant": True, "measurement_mode": "local; upload pending"}
            with lock:
                checkpoint["cases"][cid] = {"output": out, "judge": cached_verdict,
                    "judge_error": "pending judge" if needs_judge(out) and cached_verdict is None else None,
                    "provenance": provenance}
                write_json(CHECKPOINT, checkpoint)
            verdict, error = cached_verdict, None
            try:
                if verdict is None:
                    verdict = metered_judge(example["inputs"]["question"], out)
            except Exception as exc:
                error = f"{type(exc).__name__}: {str(exc)[:160]}"
            scores = evaluators.score_case(out, example["outputs"])
            metadata = trace_metadata(case_id=cid, dataset_version=golden.DATASET_VERSION, scenario_type=case["scenario_type"],
                pipeline_version=VERSION, prompt_version=graph.PROMPT_VERSIONS[VERSION], model=out["model"],
                expected_escalate=example["outputs"]["expected_escalate"], predicted_escalate=out["escalate"],
                expected_route="|".join(example["outputs"]["expected_route"]), predicted_route=out["route"], refused=out["refused"],
                sources_cited=out["sources_cited"], correct=scores["correct"], latency_ms=out["latency_ms"],
                tokens_in=out["tokens_in"], tokens_out=out["tokens_out"], cost_inr=out["cost_inr"], error=out["error"],
                retrieval_mode=out.get("retrieval_mode"))
            with lock:
                checkpoint["cases"][cid].update(judge=verdict, judge_error=error, local_trace_metadata=metadata)
                write_json(CHECKPOINT, checkpoint)
            if "budget stop" in str(error or out.get("error") or ""):
                PAUSE.touch()
            print(f"{cid}: local pipeline_error={bool(out.get('error'))} faithful={None if verdict is None else verdict.get('faithful')} accounted=Rs{meter.spent:.2f}", flush=True)

    try:
        with ThreadPoolExecutor(max_workers=2) as pool:
            list(pool.map(work, pending))
    finally:
        sdk.chat.completions.create = original
        sdk.max_retries = retries
    incomplete = pending_cases(checkpoint, list(by_id))
    if incomplete:
        raise RuntimeError(f"Local measurement incomplete; summary not published. Remaining: {', '.join(incomplete)}")
    checkpoint["status"] = "complete local measurement: 104 cases; LangSmith upload pending"
    write_json(CHECKPOINT, checkpoint)
    export_local(checkpoint, frozen)


def export_local(checkpoint: dict, frozen: list[dict]):
    """Adapt saved cases to the existing scorers; trace links stay blank until uploaded."""
    examples = [SimpleNamespace(**{k: golden.to_example(case)[k] for k in ("inputs", "outputs", "metadata")}) for case in frozen]
    class Results(list):
        experiment_name = checkpoint["local_run_id"]
        experiment_id = None
    results = Results({"example": ex, "run": SimpleNamespace(outputs=checkpoint["cases"][ex.metadata["case_id"]]["output"])} for ex in examples)
    rows = evaluators.case_rows(results, client=SimpleNamespace(get_run_url=lambda **kwargs: None))
    info = {**graph.run_info(VERSION), "run_date": date.today().isoformat(), "experiment": results.experiment_name,
        "measurement_mode": "local", "trace_upload_status": checkpoint["trace_upload_status"],
        "code_provenance": checkpoint["code_provenance"], "data_provenance": checkpoint["data_provenance"]}
    prefix = f"improved_{VERSION}_{date.today().isoformat()}"
    with (evaluators.RESULTS_DIR / f"{prefix}_cases.csv").open("w", newline="", encoding="utf-8") as stream:
        writer = csv.DictWriter(stream, fieldnames=list(rows[0])); writer.writeheader(); writer.writerows(rows)
    write_json(evaluators.RESULTS_DIR / f"{prefix}_summary.json", evaluators.summarize(rows, info))
    judged = checkpoint_judge_rows(checkpoint, examples)
    judge.export(judged, results.experiment_name)
    judge.calibration_sheet(judged, prefix=f"judge_calibration_{VERSION}")
    for filename, value in (("phase3_experiments.json", results.experiment_name), ("phase3_judge_round1.json", judge.summary(judged))):
        path = evaluators.RESULTS_DIR / filename
        saved = json.loads(path.read_text(encoding="utf-8")); saved[VERSION] = value; write_json(path, saved)
    print("LOCAL COMPLETE", results.experiment_name, "JUDGE", json.dumps(judge.summary(judged)), flush=True)


def run(resume=False, only=None, final_judge_attempt=False):
    from langsmith import Client, evaluate, get_current_run_tree, traceable
    client = Client()
    meter = Meter(LEDGER, cap=ASK_CAP_INR)
    checkpoint_lock = threading.RLock()
    checkpoint = json.loads(CHECKPOINT.read_text(encoding="utf-8")) if CHECKPOINT.exists() else {"version": VERSION, "model": llm.MAIN, "cases": {}}
    if checkpoint["model"] != llm.MAIN:
        raise RuntimeError("Cannot mix MAIN models in one checkpoint")
    if checkpoint.get("version") != VERSION:
        raise RuntimeError("Cannot mix pipeline variants in one checkpoint")
    provenance = code_provenance()
    if checkpoint.get("code_provenance", provenance) != provenance:
        raise RuntimeError("Pipeline code changed since this checkpoint; do not silently mix measurements")
    checkpoint["code_provenance"] = provenance
    if checkpoint["cases"] and not resume:
        raise RuntimeError("Checkpoint exists; use --resume (only failed or missing cases are retried)")
    frozen = golden.load()  # hash check before any provider request
    examples = list(client.list_examples(dataset_name=golden.LANGSMITH_DATASET))
    expected_examples = {c["case_id"]: golden.to_example(c) for c in frozen}
    if (len(examples) != len(expected_examples) or
            {ex.metadata["case_id"] for ex in examples} != set(expected_examples) or
            any(ex.inputs != expected_examples[ex.metadata["case_id"]]["inputs"] or
                ex.outputs != expected_examples[ex.metadata["case_id"]]["outputs"] for ex in examples)):
        raise RuntimeError("LangSmith dataset differs from the local frozen golden set; no paid calls made")
    remaining = set(pending_cases(checkpoint, list(expected_examples)))
    recorded_examples = set()
    if checkpoint.get("experiment"):
        project = client.read_project(project_name=checkpoint["experiment"])
        recorded_examples = {run.reference_example_id for run in client.list_runs(project_id=project.id, is_root=True)}
    pending = [ex for ex in examples if ex.metadata["case_id"] in remaining or ex.id not in recorded_examples]
    if only:
        pending = [ex for ex in pending if ex.metadata["case_id"] in only]
        if not pending:
            raise RuntimeError("Selected smoke case is already complete or absent; no repeated paid calls")
    sdk = llm.client()
    original, original_retries = sdk.chat.completions.create, sdk.max_retries
    sdk.max_retries = 0  # every potentially billed attempt must pass through Meter
    sdk.chat.completions.create = lambda **kw: meter.call(original, **kw)
    target_base = graph.make_target(VERSION)
    if resume:
        PAUSE.unlink(missing_ok=True)

    @traceable(name="nestling_ask")
    def target(inputs, metadata):
        if PAUSE.exists():
            raise RuntimeError("Pause requested: no new case dispatched; completed cases retained")
        cid = metadata["case_id"]
        old = checkpoint["cases"].get(cid)
        out = old["output"] if old and not old["output"].get("error") else target_base(inputs, metadata)
        cached_verdict = old.get("judge") if old and not old.get("judge_error") and not out.get("error") else None
        attempts = (old or {}).get("judge_attempts", 2 if final_judge_attempt and (old or {}).get("judge_error") else 0)
        judge_needed = needs_judge(out) and cached_verdict is None and attempts < 3
        # A judge timeout/interruption must never force a completed pipeline to run again.
        with checkpoint_lock:
            checkpoint["cases"][cid] = {"output": out, "judge": cached_verdict,
                                        "judge_error": "pending judge" if judge_needed else (old or {}).get("judge_error"),
                                        "judge_attempts": attempts + int(judge_needed),
                                        "provenance": {**((old or {}).get("provenance") or {
                                            "origin_version": VERSION, "measured_current_code": True}),
                                            "traced_in_variant": True}}
            write_json(CHECKPOINT, checkpoint)
        verdict, error = cached_verdict, (old or {}).get("judge_error") if attempts >= 3 else None
        try:
            if judge_needed:
                verdict = metered_judge(inputs["question"], out)
        except Exception as exc:
            error = f"{type(exc).__name__}: {str(exc)[:160]}"
        with checkpoint_lock:
            checkpoint["cases"][cid].update(judge=verdict, judge_error=error)
            write_json(CHECKPOINT, checkpoint)
        expected = golden.to_example(graph._golden_by_id()[cid])["outputs"]
        scores = evaluators.score_case(out, expected)
        rt = get_current_run_tree()
        if rt:
            rt.add_metadata(trace_metadata(case_id=cid, dataset_version=golden.DATASET_VERSION, scenario_type=metadata["scenario_type"],
                pipeline_version=VERSION, prompt_version=graph.PROMPT_VERSIONS[VERSION], model=out["model"], expected_escalate=expected["expected_escalate"],
                predicted_escalate=out["escalate"], expected_route="|".join(expected["expected_route"]), predicted_route=out["route"], refused=out["refused"],
                sources_cited=out["sources_cited"], correct=scores["correct"], latency_ms=out["latency_ms"], tokens_in=out["tokens_in"],
                tokens_out=out["tokens_out"], cost_inr=out["cost_inr"], error=out["error"]))
        print(f"{cid}: pipeline_error={bool(out.get('error'))} faithful={None if verdict is None else verdict.get('faithful')} accounted=Rs{meter.spent:.2f}", flush=True)
        return out

    try:
        results = evaluate(target, data=pending, evaluators=evaluators.EVALUATORS, max_concurrency=2, client=client, blocking=False,
            experiment=checkpoint.get("experiment"), experiment_prefix=None if checkpoint.get("experiment") else f"nestling-ask-improved-{VERSION}",
            metadata={**graph.run_info(VERSION), "retrieval_mode": "forced_vector_no_rerank", "budget_cap_inr": meter.cap},
            description=f"Explicit forced-vector safety-fixed variant; life-stage routing + strict verifier; MAIN={llm.MAIN}; lessons disabled")
        with checkpoint_lock:
            checkpoint["experiment"] = results.experiment_name
            write_json(CHECKPOINT, checkpoint)
        list(results)
    finally:
        sdk.chat.completions.create = original
        sdk.max_retries = original_retries
        client.flush()
    incomplete = pending_cases(checkpoint, list(expected_examples))
    if only:
        for cid in only:
            saved = checkpoint["cases"].get(cid) or {}
            out = saved.get("output") or {}
            print("SMOKE", cid, json.dumps({"sources": out.get("sources_cited"), "verification": out.get("verification"),
                "answer": out.get("answer"), "judge": saved.get("judge"), "judge_error": saved.get("judge_error"),
                "accounted_inr": round(meter.spent, 4)}, ensure_ascii=True), flush=True)
        return
    if incomplete:
        raise RuntimeError(f"Incomplete evaluation; summary not published. Resume cases: {', '.join(incomplete)}")
    n_judge_errors = sum(bool(saved.get("judge_error")) for saved in checkpoint["cases"].values())
    checkpoint["status"] = f"complete: 104 pipelines; eligible judge attempted; {n_judge_errors} judge errors after at most 3 attempts"
    checkpoint["judge_retry_policy"] = "judge-v1 maximum three attempts; persistent errors excluded and counted separately"
    write_json(CHECKPOINT, checkpoint)
    # Reconstruct exactly one latest output per frozen case; retries cannot double-count scores.
    stored = evaluators.StoredExperiment(checkpoint["experiment"], client=client)
    newest = {}
    for run in client.list_runs(project_id=stored.experiment_id, is_root=True):
        if run.reference_example_id not in newest or run.start_time > newest[run.reference_example_id].start_time:
            newest[run.reference_example_id] = run
    missing_traces = [ex.metadata["case_id"] for ex in examples if ex.id not in newest]
    if missing_traces:
        checkpoint["status"] = "complete outputs; LangSmith trace upload incomplete; no full export"
        write_json(CHECKPOINT, checkpoint)
        raise RuntimeError(f"Missing ingested case traces: {', '.join(missing_traces)}. Resume replays cached outputs/verdicts without paid calls.")
    for item in stored:
        item["run"] = newest.get(item["example"].id)
        if item["run"] and (saved := checkpoint["cases"].get(item["example"].metadata["case_id"])):
            item["run"].outputs = saved["output"]
            if saved.get("judge") is not None:
                for old in client.list_feedback(run_ids=[item["run"].id], feedback_key=["faithfulness"]):
                    client.delete_feedback(old.id)
                client.create_feedback(item["run"].id, key="faithfulness", score=int(saved["judge"]["faithful"]),
                    value=saved["judge"]["score"], comment=json.dumps(saved["judge"]["claims"])[:4000],
                    source_info={"judge": judge.JUDGE_MODEL, "version": judge.JUDGE_VERSION})
    paths = evaluators.export(stored, {**graph.run_info(VERSION), "retrieval_mode": "forced_vector_no_rerank"}, f"improved_{VERSION}")
    judge_rows = []
    for ex in examples:
        saved = checkpoint["cases"].get(ex.metadata["case_id"])
        if not saved or (saved["judge"] is None and not saved["judge_error"]):
            continue
        out, verdict = saved["output"], saved["judge"] or {}
        judge_rows.append({"case_id": ex.metadata["case_id"], "scenario_type": ex.metadata["scenario_type"], "agent": out["agent"],
            "faithful": verdict.get("faithful"), "claim_support": verdict.get("score"),
            "unsupported": " | ".join(c["claim"] for c in verdict.get("claims", []) if c.get("verdict") != "supported"),
            "question": ex.inputs["question"], "answer": out["answer"], "error": saved["judge_error"]})
    judge.export(sorted(judge_rows, key=lambda r: r["case_id"]), checkpoint["experiment"])
    judge.calibration_sheet(judge_rows, prefix=f"judge_calibration_{VERSION}")
    round1_path = evaluators.RESULTS_DIR / "phase3_judge_round1.json"
    round1 = json.loads(round1_path.read_text(encoding="utf-8"))
    round1[VERSION] = judge.summary(judge_rows)
    write_json(round1_path, round1)
    experiments_path = evaluators.RESULTS_DIR / "phase3_experiments.json"
    experiments = json.loads(experiments_path.read_text(encoding="utf-8"))
    experiments[VERSION] = checkpoint["experiment"]
    experiments_path.write_text(json.dumps(experiments, indent=1) + "\n", encoding="utf-8")
    print("EXPERIMENT", checkpoint["experiment"], "SUMMARY", paths[1], "JUDGE", json.dumps(judge.summary(judge_rows)), flush=True)


if __name__ == "__main__":
    if "--prepare-default" in sys.argv:
        print(json.dumps(prepare_default(), indent=2))
        sys.exit(0)
    if "--pause" in sys.argv:
        PAUSE.touch()
        print("Pause requested; active cases may finish, new cases will not start")
        sys.exit(0)
    if "--prepare-safe" in sys.argv:
        print(json.dumps(prepare_safe(), indent=2))
        sys.exit(0)
    if "--status" in sys.argv:
        print(json.dumps(readiness(), indent=2))
        sys.exit(0)
    from dotenv import load_dotenv
    load_dotenv(Path(__file__).resolve().parent.parent / ".env")
    only = [sys.argv[sys.argv.index("--only") + 1]] if "--only" in sys.argv else None
    if "--local" in sys.argv:
        run_local(resume="--resume" in sys.argv)
    else:
        run(resume="--resume" in sys.argv, only=only, final_judge_attempt="--final-judge-attempt" in sys.argv)
