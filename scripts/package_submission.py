"""Package saved Week 4 evidence offline; never calls providers or deploys.

Run after reports, plots, PDF, executed notebook and QA have been refreshed:
    uv run python scripts/package_submission.py
"""
from __future__ import annotations

import hashlib
import json
import os
import re
from datetime import datetime, timezone
from pathlib import Path
from zipfile import ZIP_DEFLATED, ZipFile

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "output/submission"
RESULTS = ROOT / "evals/results/golden_v3"


def round_folders():
    """Only measured Ask rounds; budgets, QA and partial work are not rounds."""
    def order(path):
        if path.name == "baseline":
            return (0, 0)
        match = re.fullmatch(r"(round|latency)(\d+)", path.name)
        return (1 if match[1] == "round" else 2, int(match[2]))
    return sorted((p for p in RESULTS.iterdir() if p.is_dir() and
                   (p.name == "baseline" or re.fullmatch(r"(?:round|latency)\d+", p.name))), key=order)


def complete_rounds():
    rounds = {}
    for folder in round_folders():
        path = folder / "summary.json"
        if not path.exists():
            continue
        summary = json.loads(path.read_text(encoding="utf-8-sig"))
        progress = summary["progress"]
        if not progress["complete"]:
            continue
        if progress["n_expected"] != 62 or progress["n_trace_verified"] != 62:
            raise ValueError(f"Incomplete/unverified evidence: {folder.name}")
        decision_path = folder / "decision.json"
        decision = json.loads(decision_path.read_text(encoding="utf-8-sig")) if decision_path.exists() else {}
        rounds[folder.name] = {"summary": summary, "decision": decision}
    if not {"baseline", "round1", "round2", "round3"} <= rounds.keys():
        raise ValueError("Historical baseline and rejected rounds must remain available")
    return rounds


def selected_round(rounds):
    return next((name for name in reversed(rounds) if rounds[name]["decision"].get("decision") == "keep"), "baseline")


def permitted(path):
    """Defense in depth after explicit input allowlists; never package passages."""
    relative = path.relative_to(ROOT)
    return (path.name.lower() not in {"checkpoint.json", "calibration.csv"}
            and path.suffix.lower() not in {".bundle", ".bak", ".backup", ".pem", ".key", ".p12", ".pfx"}
            and not any(part.lower() in {".git", ".superpowers", ".codex", "node_modules", ".next", "__pycache__", "archive", "backups"}
                        for part in relative.parts)
            and (not path.name.startswith(".env") or path.name == ".env.example"))


def check_secrets(files):
    """Reject literal configured secrets without printing their values."""
    values = {value.encode() for name, value in os.environ.items()
              if value and len(value) >= 12 and re.search(r"(?:API_KEY|TOKEN|SECRET|PASSWORD)$", name, re.I)}
    for path in files:
        if values and any(value in path.read_bytes() for value in values):
            raise ValueError(f"Configured secret found in submission input: {path.relative_to(ROOT)}")


