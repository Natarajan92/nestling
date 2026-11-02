"""Fresh owner-authorized latency campaign, reusing the unchanged v3 protocol.

Status is offline. Paid entry points require a separate authorization.json.
    uv run python -m evals.latency_run --status
    uv run python -m evals.latency_run --probe
    uv run python -m evals.latency_run --round latency1 --version latency_fast_direct
"""
from __future__ import annotations

import argparse
import hashlib
import json
import math
import threading
import time
from contextlib import contextmanager
from datetime import date
from pathlib import Path

from evals import v3_run as base
from nestling import golden, graph, retrieval

RESULTS_ROOT = base.RESULTS
BUDGET_ROOT = RESULTS_ROOT / "latency_budget"
AUTH_PATH = BUDGET_ROOT / "authorization.json"
ROUNDS = ("latency1", "latency2", "latency3")
CANDIDATES = frozenset({"latency_fast_direct", "latency_fast_low",
                        "latency_fast_direct_warm", "latency_fast_low_warm"})
SCOPE = "FAST reasoning and retrieval warmup; frozen v3; same Qwen judge"
OVERRIDES = ("ROOT", "RESULTS", "ROUNDS", "CAP_INR", "APPROVAL", "round_directory", "new_meter", "provenance", "exclusive_run", "write_json")
_CONFIG_LOCK = threading.RLock()


def validate_authorization(record):
    if not isinstance(record, dict) or record.get("approved") is not True:
        raise PermissionError("Fresh owner budget approval is required")
    if (record.get("dataset_version") != golden.DATASET_VERSION or
            record.get("dataset_hash") != golden.SHA256 or record.get("scope") != SCOPE or
            record.get("langsmith_tracing") is not True):
        raise ValueError("Authorization does not cover this frozen dataset and campaign")
    cap, probe = record.get("cap_inr"), record.get("probe_cap_inr")
    if (type(cap) not in (int, float) or not math.isfinite(cap) or cap <= 0 or
            type(probe) not in (int, float) or not math.isfinite(probe) or not 0 < probe <= cap):
        raise ValueError("Authorization needs finite positive budget caps")
    if type(record.get("max_full_rounds")) is not int or not 1 <= record["max_full_rounds"] <= len(ROUNDS):
        raise ValueError("Authorization exceeds the three-round campaign scope")
    date.fromisoformat(record.get("approved_on", ""))
    return record


def load_authorization():
    if not AUTH_PATH.is_file():
        raise PermissionError(f"Fresh owner budget approval is required: {AUTH_PATH}")
    return validate_authorization(json.loads(AUTH_PATH.read_text(encoding="utf-8")))


@contextmanager
def campaign_session(authorization, *, results_root=None, budget_root=None):
    """CLI-only scoped configuration; reused scoring/judging code stays byte-identical."""
    authorization = validate_authorization(authorization)
    results_root, budget_root = Path(results_root or RESULTS_ROOT), Path(budget_root or BUDGET_ROOT)
    with _CONFIG_LOCK:
        from evals import budgeted_run
        original = {key: getattr(base, key) for key in OVERRIDES}
        original_budget_write = budgeted_run.write_json
        allowed_rounds = ROUNDS[:authorization["max_full_rounds"]]

        def retry_write(writer):
            def write(path, payload):
                for attempt in range(6):
                    try:
                        return writer(path, payload)
                    except PermissionError:
                        if attempt==5:
                            raise
                        print(f"Retrying atomic JSON write: {Path(path).name}, attempt {attempt+1}/6", flush=True)
                        time.sleep(min(.05*2**attempt, .5))
            return write

        def directory(name, root=None):
            if name not in allowed_rounds or (root is not None and Path(root) != results_root):
                raise ValueError("Round/path is outside the authorized latency campaign")
            return results_root / name

        def meter(root=None):
            if root is not None and Path(root) != budget_root:
                raise ValueError("Budget path is outside the new latency authorization")
            return original["new_meter"](root=budget_root)

        def provenance(version):
            pinned = original["provenance"](version)
            for relative in ("evals/latency_run.py", "api/main.py"):
                pinned["files"][relative] = hashlib.sha256((base.ROOT / relative).read_bytes()).hexdigest()
            pinned["budget_authorization_sha256"] = hashlib.sha256(
                json.dumps(authorization, sort_keys=True).encode()).hexdigest()
            pinned["budget_session"] = "golden-v3-latency"
            return pinned

        try:
            base.RESULTS, base.ROUNDS = budget_root, allowed_rounds
            base.CAP_INR, base.APPROVAL = authorization["cap_inr"], authorization
            base.round_directory, base.new_meter, base.provenance = directory, meter, provenance
            base.write_json = retry_write(original["write_json"])
            budgeted_run.write_json = retry_write(original_budget_write)
            yield base
        finally:
            budgeted_run.write_json = original_budget_write
            for key, value in original.items():
                setattr(base, key, value)


