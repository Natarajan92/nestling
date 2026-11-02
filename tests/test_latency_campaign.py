"""Authorization and storage isolation for new paid latency work; all offline."""
import json
from contextlib import contextmanager, nullcontext
from pathlib import Path
from types import SimpleNamespace

import pytest


def campaign():
    from evals import latency_run
    return latency_run


def approval():
    from nestling import golden
    return {"approved": True, "approved_on": "2026-11-02", "cap_inr": 180.0,
            "dataset_version": "golden_v3", "dataset_hash": golden.SHA256,
            "max_full_rounds": 3, "probe_cap_inr": 10.0, "langsmith_tracing": True,
            "scope": "FAST reasoning and retrieval warmup; frozen v3; same Qwen judge"}


def test_missing_approval_blocks_before_paid_runner_or_writes(tmp_path, monkeypatch):
    mod = campaign()
    monkeypatch.setattr(mod, "AUTH_PATH", tmp_path / "new-budget" / "authorization.json")
    monkeypatch.setattr(mod.base, "run", lambda *a, **k: pytest.fail("provider-capable runner called"))
    with pytest.raises(PermissionError, match="approval"):
        mod.run_round("latency1", "latency_fast_direct")
    assert not (tmp_path / "new-budget").exists()


@pytest.mark.parametrize("change", [{"approved": False}, {"cap_inr": 0}, {"cap_inr": True},
                                    {"cap_inr": float("nan")}, {"max_full_rounds": 4},
                                    {"dataset_hash": "wrong"}, {"langsmith_tracing": False},
                                    {"probe_cap_inr": 181}, {"approved_on": "yesterday"}])
def test_invalid_authorization_is_rejected(change):
    with pytest.raises((ValueError, PermissionError)):
        campaign().validate_authorization({**approval(), **change})


def test_unapproved_status_is_read_only(tmp_path, monkeypatch):
    mod = campaign()
    monkeypatch.setattr(mod, "AUTH_PATH", tmp_path / "authorization.json")
    monkeypatch.setattr(mod, "BUDGET_ROOT", tmp_path / "budget")
    monkeypatch.setattr(mod, "RESULTS_ROOT", tmp_path / "results")
    result = mod.status()
    assert result["authorized"] is False and result["paid_calls_made"] == 0
    assert not list(tmp_path.iterdir())


def test_configuration_is_scoped_and_old_ledger_unchanged(tmp_path):
    mod = campaign()
    original = {key: getattr(mod.base, key) for key in mod.OVERRIDES}
    results, budget = tmp_path / "results", tmp_path / "fresh-budget"
    results.mkdir()
    old = results / "spend.json"
    old.write_text('{"accounted_inr":183.9041}')
    saved = old.read_bytes()
    with mod.campaign_session(approval(), results_root=results, budget_root=budget):
        assert mod.base.RESULTS == budget and mod.base.CAP_INR == 180
        assert mod.base.ROOT == original["ROOT"]
        assert mod.base.round_directory("latency1") == results / "latency1"
        with pytest.raises(ValueError):
            mod.base.round_directory("round1")
        meter = mod.base.new_meter()
        assert meter.path == budget / "spend.json"
        assert json.loads((budget / "approval.json").read_text()) == approval()
    assert old.read_bytes() == saved
    assert all(getattr(mod.base, key) is value for key, value in original.items())


def test_configuration_restores_after_exception(tmp_path):
    mod = campaign()
    original = {key: getattr(mod.base, key) for key in mod.OVERRIDES}
    with pytest.raises(RuntimeError, match="interrupted"):
        with mod.campaign_session(approval(), results_root=tmp_path, budget_root=tmp_path / "budget"):
            raise RuntimeError("interrupted")
    assert all(getattr(mod.base, key) is value for key, value in original.items())


def test_non_candidate_version_or_unknown_round_rejected_before_writes(tmp_path, monkeypatch):
    mod = campaign()
    path = tmp_path / "authorization.json"
    path.write_text(json.dumps(approval()))
    monkeypatch.setattr(mod, "AUTH_PATH", path)
    monkeypatch.setattr(mod, "RESULTS_ROOT", tmp_path / "results")
    monkeypatch.setattr(mod, "BUDGET_ROOT", tmp_path / "budget")
    with pytest.raises(ValueError):
        mod.run_round("round1", "latency_fast_direct")
    with pytest.raises(ValueError):
        mod.run_round("latency1", "v7_vector_safe+lessons")
    assert not (tmp_path / "budget").exists()


def test_candidate_needs_immutable_plan_before_any_runner_call(tmp_path, monkeypatch):
    mod = campaign()
    path = tmp_path / "authorization.json"
    path.write_text(json.dumps(approval()))
    monkeypatch.setattr(mod, "AUTH_PATH", path)
    monkeypatch.setattr(mod, "RESULTS_ROOT", tmp_path / "results")
    monkeypatch.setattr(mod, "BUDGET_ROOT", tmp_path / "budget")
    monkeypatch.setattr(mod.base, "run", lambda *a, **k: pytest.fail("runner called before plan"))
    with pytest.raises((ValueError, FileNotFoundError), match="plan"):
        mod.run_round("latency1", "latency_fast_direct")
    assert not (tmp_path / "budget").exists()