def build() -> Path:
    from evals.v3_run import JUDGE_SCHEMA, JUDGE_SYSTEM, JUDGE_VERSION
    from evals.label_calibration import report as calibration_report
    from nestling import golden

    golden.load()
    rounds = complete_rounds()
    selected = selected_round(rounds)
    files = [ROOT / "README.md", ROOT / "pyproject.toml", ROOT / "uv.lock",
             ROOT / ".env.example", ROOT / "render.yaml",
             ROOT / "evals/golden_v3.csv", ROOT / "evals/golden_v3.freeze.json",
             ROOT / "evals/golden_v3.submission40.json",
             ROOT / "notebooks/09_v3_evaluation.ipynb",
             ROOT / "output/pdf/Nestling_Week4_Submission.pdf",
             ROOT / "output/pdf/Nestling_Week4_Submission.provenance.json"]
    files += [ROOT / "docs" / name for name in (
        "week4_report.md", "v3_evaluation_report.md", "SUBMISSION.md",
        "engineering_notes.md", "loom_script.md", "deploy_checklist.md",
        "submission_finish_prompt.md", "NESTLING_PLAN.md", "github_cleanup.md", "latency_improvements.md")]
    files += sorted((ROOT / "docs/media").glob("*.png"))
    files += sorted((ROOT / "nestling").rglob("*.py"))
    files += sorted((ROOT / "scripts").glob("*.py"))
    files += sorted((ROOT / "api").rglob("*.py"))
    files += sorted((ROOT / "tests").glob("*.py"))
    for folder in ("app", "components", "lib", "tests"):
        files += [p for p in (ROOT / "web" / folder).rglob("*") if p.suffix in (".ts", ".tsx", ".css", ".json", ".mjs")]
    files += [p for p in (ROOT / "web").iterdir() if p.is_file() and p.suffix in (".json", ".mjs", ".ts")]
    files += [p for p in (ROOT / "lessons").rglob("*") if p.suffix in (".yaml", ".json") and "renders" not in p.parts]
    files += [ROOT / "evals" / name for name in (
        "v3_run.py", "v3_compare.py", "evaluators.py", "judge.py", "judge_prompt.md",
        "budgeted_run.py", "plot_tradeoff.py", "label_calibration.py", "latency_run.py")]
    files += sorted((ROOT / "playbooks").glob("*.yaml"))
    files += [ROOT / "sources/registry.yaml"]
    files += [p for p in RESULTS.iterdir() if p.is_file() and p.suffix in (".csv", ".json")]
    for name in rounds:
        folder = RESULTS / name
        files += [folder / name for name in ("summary.json", "cases.csv", "judge.json")]
        files += [p for p in folder.iterdir() if p.is_file() and p.suffix in (".csv", ".json")
                  and p.name not in ("checkpoint.json", "calibration.csv")]
    files += [p for p in (RESULTS / "latency_budget").glob("*.json")]
    files += [p for p in (RESULTS / "qa").rglob("*") if p.is_file()]
    files = sorted(set(p for p in files if permitted(p)))
    for path in files:
        if not path.is_file() or not path.is_relative_to(ROOT):
            raise ValueError(f"Missing/invalid submission input: {path}")
        if not path.resolve().is_relative_to(ROOT.resolve()):
            raise ValueError(f"Submission input escapes workspace: {path}")
    check_secrets(files)
    pdf_path = ROOT / "output/pdf/Nestling_Week4_Submission.pdf"
    pdf_provenance = json.loads(pdf_path.with_suffix(".provenance.json").read_text(encoding="utf-8"))
    if (pdf_provenance["selected_retained_round"] != selected
            or pdf_provenance["completed_rounds"] != list(rounds)
            or pdf_provenance["pdf_sha256"] != hashlib.sha256(pdf_path.read_bytes()).hexdigest()):
        raise ValueError("Submission PDF is stale; rebuild from the final saved decisions")
    for relative, expected in pdf_provenance["inputs"].items():
        source = ROOT / relative
        if (not source.resolve().is_relative_to(ROOT.resolve()) or not source.is_file()
                or hashlib.sha256(source.read_bytes()).hexdigest() != expected["sha256"]):
            raise ValueError(f"Submission PDF input changed; rebuild after final evidence: {relative}")
    notebook = json.loads((ROOT / "notebooks/09_v3_evaluation.ipynb").read_text(encoding="utf-8"))
    code = [cell for cell in notebook["cells"] if cell["cell_type"] == "code"]
    if not code or any(cell.get("execution_count") is None for cell in code):
        raise ValueError("Submission notebook must be executed")
    if any(output.get("output_type") == "error" for cell in code for output in cell.get("outputs", [])):
        raise ValueError("Submission notebook has an execution error")
    OUT.mkdir(parents=True, exist_ok=True)
    calibration = calibration_report(RESULTS / "human_review.csv")
    pending = []
    pending += [f"Saved decision for completed {name}" for name, data in rounds.items()
                if name != "baseline" and data["decision"].get("decision") not in ("keep", "reject")]
    for name, data in rounds.items():
        if data["summary"]["run"]["dataset_hash"] != golden.SHA256:
            raise ValueError(f"Dataset hash mismatch: {name}")
    if any(calibration[key]["n_labelled"] < calibration[key]["n_total"]
           for key in ("faithfulness", "task_fulfillment")):
        pending.append("Owner's actual-output calibration (20 cases)")
    report_text = (ROOT / "docs/week4_report.md").read_text(encoding="utf-8")
    loom = re.search(r"^\*\*Loom:\*\*\s*(.*)$", report_text, re.MULTILINE)
    if not loom or not re.search(r"https?://", loom.group(1)):
        pending.append("Owner's Loom recording/link")
    manifest = {
        "created_at": datetime.now(timezone.utc).isoformat(),
        "dataset_version": golden.DATASET_VERSION, "dataset_sha256": golden.SHA256,
        "selected_round": selected, "completed_rounds": list(rounds),
        "completed_rejected_rounds": [name for name, data in rounds.items() if data["decision"].get("decision") == "reject"],
        "budget_provenance": [p.relative_to(ROOT).as_posix() for p in files
                              if p.name in ("spend.json", "authorization.json", "approval.json", "pricing.json")],
        "pending": pending,
        "excluded": ["Secrets and personal data", "Full copyrighted source passages/checkpoints",
                     "Private Git backups", "Lesson media (separate approved local render files)"],
        "files": [{"path": p.relative_to(ROOT).as_posix(), "bytes": p.stat().st_size,
                   "sha256": hashlib.sha256(p.read_bytes()).hexdigest()} for p in files],
    }
    target = OUT / "Nestling_Week4_Submission.zip"
    with ZipFile(target, "w", ZIP_DEFLATED) as archive:
        for path in files:
            archive.write(path, path.relative_to(ROOT).as_posix())
        archive.writestr("judge_protocol.json", json.dumps({
            "judge_version": JUDGE_VERSION, "system_prompt": JUDGE_SYSTEM,
            "response_schema": JUDGE_SCHEMA}, indent=2))
        archive.writestr("manifest.json", json.dumps(manifest, indent=2))
        archive.writestr("START_HERE.txt", (
            "Read output/pdf/Nestling_Week4_Submission.pdf and docs/week4_report.md.\n"
            f"All {len(rounds)} complete runs are included; {selected} is retained.\n"
            f"Pending: {', '.join(pending) if pending else 'No missing owner calibration or Loom link'}.\n"
            "Case CSVs contain answers/scores/trace links. Private LangSmith access may be needed.\n"
            "No secrets, personal data, source PDFs or private review checkpoints are included.\n"
            "This evidence pack includes application/evaluation source; media and private source PDFs are separate.\n"
            "Complete app source: https://github.com/Natarajan92/nestling (private access required).\n"))
    with ZipFile(target) as archive:
        if archive.testzip() is not None:
            raise ValueError("ZIP integrity check failed")
        for item in manifest["files"]:
            if hashlib.sha256(archive.read(item["path"])).hexdigest() != item["sha256"]:
                raise ValueError(f"Packaged hash mismatch: {item['path']}")
    (OUT / "manifest.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    print(f"Verified {len(files)} inputs: {target}")
    return target


if __name__ == "__main__":
    import sys
    sys.path.insert(0, str(ROOT))
    build()