def status(round_name="latency1"):
    if round_name not in ROUNDS:
        raise ValueError("Unknown latency round")
    if not AUTH_PATH.exists():
        return {"authorized": False, "paid_calls_made": 0,
                "proposed_cap_inr": 160, "round": round_name, "status": "awaiting fresh owner approval"}
    with campaign_session(load_authorization()):
        return {**base.status(round_name), "authorized": True}


def validate_plan(round_name, version, authorization):
    if round_name not in ROUNDS[:authorization["max_full_rounds"]] or version not in CANDIDATES:
        raise ValueError("Round/version is outside the authorized candidate scope")
    path = RESULTS_ROOT / round_name / "plan.json"
    if not path.is_file():
        raise ValueError(f"A recorded pre-call plan is required: {path}")
    plan = json.loads(path.read_text(encoding="utf-8"))
    required = ("hypothesis", "lever", "success_criterion", "revert_criterion", "comparison_base")
    if (plan.get("candidate_version") != version or plan.get("dataset_hash") != golden.SHA256 or
            any(not plan.get(key) for key in required)):
        raise ValueError("Pre-call plan does not bind the candidate, frozen hash and gates")
    base_name = plan["comparison_base"]
    previous = ("round1", *ROUNDS[:ROUNDS.index(round_name)])
    if base_name not in previous:
        raise ValueError("Plan comparison base must be an earlier retained round")
    latest = "round1"
    for earlier in ROUNDS[:ROUNDS.index(round_name)]:
        decision_path = RESULTS_ROOT / earlier / "decision.json"
        if decision_path.exists() and json.loads(decision_path.read_text(encoding="utf-8")).get("decision")=="keep":
            latest = earlier
    if base_name != latest:
        raise ValueError("Plan must compare with the latest retained candidate")
    folder = RESULTS_ROOT / base_name
    summary = json.loads((folder / "summary.json").read_text(encoding="utf-8"))
    decision = json.loads((folder / "decision.json").read_text(encoding="utf-8"))
    if not summary["progress"]["complete"] or decision.get("decision") != "keep":
        raise ValueError("Plan comparison base is not complete and retained")
    assert_comparable(base_name, version)
    return plan


def assert_comparable(base_name, version):
    from evals.v3_compare import _provenance_changes
    folder = (base.ROOT / "evals/results/golden_v3/round1" if base_name=="round1"
              else RESULTS_ROOT / base_name)
    reference = json.loads((folder / "checkpoint.json").read_text(encoding="utf-8"))
    base.validate_identity(reference, golden.load())
    _provenance_changes(reference["provenance"], base.provenance(version))


def probe_signature(authorization):
    from nestling import llm
    return {"dataset_hash": golden.SHA256, "fast_model": llm.FAST, "main_model": llm.MAIN,
            "judge_model": base.judge.JUDGE_MODEL, "judge_version": base.JUDGE_VERSION,
            "authorization_sha256": hashlib.sha256(json.dumps(authorization, sort_keys=True).encode()).hexdigest(),
            "files": {name: hashlib.sha256((base.ROOT / name).read_bytes()).hexdigest()
                      for name in ("evals/latency_run.py", "nestling/llm.py", "nestling/guardian.py",
                                   "nestling/concierge.py", "nestling/graph.py")}}


def validate_probe(result, effort, authorization):
    if result.get("effort") != effort or result.get("signature") != probe_signature(authorization):
        raise ValueError("Saved probe identity/provenance changed; do not reuse stale compatibility results")
    return result