@pytest.fixture
def offline_probe(tmp_path, monkeypatch):
    """Exercise the real probe/meter with only the transport and trace SDK mocked."""
    import langsmith
    from nestling import llm

    mod = campaign()
    budget = tmp_path / "budget"
    budget.mkdir()
    authorization = budget / "authorization.json"
    authorization.write_text(json.dumps(approval()))
    monkeypatch.setattr(mod, "AUTH_PATH", authorization)
    monkeypatch.setattr(mod, "BUDGET_ROOT", budget)
    monkeypatch.setattr(mod, "RESULTS_ROOT", tmp_path / "results")
    reference = json.loads((mod.base.ROOT / "evals/results/golden_v3/round1/checkpoint.json").read_text(encoding="utf-8"))
    monkeypatch.setenv("PINECONE_INDEX", reference["provenance"]["pinecone_index"])
    state = {"invalid": None, "calls": []}

    def create(**kwargs):
        state["calls"].append(kwargs)
        schema = kwargs["response_format"]["json_schema"]["schema"]
        role = "guardian" if "red_flags" in schema["properties"] else "concierge"
        data = {"red_flags": [], "unsafe": []} if role == "guardian" else {"route": "care"}
        content = json.dumps(data)
        if state["invalid"] == "malformed":
            content = "this is not JSON"
        elif state["invalid"] == "schema":
            content = json.dumps({"wrong_field": "visible but invalid"})
        return SimpleNamespace(model=llm.FAST,
            usage=SimpleNamespace(prompt_tokens=10, completion_tokens=5),
            choices=[SimpleNamespace(finish_reason="stop",
                message=SimpleNamespace(content=content, reasoning_content=""))])

    sdk = SimpleNamespace(max_retries=3,
        chat=SimpleNamespace(completions=SimpleNamespace(create=create)))
    monkeypatch.setattr(llm, "client", lambda: sdk)
    monkeypatch.setattr(langsmith, "Client", lambda: SimpleNamespace(flush=lambda: None))
    monkeypatch.setattr(langsmith, "traceable", lambda **kwargs: lambda fn: fn)
    monkeypatch.setattr(langsmith, "tracing_context", lambda **kwargs: nullcontext())
    monkeypatch.setattr(langsmith, "get_current_run_tree", lambda: None)
    return mod, state, sdk


@pytest.mark.parametrize("invalid", ["malformed", "schema"])
def test_probe_rejects_visible_but_invalid_json(offline_probe, invalid):
    mod, state, _ = offline_probe
    state["invalid"] = invalid
    result = mod.run_probe("none")
    assert result["passed"] is False


@pytest.mark.parametrize("change", ["authorization", "model", "source"])
def test_saved_probe_cannot_be_reused_after_identity_change(offline_probe, monkeypatch, change):
    from nestling import llm

    mod, state, _ = offline_probe
    assert mod.run_probe("none")["passed"] is True
    before = len(state["calls"])
    if change == "authorization":
        mod.AUTH_PATH.write_text(json.dumps({**approval(), "cap_inr": 179.0}))
    elif change == "model":
        monkeypatch.setattr(llm, "FAST", "changed/FAST-model")
    else:
        read_bytes = Path.read_bytes

        def changed_source(path):
            data = read_bytes(path)
            return data + b"\n# controlled review hash change\n" if path.name == "guardian.py" else data

        monkeypatch.setattr(Path, "read_bytes", changed_source)
    with pytest.raises((RuntimeError, ValueError), match="(?i)(probe|identity|provenance|changed|mismatch)"):
        mod.run_probe("none")
    assert len(state["calls"]) == before


@pytest.mark.parametrize("rejection", ["busy lock", "checkpoint identity"])
def test_warmup_waits_for_lock_and_valid_checkpoint(offline_probe, monkeypatch, rejection):
    mod, _, _ = offline_probe
    assert mod.run_probe("none")["passed"] is True
    monkeypatch.setattr(mod, "validate_plan", lambda *args: {})
    warmups = []
    monkeypatch.setattr(mod.retrieval, "warm_sources", lambda: warmups.append("network initialization"))

    if rejection == "busy lock":
        @contextmanager
        def reject_lock(*args):
            raise RuntimeError(rejection)
            yield

        monkeypatch.setattr(mod.base, "exclusive_run", reject_lock)
    else:
        def reject_checkpoint(*args, **kwargs):
            raise RuntimeError(rejection)

        monkeypatch.setattr(mod.base, "open_checkpoint", reject_checkpoint)
    with pytest.raises(RuntimeError, match=rejection):
        mod.run_round("latency1", "latency_fast_direct_warm", resume=True)
    assert warmups == []
    assert not (mod.RESULTS_ROOT / "latency1" / "startup.json").exists()