def run_round(round_name, version, *, resume=False, only=None):
    authorization = load_authorization()
    golden.load()
    validate_plan(round_name, version, authorization)
    effort = graph.VERSIONS[version]["fast_reasoning_effort"]
    probe = BUDGET_ROOT / f"probe-{effort}.json"
    if not probe.exists():
        raise ValueError("A successful hosted-model compatibility probe is required first")
    result = validate_probe(json.loads(probe.read_text(encoding="utf-8")), effort, authorization)
    if not result.get("passed"):
        raise ValueError("Hosted-model compatibility probe did not pass")
    with campaign_session(authorization):
        original_exclusive = base.exclusive_run

        @contextmanager
        def prepared(root):
            with original_exclusive(root):
                folder = base.round_directory(round_name)
                checkpoint = folder / "checkpoint.json"
                if checkpoint.exists() or resume:
                    base.open_checkpoint(checkpoint, round_name, version, golden.load(),
                                         base.provenance(version), resume=resume)
                if graph.VERSIONS[version].get("prewarm_sources"):
                    started = time.perf_counter()
                    retrieval.warm_sources()
                    record = folder / "startup.json"
                    observations = json.loads(record.read_text(encoding="utf-8")) if record.exists() else []
                    observations.append({"recorded_at": base.now(), "elapsed_s": time.perf_counter()-started,
                                         "outcome": "ready", "excluded_from_response_timer": True})
                    base.write_json(record, observations)
                yield

        base.exclusive_run = prepared
        return base.run(round_name, version, resume, only)


def run_probe(effort="none"):
    """Small provider compatibility check, not a pipeline-quality benchmark."""
    from langsmith import Client, get_current_run_tree, traceable, tracing_context
    from jsonschema import ValidationError, validate
    from nestling import concierge, guardian, llm
    from nestling.tracing import trace_metadata

    authorization = load_authorization()
    if effort not in {"none", "low"}:
        raise ValueError("Probe effort must be none or low")
    cases = {c["case_id"]: c for c in golden.load()}
    path = BUDGET_ROOT / f"probe-{effort}.json"
    if path.exists():
        return validate_probe(json.loads(path.read_text(encoding="utf-8")), effort, authorization)
    version = "latency_fast_direct" if effort=="none" else "latency_fast_low"
    assert_comparable("round1", version)
    signature = probe_signature(authorization)
    with campaign_session(authorization), base.exclusive_run(BUDGET_ROOT):
        if path.exists():
            return validate_probe(json.loads(path.read_text(encoding="utf-8")), effort, authorization)
        meter = base.new_meter()
        first_probe_row = len(meter.rows)
        persist = meter._write

        def persist_probe():
            # Tag BEFORE every atomic ledger persistence, including reservations.
            # Recovery can then charge unknown probe outcomes to both caps.
            for pending in meter.pending.values():
                pending["purpose"] = "compatibility_probe"
            for row in meter.rows[first_probe_row:]:
                row["purpose"] = "compatibility_probe"
            persist()

        meter._write = persist_probe
        sdk = llm.client()
        create, retries = sdk.chat.completions.create, sdk.max_retries
        observed, results = [], []
        partial = BUDGET_ROOT / f"probe-{effort}-partial.json"
        if partial.exists():
            cached = json.loads(partial.read_text(encoding="utf-8"))
            if cached.get("signature") != signature:
                raise ValueError("Partial probe provenance changed; completed paid calls cannot be mixed")
            results = cached["results"]
        completed = {(r["case_id"], r["mode"]) for r in results}
        role_schema = {"value": None}

        def probe_spend():
            return sum(r["cost_inr"] for r in meter.rows if r.get("purpose")=="compatibility_probe")

        def measured(**kwargs):
            pin, pout = base.PRICES[kwargs["model"]]
            inputs = len(json.dumps({k: kwargs.get(k) for k in ("messages", "response_format")},
                                    ensure_ascii=False).encode())+1024
            ceiling = (inputs*pin+kwargs["max_tokens"]*pout)/1e6*base.USD_TO_INR
            if probe_spend()+ceiling > authorization["probe_cap_inr"]:
                raise RuntimeError("budget stop: compatibility probe sub-cap reached")
            began = time.perf_counter()
            response = meter.call(create, **kwargs)
            message = response.choices[0].message
            try:
                validate(json.loads(message.content or ""), role_schema["value"])
                valid = True
            except (ValueError, ValidationError):
                valid = False
            observed.append({"elapsed_s": time.perf_counter()-began,
                             "reasoning_chars": len(getattr(message, "reasoning_content", None) or ""),
                             "visible_chars": len(message.content or ""),
                             "finish_reason": response.choices[0].finish_reason, "schema_valid": valid,
                             "usage": llm.usage_of(response)})
            return response

        client = Client()
        project = f"nestling-golden-v3-latency-probe-{effort}"
        try:
            sdk.max_retries, sdk.chat.completions.create = 0, measured
            for cid in ("M06", "H16", "M08", "K01"):
                for mode in ("default", effort):
                    if (cid, mode) in completed:
                        continue
                    case = cases[cid]
                    observed.clear()
                    extra = {} if mode=="default" else {"reasoning_effort": effort}

                    @traceable(name="fast_reasoning_compatibility", run_type="chain")
                    def check():
                        role_schema["value"] = guardian.CLASSIFIER_SCHEMA
                        classifier = guardian.classify(case["input"], **extra)
                        decision = guardian.decide(case["input"], classifier)
                        role_schema["value"] = {**concierge.SCHEMA, "properties": {
                            "route": {"type": "string", "enum": [*concierge.ROUTES, "lessons"]}}}
                        route = concierge.route(case["input"], lessons=True, **extra)
                        row = {"case_id": cid, "mode": mode, "route": route["route"],
                               "escalate": decision.escalate, "component_error": route.get("error"),
                               "calls": list(observed)}
                        rt = get_current_run_tree()
                        if rt:
                            row["trace_id"] = str(rt.id)
                            rt.add_metadata({"predicted_route": route["route"], "predicted_escalate": decision.escalate})
                        return row

                    metadata = trace_metadata(case_id=cid, dataset_version=golden.DATASET_VERSION,
                        scenario_type=case["scenario_type"], pipeline_version="compatibility-probe",
                        prompt_version=f"fast-reasoning-{mode}", model=llm.FAST,
                        expected_escalate=case["expected_escalate"]=="Y",
                        expected_route=case["expected_route"])
                    with tracing_context(enabled=True, client=client, project_name=project,
                                         metadata={**metadata, "dataset_hash": golden.SHA256,
                                                   "evaluation_scope": "compatibility_only"}):
                        row = check()
                    results.append(row)
                    base.write_json(partial, {"signature": signature, "results": results})
            explicit = [r for r in results if r["mode"]==effort]
            passed = (len(explicit)==4 and all(not r["component_error"] and r["calls"] and
                all(c["schema_valid"] and c["visible_chars"] and c["finish_reason"]!="length" and
                    (effort!="none" or c["reasoning_chars"]==0) for c in r["calls"]) for r in explicit))
            result = {"probe_only": True, "effort": effort, "passed": passed,
                      "dataset_hash": golden.SHA256, "signature": signature,
                      "accounted_probe_inr": round(probe_spend(), 4),
                      "results": results}
            base.write_json(path, result)
            return result
        finally:
            sdk.chat.completions.create, sdk.max_retries = create, retries
            client.flush()


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--status", action="store_true")
    parser.add_argument("--probe", action="store_true")
    parser.add_argument("--effort", choices=("none", "low"), default="none")
    parser.add_argument("--round", choices=ROUNDS, default="latency1")
    parser.add_argument("--version", choices=sorted(CANDIDATES), default="latency_fast_direct")
    parser.add_argument("--resume", action="store_true")
    parser.add_argument("--only", nargs="+")
    args = parser.parse_args(argv)
    if args.status:
        result = status(args.round)
    else:
        from dotenv import find_dotenv, load_dotenv
        load_dotenv(find_dotenv(usecwd=True))
        result = run_probe(args.effort) if args.probe else run_round(
            args.round, args.version, resume=args.resume, only=args.only)
    print(json.dumps(result, indent=2))


if __name__=="__main__":
    main()