def test_probe_client_initialization_failure_restores_sdk(offline_probe, monkeypatch):
    import langsmith

    mod, _, sdk = offline_probe
    original_create, original_retries = sdk.chat.completions.create, sdk.max_retries

    def unavailable_client():
        raise RuntimeError("trace client initialization failed")

    monkeypatch.setattr(langsmith, "Client", unavailable_client)
    with pytest.raises(RuntimeError, match="trace client initialization failed"):
        mod.run_probe("none")
    assert sdk.chat.completions.create is original_create
    assert sdk.max_retries == original_retries


def test_full_round_spend_does_not_consume_separate_probe_subcap(offline_probe):
    mod, _, _ = offline_probe
    assert mod.run_probe("none")["passed"]
    ledger = mod.BUDGET_ROOT / "spend.json"
    saved = json.loads(ledger.read_text())
    saved["calls"].append({"model": "deepseek-ai/DeepSeek-V4-Pro", "cost_inr": 50,
                           "purpose": "full_evaluation"})
    ledger.write_text(json.dumps(saved))
    result = mod.run_probe("low")
    assert result["passed"] and result["accounted_probe_inr"] < approval()["probe_cap_inr"]
    assert any(row.get("purpose")=="full_evaluation" and row["cost_inr"]==50
               for row in json.loads(ledger.read_text())["calls"])


def test_changed_judge_protocol_blocks_before_probe_requests(offline_probe, monkeypatch):
    from copy import deepcopy
    mod, state, _ = offline_probe
    original = mod.base.provenance
    def changed(version):
        pinned = deepcopy(original(version))
        pinned["files"]["evals/judge.py"] = "different-protocol"
        return pinned
    monkeypatch.setattr(mod.base, "provenance", changed)
    with pytest.raises(ValueError, match="provenance"):
        mod.run_probe("none")
    assert state["calls"] == []
    assert not (mod.BUDGET_ROOT / "spend.json").exists()


def test_every_probe_ledger_write_already_tags_pending_and_charges(offline_probe, monkeypatch):
    from copy import deepcopy
    from evals import budgeted_run
    mod, _, _ = offline_probe
    original = budgeted_run.write_json
    snapshots = []
    def inspect_persistence(path, payload):
        if path.name == "spend.json":
            saved = deepcopy(payload)
            snapshots.append(saved)
            assert all(p.get("purpose")=="compatibility_probe" for p in saved.get("pending",{}).values())
            assert all(p.get("purpose")=="compatibility_probe" for p in saved.get("calls",[]))
        return original(path, payload)
    monkeypatch.setattr(budgeted_run, "write_json", inspect_persistence)
    assert mod.run_probe("none")["passed"]
    assert any(snapshot["pending"] for snapshot in snapshots)
    assert any(snapshot["calls"] for snapshot in snapshots)


def test_recovered_unknown_probe_reservation_stops_at_probe_subcap(offline_probe):
    mod, state, _ = offline_probe
    ledger = mod.BUDGET_ROOT / "spend.json"
    ledger.write_text(json.dumps({"cap_inr":180,"calls":[],"pending":{
        "interrupted": {"model":"deepseek-ai/DeepSeek-V4.1-Flash", "cost_inr":9.99,
                        "purpose":"compatibility_probe"}}}))
    with pytest.raises(RuntimeError, match="probe sub-cap"):
        mod.run_probe("none")
    assert state["calls"]==[]
    saved = json.loads(ledger.read_text())
    assert saved["accounted_inr"]>=9.99
    assert saved["calls"][0]["purpose"]=="compatibility_probe"


def test_transient_ledger_lock_retries_write_without_repeating_provider(offline_probe, monkeypatch):
    from evals import budgeted_run
    mod, state, _ = offline_probe
    original = budgeted_run.write_json
    failures = []
    def temporarily_locked(path, payload):
        if path.name=="spend.json" and payload.get("pending") and len(failures)<2:
            failures.append("file lock")
            raise PermissionError("transient Windows read lock")
        return original(path, payload)
    monkeypatch.setattr(budgeted_run, "write_json", temporarily_locked)
    monkeypatch.setattr(mod.time, "sleep", lambda _: None)
    assert mod.run_probe("none")["passed"]
    assert len(failures)==2 and len(state["calls"])==16
    assert budgeted_run.write_json is temporarily_locked


def test_permanent_ledger_lock_is_bounded_and_never_calls_provider(offline_probe, monkeypatch):
    from evals import budgeted_run
    mod, state, _ = offline_probe
    writes = []
    def locked(*args):
        writes.append(1)
        raise PermissionError("permanent lock")
    monkeypatch.setattr(budgeted_run, "write_json", locked)
    monkeypatch.setattr(mod.time, "sleep", lambda _: None)
    with pytest.raises(PermissionError, match="permanent lock"):
        mod.run_probe("none")
    assert 1<len(writes)<=6 and state["calls"]==[]
    assert budgeted_run.write_json is locked
